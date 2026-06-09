from app.exceptions import AIProviderError
from app.services.ai_provider import AIProvider


class ClaudeProvider(AIProvider):
    name = "claude"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        data = await self._post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 2500,
                "temperature": 0.2,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )
        text = "\n".join(item.get("text", "") for item in data.get("content", [])).strip()
        if not text:
            raise AIProviderError("Claude mengembalikan respons kosong.")
        return text

