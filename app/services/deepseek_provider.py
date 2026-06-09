from app.exceptions import AIProviderError
from app.services.ai_provider import AIProvider


class DeepSeekProvider(AIProvider):
    name = "deepseek"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        data = await self._post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise AIProviderError("DeepSeek mengembalikan respons kosong.") from exc

