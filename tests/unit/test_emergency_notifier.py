"""Testes unitarios do EmergencyTelegramNotifier."""

from unittest.mock import AsyncMock, patch

import pytest

from vgb.infrastructure.notifications.emergency_notifier import EmergencyTelegramNotifier


@pytest.fixture
def notifier() -> EmergencyTelegramNotifier:
    return EmergencyTelegramNotifier(token="test-token", chat_id="123456")


class TestSendAlert:
    async def test_envio_sucesso(self, notifier: EmergencyTelegramNotifier) -> None:
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {"result": {"message_id": 42}}
            mock_response.raise_for_status = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

            sent = await notifier.send_alert(ValueError("Algo quebrou"))
            assert sent is True
            mock_client.post.assert_awaited_once()

    async def test_envio_falha(self, notifier: EmergencyTelegramNotifier) -> None:
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Network down")
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

            sent = await notifier.send_alert(ValueError("Algo quebrou"))
            assert sent is False
