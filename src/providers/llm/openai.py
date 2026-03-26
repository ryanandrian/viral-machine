"""
OpenAI LLM Provider — provider default untuk semua tenant.
Membungkus semua panggilan GPT dari Intelligence Layer.

Model yang didukung:
  - gpt-4o-mini (default) — cepat, murah, cukup untuk pipeline
  - gpt-4o                — lebih cerdas, untuk kasus kompleks

Cara ganti model via dashboard (nanti):
  llm_provider = 'openai'
  llm_model    = 'gpt-4o'
  llm_api_key  = (opsional — jika tidak diisi, pakai system key dari .env)
"""

import json
import os
import re

from loguru import logger
from openai import AsyncOpenAI, OpenAI

from src.providers.llm.base import LLMProvider, LLMResponse, LLMError


SUPPORTED_MODELS = {
    "gpt-4o-mini": {
        "description":        "Cepat, murah — default pipeline",
        "input_cost_per_1m":  0.15,
        "output_cost_per_1m": 0.60,
        "max_tokens":         16_000,
    },
    "gpt-4o": {
        "description":        "Lebih cerdas — untuk kasus kompleks",
        "input_cost_per_1m":  2.50,
        "output_cost_per_1m": 10.00,
        "max_tokens":         16_000,
    },
}

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(LLMProvider):
    """
    OpenAI LLM Provider.
    Support sync dan async — pipeline saat ini sync, future async.
    """

    def __init__(self, config: dict):
        super().__init__(config)

        self.api_key = (
            config.get("llm_api_key")
            or os.getenv("OPENAI_API_KEY", "")
        )
        if not self.api_key:
            raise LLMError(
                "OpenAI membutuhkan API key. "
                "Set llm_api_key di tenant_configs atau OPENAI_API_KEY di .env."
            )

        self.model = config.get("llm_model", DEFAULT_MODEL)
        if self.model not in SUPPORTED_MODELS:
            logger.warning(
                f"[OpenAI] Model '{self.model}' tidak dikenal — "
                f"fallback ke '{DEFAULT_MODEL}'"
            )
            self.model = DEFAULT_MODEL

        # Sync client untuk kompatibilitas pipeline saat ini
        self._sync_client  = OpenAI(api_key=self.api_key)
        # Async client untuk future async pipeline
        self._async_client = AsyncOpenAI(api_key=self.api_key)

        logger.info(f"[OpenAI] Initialized: model={self.model}")

    # ──────────────────────────────────────────────
    # Async API (abstract methods dari base)
    # ──────────────────────────────────────────────

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: str = "text",
    ) -> LLMResponse:
        """Async completion — untuk future pipeline."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model":       self.model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._async_client.chat.completions.create(**kwargs)
            usage    = response.usage
            return LLMResponse(
                content=response.choices[0].message.content.strip(),
                model=self.model,
                provider=self.provider_name,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
        except Exception as e:
            raise LLMError(f"OpenAI completion failed: {e}") from e

    async def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> dict:
        """Async JSON completion — langsung return dict."""
        response = await self.complete(
            prompt=prompt,
            system=system,
            temperature=temperature,
            response_format="json",
        )
        return self._parse_json(response.content)

    # ──────────────────────────────────────────────
    # Sync API — dipakai Intelligence Layer saat ini
    # ──────────────────────────────────────────────

    def complete_sync(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: str = "json",
        max_retries: int = 3,
    ) -> LLMResponse:
        """
        Sync completion dengan retry logic built-in.
        Dipakai oleh niche_selector, script_engine, hook_optimizer.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model":       self.model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"[OpenAI] Attempt {attempt}/{max_retries} model={self.model}")
                response = self._sync_client.chat.completions.create(**kwargs)
                usage    = response.usage
                content  = response.choices[0].message.content.strip()

                logger.debug(
                    f"[OpenAI] Success: "
                    f"prompt={usage.prompt_tokens} "
                    f"completion={usage.completion_tokens} tokens"
                )
                return LLMResponse(
                    content=content,
                    model=self.model,
                    provider=self.provider_name,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
            except Exception as e:
                last_error = e
                logger.warning(f"[OpenAI] Attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    logger.info("[OpenAI] Retrying...")

        raise LLMError(
            f"OpenAI completion failed after {max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def complete_json_sync(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> dict:
        """
        Sync JSON completion dengan retry + parsing robust.
        Shortcut untuk Intelligence Layer.
        """
        response = self.complete_sync(
            prompt=prompt,
            system=system,
            temperature=temperature,
            response_format="json",
            max_retries=max_retries,
        )
        return self._parse_json(response.content)

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Parse JSON dari response GPT dengan fallback cleaning."""
        # Hapus markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        # Cari JSON object atau array
        for pattern in [r'\{.*\}', r'\[.*\]']:
            match = re.search(pattern, raw, re.DOTALL)
            if match:
                raw = match.group(0)
                break
        # Hapus trailing comma
        raw = re.sub(r',\s*([}\]])', r'\1', raw)
        # Hapus control characters
        raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMError(f"JSON parse failed: {e}\nRaw: {raw[:200]}") from e

    @property
    def provider_name(self) -> str:
        return "openai"
