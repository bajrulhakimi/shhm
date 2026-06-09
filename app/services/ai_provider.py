from abc import ABC, abstractmethod

import httpx

from app.exceptions import AIProviderError


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
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            message = f"{self.name} API error ({exc.response.status_code}): {detail}"
            raise AIProviderError(message) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise AIProviderError(f"{self.name} tidak dapat dihubungi.") from exc
