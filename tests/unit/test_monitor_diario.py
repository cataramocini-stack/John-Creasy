"""Testes unitarios do MonitorDiarioUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from vgb.application.ports.ai_analyzer import AIAnalysisResult, AIOccurrence
from vgb.application.ports.source import SourceLink
from vgb.application.use_cases.monitor_diario import MonitorDiarioUseCase
from vgb.domain.enums import ActType, AnalysisModel, OccurrenceType
from vgb.infrastructure.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        nome_busca="Maria",
        cargo_busca="Engenheiro",
        telegram_token="fake",
        telegram_chat_id="123",
        diario_url="https://example.gov.br/jornal/",
        diario_base_url="https://example.gov.br",
    )


@pytest.fixture
def use_case(settings: Settings) -> MonitorDiarioUseCase:
    source = AsyncMock()
    analyzer = AsyncMock()
    notifier = AsyncMock()
    edition_repo = AsyncMock()
    analysis_repo = AsyncMock()
    http_client = AsyncMock()

    return MonitorDiarioUseCase(
        source=source,
        analyzer=analyzer,
        notifier=notifier,
        edition_repo=edition_repo,
        analysis_repo=analysis_repo,
        http_client=http_client,
        settings=settings,
    )


def _make_response(content: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


class TestExecute:
    async def test_fluxo_com_ocorrencia(self, use_case: MonitorDiarioUseCase) -> None:
        use_case._source.fetch_links.return_value = [SourceLink(title="DO 01", url="https://exemplo.gov.br/do.pdf")]
        use_case._edition_repo.get_by_url.return_value = None
        use_case._http.head.return_value = MagicMock(headers={"content-length": "1024"})
        use_case._http.get.return_value = _make_response(b"pdfdata")
        use_case._edition_repo.get_by_hash.return_value = None
        use_case._analyzer.analyze.return_value = AIAnalysisResult(
            found=True,
            occurrences=[
                AIOccurrence(
                    type=OccurrenceType.BOTH,
                    context="NOMEIA MARIA",
                    confidence=0.95,
                    act_type=ActType.NOMEACAO,
                )
            ],
            model_used=AnalysisModel.GEMINI_25_FLASH.value,
            processing_time_ms=1234,
        )
        use_case._analysis_repo.save.side_effect = lambda a: a

        stats = await use_case.execute()

        assert stats["processed"] == 1
        assert stats["new"] == 1
        assert stats["found"] == 1
        assert stats["notified"] == 1
        use_case._notifier.send.assert_awaited_once()
        use_case._notifier.send_summary.assert_awaited_once()

    async def test_fluxo_sem_ocorrencia(self, use_case: MonitorDiarioUseCase) -> None:
        use_case._source.fetch_links.return_value = [SourceLink(title="DO 01", url="https://exemplo.gov.br/do.pdf")]
        use_case._edition_repo.get_by_url.return_value = None
        use_case._http.head.return_value = MagicMock(headers={"content-length": "1024"})
        use_case._http.get.return_value = _make_response(b"pdfdata")
        use_case._edition_repo.get_by_hash.return_value = None
        use_case._analyzer.analyze.return_value = AIAnalysisResult(
            found=False,
            occurrences=[],
            model_used=AnalysisModel.GEMINI_25_FLASH.value,
            processing_time_ms=500,
        )
        use_case._analysis_repo.save.side_effect = lambda a: a

        stats = await use_case.execute()

        assert stats["processed"] == 1
        assert stats["new"] == 1
        assert stats["found"] == 0
        assert stats["notified"] == 0
        use_case._notifier.send.assert_not_called()
        use_case._notifier.send_summary.assert_awaited_once()

    async def test_falha_de_link_nao_quebra_outros(self, use_case: MonitorDiarioUseCase) -> None:
        use_case._source.fetch_links.return_value = [
            SourceLink(title="DO 01", url="https://exemplo.gov.br/do1.pdf"),
            SourceLink(title="DO 02", url="https://exemplo.gov.br/do2.pdf"),
        ]
        # Primeiro link: falha no download
        use_case._edition_repo.get_by_url.side_effect = [None, None]
        use_case._http.head.side_effect = [
            MagicMock(headers={"content-length": "1024"}),
            Exception("Timeout"),
        ]
        use_case._http.get.return_value = _make_response(b"pdfdata")
        use_case._edition_repo.get_by_hash.return_value = None
        use_case._analyzer.analyze.return_value = AIAnalysisResult(
            found=False,
            occurrences=[],
            model_used=AnalysisModel.OCR_LOCAL.value,
            processing_time_ms=100,
        )

        stats = await use_case.execute()

        assert stats["processed"] == 1
        assert stats["errors"] == 1
        use_case._notifier.send_summary.assert_awaited_once()

    async def test_source_falha_envia_resumo(self, use_case: MonitorDiarioUseCase) -> None:
        use_case._source.fetch_links.side_effect = Exception("Site fora do ar")

        stats = await use_case.execute()

        assert stats["errors"] == 1
        use_case._notifier.send_summary.assert_awaited_once()
        use_case._notifier.send.assert_not_called()
