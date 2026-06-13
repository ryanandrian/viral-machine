"""
Base + util untuk semua LLM Provider.

Prinsip (SOFTCODE Phase 1.1): provider adalah SATU-SATUNYA tempat yang boleh
menyentuh SDK vendor (anthropic/openai) dan tahu format parameter API spesifik
vendor. Business logic (script_engine, niche_selector, hook_optimizer,
script_analyzer, ai_image) TIDAK boleh meng-instansiasi client atau menyebut
nama SDK — cukup panggil complete()/complete_json() lewat abstraksi ini.

Kontrak SYNC seragam + model PER-PANGGILAN (1 tenant 1 library, tapi beda model
per-task: script/utility/analyzer/rewrite). Gagal -> raise LLMError; caller yang
memutuskan stop + notify (TIDAK ada silent fallback lintas-provider).
"""

import json
import re
from abc import ABC, abstractmethod


# LLMError di-RE-EXPORT dari hierarki terpusat (Phase 2) — kini PipelineError subclass.
# Import lama `from src.providers.llm.base import LLMError` tetap jalan.
from src.exceptions import LLMError  # noqa: E402,F401


def parse_json_lenient(raw: str) -> dict:
    """Parser JSON robust bersama untuk semua provider — buang markdown fence,
    ekstrak objek/array pertama, hapus trailing comma + control char.

    Raise LLMError jika tak bisa di-parse (sebelumnya 3 helper terpisah di
    script_engine/hook_optimizer/openai — dikonsolidasi di sini)."""
    if not raw:
        raise LLMError("LLM mengembalikan response kosong")
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise LLMError(f"JSON parse gagal: {e} | raw: {raw[:200]}") from e


class LLMProvider(ABC):
    """Abstract base class — kontrak sync seragam, model per-panggilan."""

    def __init__(self, config: dict | None = None):
        """config = dict dari tenant_config.to_provider_config(). Hanya butuh
        llm_api_key (BYOK). Model TIDAK diambil dari config — dikirim per call."""
        self.config = config or {}
        self.api_key = self.config.get("llm_api_key") or ""
        # legacy flat — fallback terakhir bila caller tak kirim model
        self.default_model = self.config.get("llm_model") or ""

    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        as_json: bool = False,
    ) -> str:
        """Kirim 1 prompt, return raw text response.

        Tiap provider memetakan `as_json` ke mekanisme JSON vendor-nya sendiri
        (OpenAI: response_format; Claude: instruksi prompt). Raise LLMError jika
        gagal — TIDAK pernah silent-fallback ke provider lain.
        """
        ...

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> dict:
        """Sugar: complete(as_json=True) lalu robust-parse jadi dict."""
        raw = self.complete(
            system=system,
            user=user,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            as_json=True,
        )
        return parse_json_lenient(raw)

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nama unik provider, contoh: 'claude', 'openai'."""
        ...
