"""Analisador composto com fallback chain."""

import structlog

from vgb.application.ports.ai_analyzer import AIAnalysisResult, PDFAnalyzer
from vgb.domain.entities import SearchTarget
from vgb.domain.exceptions import AnaliseIndisponivelError
from vgb.infrastructure.ai.gemini_analyzer import GeminiAnalyzer
from vgb.infrastructure.ai.ocr_analyzer import OcrAnalyzer
from vgb.infrastructure.ai.openrouter_analyzer import OpenRouterAnalyzer
from vgb.infrastructure.config import Settings

logger = structlog.get_logger()


class CompositeAnalyzer(PDFAnalyzer):
    """Orquestra analisadores em cadeia de fallback:
    1. Gemini
    2. OpenRouter
    3. OCR local (sempre disponivel)
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._analyzers: list[tuple[str, PDFAnalyzer]] = []

        # Tenta inicializar cada analisador; falhas de config nao quebram a cadeia
        try:
            gemini = GeminiAnalyzer(settings)
            self._analyzers.append(("gemini", gemini))
        except AnaliseIndisponivelError as exc:
            logger.warning("composite.gemini.unavailable", reason=str(exc))

        try:
            openrouter = OpenRouterAnalyzer(settings)
            self._analyzers.append(("openrouter", openrouter))
        except AnaliseIndisponivelError as exc:
            logger.warning("composite.openrouter.unavailable", reason=str(exc))

        # OCR local sempre disponivel
        self._analyzers.append(("ocr", OcrAnalyzer(max_pages=settings.max_pages_to_analyze)))

    async def analyze(self, pdf_bytes: bytes, target: SearchTarget) -> AIAnalysisResult:
        last_error: Exception | None = None

        for name, analyzer in self._analyzers:
            try:
                result = await analyzer.analyze(pdf_bytes, target)
                logger.info(
                    "composite.success",
                    analyzer=name,
                    found=result.found,
                    occurrences=len(result.occurrences),
                )
                return result
            except Exception as exc:
                last_error = exc
                logger.warning("composite.fallback", analyzer=name, error=str(exc))
                continue

        logger.error("composite.all_failed", analyzers=[n for n, _ in self._analyzers])
        raise AnaliseIndisponivelError(f"Todos os analisadores falharam. Ultimo erro: {last_error}") from last_error
