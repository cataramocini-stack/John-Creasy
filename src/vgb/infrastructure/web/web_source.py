"""Coletor de fonte web para documentos oficiais."""

from collections.abc import Sequence

import structlog
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from vgb.application.ports.source import DocumentSource, SourceLink
from vgb.infrastructure.config import Settings
from vgb.infrastructure.http.resilient_client import ResilientHTTPClient

logger = structlog.get_logger()


class WebDocumentSource(DocumentSource):
    """Coleta links de PDFs de uma fonte web configuravel."""

    def __init__(self, client: ResilientHTTPClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    @retry(
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def fetch_links(self, limit: int = 10) -> Sequence[SourceLink]:
        url = self._settings.diario_url
        logger.info("source.fetching", url=url)

        response = await self._client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links: list[SourceLink] = []
        seen = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if ".pdf" not in href.lower():
                continue

            base = self._settings.diario_base_url.rstrip("/")
            full_url = href if href.startswith("http") else base + "/" + href.lstrip("/")

            if full_url in seen:
                continue
            seen.add(full_url)

            title = anchor.get_text(strip=True) or "Diario Oficial"
            links.append(SourceLink(title=title, url=full_url))

            if len(links) >= limit:
                break

        logger.info("source.fetched", count=len(links), limit=limit)
        return links
