"""Porta para coleta de fontes do Diario Oficial."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SourceLink:
    """Link de PDF coletado da fonte."""

    title: str
    url: str
    published_at: datetime | None = None


class DocumentSource(ABC):
    """Contrato para coleta de links de PDFs do Diario Oficial."""

    @abstractmethod
    async def fetch_links(self, limit: int = 10) -> Sequence[SourceLink]:
        """Retorna links de PDFs encontrados na fonte."""
        ...
