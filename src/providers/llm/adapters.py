"""
Adapter transport LLM — per PROTOKOL API (bukan per-vendor).

Ini SATU-SATUNYA tempat di kode yang menyentuh SDK vendor + tahu format parameter
API spesifik protokol. Vendor baru yang memakai protokol yang sama (mis. endpoint
OpenAI-compatible) cukup ditambah sebagai ROW di ai_providers (base_url+model) —
NOL koding. Protokol benar-benar baru = tambah 1 adapter di sini.

ADAPTERS = registry protokol (kode). Pemilihan provider/model = dari DB
(ai_providers.adapter), bukan hardcode di business logic.
"""

import json
import urllib.error
import urllib.request

from src.providers.llm.base import LLMProvider, LLMError
from src.providers.llm import catalog as _catalog
from src.exceptions import ErrorClass


# [ERROR-MGMT] Classifier transport OpenAI-COMPATIBLE (SPEC AI_ERROR_MANAGEMENT_ARCHITECTURE.md
# §4 registry; pola persis _classify_el_error). HANYA kode ber-BUKTI-SAMPEL nyata. Kode lain → UNKNOWN (aman).
# Token = string PASTI muncul di str(exc) (SDK cetak body vendor utuh). Bukti sampel:
#   • `invalid_api_key` (401) · `model_not_found` (404) — worker.log 20-Jul (insiden MVT via Groq).
#   • `is no longer available` (Gemini 404 model dipensiunkan) — production_runs 21/22-Jul (insiden riandipantria `gemini-2.5-flash`).
#   • `insufficient_quota` — worker.log 09-Jul (OpenAI) · `exceeded your current quota` — production_runs 21-Jul (OpenAI, insiden riandipantria).
# CATATAN 429: HANYA token quota di atas → fast-fail; 429 rate-limit throttle (pesan "Rate limit reached") TIDAK di-map → UNKNOWN/retryable (jangan salah-rem).
_OPENAI_COMPAT_ERROR_MAP = {
    "invalid_api_key": ErrorClass.AUTH_INVALID,
    "model_not_found": ErrorClass.MODEL_UNAVAILABLE,
    "is no longer available": ErrorClass.MODEL_UNAVAILABLE,
    "insufficient_quota": ErrorClass.QUOTA_EXHAUSTED,
    "exceeded your current quota": ErrorClass.QUOTA_EXHAUSTED,
}
_OPENAI_COMPAT_HUMAN = {
    ErrorClass.AUTH_INVALID: "Kunci API AI (penulis naskah) ditolak penyedia. Periksa/perbarui kunci di halaman Integrasi, lalu pastikan Akun (kunci) di setting channel sepadan dengan penyedianya.",
    ErrorClass.MODEL_UNAVAILABLE: "Model AI ini sudah tidak tersedia di penyedianya (dipensiunkan/tak bisa diakses). Pilih model lain di setting channel.",
    ErrorClass.QUOTA_EXHAUSTED: "Kuota/kredit penyedia AI (penulis naskah) sudah habis. Isi saldo/kredit di akun penyedia Anda, lalu Jalankan Ulang.",
}


def _classify_openai_compat_error(exc: Exception) -> tuple[ErrorClass, str | None]:
    """Petakan error transport OpenAI-compatible → (ErrorClass, human_message).
    String-scan token kode PASTI di str(exc) (body vendor tercetak utuh oleh SDK).
    Tak cocok → (UNKNOWN, None) = perilaku lama persis."""
    blob = str(exc)
    for tok, ec in _OPENAI_COMPAT_ERROR_MAP.items():
        if tok in blob:
            return ec, _OPENAI_COMPAT_HUMAN.get(ec)
    return ErrorClass.UNKNOWN, None


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
    """Protokol Anthropic Messages API. JSON via instruksi prompt (tanpa response_format).

    ADAPTASI-PROTOKOL `temperature` (bugfix owner 2026-07-16): model Claude generasi baru
    (keluarga Claude 5 / Opus 4.8) MENOLAK parameter `temperature` (HTTP 400 "deprecated").
    Solusi tanpa-hardcode-nama-model: kirim normal → HANYA bila vendor menjawab persis
    error itu → ulang SEKALI tanpa `temperature` (tercatat di log) → model dimemo di
    `_NO_TEMPERATURE_MODELS` (per-proses) sehingga panggilan berikutnya langsung bersih
    (nol penalti latensi berulang). Satu adapter = satu perilaku utk tombol-Test admin
    DAN produksi tenant (mustahil 'test lulus, tenant gagal'). Error lain apa pun =
    GAGAL JUJUR seperti sebelumnya. Model lama: byte-identik (temperature tetap dikirim)."""

    # Memo per-proses: model yang TERBUKTI menolak temperature (belajar dari jawaban vendor).
    _NO_TEMPERATURE_MODELS: set = set()

    @staticmethod
    def _is_temperature_rejected(err: Exception) -> bool:
        """Cocokkan KETAT: 400 invalid_request + 'temperature' + deprecated/not supported."""
        msg = str(err).lower()
        return ("temperature" in msg
                and ("deprecated" in msg or "not supported" in msg)
                and ("400" in msg or "invalid_request" in msg))

    def complete(self, *, system, user, model, temperature=0.7, max_tokens=2000,
                 as_json=False) -> str:
        if not self.api_key:
            raise LLMError(f"Provider '{self.display_name}' butuh API key (BYOK).")
        if not model:
            raise LLMError(f"Model untuk '{self.display_name}' tidak ditentukan.")
        # [Fix 2026-07-20] model_key katalog → model_id resmi vendor — SATU pintu utk seluruh
        # pemanggil produksi (menyamakan jalur produksi dgn jalur Uji admin: lolos Uji = pasti jalan).
        model = _catalog.resolve_model_id(model)
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

        def _call(client, with_temperature: bool):
            req = dict(model=model, max_tokens=max_tokens, system=system_prompt,
                       messages=[{"role": "user", "content": user}])
            if with_temperature:
                req["temperature"] = min(temperature, 1.0)
            return client.messages.create(**req)

        try:
            client = anthropic.Anthropic(**kwargs)
            _with_temp = model not in self._NO_TEMPERATURE_MODELS
            try:
                resp = _call(client, with_temperature=_with_temp)
            except Exception as e:
                if _with_temp and self._is_temperature_rejected(e):
                    # Vendor menyatakan temperature usang utk model ini → ulang SEKALI tanpanya + memo.
                    from loguru import logger
                    logger.info(f"[LLM] model '{model}' menolak `temperature` (vendor: deprecated) — "
                                f"dikirim ulang tanpa parameter itu & dimemo utk panggilan berikutnya")
                    self._NO_TEMPERATURE_MODELS.add(model)
                    resp = _call(client, with_temperature=False)
                else:
                    raise
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
    JSON via response_format={'type':'json_object'}.

    ADAPTASI-PROTOKOL parameter (bugfix owner 2026-07-16 — kelanjutan pola Anthropic):
    model OpenAI generasi baru MENOLAK parameter lama (400): `max_tokens` → wajib
    `max_completion_tokens`; `temperature` custom ditolak sebagian model. Solusi
    tanpa-hardcode-nama-model: kirim normal → HANYA bila vendor menjawab persis
    "unsupported parameter X (use Y instead)" / "'X' does not support ..." → tukar/
    tanggalkan parameter itu, ulang (maks 3 adaptasi/panggilan, tiap ulang WAJIB
    dipicu parameter BARU yang masih ada di body — anti loop) → memo per (vendor,model)
    di `_PARAM_ADAPTATIONS` sehingga panggilan berikutnya langsung bersih. Adapter ini
    dipakai BANYAK vendor via base_url → memo dikunci per-vendor agar tak menular.
    Error lain = GAGAL JUJUR. Model lama: byte-identik."""

    # Memo per-proses: (base_url|'openai', model) -> {param_lama: pengganti|None(=ditanggalkan)}
    _PARAM_ADAPTATIONS: dict = {}

    @staticmethod
    def _parse_param_rejection(err: Exception):
        """Cocokkan KETAT jawaban vendor 400 unsupported-parameter.
        Return (param, pengganti|None) atau None bila bukan kelas error ini."""
        import re
        low = str(err).lower()
        if not (("400" in low) or ("invalid_request" in low)):
            return None
        m = re.search(r"unsupported parameter:?\s*'(\w+)'", low)
        if m:
            m2 = re.search(r"use\s+'(\w+)'\s+instead", low)
            return (m.group(1), m2.group(1) if m2 else None)
        m = re.search(r"'(\w+)'\s+(?:does not support|is not supported)", low)
        if m:
            return (m.group(1), None)
        return None

    def complete(self, *, system, user, model, temperature=0.7, max_tokens=2000,
                 as_json=False) -> str:
        if not self.api_key:
            raise LLMError(f"Provider '{self.display_name}' butuh API key (BYOK).")
        if not model:
            raise LLMError(f"Model untuk '{self.display_name}' tidak ditentukan.")
        # [Fix 2026-07-20] model_key katalog → model_id resmi vendor — SATU pintu utk seluruh
        # pemanggil produksi (menyamakan jalur produksi dgn jalur Uji admin: lolos Uji = pasti jalan).
        model = _catalog.resolve_model_id(model)
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

        # Terapkan adaptasi yang SUDAH dipelajari utk (vendor, model) ini — langsung bersih.
        memo_key = (self.base_url or "openai", model)
        for old, new in (self._PARAM_ADAPTATIONS.get(memo_key) or {}).items():
            if old in body:
                val = body.pop(old)
                if new:
                    body[new] = val

        try:
            client = OpenAI(**kwargs)
            resp = None
            for _attempt in range(4):                      # 1 normal + maks 3 adaptasi (bounded)
                try:
                    resp = client.chat.completions.create(**body)
                    break
                except Exception as e:
                    rej = self._parse_param_rejection(e)
                    if not rej or rej[0] not in body:      # bukan kelas ini / param tak ada → gagal jujur
                        raise
                    old, new = rej
                    from loguru import logger
                    logger.info(f"[LLM] model '{model}' ({memo_key[0]}) menolak `{old}`"
                                f"{f' → pakai `{new}`' if new else ' → ditanggalkan'} (vendor: unsupported) — dimemo")
                    val = body.pop(old)
                    if new:
                        body[new] = val
                    self._PARAM_ADAPTATIONS.setdefault(memo_key, {})[old] = new
            if resp is None:                               # 3 adaptasi tak cukup → jangan berputar
                raise LLMError(f"Provider '{self.display_name}' gagal: parameter model '{model}' "
                               f"tak kunjung diterima setelah adaptasi berulang.")
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
            # [ERROR-MGMT 2026-07-20] klasifikasi ber-bukti-sampel → error_class + pesan manusiawi
            # mengalir terstruktur (rem-cepat FAST_FAIL di hilir membaca MAKNA, bukan teks).
            _ec, _human = _classify_openai_compat_error(e)
            raise LLMError(f"Provider '{self.display_name}' gagal: {e}",
                           error_class=_ec, human_message=_human) from e


class FalAnyLlmAdapter(_BaseAdapter):
    """Protokol fal.ai `any-llm` — SATU kunci fal untuk banyak model (Claude/Gemini/GPT/Llama).

    Beda bentuk dari dua adapter di atas, dan itu disengaja oleh vendornya:
      * bukan percakapan berperan — hanya `prompt` + `system_prompt`, jawaban di field `output`;
      * TIDAK punya mode JSON asli (tak ada `response_format`). JSON diminta lewat instruksi,
        lalu dibaca `parse_json_lenient` — cara yang sama dipakai adapter Anthropic sejak lama.
        Terverifikasi 2026-07-28 pada gpt-4o-mini (JSON bersih) & gemini-2.5-flash + claude-haiku-4.5
        (terbungkus pagar kode, tetap terbaca parser toleran);
      * tarifnya PER PERMINTAAN, bukan per token.

    Model dikirim apa adanya sesuai daftar fal (mis. "anthropic/claude-haiku-4.5"). Model di luar
    daftar dijawab 404 oleh fal → GAGAL JUJUR, tidak pernah diam-diam diganti model lain.
    """

    _BASE = "https://fal.run/fal-ai/any-llm"

    def complete(self, *, system, user, model, temperature=0.7, max_tokens=2000,
                 as_json=False) -> str:
        if not self.api_key:
            raise LLMError(f"Provider '{self.display_name}' butuh API key (BYOK).")
        if not model:
            raise LLMError(f"Model untuk '{self.display_name}' tidak ditentukan.")
        model = _catalog.resolve_model_id(model)
        sistem = system or ""
        if as_json:
            # Tanpa mode JSON asli → tegaskan lewat instruksi (pola sama dgn adapter Anthropic).
            sistem = (sistem + "\n\nJawab HANYA dengan JSON valid. Tanpa penjelasan, "
                               "tanpa pagar kode ```.").strip()
        body = json.dumps({"model": model, "prompt": user, "system_prompt": sistem,
                           "temperature": temperature, "max_tokens": max_tokens}).encode()
        req = urllib.request.Request(
            self.base_url or self._BASE, data=body,
            headers={"Authorization": f"Key {self.api_key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read())
        except Exception as e:
            detail = ""
            if isinstance(e, urllib.error.HTTPError):
                try:
                    detail = e.read()[:300].decode("utf-8", "replace")
                except Exception:
                    detail = ""
            _ec, _human = _classify_openai_compat_error(e)
            raise LLMError(f"Provider '{self.display_name}' gagal: {e} {detail}".strip(),
                           error_class=_ec, human_message=_human) from e
        # fal membalas 200 dengan field `error` terisi bila model menolak → tetap GAGAL JUJUR.
        if data.get("error"):
            raise LLMError(f"Provider '{self.display_name}' gagal: {data['error']}")
        teks = (data.get("output") or "").strip()
        if not teks:
            raise LLMError(f"Provider '{self.display_name}' mengembalikan jawaban kosong.")
        return teks


# Registry PROTOKOL transport (kode). Key = ai_providers.adapter di DB.
ADAPTERS = {
    "anthropic_messages": AnthropicMessagesAdapter,
    "openai_chat":        OpenAIChatAdapter,
    "fal_any_llm":        FalAnyLlmAdapter,
}
