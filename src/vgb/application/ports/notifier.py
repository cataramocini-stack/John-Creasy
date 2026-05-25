"""Porta para envio de notificacoes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from vgb.domain.entities import Edition, Occurrence


@dataclass(frozen=True, slots=True)
class NotificationPayload:
    """Dados para notificacao de ocorrencia."""

    edition: Edition
    occurrences: list[Occurrence]
    message_html: str


@dataclass(frozen=True, slots=True)
class SummaryPayload:
    """Dados para relatorio diario de resumo."""

    run_date: date
    total_links: int
    total_new: int
    total_found: int
    total_errors: int
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class AlertPayload:
    """Dados para alerta critico de falha do sistema."""

    run_date: date
    error_summary: str
    traceback_snippet: str


class Notifier(ABC):
    """Contrato para notificadores."""

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> str:
        """Envia notificacao de ocorrencia e retorna ID ou confirmacao."""
        ...

    @abstractmethod
    async def send_summary(self, payload: SummaryPayload) -> str:
        """Envia relatorio diario de resumo."""
        ...

    @abstractmethod
    async def send_alert(self, payload: AlertPayload) -> str:
        """Envia alerta critico de falha do sistema."""
        ...
