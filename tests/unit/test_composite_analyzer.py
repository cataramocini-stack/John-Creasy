"""Testes unitarios do CompositeAnalyzer (fallback chain)."""

from unittest.mock import AsyncMock, patch

import pytest

from vgb.application.ports.ai_analyzer import AIAnalysisResult, AIOccurrence
from vgb.domain.entities import SearchTarget
from vgb.domain.enums import OccurrenceType
from vgb.domain.value_objects import Cargo, Nome
from vgb.infrastructure.ai.composite_analyzer import CompositeAnalyzer
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
def target() -> SearchTarget:
    return SearchTarget(nome=Nome("Maria"), cargo=Cargo("Engenheiro"))


class TestFallbackChain:
    async def test_gemini_sucesso_nao_tenta_fallback(self, settings: Settings, target: SearchTarget) -> None:
        with (
            patch("vgb.infrastructure.ai.composite_analyzer.GeminiAnalyzer") as mock_gemini,
            patch("vgb.infrastructure.ai.composite_analyzer.OpenRouterAnalyzer") as mock_or,
            patch("vgb.infrastructure.ai.composite_analyzer.OcrAnalyzer") as mock_ocr,
        ):
            gemini_instance = AsyncMock()
            gemini_instance.analyze.return_value = AIAnalysisResult(
                found=True,
                occurrences=[
                    AIOccurrence(
                        type=OccurrenceType.NOME,
                        context="NOMEIA MARIA",
                        confidence=0.9,
                    )
                ],
                model_used="gemini-2.5-flash",
            )
            mock_gemini.return_value = gemini_instance
            mock_or.return_value = AsyncMock()
            mock_ocr.return_value = AsyncMock()

            analyzer = CompositeAnalyzer(settings)
            result = await analyzer.analyze(b"pdf", target)

            assert result.found is True
            assert result.model_used == "gemini-2.5-flash"
            gemini_instance.analyze.assert_awaited_once()

    async def test_fallback_para_openrouter(self, settings: Settings, target: SearchTarget) -> None:
        with (
            patch("vgb.infrastructure.ai.composite_analyzer.GeminiAnalyzer") as mock_gemini,
            patch("vgb.infrastructure.ai.composite_analyzer.OpenRouterAnalyzer") as mock_or,
            patch("vgb.infrastructure.ai.composite_analyzer.OcrAnalyzer") as mock_ocr,
        ):
            gemini_instance = AsyncMock()
            gemini_instance.analyze.side_effect = Exception("Gemini down")
            mock_gemini.return_value = gemini_instance

            or_instance = AsyncMock()
            or_instance.analyze.return_value = AIAnalysisResult(
                found=True,
                occurrences=[
                    AIOccurrence(
                        type=OccurrenceType.CARGO,
                        context="Cargo de Engenheiro",
                        confidence=0.8,
                    )
                ],
                model_used="openrouter-free",
            )
            mock_or.return_value = or_instance
            mock_ocr.return_value = AsyncMock()

            analyzer = CompositeAnalyzer(settings)
            result = await analyzer.analyze(b"pdf", target)

            assert result.found is True
            assert result.model_used == "openrouter-free"
            gemini_instance.analyze.assert_awaited_once()
            or_instance.analyze.assert_awaited_once()

    async def test_fallback_para_ocr(self, settings: Settings, target: SearchTarget) -> None:
        with (
            patch("vgb.infrastructure.ai.composite_analyzer.GeminiAnalyzer") as mock_gemini,
            patch("vgb.infrastructure.ai.composite_analyzer.OpenRouterAnalyzer") as mock_or,
            patch("vgb.infrastructure.ai.composite_analyzer.OcrAnalyzer") as mock_ocr,
        ):
            gemini_instance = AsyncMock()
            gemini_instance.analyze.side_effect = Exception("Gemini down")
            mock_gemini.return_value = gemini_instance

            or_instance = AsyncMock()
            or_instance.analyze.side_effect = Exception("OpenRouter down")
            mock_or.return_value = or_instance

            ocr_instance = AsyncMock()
            ocr_instance.analyze.return_value = AIAnalysisResult(
                found=False,
                occurrences=[],
                model_used="ocr-local",
            )
            mock_ocr.return_value = ocr_instance

            analyzer = CompositeAnalyzer(settings)
            result = await analyzer.analyze(b"pdf", target)

            assert result.found is False
            assert result.model_used == "ocr-local"
