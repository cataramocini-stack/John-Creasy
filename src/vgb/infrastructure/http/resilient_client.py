"""Cliente HTTP com retry, timeouts e headers realistas."""

from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = structlog.get_logger()

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


class ResilientHTTPClient:
    """Wrapper async sobre httpx.AsyncClient com retry automatico."""

    def __init__(self, timeout: float = 30.0, verify_ssl: bool = True) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers=_DEFAULT_HEADERS,
            verify=verify_ssl,
            http2=True,
            follow_redirects=True,
        )

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("GET", url, **kwargs)

    async def head(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("HEAD", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("POST", url, **kwargs)

    @retry(
        retry=retry_if_exception_type(
            (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError,
                httpx.HTTPStatusError,
            )
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True,
    )
    async def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        logger.debug("http.request", method=method, url=url)
        response = await self._client.request(method, url, **kwargs)

        # Retry em rate limit (429) e server errors (5xx)
        if response.status_code == 429:
            logger.warning("http.rate_limited", url=url, status=429)
            raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
        if response.status_code >= 500:
            logger.warning("http.server_error", url=url, status=response.status_code)
            raise httpx.HTTPStatusError(
                f"Server error {response.status_code}",
                request=response.request,
                response=response,
            )

        logger.debug("http.response", method=method, url=url, status=response.status_code)
        return response

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ResilientHTTPClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()
