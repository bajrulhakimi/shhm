from app.exceptions import AIProviderError
from app.services.ai_provider import AIProvider


class GeminiProvider(AIProvider):
    name = "gemini"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        data = await self._post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"temperature": 0.2},
            },
        )
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as exc:
            raise AIProviderError("Gemini mengembalikan respons kosong.") from exc
