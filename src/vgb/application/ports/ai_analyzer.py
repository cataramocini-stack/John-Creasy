"""Porta para analise de PDF por IA ou OCR."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field

from vgb.domain.entities import SearchTarget
from vgb.domain.enums import OccurrenceType


@dataclass(frozen=True, slots=True)
class AIOccurrence:
    """Ocorrencia retornada por um analisador."""

    type: OccurrenceType
    context: str
    page: int | None = None
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class AIAnalysisResult:
    """Resultado completo da analise de um PDF."""

    found: bool
    occurrences: Sequence[AIOccurrence] = field(default_factory=tuple)
    raw_response: str = ""
    model_used: str = "unknown"
    confidence_score: float = 0.0
    processing_time_ms: int = 0


class PDFAnalyzer(ABC):
    """Contrato para analisadores de PDF."""

    @abstractmethod
    async def analyze(self, pdf_bytes: bytes, target: SearchTarget) -> AIAnalysisResult:
        """Analisa um PDF em busca do nome e cargo configurados."""
        ...
