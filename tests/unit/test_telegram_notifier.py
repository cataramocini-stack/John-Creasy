"""Testes unitarios do TelegramNotifier."""

from datetime import date

import pytest

from vgb.application.ports.notifier import AlertPayload, NotificationPayload, SummaryPayload
from vgb.domain.entities import Edition
from vgb.domain.enums import ActType, OccurrenceType
from vgb.domain.value_objects import HashSHA256
from vgb.infrastructure.config.settings import Settings
from vgb.infrastructure.notifications.telegram_notifier import TelegramNotifier


@pytest.fixture
def settings() -> Settings:
    return Settings(
        nome_busca="Teste",
        cargo_busca="Cargo",
        telegram_token="fake-token",
        telegram_chat_id="123456",
        diario_url="https://example.gov.br/jornal/",
        diario_base_url="https://example.gov.br",
    )


class TestFormatOccurrence:
    def test_nome_encontrado(self, settings: Settings) -> None:
        notifier = TelegramNotifier(None, settings)  # type: ignore[arg-type]
        edition = Edition(
            id=1,
            url="https://exemplo.gov.br/do.pdf",
            title="DO 01/01/2024",
            hash=HashSHA256.from_bytes(b"x"),
            size_bytes=1024,
        )
        payload = NotificationPayload(
            edition=edition,
            occurrences=[
                type(
                    "Occ",
                    (),
                    {
                        "type": OccurrenceType.BOTH,
                        "act_type": ActType.NOMEACAO,
                        "confidence": 0.95,
                        "page_hint": 12,
                        "context_snippet": "NOMEIA-SE JOAO SILVA",
                    },
                )()
            ],
            message_html="",
        )
        msg = notifier._format_occurrence(payload)
        assert "NOME ENCONTRADO" in msg
        assert "NOMEACAO" in msg
        assert "Pagina:" in msg
        assert "NOMEIA-SE JOAO SILVA" in msg

    def test_cargo_encontrado(self, settings: Settings) -> None:
        notifier = TelegramNotifier(None, settings)  # type: ignore[arg-type]
        edition = Edition(
            id=1,
            url="https://exemplo.gov.br/do.pdf",
            title="DO 01/01/2024",
            hash=HashSHA256.from_bytes(b"x"),
            size_bytes=2048,
        )
        payload = NotificationPayload(
            edition=edition,
            occurrences=[
                type(
                    "Occ",
                    (),
                    {
                        "type": OccurrenceType.CARGO,
                        "act_type": ActType.DESIGNACAO,
                        "confidence": 0.88,
                        "page_hint": None,
                        "context_snippet": "",
                    },
                )()
            ],
            message_html="",
        )
        msg = notifier._format_occurrence(payload)
        assert "CARGO ENCONTRADO" in msg
        assert "DESIGNACAO" in msg
        assert "Pagina" not in msg


class TestFormatSummary:
    def test_com_ocorrencias(self, settings: Settings) -> None:
        notifier = TelegramNotifier(None, settings)  # type: ignore[arg-type]
        payload = SummaryPayload(
            run_date=date(2024, 1, 15),
            total_links=3,
            total_new=2,
            total_found=1,
            total_errors=0,
        )
        msg = notifier._format_summary(payload)
        assert "PDFs analisados: <b>3</b>" in msg
        assert "Novos: <b>2</b>" in msg
        assert "Ocorrencias: <b>1</b>" in msg
        assert "Nenhuma mencao" not in msg

    def test_sem_ocorrencias(self, settings: Settings) -> None:
        notifier = TelegramNotifier(None, settings)  # type: ignore[arg-type]
        payload = SummaryPayload(
            run_date=date(2024, 1, 15),
            total_links=2,
            total_new=1,
            total_found=0,
            total_errors=0,
        )
        msg = notifier._format_summary(payload)
        assert "Nenhuma mencao ao nome ou cargo foi encontrada hoje" in msg

    def test_com_erros(self, settings: Settings) -> None:
        notifier = TelegramNotifier(None, settings)  # type: ignore[arg-type]
        payload = SummaryPayload(
            run_date=date(2024, 1, 15),
            total_links=3,
            total_new=2,
            total_found=0,
            total_errors=1,
        )
        msg = notifier._format_summary(payload)
        assert "Erros: <b>1</b>" in msg


class TestFormatAlert:
    def test_alerta_critico(self, settings: Settings) -> None:
        notifier = TelegramNotifier(None, settings)  # type: ignore[arg-type]
        payload = AlertPayload(
            run_date=date(2024, 1, 15),
            error_summary="DatabaseConnectionError: unable to connect",
            traceback_snippet="Traceback (most recent call last):\n  File ...",
        )
        msg = notifier._format_alert(payload)
        assert "ALERTA CRITICO" in msg
        assert "DatabaseConnectionError" in msg
        assert "Traceback" in msg
        assert "Verifique os logs" in msg
