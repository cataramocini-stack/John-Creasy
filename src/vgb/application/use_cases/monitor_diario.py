"""Caso de uso principal: monitorar o Diario Oficial."""

import time
from datetime import date

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from vgb.application.ports.ai_analyzer import PDFAnalyzer
from vgb.application.ports.notifier import Notifier, SummaryPayload
from vgb.application.ports.repository import AnalysisRepository, EditionRepository
from vgb.application.ports.source import DocumentSource, SourceLink
from vgb.domain.entities import Analysis, Edition, Occurrence, SearchTarget
from vgb.domain.enums import AnalysisModel, EditionStatus
from vgb.domain.exceptions import LimiteTamanhoExcedidoError
from vgb.domain.value_objects import Cargo, HashSHA256, Nome
from vgb.infrastructure.config import Settings
from vgb.infrastructure.http.resilient_client import ResilientHTTPClient

logger = structlog.get_logger()


class MonitorDiarioUseCase:
    """Orquestra o fluxo completo:
    1. Coleta de links
    2. Download com deduplicacao por hash
    3. Analise por IA/OCR
    4. Notificacao se relevante
    5. Relatorio diario obrigatorio
    """

    def __init__(
        self,
        source: DocumentSource,
        analyzer: PDFAnalyzer,
        notifier: Notifier,
        edition_repo: EditionRepository,
        analysis_repo: AnalysisRepository,
        http_client: ResilientHTTPClient,
        settings: Settings,
    ) -> None:
        self._source = source
        self._analyzer = analyzer
        self._notifier = notifier
        self._edition_repo = edition_repo
        self._analysis_repo = analysis_repo
        self._http = http_client
        self._settings = settings
        self._target = SearchTarget(
            nome=Nome(settings.nome_busca),
            cargo=Cargo(settings.cargo_busca),
        )

    async def execute(self) -> dict[str, int]:
        import uuid
        from datetime import datetime
        from zoneinfo import ZoneInfo

        run_id = str(uuid.uuid4())[:8]
        structlog.contextvars.bind_contextvars(run_id=run_id)
        today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        start_time = time.monotonic()

        logger.info("monitor.start", run_id=run_id)

        stats: dict[str, int] = {
            "processed": 0,
            "new": 0,
            "found": 0,
            "notified": 0,
            "errors": 0,
        }

        try:
            links = await self._source.fetch_links(limit=self._settings.max_pdfs_per_run)
        except Exception as exc:
            logger.error("monitor.source_failed", error=str(exc))
            stats["errors"] += 1
            duration = time.monotonic() - start_time
            await self._send_summary(run_id, today, stats, duration)
            return stats

        logger.info("monitor.links_fetched", count=len(links))

        for link in links:
            try:
                result = await self._process_link(link)
                stats["processed"] += 1
                if result.get("is_new"):
                    stats["new"] += 1
                if result.get("found"):
                    stats["found"] += 1
                if result.get("notified"):
                    stats["notified"] += 1
            except Exception as exc:
                stats["errors"] += 1
                logger.error("monitor.link_failed", url=link.url, error=str(exc))

        duration = time.monotonic() - start_time
        logger.info("monitor.done", stats=stats, duration_seconds=duration)
        await self._send_summary(run_id, today, stats, duration)
        return stats

    async def _send_summary(self, run_id: str, today: date, stats: dict[str, int], duration: float = 0.0) -> None:
        try:
            payload = SummaryPayload(
                run_date=today,
                total_links=stats["processed"],
                total_new=stats["new"],
                total_found=stats["found"],
                total_errors=stats["errors"],
                duration_seconds=duration,
            )
            await self._notifier.send_summary(payload)
            logger.info("monitor.summary_sent", run_id=run_id)
        except Exception as exc:
            logger.error("monitor.summary_failed", run_id=run_id, error=str(exc))

    @retry(
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _process_link(self, link: SourceLink) -> dict[str, bool]:
        url = link.url
        title = link.title

        # Verifica se ja conhecemos pela URL
        existing = await self._edition_repo.get_by_url(url)
        if existing and existing.status == EditionStatus.PROCESSED:
            logger.info("monitor.skip_url", url=url, reason="already_processed")
            return {"is_new": False, "found": False, "notified": False}

        # HEAD para tamanho
        head_resp = await self._http.head(url)
        size = int(head_resp.headers.get("content-length", 0))
        max_size = self._settings.max_pdf_size_mb * 1024 * 1024
        if size > max_size:
            raise LimiteTamanhoExcedidoError(f"PDF {url} excede {self._settings.max_pdf_size_mb}MB")

        # Download
        logger.info("monitor.download.start", url=url, size=size)
        resp = await self._http.get(url)
        resp.raise_for_status()
        pdf_bytes = resp.content
        logger.info("monitor.download.done", url=url, bytes=len(pdf_bytes))

        # Deduplicacao por hash
        file_hash = HashSHA256.from_bytes(pdf_bytes)
        existing_hash = await self._edition_repo.get_by_hash(file_hash)
        if existing_hash:
            logger.info("monitor.skip_hash", url=url, hash=file_hash.valor[:16])
            return {"is_new": False, "found": False, "notified": False}

        # Cria ou atualiza edicao
        edition = existing or Edition.from_scrape(url=url, title=title)
        edition.mark_downloaded(pdf_bytes)
        edition = await self._edition_repo.save(edition)

        # Analise
        logger.info("monitor.analyze.start", url=url)
        ai_result = await self._analyzer.analyze(pdf_bytes, self._target)
        logger.info(
            "monitor.analyze.done",
            url=url,
            found=ai_result.found,
            model=ai_result.model_used,
            elapsed_ms=ai_result.processing_time_ms,
        )

        # Persiste analise
        analysis = Analysis(
            edition_id=edition.id,
            model_used=AnalysisModel(ai_result.model_used),
            raw_response=ai_result.raw_response,
            structured_result=ai_result.structured_result if hasattr(ai_result, "structured_result") else {},
            confidence_score=ai_result.confidence_score,
            processing_time_ms=ai_result.processing_time_ms,
            occurrences=[
                Occurrence(
                    type=o.type,
                    context_snippet=o.context,
                    page_hint=o.page,
                    confidence=o.confidence,
                )
                for o in ai_result.occurrences
            ],
        )
        analysis = await self._analysis_repo.save(analysis)
        edition.mark_processed()
        await self._edition_repo.save(edition)

        # Notifica se encontrou algo significativo
        notified = False
        significant = [o for o in analysis.occurrences if o.is_significant()]
        if significant:
            from vgb.application.ports.notifier import NotificationPayload

            payload = NotificationPayload(
                edition=edition,
                occurrences=significant,
                message_html="",
            )
            await self._notifier.send(payload)
            notified = True
            logger.info("monitor.notify.sent", url=url, occurrences=len(significant))

        return {
            "is_new": True,
            "found": analysis.has_occurrences(),
            "notified": notified,
        }
