"""
Base class untuk semua LLM Provider.
Setiap provider baru WAJIB inherit class ini dan implement method complete().
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Representasi response dari LLM provider."""
    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMProvider(ABC):
    """Abstract base class untuk Large Language Model provider."""

    def __init__(self, config: dict):
        """
        Args:
            config: dict berisi konfigurasi provider dari tenant_configs.
                    Minimal: {'llm_provider': str, 'llm_model': str}
        """
        self.config = config
        self.model = config.get("llm_model", "gpt-4o-mini")
        self.api_key = config.get("llm_api_key")

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: str = "text"  # "text" | "json"
    ) -> LLMResponse:
        """
        Kirim prompt ke LLM dan dapat response.

        Args:
            prompt: User prompt
            system: System prompt (opsional)
            temperature: Kreativitas output (0.0-1.0)
            max_tokens: Batas panjang response
            response_format: "text" atau "json" untuk structured output

        Returns:
            LLMResponse dengan content dan metadata usage

        Raises:
            LLMError: Jika request gagal
        """
        pass

    @abstractmethod
    async def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3
    ) -> dict:
        """
        Shortcut untuk complete() yang langsung return dict.
        Provider wajib memastikan response adalah valid JSON.

        Returns:
            Dict hasil parse JSON response
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nama unik provider, contoh: 'openai', 'anthropic'"""
        pass


class LLMError(Exception):
    """Exception untuk error pada LLM provider."""
    pass
