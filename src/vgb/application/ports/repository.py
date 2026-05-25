"""Porta para persistencia de dados."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from vgb.domain.entities import Analysis, Edition
from vgb.domain.value_objects import HashSHA256


class EditionRepository(ABC):
    """Contrato para repositorio de edicoes."""

    @abstractmethod
    async def get_by_hash(self, hash_: HashSHA256) -> Edition | None:
        """Busca edicao pelo hash do conteudo."""
        ...

    @abstractmethod
    async def get_by_url(self, url: str) -> Edition | None:
        """Busca edicao pela URL."""
        ...

    @abstractmethod
    async def save(self, edition: Edition) -> Edition:
        """Persiste uma edicao (insert ou update)."""
        ...

    @abstractmethod
    async def list_recent(self, limit: int = 20) -> Sequence[Edition]:
        """Lista edicoes mais recentes."""
        ...


class AnalysisRepository(ABC):
    """Contrato para repositorio de analises."""

    @abstractmethod
    async def save(self, analysis: Analysis) -> Analysis:
        """Persiste uma analise e suas ocorrencias."""
        ...

    @abstractmethod
    async def get_by_edition(self, edition_id: int) -> Analysis | None:
        """Busca analise por edicao."""
        ...
