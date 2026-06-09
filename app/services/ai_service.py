import asyncio
import logging
from typing import Any

from app.config import get_settings
from app.exceptions import AIProviderError, ConfigurationError
from app.prompts.analysis_prompt import SYSTEM_PROMPT, build_analysis_prompt
from app.prompts.scan_prompt import build_scan_prompt
from app.prompts.summary_prompt import SUMMARY_SYSTEM_PROMPT, build_summary_prompt
from app.services.ai_provider import AIProvider
from app.services.claude_provider import ClaudeProvider
from app.services.deepseek_provider import DeepSeekProvider
from app.services.gemini_provider import GeminiProvider
from app.services.openai_provider import OpenAIProvider
from app.services.structured_result_service import StructuredResultService

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self) -> None:
        self.settings = get_settings()
        timeout = self.settings.ai_request_timeout_seconds
        self.providers: dict[str, AIProvider] = {}
        provider_config = [
            ("openai", self.settings.openai_api_key, self.settings.openai_model, OpenAIProvider),
            ("gemini", self.settings.gemini_api_key, self.settings.gemini_model, GeminiProvider),
            ("claude", self.settings.claude_api_key, self.settings.claude_model, ClaudeProvider),
            (
                "deepseek",
                self.settings.deepseek_api_key,
                self.settings.deepseek_model,
                DeepSeekProvider,
            ),
        ]
        for name, key, model, provider_class in provider_config:
            if key:
                self.providers[name] = provider_class(key, model, timeout)

    def _default_provider(self) -> AIProvider:
        provider = self.providers.get(self.settings.default_ai_provider)
        if provider:
            return provider
        if self.providers:
            return next(iter(self.providers.values()))
        raise ConfigurationError("Belum ada AI provider aktif. Isi minimal satu API key di .env.")

    def ensure_available(self) -> None:
        self._default_provider()

    @staticmethod
    def parse_result(text: str, stock_code: str) -> dict[str, Any]:
        structured = StructuredResultService.parse(text, stock_code)
        return {
            "text": StructuredResultService.render(structured),
            "structured": StructuredResultService.as_dict(structured),
            "final_signal": structured.signal,
            "confidence_level": structured.confidence,
        }

    @staticmethod
    def _compact_data(data: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in data.items() if key != "history"}

    async def analyze(self, data: dict[str, Any], quick: bool = False) -> dict[str, Any]:
        compact = self._compact_data(data)
        if quick:
            provider = self._default_provider()
            text = await provider.generate(SYSTEM_PROMPT, build_scan_prompt(compact))
            return self._result(provider.name, text, {provider.name: text}, compact)

        if not self.settings.enable_multi_ai:
            provider = self._default_provider()
            text = await provider.generate(SYSTEM_PROMPT, build_analysis_prompt(compact))
            return self._result(provider.name, text, {provider.name: text}, compact)

        if not self.providers:
            raise ConfigurationError(
                "Belum ada AI provider aktif. Isi minimal satu API key di .env."
            )
        tasks = {
            name: asyncio.create_task(
                provider.generate(SYSTEM_PROMPT, build_analysis_prompt(compact))
            )
            for name, provider in self.providers.items()
        }
        individual: dict[str, str] = {}
        errors: dict[str, str] = {}
        for name, task in tasks.items():
            try:
                individual[name] = await task
            except AIProviderError as exc:
                logger.warning("AI provider %s failed: %s", name, exc)
                errors[name] = str(exc)
        if not individual:
            raise AIProviderError("Semua AI provider gagal memberikan analisa.")

        summarizer = (
            self.providers.get(self.settings.summary_ai_provider) or self._default_provider()
        )
        try:
            final_text = await summarizer.generate(
                SUMMARY_SYSTEM_PROMPT,
                build_summary_prompt(compact, individual),
            )
            provider_name = f"multi-ai:{summarizer.name}"
        except AIProviderError:
            first_name, final_text = next(iter(individual.items()))
            provider_name = f"multi-ai-fallback:{first_name}"
        result = self._result(provider_name, final_text, individual, compact)
        result["provider_errors"] = errors
        return result

    @staticmethod
    def _result(
        provider: str,
        text: str,
        individual: dict[str, str],
        data: dict[str, Any],
    ) -> dict[str, Any]:
        structured = StructuredResultService.parse(text, data["stock"]["code"])
        return {
            "provider": provider,
            "text": StructuredResultService.render(structured),
            "raw_text": text,
            "structured": StructuredResultService.as_dict(structured),
            "individual_results": individual,
            "final_signal": structured.signal,
            "confidence_level": structured.confidence,
        }
