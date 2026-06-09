from app.exceptions import AIProviderError
from app.services.ai_provider import AIProvider


class OpenAIProvider(AIProvider):
    name = "openai"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        data = await self._post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "instructions": system_prompt,
                "input": user_prompt,
            },
        )
        if data.get("output_text"):
            return data["output_text"].strip()
        parts = [
            item.get("text", "")
            for output in data.get("output", [])
            for item in output.get("content", [])
            if item.get("type") == "output_text"
        ]
        text = "\n".join(part for part in parts if part).strip()
        if not text:
            raise AIProviderError("OpenAI mengembalikan respons kosong.")
        return text

