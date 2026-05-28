"""Entidades do dominio."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Self

from vgb.domain.enums import AnalysisModel, EditionStatus, OccurrenceType
from vgb.domain.value_objects import Cargo, HashSHA256, Nome


@dataclass
class Edition:
    """Edicao do Diario Oficial."""

    id: int | None = None
    url: str = ""
    title: str = ""
    published_at: datetime | None = None
    hash: HashSHA256 | None = None
    size_bytes: int = 0
    status: EditionStatus = EditionStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_scrape(
        cls,
        url: str,
        title: str,
        published_at: datetime | None = None,
    ) -> Self:
        return cls(url=url, title=title, published_at=published_at, status=EditionStatus.PENDING)

    def mark_downloaded(self, data: bytes) -> None:
        self.hash = HashSHA256.from_bytes(data)
        self.size_bytes = len(data)
        self.status = EditionStatus.ANALYZING
        self.updated_at = datetime.now(UTC)

    def mark_processed(self) -> None:
        self.status = EditionStatus.PROCESSED
        self.updated_at = datetime.now(UTC)

    def mark_failed(self) -> None:
        self.status = EditionStatus.FAILED
        self.updated_at = datetime.now(UTC)


@dataclass
class Occurrence:
    """Ocorrencia encontrada em uma edicao."""

    id: int | None = None
    analysis_id: int | None = None
    type: OccurrenceType = OccurrenceType.NOME
    context_snippet: str = ""
    page_hint: int | None = None
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_significant(self, threshold: float = 0.7) -> bool:
        return self.confidence >= threshold


@dataclass
class Analysis:
    """Resultado da analise de uma edicao."""

    id: int | None = None
    edition_id: int | None = None
    model_used: AnalysisModel = AnalysisModel.OCR_LOCAL
    raw_response: str = ""
    structured_result: dict[str, object] = field(default_factory=dict)
    confidence_score: float = 0.0
    processing_time_ms: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    occurrences: list[Occurrence] = field(default_factory=list)

    def has_occurrences(self) -> bool:
        return len(self.occurrences) > 0

    def best_occurrence(self) -> Occurrence | None:
        if not self.occurrences:
            return None
        return max(self.occurrences, key=lambda o: o.confidence)


@dataclass
class SearchTarget:
    """Alvos de busca configurados."""

    nome: Nome
    cargo: Cargo

    def matches_nome(self, text: str) -> bool:
        return self.nome.normalizado() in text.upper()

    def matches_cargo(self, text: str) -> bool:
        return self.cargo.normalizado() in text.upper()
