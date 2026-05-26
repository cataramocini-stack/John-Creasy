"""Notificador via Telegram Bot API."""

from datetime import datetime
from zoneinfo import ZoneInfo

import structlog

from vgb.application.ports.notifier import (
    AlertPayload,
    NotificationPayload,
    Notifier,
    SummaryPayload,
)
from vgb.infrastructure.config import Settings
from vgb.infrastructure.http.resilient_client import ResilientHTTPClient

logger = structlog.get_logger()


class TelegramNotifier(Notifier):
    """Envia notificacoes para um chat do Telegram."""

    def __init__(self, client: ResilientHTTPClient, settings: Settings) -> None:
        self._client = client
        self._token = settings.telegram_token.get_secret_value()
        self._chat_id = settings.telegram_chat_id

    async def send(self, payload: NotificationPayload) -> str:
        message = self._format_occurrence(payload)
        return await self._dispatch(message)

    async def send_summary(self, payload: SummaryPayload) -> str:
        message = self._format_summary(payload)
        return await self._dispatch(message)

    async def send_alert(self, payload: AlertPayload) -> str:
        message = self._format_alert(payload)
        return await self._dispatch(message)

    async def _dispatch(self, text: str) -> str:
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        logger.info("telegram.dispatch", chat_id=self._chat_id)

        response = await self._client.post(
            url,
            json={
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        response.raise_for_status()
        data = response.json()
        message_id = str(data.get("result", {}).get("message_id", "unknown"))
        logger.info("telegram.sent", message_id=message_id)
        return message_id

    def _format_occurrence(self, payload: NotificationPayload) -> str:
        ed = payload.edition
        occs = payload.occurrences

        if not occs:
            return ""

        occ = occs[0]  # Mensagem enxuta: foca na melhor ocorrencia
        act_emoji = {
            "nomeacao": "🎖",
            "exoneracao": "⚠",
            "designacao": "📋",
            "licenca": "🏖",
            "outro": "📌",
        }.get(occ.act_type.value, "📌")

        header = "🚨 NOME" if occ.type.value in ("nome", "both") else "🔔 CARGO"
        now_brt = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")

        lines = [
            f"<b>{header} ENCONTRADO</b>",
            f"<b>{occ.act_type.value.upper()}</b> {act_emoji}",
            f"<b>Confianca:</b> {occ.confidence:.0%}",
            "",
            f'<a href="{ed.url}">{ed.title}</a>',
        ]

        if occ.page_hint:
            lines.append(f"<b>Pagina:</b> {occ.page_hint}")

        if occ.context_snippet:
            snippet = occ.context_snippet.replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f"<code>{snippet}</code>")

        lines.append(f"\n🕐 {now_brt} BRT")

        return "\n".join(lines)

    def _format_summary(self, payload: SummaryPayload) -> str:
        now_brt = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
        lines = [
            f"<b>Data:</b> {payload.run_date.strftime('%d/%m/%Y')}",
            "",
            f"PDFs analisados: <b>{payload.total_links}</b>",
            f"Novos: <b>{payload.total_new}</b>",
            f"Ocorrencias: <b>{payload.total_found}</b>",
        ]

        if payload.total_errors:
            lines.append(f"Erros: <b>{payload.total_errors}</b> ⚠️")

        lines.append(f"Duracao: <b>{payload.duration_seconds:.1f}s</b>")

        if payload.total_found == 0:
            lines.extend(
                [
                    "",
                    "✅ Nenhuma mencao ao nome ou cargo foi encontrada hoje.",
                ]
            )

        lines.append(f"\n🕐 {now_brt} BRT")

        return "\n".join(lines)

    def _format_alert(self, payload: AlertPayload) -> str:
        now_brt = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
        lines = [
            "🆘 <b>ALERTA CRITICO — VGB FALHOU</b>",
            f"<b>Data:</b> {payload.run_date.strftime('%d/%m/%Y %H:%M')}",
            "",
            f"<b>Erro:</b> <code>{payload.error_summary}</code>",
        ]

        if payload.traceback_snippet:
            tb = payload.traceback_snippet[:800].replace("<", "&lt;").replace(">", "&gt;")
            lines.extend(["", f"<b>Traceback:</b>\n<pre>{tb}</pre>"])

        lines.extend(
            [
                "",
                "⚠️ O sistema nao conseguiu completar a execucao. Verifique os logs do GitHub Actions.",
            ]
        )

        lines.append(f"\n🕐 {now_brt} BRT")

        return "\n".join(lines)
