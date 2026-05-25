"""Testes de integracao da fonte com mocks HTTP."""

import pytest
import respx
from httpx import Response

from vgb.infrastructure.config.settings import Settings
from vgb.infrastructure.http.resilient_client import ResilientHTTPClient
from vgb.infrastructure.web.web_source import WebDocumentSource


@pytest.fixture
def settings() -> Settings:
    return Settings(
        nome_busca="Teste",
        cargo_busca="Cargo",
        telegram_token="fake",
        telegram_chat_id="123",
        diario_url="https://example.gov.br/jornal/",
        diario_base_url="https://example.gov.br",
    )


@pytest.fixture
def client() -> ResilientHTTPClient:
    return ResilientHTTPClient()


@respx.mock
async def test_fetch_links(settings: Settings, client: ResilientHTTPClient) -> None:
    html = """
    <html><body>
        <a href="/jornal/do-01.pdf">Diario 01</a>
        <a href="https://externo.com/do-02.pdf">Diario 02</a>
        <a href="/outra">Link normal</a>
    </body></html>
    """
    respx.get(str(settings.diario_url)).mock(return_value=Response(200, text=html))

    source = WebDocumentSource(client, settings)
    links = await source.fetch_links(limit=10)

    assert len(links) == 2
    assert links[0].title == "Diario 01"
    assert ".pdf" in links[0].url
