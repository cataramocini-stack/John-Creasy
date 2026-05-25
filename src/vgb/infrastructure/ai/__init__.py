"""Analisadores de PDF: Gemini, OpenRouter fallback, OCR local."""

from vgb.infrastructure.ai.composite_analyzer import CompositeAnalyzer
from vgb.infrastructure.ai.gemini_analyzer import GeminiAnalyzer
from vgb.infrastructure.ai.ocr_analyzer import OcrAnalyzer
from vgb.infrastructure.ai.openrouter_analyzer import OpenRouterAnalyzer

__all__ = ["CompositeAnalyzer", "GeminiAnalyzer", "OpenRouterAnalyzer", "OcrAnalyzer"]
