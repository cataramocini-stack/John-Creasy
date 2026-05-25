"""CLI principal do VGB."""

import asyncio
import sys

import click
import structlog

from vgb.application.use_cases.monitor_diario import MonitorDiarioUseCase
from vgb.infrastructure.ai.composite_analyzer import CompositeAnalyzer
from vgb.infrastructure.config import Settings
from vgb.infrastructure.http.resilient_client import ResilientHTTPClient
from vgb.infrastructure.notifications.emergency_notifier import EmergencyTelegramNotifier
from vgb.infrastructure.notifications.telegram_notifier import TelegramNotifier
from vgb.infrastructure.storage.database import Database
from vgb.infrastructure.storage.repositories import (
    SqlAlchemyAnalysisRepository,
    SqlAlchemyEditionRepository,
)
from vgb.infrastructure.web.web_source import WebDocumentSource


def _configure_logging(log_level: str, json_format: bool) -> None:
    import logging

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


async def _run() -> int:
    settings = Settings()
    _configure_logging(settings.log_level, settings.log_json)
    logger = structlog.get_logger()
    logger.info("vgb.start")

    try:
        db = Database(str(settings.database_url))
        await db.create_tables()

        http_client = ResilientHTTPClient()

        source = WebDocumentSource(http_client, settings)
        analyzer = CompositeAnalyzer(settings)
        notifier = TelegramNotifier(http_client, settings)
        edition_repo = SqlAlchemyEditionRepository(db)
        analysis_repo = SqlAlchemyAnalysisRepository(db)

        use_case = MonitorDiarioUseCase(
            source=source,
            analyzer=analyzer,
            notifier=notifier,
            edition_repo=edition_repo,
            analysis_repo=analysis_repo,
            http_client=http_client,
            settings=settings,
        )

        stats = await use_case.execute()
        logger.info("vgb.complete", stats=stats)

        await http_client.close()
        await db.close()
        return 0

    except Exception as exc:
        logger.exception("vgb.critical_failure")
        await _send_emergency_alert(settings, exc)
        return 1


async def _send_emergency_alert(settings: Settings, error: Exception) -> None:
    """Dead Man's Switch: tenta enviar alerta critico mesmo com sistema quebrado."""
    try:
        if not settings.telegram_token or not settings.telegram_chat_id:
            return

        emergency = EmergencyTelegramNotifier(
            token=settings.telegram_token.get_secret_value(),
            chat_id=settings.telegram_chat_id,
        )
        sent = await emergency.send_alert(error)
        if sent:
            structlog.get_logger().info("vgb.emergency_alert_sent")
        else:
            structlog.get_logger().error("vgb.emergency_alert_failed")
    except Exception:
        structlog.get_logger().error("vgb.emergency_alert_exception")


@click.command()
@click.version_option(version="2.0.0", prog_name="vgb")
def main() -> None:
    """VGB - Vigilante do Diario Oficial."""
    sys.exit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
