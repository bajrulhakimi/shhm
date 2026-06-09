from abc import ABC, abstractmethod

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.exceptions import AIProviderError, RetryableExternalError
from app.monitoring import AI_PROVIDER_REQUESTS


class AIProvider(ABC):
    name: str

    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    async def _post(self, url: str, **kwargs) -> dict:
        settings = get_settings()
        retrying = AsyncRetrying(
            retry=retry_if_exception_type(RetryableExternalError),
            stop=stop_after_attempt(settings.external_request_max_attempts),
            wait=wait_exponential(
                multiplier=settings.external_request_backoff_seconds,
                min=settings.external_request_backoff_seconds,
                max=30,
            ),
            reraise=True,
        )
        try:
            async for attempt in retrying:
                with attempt:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(url, **kwargs)
                    if response.status_code == 429 or response.status_code >= 500:
                        raise RetryableExternalError(
                            f"{self.name} sementara tidak tersedia ({response.status_code})."
                        )
                    response.raise_for_status()
                    payload = response.json()
                    AI_PROVIDER_REQUESTS.labels(self.name, "success").inc()
                    return payload
        except httpx.HTTPStatusError as exc:
            AI_PROVIDER_REQUESTS.labels(self.name, "error").inc()
            detail = exc.response.text[:500]
            message = f"{self.name} API error ({exc.response.status_code}): {detail}"
            raise AIProviderError(message) from exc
        except (httpx.HTTPError, ValueError, RetryableExternalError) as exc:
            AI_PROVIDER_REQUESTS.labels(self.name, "error").inc()
            message = f"{self.name} tidak dapat dihubungi setelah beberapa percobaan."
            raise AIProviderError(message) from exc
        raise AIProviderError(f"{self.name} tidak memberikan respons.")
