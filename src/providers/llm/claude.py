"""
Claude LLM Provider — Anthropic Claude untuk script generation.
Fase 6C: Default provider untuk script engine (kualitas terbaik).
Multi-tenant: dipilih via tenant_configs.llm_provider = 'claude'
"""

import os
import json
import re
from loguru import logger
from src.providers.llm.base import LLMProvider, LLMError


class ClaudeProvider(LLMProvider):
    """
    Anthropic Claude — unggul untuk nuanced storytelling dan
    mengikuti instruksi kompleks berlapis (ideal untuk 8-section script).
    """

    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, config: dict):
        super().__init__(config)
        self.model   = config.get("llm_model", self.DEFAULT_MODEL)
        self.api_key = (
            config.get("llm_api_key")
            or os.getenv("ANTHROPIC_API_KEY", "")
        )
        if not self.api_key:
            raise LLMError(
                "Claude membutuhkan ANTHROPIC_API_KEY di .env "
                "atau llm_api_key di tenant_configs."
            )

    def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        Single completion call ke Claude.
        Return raw string response.
        """
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)

            response = client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.85),
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )
            return response.content[0].text.strip()

        except Exception as e:
            raise LLMError(f"Claude completion failed: {e}") from e

    def complete_json(self, system_prompt: str, user_prompt: str, **kwargs) -> dict:
        """
        Completion yang return parsed JSON dict.
        Claude sangat reliable untuk JSON jika instruksi jelas di prompt.
        """
        raw = self.complete(system_prompt, user_prompt, **kwargs)

        try:
            # Bersihkan response sebelum parse
            cleaned = raw.replace("```json", "").replace("```", "").strip()
            match   = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                cleaned = match.group(0)
            cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
            return json.loads(cleaned)

        except json.JSONDecodeError as e:
            raise LLMError(f"Claude JSON parse failed: {e} | raw: {raw[:200]}") from e

    @property
    def provider_name(self) -> str:
        return "claude"
