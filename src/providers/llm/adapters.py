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
import re

from src.exceptions import ErrorClass


# [ERROR-MGMT] Penggolongan galat transport OpenAI-compatible.
# ⚠️ TABEL KODENYA TIDAK LAGI DI SINI — seluruh pemetaan pindah ke `src/providers/galat_registry.py`,
# satu-satunya tempat pemetaan galat penyedia AI (ketok owner 12-Agu: "pastikan tidak ada jalur lain
# yang menghandle AI error management"). Menambah vendor/model = menambah DATA di registry, nol koding.
# Latar yang tetap penting dan sudah dipindahkan ke registry sebagai catatan per-vendor:
#   • Batas HARIAN tingkat gratis (Groq `tokens per day`, sampel nyata 01-Agu ×8) SENGAJA bukan
#     QUOTA_EXHAUSTED — kelas itu FAST_FAIL yang MENGHENTIKAN channel & menuntut "Jalankan Ulang"
#     manual, sedangkan jatah harian pulih sendiri; tenant gratis akan terpaksa menekannya tiap hari.
#   • Kode yang sama bisa berbeda arti antar vendor (`quota_exceeded`: harian di Gemini, bulanan di
#     ElevenLabs) — itu sebabnya penilai WAJIB tahu identitas vendornya.
# [2026-08-12] TABEL KODE DIPINDAH ke `src/providers/galat_registry.py` — SATU-SATUNYA tempat pemetaan
# galat penyedia AI (ketok owner: "pastikan tidak ada jalur lain yang menghandle AI error management").
# Yang TINGGAL di berkas ini hanyalah ANJURAN untuk tenant per-golongan (di bawah), karena anjuran itu
# khas-komponen: "penulis naskah" berbeda kalimatnya dari "pembuat gambar" walau golongannya sama.
# Keluarga openai-compatible = penyedia yang memakai adaptor ini (katalog DB: openai · groq · gemini).
_KELUARGA_COMPAT: tuple[str, ...] = ("openai", "groq", "gemini")
_OPENAI_COMPAT_HUMAN = {
    ErrorClass.AUTH_INVALID: "Kunci API AI (penulis naskah) ditolak penyedia. Periksa/perbarui kunci di halaman Integrasi, lalu pastikan Akun (kunci) di setting channel sepadan dengan penyedianya.",
    # [17-Agu] IDENTITAS WAJIB IKUT. Keluhan tenant BISIK NUSANTARA: produksi berhenti dgn kalimat
    # "Model AI ini sudah tidak tersedia" — tanpa menyebut model yang mana. Satu channel memakai TIGA
    # slot AI (naskah · suara · gambar), jadi anjuran "pilih model lain" MUSTAHIL dikerjakan. Padahal
    # vendor sudah menyebutkannya tepat ('The model `llama-3.3-70b-versatile` does not exist'), dan
    # kita memegang ketiganya — penyedia, slot, nama model — lalu membuang semuanya. Ini satu-satunya
    # golongan di tabel ini yang dulu tak menyebut slotnya, justru golongan yang paling membutuhkan.
    # `{ident}` diisi `_anjuran`; kosong (pemanggil lama) → kalimat tetap utuh & tak bocor kerangka.
    ErrorClass.MODEL_UNAVAILABLE: "Model AI penulis naskah{ident} sudah tidak tersedia di penyedianya (dipensiunkan/tak bisa diakses). Pilih model lain di setting channel.",
    ErrorClass.QUOTA_EXHAUSTED: "Kuota/kredit penyedia AI (penulis naskah) sudah habis. Isi saldo/kredit di akun penyedia Anda, lalu Jalankan Ulang.",
    # Pesan UMUM 429: berlaku untuk penyedia mana pun. Varian "jatah harian" hanya dipakai bila
    # penyedianya sendiri menyebutkannya — mengatakan "jatah harian habis" untuk throttle per-menit
    # adalah berbohong kepada tenant, dan ia akan menunggu sampai besok padahal cukup beberapa detik.
    ErrorClass.RATE_LIMIT: "Penyedia AI (penulis naskah) sedang menolak permintaan karena terlalu banyak permintaan dalam waktu singkat. Ini batas di sisi penyedia, bukan masalah di MesinViral. Produksi akan dicoba lagi otomatis.",
}
# Varian pesan bila penyedianya menyebut batas HARIAN (bukan per-menit) — tindakan tenantnya berbeda:
# yang satu cukup ditunggu, yang lain perlu menaikkan paket bila ingin produksi lebih banyak per hari.
_HUMAN_KUOTA_HARIAN = ("Jatah HARIAN penyedia AI (penulis naskah) sudah terpakai habis untuk hari ini "
                       "— ini batas paket penyedia, bukan masalah di MesinViral. Produksi berlanjut "
                       "otomatis setelah jatahnya pulih; bila ingin produksi lebih banyak per hari, "
                       "tingkatkan paket di akun penyedia AI Anda.")
_RX_HARIAN = re.compile(r"per day|daily limit|/day|harian", re.I)


class _Vonis(tuple):
    """(kelas, anjuran) — TETAP bisa di-unpack dua nilai (pemanggil & uji lama tak tersentuh),
    plus `.dasar` untuk yang perlu tahu ASAL putusan. `dasar` inilah pembeda antara "vendor
    menyebut modelnya mati" dan "404 telanjang" — dan tanpa pembeda itu karantina katalog bisa
    mematikan model yang masih hidup (lihat src/orchestrator/karantina_model.py).

    (Tanpa `__slots__`: subkelas `tuple` tak mengizinkannya — Python menolak di waktu impor.)"""

    def __new__(cls, kelas, anjuran, dasar: str = ""):
        obj = super().__new__(cls, (kelas, anjuran))
        obj.dasar = dasar
        return obj


def _classify_openai_compat_error(exc: Exception, penyedia: str = "", *,
                                  model: str = "", penyedia_nama: str = "") -> tuple[ErrorClass, str | None]:
    """Galat transport OpenAI-compatible → (ErrorClass, anjuran untuk tenant).

    Pembungkus tipis di atas `galat_registry.golongkan()` — penggolongannya milik registry, yang
    tinggal di sini hanya ANJURAN khas komponen "penulis naskah". `penyedia` = `ai_providers.
    provider_key`; bila pemanggil tak menyebutkannya, seluruh keluarga adaptor ini dicoba.

    `model` + `penyedia_nama` = IDENTITAS yang dibawa ke kalimat anjuran (17-Agu, keluhan tenant
    BISIK NUSANTARA): tanpa keduanya, "pilih model lain" tak bisa dikerjakan tenant yang punya tiga
    slot AI. Keduanya SUDAH ada di tangan setiap adapter saat galat terjadi — hanya belum diteruskan.

    Tanda tangan lama (satu argumen) SENGAJA tetap sah — dipakai uji-uji yang sudah ada.
    """
    from src.providers.galat_registry import golongkan

    blob = str(exc)
    # Status HTTP dari atribut SDK bila ada (openai/groq/anthropic sama-sama menyediakannya),
    # else dari teks — SDK selalu mencetak "Error code: NNN".
    _status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if _status is None:
        # Bentuk yang dipakai vendor/SDK berbeda-beda: "Error code: 429" (SDK OpenAI-compat),
        # "429 Too Many Requests" (HTTP mentah), "HTTP 503" (transport kita). Regresi nyata:
        # versi pertama hanya membaca bentuk PERTAMA, sehingga 429 mentah jatuh ke UNKNOWN.
        _m = re.search(r"Error code: (\d{3})|HTTP (\d{3})|\b(\d{3}) (?:Too Many|Service|Internal|Bad|Unauthorized|Forbidden|Not Found)", blob)
        _status = int(next((g for g in _m.groups() if g), 0)) or None if _m else None
    _kode = getattr(exc, "code", None) or getattr(exc, "type", None)

    # Vendor yang dicoba: yang diberitahu pemanggil, else seluruh keluarga adaptor ini. Vendor SPESIFIK
    # penting karena kode yang sama bisa berarti hal berbeda antar vendor (mis. `quota_exceeded` =
    # jatah HARIAN di Gemini tapi jatah BULANAN di ElevenLabs) — menebaknya = menasihati tenant salah.
    # Identitas dirakit SEKALI di sini, lalu dipakai cabang mana pun di bawah — mis. " 'gpt-4o' (OpenAI)".
    _ident = _identitas(model, penyedia_nama)
    _kandidat = (penyedia,) if penyedia else _KELUARGA_COMPAT
    for nama in _kandidat:
        p = golongkan(nama, status=_status, kode=_kode, teks=blob)
        if p.dasar.startswith(("kode/teks-vendor", "terusan-agregator")):
            return _Vonis(p.kelas, _anjuran(p.kelas, blob, _ident), p.dasar)

    # Tak ada kode vendor yang cocok → jaring generik (batas berkala · semantik HTTP).
    p = golongkan(penyedia or "", status=_status, kode=_kode, teks=blob)
    return _Vonis(p.kelas, (_anjuran(p.kelas, blob, _ident) if p.kelas is not ErrorClass.UNKNOWN else None), p.dasar)


def _biaya_yang_vendor_sebut(u) -> float | None:
    """[F5, 23-Agu] BIAYA yang vendor sebutkan sendiri untuk panggilan ini, dari objek `usage` yang
    sudah kita terima. None = vendor tidak menyebutkannya (mayoritas penyedia langsung).

    Kenapa hanya `cost`, tanpa nama cadangan: nama kolom yang DITEBAK = kelas cacat yang baru
    ditutup (kolom `output_cost_per_token` bermakna dua hal, dan menerimanya membuat biaya suara 4×
    terlalu murah selama 16 produksi). `cost` diverifikasi ke dokumen resmi OpenRouter (23-Agu):
    selalu dikirim, satuannya *credit*, 1 credit = 1 USD. Vendor lain yang memakai nama berbeda akan
    muncul sebagai "belum terhitung" di laporan harian — BERISIK, bukan salah diam-diam.

    Bentuk balasan bisa objek SDK, dict polos, atau objek pydantic yang menaruh kolom asing di
    `model_extra`. Nilai yang bukan angka diperlakukan seperti TIDAK ADA (jalur jujur), bukan 0
    (gratis palsu)."""
    if u is None:
        return None
    nilai = getattr(u, "cost", None)
    if nilai is None and isinstance(u, dict):
        nilai = u.get("cost")
    if nilai is None:
        extra = getattr(u, "model_extra", None)
        if isinstance(extra, dict):
            nilai = extra.get("cost")
    if nilai is None:
        return None
    try:
        return float(nilai)
    except (TypeError, ValueError):
        return None


def _identitas(model: str, penyedia_nama: str) -> str:
    """" 'nama-model' (Nama Penyedia)" — sisipan yang membuat anjuran BISA DIKERJAKAN tenant.
    Kosong bila keduanya tak diketahui; separuh diketahui tetap lebih baik daripada tak ada."""
    model, penyedia_nama = (model or "").strip(), (penyedia_nama or "").strip()
    if model and penyedia_nama:
        return f" '{model}' ({penyedia_nama})"
    if model:
        return f" '{model}'"
    return f" di {penyedia_nama}" if penyedia_nama else ""


def _anjuran(kelas: ErrorClass, blob: str, ident: str = "") -> str | None:
    """Anjuran untuk tenant — khas komponen 'penulis naskah'. Golongan datang dari registry;
    kalimat anjurannya tinggal di sini karena beda komponen beda tindakan.

    `ident` disisipkan hanya pada kalimat yang menyediakan penampungnya. Kalimat tanpa penampung
    tak tersentuh, dan penampung yang tak terisi TIDAK PERNAH bocor ke mata tenant."""
    if kelas is ErrorClass.RATE_LIMIT and _RX_HARIAN.search(blob):
        return _HUMAN_KUOTA_HARIAN
    pesan = _OPENAI_COMPAT_HUMAN.get(kelas)
    return pesan.replace("{ident}", ident) if pesan else pesan


class _BaseAdapter(LLMProvider):
    """Adapter dibangun oleh factory dari spec DB (ai_providers) + key tenant."""

    def __init__(self, *, api_key: str = "", display_name: str = "",
                 base_url: str | None = None, param_schema: dict | None = None,
                 provider_key: str = ""):
        self.api_key = api_key or ""
        self.display_name = display_name or "LLM provider"
        self.base_url = base_url or None
        self.param_schema = param_schema or {}
        # [2026-08-12] IDENTITAS vendor (`ai_providers.provider_key`) — bukan nama tampilan.
        # Wajib ada karena kode galat yang SAMA berarti hal BERBEDA antar vendor: `quota_exceeded`
        # = jatah HARIAN di Gemini (pulih besok) tapi jatah BULANAN di ElevenLabs (harus upgrade).
        # Tanpa identitas ini penilai harus menebak, dan menebak = menasihati tenant salah.
        self.provider_key = (provider_key or "").strip().lower()

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
            raise LLMError(f"Provider '{self.display_name}' butuh API key (BYOK).", milik_kita=True)
        if not model:
            raise LLMError(f"Model untuk '{self.display_name}' tidak ditentukan.", milik_kita=True)
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
                cost_meter.add_llm(model, getattr(resp.usage, "input_tokens", 0),
                                   getattr(resp.usage, "output_tokens", 0),
                                   penyedia=self.provider_key)
            except Exception:
                pass
            return resp.content[0].text.strip()
        except LLMError:
            raise
        except Exception as e:
            # [2026-08-12] Dulu galat Anthropic TIDAK PERNAH digolongkan — seluruh kegagalan jadi
            # "tak dikenal": diulang 3x walau kunci salah, dan tenant tak diberi tahu apa pun yang
            # bisa dikerjakan. Anthropic satu-satunya vendor dengan kode TAGIHAN tersendiri (402
            # `billing_error`); tanpa penggolongan, itu ikut hilang.
            _vonis = _classify_openai_compat_error(e, self.provider_key, model=model, penyedia_nama=self.display_name)
            _ec, _human = _vonis
            raise LLMError(f"Provider '{self.display_name}' gagal: {e}",
                           error_class=_ec, human_message=_human,
                           dasar=getattr(_vonis, 'dasar', ''), model=model) from e


# ── [18-Agu] Angka JATAH TOKEN — TERUKUR, dan sejak 20-Agu DARI DATABASE ──────────────────────
# Jawaban sah untuk permintaan terbesar (5 topik x 13 keterangan) TERUKUR 1.235-1.280 token.
# Gemini 3.6/3.7/flash-latest: TERPOTONG di 2000, LULUS di 4000 (3x berturut, 18-Agu).
# Groq MENOLAK 8000 — galat 413 "Request too large". Maka 4000 = titik yang menyembuhkan tanpa
# ditolak vendor. Model boleh menyatakan batasnya sendiri lewat `ai_models.default_params`.
#
# [20-Agu] KEDUA ANGKA PINDAH KE `app_config` — teguran owner: "aplikasi ini anda bangun full
# configuration, minim hardcode, semuanya bisa diadjust lewat database (admin panel), ini rancangan
# anda, tapi anda rusak rancangan anda sendiri." BENAR: saya menanamnya sebagai literal 18-Agu,
# beberapa jam setelah mengutip aturan "nilai bisnis dari DB, nol literal di kode". Vendor & model
# berganti generasi terus (2x dalam 3 hari), jadi owner WAJIB bisa menyetelnya tanpa deploy.
# Angka di bawah tinggal sebagai CADANGAN fail-soft: gangguan DB tak boleh melumpuhkan produksi.
_BATAS_JATAH_CADANGAN = 4000
_MIN_JATAH_NAIK_CADANGAN = 2000


def _batas_jatah_global() -> int:
    """Batas atas jatah token — DATA (`app_config.llm_jatah_token_batas_atas`), admin-editable."""
    try:
        from src.config.app_config import get_int
        return get_int("llm_jatah_token_batas_atas", _BATAS_JATAH_CADANGAN)
    except Exception:
        return _BATAS_JATAH_CADANGAN


def _min_jatah_naik() -> int:
    """Lantai kenaikan jatah — DATA (`app_config.llm_jatah_token_kenaikan_min`), admin-editable."""
    try:
        from src.config.app_config import get_int
        return get_int("llm_jatah_token_kenaikan_min", _MIN_JATAH_NAIK_CADANGAN)
    except Exception:
        return _MIN_JATAH_NAIK_CADANGAN


# ── [27-Agu] PENOLAKAN "PERMINTAAN TERLALU BESAR" — VENDOR MENYEBUT BATASNYA SENDIRI ────────────
# KENAPA ADA. Jatah token punya DUA arah gagal, dan sebelum ini mesin hanya mengenal satu:
#   kekecilan → jawaban terpotong  (sudah ditangani di bawah, sejak 18-Agu)
#   kebesaran → vendor MENOLAK     (tak dikenali sama sekali ⇒ produksi tenant mati)
#
# Terukur 27-Agu, kunci Test Lab, `openai/gpt-oss-120b` di Groq — pesan aslinya:
#     413 — Request too large for model `openai/gpt-oss-120b` ... service tier `on_demand`
#           on tokens per minute (TPM): Limit 8000, Requested 8121
# Batasnya BUKAN milik model, melainkan milik AKUN (token per menit), dan vendor menghitung
# PERTANYAAN + JATAH JAWABAN bersama-sama: 121 + 8000 = 8121, lewat 121 token ⇒ ditolak.
#
# KENAPA TIDAK DIPECAHKAN DENGAN SATU ANGKA TETAP (terukur 27-Agu, bukan pendapat):
#   dibutuhkan naskah 90 dtk terpanjang  : 3.790 token
#   diizinkan Groq saat mencoba ulang    : 2.860 token  (prompt membengkak jadi ±5.100 krn umpan balik)
#   3.790 > 2.860 ⇒ angka tetap yang benar TIDAK ADA. Yang benar = HITUNGAN, dan angkanya
#   hanya vendor yang tahu — batas TPM berbeda per akun tenant, per paket, dan berubah kapan saja.
#
# KENAPA MEMBACA PESAN VENDOR, BUKAN MENAKSIR PANJANG PROMPT SENDIRI: alat hitung token
# (`tiktoken`) BUKAN dependensi resmi mesin ini, dan tiap vendor memakai pemenggal token berbeda —
# taksiran kita akan salah. Pesan penolakan memberi angka EKSAK sebagaimana vendor menghitungnya,
# tanpa satu pun panggilan tambahan. Penolakan 413 tidak menghasilkan token ⇒ NOL biaya tenant.
_RX_BATAS_VENDOR = re.compile(r"\blimit\s+(\d+)\s*,\s*requested\s+(\d+)\b", re.I)

# Cadangan kecil: batas TPM dihitung PER MENIT, jadi panggilan lain di menit yang sama ikut memakan
# kuota. Tanpa cadangan, jatah "pas mentok" akan ditolak lagi begitu ada dua panggilan berdempet.
_CADANGAN_TPM = 200


# [27-Agu] GEJALA YANG SAMA, TAPI DILAPORKAN SEBAGAI PENOLAKAN — bukan sebagai jawaban terpotong.
# Groq dalam mode JSON menolak dengan 400 SEBELUM satu pun jawaban dikembalikan, jadi gejala
# "model bernalar menghabiskan jatah" tidak bisa dibaca dari objek jawaban (tak ada objeknya).
# Yang tersisa sebagai bukti: kode `json_validate_failed`/`json_generate_failed` DENGAN
# `failed_generation` KOSONG = vendor sendiri menyatakan tak ada apa pun yang dihasilkan.
# Terukur 27-Agu — pesan aslinya:
#   400 {'message': "Failed to validate JSON...", 'code': 'json_validate_failed', 'failed_generation': ''}
# `failed_generation` yang BERISI = penyakit lain (model menulis JSON cacat) ⇒ sengaja TIDAK
# ditangani di sini; mengekang waktu berpikir takkan menolongnya dan hanya menyamarkan sebabnya.
_RX_NIHIL_DIHASILKAN = re.compile(
    r"json_(?:validate|generate)_failed(?=.*failed_generation['\"]\s*:\s*(?:''|\"\"))", re.I | re.S)


def _gejala_jatah_habis_untuk_berpikir(err: Exception) -> bool:
    """`True` bila vendor menolak dgn menyatakan NOL keluaran dihasilkan (lihat catatan di atas)."""
    try:
        return bool(_RX_NIHIL_DIHASILKAN.search(str(err)))
    except Exception:
        return False


def _batas_yang_vendor_sebut(err: Exception) -> tuple[int, int] | None:
    """`(batas, diminta)` bila vendor menolak karena kebesaran DAN menyebut angkanya; else `None`.

    Sengaja SEMPIT — hanya pola `Limit <n>, Requested <m>` dengan `m > n`. Salah tafsir di sini
    menurunkan jatah tanpa sebab (naskah jadi terpotong), jadi yang RAGU wajib jatuh ke `None`.
    """
    try:
        m = _RX_BATAS_VENDOR.search(str(err))
        if not m:
            return None
        batas, diminta = int(m.group(1)), int(m.group(2))
        return (batas, diminta) if 0 < batas < diminta else None
    except Exception:
        return None


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
    # Memo jatah token yang SUDAH terbukti perlu — kunci (vendor, model, JATAH-YANG-DIMINTA).
    # Jatah-yang-diminta IKUT jadi kunci dengan sengaja: tiap tugas punya ukuran jawaban sendiri
    # (penilai naskah 500 · hook 1.200 · seleksi topik 2.000). Tanpa itu, pelajaran dari tugas
    # besar menular ke tugas kecil dan model diberi ruang bicara jauh di atas rancangannya.
    # Pola sama dgn _PARAM_ADAPTATIONS: belajar sekali, panggilan berikutnya langsung bersih.
    _JATAH_NAIK: dict = {}

    # [27-Agu] Model bernalar yang terbukti menghabiskan jatah untuk BERPIKIR (jawaban kosong).
    # Pola sama: belajar sekali dari gejalanya, panggilan berikutnya langsung dikekang.
    _KEKANG_NALAR: dict = {}

    @staticmethod
    def _terpotong(resp) -> bool:
        """Vendor MENYATAKAN jawabannya terpotong. Fail-safe: bentuk tak dikenal → BUKAN terpotong
        (yang RAGU tidak boleh memicu percobaan berbayar)."""
        try:
            alasan = str(getattr(resp.choices[0], "finish_reason", "") or "").lower()
        except Exception:
            return False
        return alasan in ("length", "max_tokens")

    @staticmethod
    def _token_berpikir(resp) -> int:
        """Token yang dipakai model untuk BERPIKIR di dalam (bukan menjawab). 0 = tak dilaporkan.

        Vendor melaporkannya di `usage.completion_tokens_details.reasoning_tokens` (protokol OpenAI).
        Fail-soft: vendor yang tak melaporkannya tidak boleh mengubah perilaku apa pun.
        """
        try:
            d = getattr(getattr(resp, "usage", None), "completion_tokens_details", None)
            return int(getattr(d, "reasoning_tokens", 0) or 0)
        except Exception:
            return 0

    @staticmethod
    def _batas_model_dinyatakan(model: str) -> int | None:
        """Batas yang MODEL nyatakan sendiri (`ai_models.default_params.max_output_tokens`).

        `None` = model tidak menyatakan apa pun — BUKAN sama dengan "batasnya angka cadangan".
        Perbedaan itu penting: batas yang dinyatakan MENGIKAT (haram dilewati), sedangkan cadangan
        global hanya titik awal yang boleh diperlebar lalu dikoreksi vendor.
        """
        try:
            nilai = ((_catalog.get_models() or {}).get(model) or {}).get("default_params") or {}
            n = nilai.get("max_output_tokens")
            return int(n) if n and int(n) > 0 else None
        except Exception:
            return None

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
            raise LLMError(f"Provider '{self.display_name}' butuh API key (BYOK).", milik_kita=True)
        if not model:
            raise LLMError(f"Model untuk '{self.display_name}' tidak ditentukan.", milik_kita=True)
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
        # Jatah yang sudah terbukti perlu (dipelajari dari jawaban terpotong sebelumnya) dipakai
        # SEJAK AWAL — hanya untuk permintaan JSON, dan hanya bila LEBIH BESAR (nol penurunan).
        _jatah_diminta = max_tokens
        if as_json:
            _memo_jatah = self._JATAH_NAIK.get((memo_key, _jatah_diminta))
            if _memo_jatah and _memo_jatah > body.get("max_tokens", 0):
                body["max_tokens"] = _memo_jatah
                max_tokens = _memo_jatah
        # Kekangan berpikir yang SUDAH terbukti perlu untuk (vendor, model) ini — langsung bersih,
        # tanpa mengulang satu panggilan kosong lagi.
        _memo_nalar = self._KEKANG_NALAR.get(memo_key)
        if _memo_nalar:
            body["reasoning_effort"] = _memo_nalar
        for old, new in (self._PARAM_ADAPTATIONS.get(memo_key) or {}).items():
            if old in body:
                val = body.pop(old)
                if new:
                    body[new] = val

        try:
            client = OpenAI(**kwargs)
            resp = None
            # Langit-langit yang VENDOR sebutkan sendiri saat menolak kebesaran (None = belum tahu).
            # Dipakai juga oleh jaring "jawaban terpotong" di bawah, supaya ia tak menaikkan jatah
            # kembali ke angka yang baru saja ditolak — itu akan berputar antara dua kegagalan.
            _langit_akun = None
            _kekang_dipakai = False        # kekangan berpikir dipasang di tengah jalan?
            for _attempt in range(4):                      # 1 normal + maks 3 adaptasi (bounded)
                try:
                    resp = client.chat.completions.create(**body)
                    break
                except Exception as e:
                    rej = self._parse_param_rejection(e)
                    if not rej or rej[0] not in body:      # bukan kelas ini / param tak ada
                        # ── [27-Agu] VENDOR MENOLAK: PERMINTAAN KEBESARAN ───────────────────────
                        # Vendor menyebut batas & jumlah yang diminta. Dari dua angka itu panjang
                        # pertanyaan terhitung EKSAK (sebagaimana vendor menghitungnya), jadi jatah
                        # yang pas bisa dihitung — bukan ditebak, bukan ditetapkan admin.
                        # ── [27-Agu] Vendor menolak & menyatakan NOL keluaran dihasilkan:
                        # jatah habis untuk BERPIKIR. Kekang waktu berpikirnya, lalu ulangi SEKALI.
                        if (_gejala_jatah_habis_untuk_berpikir(e)
                                and "reasoning_effort" not in body):
                            from loguru import logger
                            logger.warning(
                                f"[LLM] '{model}' ({memo_key[0]}): vendor menyatakan NOL keluaran "
                                f"dihasilkan pada jatah {max_tokens} → diulang sekali dengan waktu "
                                f"berpikir dikekang (reasoning_effort=low)")
                            body["reasoning_effort"] = "low"
                            _kekang_dipakai = True
                            continue
                        _kb = _batas_yang_vendor_sebut(e)
                        if _kb:
                            _batas_akun, _diminta_vendor = _kb
                            _terkirim = next((body[_k] for _k in ("max_tokens", "max_completion_tokens")
                                              if _k in body), max_tokens)
                            _prompt_tok = max(_diminta_vendor - _terkirim, 0)
                            _pas = _batas_akun - _prompt_tok - _CADANGAN_TPM
                            if _pas > 0 and _langit_akun is None:
                                _langit_akun = _pas
                                from loguru import logger
                                logger.warning(
                                    f"[LLM] '{model}' ({memo_key[0]}): vendor MENOLAK jatah {_terkirim} "
                                    f"(batas akun {_batas_akun}/menit, pertanyaan {_prompt_tok}) → "
                                    f"diulang dengan {_pas} — angka dari vendor, bukan tebakan")
                                for _k in ("max_tokens", "max_completion_tokens"):
                                    if _k in body:
                                        body[_k] = _pas
                                max_tokens = _pas
                                continue
                            # Sudah diturunkan dan MASIH ditolak, atau pertanyaannya sendiri sudah
                            # melebihi batas akun ⇒ menurunkan lagi tak menolong. Gagal JUJUR, dan
                            # sebutkan tindakan yang benar-benar ada di tangan tenant.
                            raise LLMError(
                                f"Provider '{self.display_name}' menolak permintaan: batas akun "
                                f"{_batas_akun} token/menit, pertanyaan {_prompt_tok} token.",
                                error_class=ErrorClass.QUOTA_EXHAUSTED,
                                human_message=(
                                    f"Paket penyedia AI Anda ({self.display_name}) hanya mengizinkan "
                                    f"{_batas_akun} token per menit — tidak cukup untuk menulis naskah "
                                    f"sepanjang ini. Naikkan paket di penyedia tersebut, pilih preset "
                                    f"durasi yang lebih pendek, atau pilih penyedia lain."),
                                model=model) from e
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
            def _catat(r):
                try:
                    from src.utils import cost_meter
                    u = getattr(r, "usage", None)
                    cost_meter.add_llm(model, getattr(u, "prompt_tokens", 0),
                                       getattr(u, "completion_tokens", 0),
                                       penyedia=self.provider_key)
                    # [F5] Penyedia router (OpenRouter dst) menyebutkan BIAYA panggilan ini di objek
                    # usage yang sama — nol panggilan tambahan. Bila disebut, biaya itu yang dipakai
                    # (bukan taksiran token), dan yang menentukan mana yang ditagih adalah FORMULA
                    # di baris modelnya ⇒ mustahil tertagih dua kali.
                    biaya = _biaya_yang_vendor_sebut(u)
                    if biaya is not None:
                        cost_meter.add_biaya_vendor(model, biaya, penyedia=self.provider_key)
                except Exception:
                    pass

            _catat(resp)
            if _kekang_dipakai and (resp.choices[0].message.content or "").strip():
                # Terbukti menolong ⇒ dimemo: panggilan berikutnya tak membayar percobaan kosong lagi.
                self._KEKANG_NALAR[memo_key] = "low"

            # ── [27-Agu] MODEL BERNALAR MENGHABISKAN JATAH UNTUK BERPIKIR ────────────────────────
            # AKAR kegagalan 10 produksi 18–26 Agu (BISIK NUSANTARA · RETRO REWIND GARAGE ·
            # JaydenSaverio · Bang Us-Dat) — terukur 27-Agu pada `openai/gpt-oss-120b` di Groq
            # dengan prompt naskah SUNGGUHAN:
            #     finish_reason=length · isi jawaban 0 huruf · reasoning_tokens 4.498 dari 4.500
            # Model bernalar memakai SELURUH jatah untuk berpikir di dalam; jawabannya tak pernah
            # dimulai. Vendor lalu menolak dengan `json_validate_failed` / `json_generate_failed`
            # ber-`failed_generation: ''` — itulah pesan yang selama ini terlihat di layar tenant.
            #
            # MENAIKKAN JATAH TIDAK MENOLONG — diuji: 4.500 dan 8.000 dua-duanya menghasilkan
            # jawaban KOSONG, ia hanya berpikir lebih lama. Yang menolong: MENGEKANG waktu berpikir.
            #     reasoning_effort="low" → berpikir 1.270 · jawaban UTUH 2.869 huruf · finish=stop
            #
            # Dikenali dari GEJALA, bukan dari nama model atau daftar vendor: jawaban KOSONG +
            # jatah habis + ada token berpikir. Model bernalar yang BELUM ADA hari ini ikut
            # tertangani tanpa satu pun suntingan kode, dan nol kenop yang harus admin tetapkan.
            # Sengaja TIDAK dibatasi `as_json`: jawaban kosong tak berguna dalam mode apa pun.
            # Jawaban yang terpotong tapi ADA ISINYA sama sekali tidak tersentuh (mis. pemanggil
            # judul/prompt gambar) — syarat "kosong" yang memisahkannya.
            if (self._terpotong(resp)
                    and (as_json or not (resp.choices[0].message.content or "").strip())
                    and self._token_berpikir(resp) > 0
                    and "reasoning_effort" not in body):
                from loguru import logger
                logger.warning(
                    f"[LLM] '{model}' ({memo_key[0]}): jawaban KOSONG — "
                    f"{self._token_berpikir(resp)} dari {max_tokens} token habis untuk BERPIKIR. "
                    f"Diulang sekali dengan waktu berpikir dikekang (reasoning_effort=low).")
                body["reasoning_effort"] = "low"
                try:
                    _r2 = client.chat.completions.create(**body)
                    if (_r2.choices[0].message.content or "").strip():
                        # Terbukti menolong ⇒ dimemo: panggilan berikutnya tak membayar percobaan
                        # kosong lagi. Pola sama dgn `_PARAM_ADAPTATIONS`/`_JATAH_NAIK` yang sudah ada.
                        self._KEKANG_NALAR[memo_key] = "low"
                        resp = _r2
                        _catat(resp)
                    else:
                        body.pop("reasoning_effort", None)
                except Exception as _e3:
                    # Vendor tak mengenal kekangan ini (atau menolak) ⇒ JANGAN dipaksakan dan jangan
                    # dimemo. Kembalikan permintaan ke bentuk semula; galat jujur di bawah tetap jalan.
                    body.pop("reasoning_effort", None)
                    logger.warning(f"[LLM] '{model}' ({memo_key[0]}): kekangan berpikir tak diterima "
                                   f"vendor — tak dimemo. Sebab: {str(_e3)[:120]}")

            # ── [18-Agu] JAWABAN TERPOTONG: naikkan jatahnya, JANGAN ulangi yang sama ────────────
            # Jatah token = SATU kantong untuk berpikir + menjawab. Model generasi baru memakainya
            # untuk berpikir, jawabannya terpotong, JSON gugur. Pemanggil lalu mengulang permintaan
            # IDENTIK 3x (terukur pada kegagalan tenant BISIK NUSANTARA): tenant ditagih 3x untuk
            # sesuatu yang MUSTAHIL berhasil, dan diberi tahu sebab yang salah.
            #
            # Ditangani DI SINI, bukan di 11 pemanggil: satu tempat, langsung benar untuk seluruh
            # jalur (seleksi topik · penulis naskah · penilai · hook · analis) dan untuk vendor yang
            # BELUM ADA. Riwayat: mekanisme ini saya temukan sendiri di `ede8a88` (16-Jul) lalu
            # HANYA diperbaiki di jalur uji — inilah separuh yang tertinggal.
            #
            # Hanya untuk permintaan JSON: JSON separuh tak terpakai, sedangkan teks biasa yang
            # terpotong masih berguna (pemanggil judul/kalimat pendek) ⇒ perilakunya tak disentuh.
            if as_json and self._terpotong(resp):
                # [27-Agu] LANGIT-LANGIT: angka yang VENDOR sebutkan saat menolak MENGALAHKAN angka
                # mana pun di katalog/app_config — ia satu-satunya yang mengikat, dan ia milik AKUN
                # tenant ini (batas token/menit), bukan milik modelnya. Selama vendor belum bicara,
                # ruang naik dibuka 2x dari yang diminta; bila kelewatan, vendor sendiri yang
                # mengoreksinya di bawah. ⇒ nol angka yang harus admin tetapkan, nol angka basi.
                # Dua langit-langit yang MENGIKAT: yang model nyatakan sendiri di katalog, dan
                # yang vendor sebut saat menolak. Yang terkecil menang. Bila TAK SATU PUN ada,
                # barulah ruang dibuka (2x yang diminta) — dan bila itu kelewatan, vendor sendiri
                # yang mengoreksinya lewat penolakan di atas.
                _pengikat = [x for x in (_langit_akun, self._batas_model_dinyatakan(model))
                             if x is not None]
                _batas = (min(_pengikat) if _pengikat
                          else max(_batas_jatah_global(), max_tokens * 2))
                _naik = min(max(max_tokens * 2, _min_jatah_naik()), _batas)
                if _naik > max_tokens:
                    from loguru import logger
                    logger.warning(f"[LLM] '{model}' ({memo_key[0]}): jawaban TERPOTONG pada jatah "
                                   f"{max_tokens} → diulang dengan {_naik} (sekali, berbatas {_batas})")
                    # Dimemo: panggilan berikutnya dalam proses ini LANGSUNG memakai jatah besar —
                    # tanpa ini, tiap percobaan pemanggil membayar dua kali (boros yang kita cabut).
                    self._JATAH_NAIK[(memo_key, _jatah_diminta)] = _naik
                    for _k in ("max_tokens", "max_completion_tokens"):
                        if _k in body:
                            body[_k] = _naik
                    try:
                        resp = client.chat.completions.create(**body)
                        _catat(resp)
                    except Exception as _e2:
                        # Kenaikan itu sendiri ditolak vendor karena kebesaran ⇒ TIDAK ADA ruang
                        # lagi. Haram berputar antara "terpotong" dan "ditolak": simpan langit-langit
                        # yang vendor sebut, batalkan kenaikan, dan laporkan jujur di bawah.
                        _kb2 = _batas_yang_vendor_sebut(_e2)
                        if not _kb2:
                            raise
                        self._JATAH_NAIK.pop((memo_key, _jatah_diminta), None)
                        _langit_akun = _kb2[0] - max(_kb2[1] - _naik, 0) - _CADANGAN_TPM
                        _naik = max_tokens
                else:
                    # Tak ada ruang naik sama sekali → pesan galat WAJIB menyebut jatah yang
                    # SESUNGGUHNYA dipakai, bukan angka langit-langit yang tak pernah terkirim.
                    _naik = max_tokens
                if self._terpotong(resp):
                    # Sudah di jatah tertinggi dan MASIH terpotong ⇒ model ini memang tak sanggup
                    # menyelesaikan permintaan sebesar ini. Terukur 18-Agu: GPT-OSS 20B menghabiskan
                    # 4000 token dan hanya menghasilkan 2 dari 5 topik. Gagal JUJUR + tenant diberi
                    # tahu tindakannya (ganti model) — bukan dibiarkan menebak.
                    raise LLMError(
                        f"Provider '{self.display_name}' gagal: jawaban model '{model}' terpotong "
                        f"pada jatah {_naik} token (batas {_batas}).",
                        # UNKNOWN = perilaku lama, dipertahankan persis; hanya kasus langit-langit
                        # AKUN yang berpindah kelas, sebab di situ mengulang MUSTAHIL menolong.
                        error_class=(ErrorClass.QUOTA_EXHAUSTED if _langit_akun is not None
                                     else ErrorClass.UNKNOWN),
                        human_message=(
                            (f"Paket penyedia AI Anda ({self.display_name}) tidak menyisakan ruang "
                             f"cukup untuk menulis naskah sepanjang ini. Naikkan paket di penyedia "
                             f"tersebut, pilih preset durasi yang lebih pendek, atau pilih penyedia lain.")
                            if _langit_akun is not None else
                            (f"Model AI penulis naskah '{model}' tidak sanggup "
                             f"menyelesaikan permintaan ini — jawabannya selalu terpotong. "
                             f"Pilih model lain di setting channel.")))
            return (resp.choices[0].message.content or "").strip()
        except LLMError:
            raise
        except Exception as e:
            # [ERROR-MGMT 2026-07-20] klasifikasi ber-bukti-sampel → error_class + pesan manusiawi
            # mengalir terstruktur (rem-cepat FAST_FAIL di hilir membaca MAKNA, bukan teks).
            _vonis = _classify_openai_compat_error(e, self.provider_key, model=model, penyedia_nama=self.display_name)
            _ec, _human = _vonis
            raise LLMError(f"Provider '{self.display_name}' gagal: {e}",
                           error_class=_ec, human_message=_human,
                           dasar=getattr(_vonis, 'dasar', ''), model=model) from e


class FalAnyLlmAdapter(_BaseAdapter):
    """Protokol naskah fal.ai — SATU kunci fal untuk banyak model (Claude/Gemini/GPT/Llama).

    Beda bentuk dari dua adapter di atas, dan itu disengaja oleh vendornya:
      * bukan percakapan berperan — hanya `prompt` + `system_prompt`, jawaban di field `output`;
      * TIDAK punya mode JSON asli (tak ada `response_format`). JSON diminta lewat instruksi,
        lalu dibaca `parse_json_lenient` — cara yang sama dipakai adapter Anthropic sejak lama.
        Terverifikasi 2026-07-28 & diulang 2026-08-16 pada ketiga model (kunci JSON lengkap);
      * membalas HTTP 200 dengan field `error` terisi bila permintaannya ditolak — jalur galat
        KEDUA yang wajib digolongkan sama seriusnya dengan galat transport.

    [2026-08-16] ALAMAT DIPINDAH — endpoint lama `fal-ai/any-llm` DIPENSIUNKAN vendornya
    ("This endpoint is deprecated. This model is no longer supported.", dokumen resmi fal dibaca
    2026-08-16). Penggantinya masih didukung, dan bedanya menentukan bagi kita: ia MELAPORKAN
    pemakaian token, sehingga tabel harga otomatis punya angka untuk dikalikan. Endpoint lama tak
    melaporkan apa pun dan bertarif per-permintaan — di atasnya, biaya tenant mustahil dilacak.

    ⚠️ `ai_providers.base_url` milik penyedia `fal` SENGAJA TIDAK dipakai di sini: kolom itu berisi
    alamat ANTREAN jalur VISUAL (`queue.fal.run`, dipakai ai_image/ai_video). Sejak migrasi 0180
    menyatukan tiga baris penyedia fal jadi satu, jalur naskah ikut memungutnya dan memanggil alamat
    yang salah → HTTP 404 pada panggilan PERTAMA (terbukti 2026-08-16). Alamat protokol = milik
    ADAPTER, pola yang sudah dipakai adaptor suara fal & ElevenLabs.

    Model dikirim apa adanya sesuai daftar fal (mis. "anthropic/claude-haiku-4.5"). Model di luar
    daftar dijawab 404 oleh fal → GAGAL JUJUR, tidak pernah diam-diam diganti model lain.
    """

    _BASE = "https://fal.run/openrouter/router"

    def complete(self, *, system, user, model, temperature=0.7, max_tokens=2000,
                 as_json=False) -> str:
        if not self.api_key:
            raise LLMError(f"Provider '{self.display_name}' butuh API key (BYOK).", milik_kita=True)
        if not model:
            raise LLMError(f"Model untuk '{self.display_name}' tidak ditentukan.", milik_kita=True)
        model = _catalog.resolve_model_id(model)
        sistem = system or ""
        if as_json:
            # Tanpa mode JSON asli → tegaskan lewat instruksi (pola sama dgn adapter Anthropic).
            sistem = (sistem + "\n\nJawab HANYA dengan JSON valid. Tanpa penjelasan, "
                               "tanpa pagar kode ```.").strip()
        body = json.dumps({"model": model, "prompt": user, "system_prompt": sistem,
                           "temperature": temperature, "max_tokens": max_tokens}).encode()
        # Alamat = milik ADAPTER (lihat docstring): `base_url` penyedia `fal` adalah antrean VISUAL.
        req = urllib.request.Request(
            self._BASE, data=body,
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
            _vonis = _classify_openai_compat_error(e, self.provider_key, model=model, penyedia_nama=self.display_name)
            _ec, _human = _vonis
            raise LLMError(f"Provider '{self.display_name}' gagal: {e} {detail}".strip(),
                           error_class=_ec, human_message=_human,
                           dasar=getattr(_vonis, 'dasar', ''), model=model) from e
        # B2 cost-tracking: usage menumpang di respons yg sama (nol overhead). Fail-soft.
        # Dicatat SEBELUM cabang galat — permintaan yang ditolak pun sudah memakai uang tenant
        # (pola yang sama dipakai pipeline: "run gagal pun uang TERPAKAI — tetap dicatat").
        try:
            from src.utils import cost_meter
            u = data.get("usage") or {}
            cost_meter.add_llm(model, int(u.get("prompt_tokens") or 0),
                               int(u.get("completion_tokens") or 0),
                               penyedia=self.provider_key)
        except Exception:
            pass
        # fal membalas 200 dengan field `error` terisi bila model menolak → tetap GAGAL JUJUR.
        # [2026-08-16] Golongannya WAJIB ikut: tanpa itu galat jatuh ke UNKNOWN = boleh-diulang,
        # sehingga saldo tenant yang habis (`Exhausted balance`, sampel nyata fal) memakan 3 produksi
        # sebelum channel direm — padahal QUOTA_EXHAUSTED ∈ FAST_FAIL mengerem setelah SATU kegagalan
        # dan memberi tahu tenant apa yang harus ia lakukan. Penilainya SATU, yang sudah dipakai
        # cabang galat transport di bawah — bukan penilai kedua.
        if data.get("error"):
            _pesan = str(data["error"])
            _vonis = _classify_openai_compat_error(Exception(_pesan), self.provider_key, model=model, penyedia_nama=self.display_name)
            _ec, _human = _vonis
            raise LLMError(f"Provider '{self.display_name}' gagal: {_pesan}",
                           error_class=_ec, human_message=_human,
                           dasar=getattr(_vonis, 'dasar', ''), model=model)
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
