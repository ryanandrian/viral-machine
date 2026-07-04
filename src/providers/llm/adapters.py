"""
Adapter transport LLM — per PROTOKOL API (bukan per-vendor).

Ini SATU-SATUNYA tempat di kode yang menyentuh SDK vendor + tahu format parameter
API spesifik protokol. Vendor baru yang memakai protokol yang sama (mis. endpoint
OpenAI-compatible) cukup ditambah sebagai ROW di ai_providers (base_url+model) —
NOL koding. Protokol benar-benar baru = tambah 1 adapter di sini.

ADAPTERS = registry protokol (kode). Pemilihan provider/model = dari DB
(ai_providers.adapter), bukan hardcode di business logic.
"""

from src.providers.llm.base import LLMProvider, LLMError


class _BaseAdapter(LLMProvider):
    """Adapter dibangun oleh factory dari spec DB (ai_providers) + key tenant."""

    def __init__(self, *, api_key: str = "", display_name: str = "",
                 base_url: str | None = None, param_schema: dict | None = None):
        self.api_key = api_key or ""
        self.display_name = display_name or "LLM provider"
        self.base_url = base_url or None
        self.param_schema = param_schema or {}

    @property
    def provider_name(self) -> str:
        # Nama dari DB (display_name) — bukan literal vendor di kode.
        return self.display_name


class AnthropicMessagesAdapter(_BaseAdapter):
    """Protokol Anthropic Messages API. JSON via instruksi prompt (tanpa response_format)."""

    def complete(self, *, system, user, model, temperature=0.7, max_tokens=2000,
                 as_json=False) -> str:
        if not self.api_key:
            raise LLMError(f"Provider '{self.display_name}' butuh API key (BYOK).")
        if not model:
            raise LLMError(f"Model untuk '{self.display_name}' tidak ditentukan.")
        try:
            import anthropic
        except ImportError as e:
            raise LLMError("SDK transport tidak terinstall untuk provider ini.") from e

        system_prompt = system or ""
        if as_json:
            system_prompt = (
                system_prompt + "\n\nReturn ONLY valid JSON. No markdown, no prose."
            ).strip()
        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        try:
            client = anthropic.Anthropic(**kwargs)
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=min(temperature, 1.0),
                system=system_prompt,
                messages=[{"role": "user", "content": user}],
            )
            # B2 cost-tracking: usage menumpang di respons yg sama (nol overhead). Fail-soft.
            try:
                from src.utils import cost_meter
                cost_meter.add_llm(model, getattr(resp.usage, "input_tokens", 0), getattr(resp.usage, "output_tokens", 0))
            except Exception:
                pass
            return resp.content[0].text.strip()
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"Provider '{self.display_name}' gagal: {e}") from e


class OpenAIChatAdapter(_BaseAdapter):
    """Protokol OpenAI Chat Completions (kompatibel banyak vendor via base_url).
    JSON via response_format={'type':'json_object'}."""

    def complete(self, *, system, user, model, temperature=0.7, max_tokens=2000,
                 as_json=False) -> str:
        if not self.api_key:
            raise LLMError(f"Provider '{self.display_name}' butuh API key (BYOK).")
        if not model:
            raise LLMError(f"Model untuk '{self.display_name}' tidak ditentukan.")
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMError("SDK transport tidak terinstall untuk provider ini.") from e

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if as_json:
            body["response_format"] = {"type": "json_object"}
        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        try:
            client = OpenAI(**kwargs)
            resp = client.chat.completions.create(**body)
            # B2 cost-tracking: usage menumpang di respons yg sama (nol overhead). Fail-soft.
            try:
                from src.utils import cost_meter
                u = getattr(resp, "usage", None)
                cost_meter.add_llm(model, getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0))
            except Exception:
                pass
            return (resp.choices[0].message.content or "").strip()
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"Provider '{self.display_name}' gagal: {e}") from e


# Registry PROTOKOL transport (kode). Key = ai_providers.adapter di DB.
ADAPTERS = {
    "anthropic_messages": AnthropicMessagesAdapter,
    "openai_chat":        OpenAIChatAdapter,
}
