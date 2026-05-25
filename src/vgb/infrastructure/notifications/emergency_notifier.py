"""Notificador de emergencia que nao depende de nenhuma infraestrutura do projeto.

Usado pelo Dead Man's Switch: se o sistema principal crashar,
este modulo tenta enviar um alerta via Telegram usando apenas httpx.
"""

from __future__ import annotations

import traceback
from datetime import datetime

import httpx


class EmergencyTelegramNotifier:
    """Envia alerta critico usando httpx puro, sem dependencias do projeto."""

    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id

    async def send_alert(self, error: Exception) -> bool:
        """Tenta enviar alerta de emergencia. Retorna True se enviou."""
        try:
            text = self._build_message(error)
            url = f"https://api.telegram.org/bot{self._token}/sendMessage"

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": self._chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                    },
                )
                response.raise_for_status()
                return True
        except Exception:
            # Se ate o emergencia falhar, nao ha mais nada a fazer
            return False

    def _build_message(self, error: Exception) -> str:
        error_type = type(error).__name__
        error_msg = str(error)[:200]
        tb = traceback.format_exc()[-800:].replace("<", "&lt;").replace(">", "&gt;")
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        return (
            f"🆘 <b>ALERTA CRITICO — VGB FALHOU</b>\n"
            f"<b>Horario:</b> {now}\n"
            f"\n"
            f"<b>Erro:</b> <code>{error_type}: {error_msg}</code>\n"
            f"\n"
            f"<pre>{tb}</pre>\n"
            f"\n"
            f"⚠️ Verifique os logs do GitHub Actions imediatamente."
        )
