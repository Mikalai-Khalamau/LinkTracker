import httpx
from datetime import timedelta
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_result,
    retry_if_exception_type,
)
from aiobreaker import CircuitBreaker

from src.config import settings
from src.logger import get_logger

logger = get_logger()


def _is_retryable_status(response: httpx.Response) -> bool:
    return response.status_code in settings.retry_statuses


class ResilientHttpClient:
    def __init__(self):
        self.timeout = httpx.Timeout(
            timeout=settings.http_timeout_seconds,
            connect=settings.http_timeout_connect,
        )
        self.breaker = CircuitBreaker(
            fail_max=settings.circuit_breaker_minimum_required_calls,
            timeout_duration=timedelta(
                seconds=settings.circuit_breaker_wait_duration_seconds
            ),
        )
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        async def _make_request():
            response = await self._client.request(method, url, **kwargs)
            if 400 <= response.status_code < 500:
                return response
            if _is_retryable_status(response):
                response.raise_for_status()
            return response

        @retry(
            stop=stop_after_attempt(settings.retry_max_attempts),
            wait=wait_fixed(settings.retry_wait_seconds),
            retry=retry_if_result(_is_retryable_status)
            | retry_if_exception_type(httpx.HTTPStatusError),
            reraise=True,
        )
        async def _with_retry():
            return await self.breaker.call(_make_request)

        try:
            return await _with_retry()
        except Exception as e:
            logger.error(
                "resilient_http_request_failed",
                url=url,
                method=method,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def close(self):
        await self._client.aclose()

    @property
    def is_available(self) -> bool:
        return self.breaker.current_state.name != "OPEN"
