"""SATU-SATUNYA tempat pemetaan galat penyedia AI → makna MesinViral.

═══════════════════════════════════════════════════════════════════════════════════════════════════
KENAPA BERKAS INI ADA (ketok owner 2026-08-11/12)
Sebelum ini ada EMPAT penilai galat tersebar (naskah · suara · gambar · dua tambahan). Menambah
vendor = menulis fungsi penilai baru = kesempatan baru untuk salah. Akibatnya terukur: gejala yang
IDENTIK — jatah gratis harian tenant habis — ditangani berbeda-beda tergantung vendor & komponennya.
Jalur naskah benar; jalur gambar sempat menyuruh tenant "isi ulang saldo" untuk jatah gratis yang
pulih sendiri tengah malam. Owner: *"satu gejala, tiga perlakuan berbeda — ini perbuatan goblok."*

KONSEP DASAR YANG DISEPAKATI — dilarang ditawar:
  1. Pemetaan per GOLONGAN, TIDAK PERNAH per nama vendor. Semua layar/Telegram/rem membaca golongan
     (`AI_ERROR_MANAGEMENT_ARCHITECTURE.md §9`), jadi vendor baru otomatis dapat pesan + perilaku
     benar tanpa satu baris kode tampilan baru.
  2. Pesan yang tenant baca = **kalimat vendor apa adanya**. Tidak diterjemahkan, tidak dikarang,
     tidak dipotong (ketok owner 08-Agu: akan ada ratusan model; aslinya lebih informatif).
  3. Kode galat diperlakukan menurut **aturan MesinViral** (7 golongan), bukan menurut kata-kata vendor.
  4. Sumber pemetaan = **DOKUMEN RESMI vendor, dibaca SEBELUM vendor dinyalakan** (§1 Aturan Emas).
     Tiap penyedia di bawah membawa `sumber` + `dibaca`. Menunggu tenant rusak = pelanggaran.
  5. Vendor/model baru = **menambah DATA di bawah**, bukan menulis kode.
  6. Yang belum dipetakan tidak boleh lewat diam-diam — dijaga `tests/test_galat_generik.py`.

⚠️ PELAJARAN YANG MENGUNCI SEMUANYA: hampir SETIAP vendor memakai **HTTP 429 untuk dua hal
   berlawanan** — batas yang pulih sendiri vs saldo yang harus diisi. Memetakan dari status HTTP saja
   = menghentikan channel tenant atas dasar yang salah, atau menyuruh menunggu sesuatu yang tak akan
   pernah pulih. Karena itu kode SPESIFIK selalu dicoba lebih dulu, status HTTP hanya jaring terakhir.

🔀 AGREGATOR (fal.ai hari ini; blackbox.ai dsb. ke depan) meneruskan galat vendor DI BALIKNYA. Karena
   itu ada penanda `agregator` + tipe `_TERUSAN`: bila galat ternyata milik lapis bawah, teks-nya
   disisir ulang memakai penanda SEMUA vendor. Agregator baru cukup menambah data + penanda.
═══════════════════════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import re
from typing import NamedTuple

from src.exceptions import ErrorClass

# Golongan bila benar-benar tak dikenali: UNKNOWN = boleh diulang = perilaku lama, aman.
_AMAN = ErrorClass.UNKNOWN


class Putusan(NamedTuple):
    """Hasil penggolongan. `pesan` = kalimat VENDOR apa adanya (None bila tak ada)."""
    kelas: ErrorClass
    pesan: str | None
    milik_kita: bool
    dasar: str           # dari mana putusan ini: kode / teks / terusan / status-http / tak-dikenal


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# JARING TERAKHIR — semantik HTTP yang berlaku untuk vendor MANA PUN, termasuk yang belum ada
# hari ini. Ini yang membuat vendor baru langsung berperilaku waras walau datanya belum lengkap;
# ia TIDAK menggantikan kewajiban memetakan (pagar uji tetap menuntut).
# 429 sengaja → RATE_LIMIT (boleh diulang): salah-rem jauh lebih mahal daripada satu percobaan lebih.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
_STATUS_UMUM: dict[int, ErrorClass] = {
    # SENGAJA SEMPIT — hanya status yang maknanya TIDAK MUNGKIN salah tafsir lintas vendor.
    # 5xx / 408 / 422 / 409 DIKELUARKAN dengan sadar: keputusan owner yang sudah berlaku adalah
    # "yang RAGU tetap UNKNOWN" (dijaga `tests/test_kelas_error_visual.py` &
    # `tests/test_error_429_generik.py`). Vendor yang dokumennya MENYEBUT arti status itu tetap
    # tertangani lewat tabelnya sendiri di bawah (mis. Anthropic `api_error`, fal `internal_error`,
    # ElevenLabs `service_unavailable`) — jadi ketelitian TIDAK hilang, hanya tidak ditebak untuk
    # vendor yang belum dipetakan. Melebarkan jaring ini = mengubah perilaku-saat-gagal = butuh ketok owner.
    401: ErrorClass.AUTH_INVALID,
    402: ErrorClass.ACCOUNT_BILLING,
    403: ErrorClass.AUTH_INVALID,
    404: ErrorClass.MODEL_UNAVAILABLE,
    429: ErrorClass.RATE_LIMIT,
}
# Status yang menandakan permintaan KITA cacat (bukan akun tenant) — haram ditimpakan ke tenant.
_STATUS_MILIK_KITA: frozenset[int] = frozenset({413})

# Kalimat vendor yang menandakan batas BERKALA (harian/periodik) — pulih sendiri saat jatah berganti.
# Dipakai untuk vendor yang TIDAK menerbitkan kode rinci (mis. Groq: hanya status HTTP + kalimat).
_RX_BERKALA = re.compile(r"per day|tokens per day|\bTPD\b|\bRPD\b|daily limit|/day|per hari|harian",
                         re.I)

# Tipe agregator yang berarti "ini galat vendor DI BALIK saya, saya hanya meneruskan".
_TERUSAN: frozenset[str] = frozenset({"downstream_service_error", "downstream_service_unavailable"})


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# DATA PER PENYEDIA — inilah yang ditambah saat vendor/model baru masuk. Nol kode baru.
#   kode  : kode/status resmi vendor (paling spesifik, dicoba pertama)
#   teks  : potongan kalimat yang PASTI (dari dokumen resmi ATAU sampel produksi nyata)
#   kita  : penanda "permintaan KITA yang cacat" — dokumen vendor sendiri yang menyatakannya
# ═══════════════════════════════════════════════════════════════════════════════════════════════
PENYEDIA: dict[str, dict] = {

    # ── Cloudflare Workers AI (jalur GAMBAR; 6 channel aktif) ────────────────────────────────
    "cloudflare": {
        "sumber": "https://developers.cloudflare.com/workers-ai/platform/errors/",
        "dibaca": "2026-08-11",
        "catatan": ("Balasan berbentuk DAFTAR `{\"errors\":[{\"code\":N}]}`. 3036 (jatah gratis "
                    "harian 10.000 neuron) dan 3040 (kapasitas sesaat) DUA-DUANYA HTTP 429."),
        "kode": {
            3036: ErrorClass.RATE_LIMIT,          # 429 · jatah harian habis → pulih besok UTC
            3040: ErrorClass.TRANSIENT,           # 429 · kapasitas penuh sesaat
            3007: ErrorClass.TRANSIENT,           # 408 · timeout
            3008: ErrorClass.TRANSIENT,           # 408 · aborted
            3023: ErrorClass.ACCOUNT_BILLING,     # 403 · akun diblokir
            5035: ErrorClass.ACCOUNT_BILLING,     # 403 · model menuntut Workers PAID
            5016: ErrorClass.AUTH_INVALID,        # 403 · syarat model belum disetujui tenant
            5018: ErrorClass.AUTH_INVALID,        # 403 · akun tak diizinkan (model privat)
            3041: ErrorClass.AUTH_INVALID,        # 403 · idem
            5007: ErrorClass.MODEL_UNAVAILABLE,   # 400 · "No such model or task"
            3042: ErrorClass.MODEL_UNAVAILABLE,   # 404 · model ID tak sah
            5005: ErrorClass.MODEL_UNAVAILABLE,   # 405 · model tak mendukung LoRa
        },
        "kita": {3003, 5004, 3006, 5019, 3039},   # dokumen CF: permintaan kita cacat/kebesaran
    },

    # ── Google Gemini (naskah via openai_chat · jalur gambar sendiri) ─────────────────────────
    "gemini": {
        "sumber": "https://ai.google.dev/gemini-api/docs/api-errors",
        "dibaca": "2026-08-11",
        "catatan": ("`resource_exhausted` menaungi jatah HARIAN dan batas PER-MENIT sekaligus; tanpa "
                    "kode spesifik dipilih yang boleh diulang supaya tak pernah salah-rem."),
        "kode": {
            "quota_exceeded":      ErrorClass.RATE_LIMIT,        # 429 · jatah harian → pulih besok
            "rate_limit_exceeded": ErrorClass.RATE_LIMIT,        # 429 · per-menit
            "resource_exhausted":  ErrorClass.RATE_LIMIT,        # 429 · ambigu → konservatif
            "failed_precondition": ErrorClass.ACCOUNT_BILLING,   # 400 · prasyarat tagihan
            "authentication":      ErrorClass.AUTH_INVALID,      # 401
            "unauthenticated":     ErrorClass.AUTH_INVALID,      # 401
            "permission_denied":   ErrorClass.AUTH_INVALID,      # 403
            "model_not_found":     ErrorClass.MODEL_UNAVAILABLE,  # 404
            "not_found":           ErrorClass.MODEL_UNAVAILABLE,  # 404
            "service_unavailable": ErrorClass.TRANSIENT,          # 503
            "unavailable":         ErrorClass.TRANSIENT,          # 503
            "deadline_exceeded":   ErrorClass.TRANSIENT,          # 504
            "api_error":           ErrorClass.TRANSIENT,          # 500
            "internal":            ErrorClass.TRANSIENT,          # 500
        },
        "kita": {"invalid_request", "invalid_argument", "parameter_unknown", "out_of_range"},
        "teks": [("is no longer available", ErrorClass.MODEL_UNAVAILABLE)],  # sampel nyata 21-Jul
    },

    # ── OpenAI (naskah · gambar · suara; 4 channel aktif) ─────────────────────────────────────
    "openai": {
        "sumber": "https://developers.openai.com/api/docs/guides/error-codes",
        "dibaca": "2026-08-12",
        "catatan": ("Dokumen memisahkan SALDO habis (`credit_balance_exhausted`) dari BATAS PEMAKAIAN "
                    "(`organization_usage_limit_exceeded`); keduanya 429. Beberapa galat (kunci salah, "
                    "beban server) tak diberi nama kode di dokumen → ditangkap status HTTP + sampel."),
        "kode": {
            "credit_balance_exhausted":          ErrorClass.QUOTA_EXHAUSTED,  # saldo habis → tindak
            "insufficient_quota":                ErrorClass.QUOTA_EXHAUSTED,  # sampel nyata
            "organization_usage_limit_exceeded": ErrorClass.RATE_LIMIT,       # batas pakai → pulih
            "rate_limit_exceeded":               ErrorClass.RATE_LIMIT,
            "invalid_api_key":                   ErrorClass.AUTH_INVALID,     # sampel nyata
            "model_not_found":                   ErrorClass.MODEL_UNAVAILABLE,
            "billing_hard_limit_reached":        ErrorClass.ACCOUNT_BILLING,  # sampel nyata (gambar)
        },
        "teks": [("exceeded your current quota", ErrorClass.QUOTA_EXHAUSTED)],  # sampel nyata
        "kita": {"context_length_exceeded"},
    },
    "openai_tts": {"alias": "openai"},   # transport beda, vendor & tabel galat SAMA

    # ── Groq (naskah; 5 channel aktif) ────────────────────────────────────────────────────────
    "groq": {
        "sumber": "https://console.groq.com/docs/errors",
        "dibaca": "2026-08-12",
        "catatan": ("KETERBATASAN VENDOR, bukan kelalaian kita: Groq TIDAK menerbitkan kode galat "
                    "rinci — hanya status HTTP + kalimat. Batas HARIAN vs PER-MENIT hanya bisa "
                    "dibedakan dari kalimatnya (`tokens per day (TPD)`), dan itu ditangkap "
                    "`_RX_BERKALA`. 8 sampel nyata di production_runs (01-Agu)."),
        "kode": {},
        "teks": [("model_decommissioned", ErrorClass.MODEL_UNAVAILABLE)],
    },

    # ── Anthropic Claude (naskah; 0 channel aktif, tapi bisa dipilih tenant kapan saja) ───────
    "anthropic": {
        "sumber": "https://platform.claude.com/docs/en/api/errors",
        "dibaca": "2026-08-12",
        "catatan": ("Satu-satunya vendor dengan kode TAGIHAN tersendiri (`billing_error`, 402) — "
                    "vendor lain menumpangkannya ke 429."),
        "kode": {
            "billing_error":        ErrorClass.ACCOUNT_BILLING,   # 402
            "authentication_error": ErrorClass.AUTH_INVALID,      # 401
            "permission_error":     ErrorClass.AUTH_INVALID,      # 403
            "not_found_error":      ErrorClass.MODEL_UNAVAILABLE,  # 404
            "rate_limit_error":     ErrorClass.RATE_LIMIT,        # 429
            "overloaded_error":     ErrorClass.TRANSIENT,         # 529
            "timeout_error":        ErrorClass.TRANSIENT,         # 504
            "api_error":            ErrorClass.TRANSIENT,         # 500
            "conflict_error":       ErrorClass.TRANSIENT,         # 409
        },
        "kita": {"invalid_request_error", "request_too_large"},   # 400 / 413
    },

    # ── ElevenLabs (suara; 1 channel aktif) ───────────────────────────────────────────────────
    "elevenlabs": {
        "sumber": "https://elevenlabs.io/docs/eleven-api/resources/errors",
        "dibaca": "2026-08-12",
        "catatan": ("Jatah karakter pulih saat GANTI BULAN. Sebulan terlalu lama untuk disebut "
                    "'tunggu saja' — channel tenant akan mati sebulan. Karena itu jatah habis "
                    "diperlakukan MENUNTUT TINDAKAN (upgrade/isi ulang), bukan pulih-sendiri. "
                    "Keputusan ini diambil sadar, bukan karena keterbatasan data."),
        "kode": {
            "insufficient_credits":      ErrorClass.QUOTA_EXHAUSTED,   # 402
            "quota_exceeded":            ErrorClass.QUOTA_EXHAUSTED,   # sampel nyata
            "payment_required":          ErrorClass.ACCOUNT_BILLING,   # 402
            "payment_issue":             ErrorClass.ACCOUNT_BILLING,   # sampel nyata
            "subscription_required":     ErrorClass.ACCOUNT_BILLING,   # 403
            "invalid_api_key":           ErrorClass.AUTH_INVALID,      # 401
            "missing_api_key":           ErrorClass.AUTH_INVALID,      # 401
            "insufficient_permissions":  ErrorClass.AUTH_INVALID,      # 403
            "voice_not_found":           ErrorClass.MODEL_UNAVAILABLE,  # 404
            "concurrent_limit_exceeded": ErrorClass.RATE_LIMIT,        # 429
            "rate_limit_exceeded":       ErrorClass.RATE_LIMIT,        # 429
            "system_busy":               ErrorClass.TRANSIENT,         # 429 · beban vendor
            "service_unavailable":       ErrorClass.TRANSIENT,         # 503
            "internal_error":            ErrorClass.TRANSIENT,         # 500
        },
        "kita": {"validation_error", "invalid_request"},               # 400
        "teks": [("detected_unusual_activity", ErrorClass.ACCOUNT_BILLING)],
    },

    # ── fal.ai — AGREGATOR (gambar/video; 0 channel aktif) ────────────────────────────────────
    "fal": {
        "sumber": "https://fal.ai/docs/documentation/model-apis/errors",
        "dibaca": "2026-08-12",
        "agregator": True,
        "catatan": ("AGREGATOR: `downstream_service_*` berarti galat milik vendor DI BALIKNYA, hanya "
                    "diteruskan → teks disisir ulang lintas-vendor. Akun terkunci saat saldo di bawah "
                    "batas (sampel nyata kita ×6: 'Exhausted balance', 'User is locked'). "
                    "`content_policy_violation` = isi prompt ditolak penyaring — bukan salah akun "
                    "tenant dan bukan salah kita; dibiarkan boleh-diulang supaya jalur tulis-ulang "
                    "prompt yang menanganinya."),
        "kode": {
            "request_timeout":                ErrorClass.TRANSIENT,   # 504
            "startup_timeout":                ErrorClass.TRANSIENT,   # 504
            "generation_timeout":             ErrorClass.TRANSIENT,   # 504
            "runner_scheduling_failure":      ErrorClass.TRANSIENT,   # 503
            "runner_server_error":            ErrorClass.TRANSIENT,   # 500
            "runner_incomplete_response":     ErrorClass.TRANSIENT,   # 502
            "internal_error":                 ErrorClass.TRANSIENT,   # 500
            "internal_server_error":          ErrorClass.TRANSIENT,   # 500
            "downstream_service_unavailable": ErrorClass.TRANSIENT,   # 500
            "client_disconnected":            ErrorClass.TRANSIENT,   # 499
            "client_cancelled":               ErrorClass.TRANSIENT,   # 499
            "content_policy_violation":       _AMAN,                  # 422 · tulis-ulang prompt
        },
        "kita": {"bad_request", "missing", "value_error", "input_value_error",
                 "image_too_small", "image_too_large", "file_too_large",
                 "sequence_too_short", "sequence_too_long"},
        "teks": [("Exhausted balance", ErrorClass.QUOTA_EXHAUSTED),   # sampel nyata ×6
                 ("User is locked", ErrorClass.QUOTA_EXHAUSTED)],     # sampel nyata
    },

    # ── Edge TTS (suara; 6 channel aktif) ─────────────────────────────────────────────────────
    "edge_tts": {
        "sumber": None,
        "dibaca": "2026-08-12",
        "catatan": ("TIDAK ADA dokumen galat resmi — layanan Microsoft tanpa kunci lewat pustaka "
                    "komunitas. Aturan Emas §1 tak bisa dipenuhi di sini, dan itu dicatat terang "
                    "alih-alih dikarang. Tanpa kunci/saldo/jatah, satu-satunya kegagalan wajar = "
                    "jaringan/layanan (gangguan sesaat); kegagalan setelan = MILIK KITA."),
        "kode": {},
        "teks": [("belum ter-resolve", None),          # setelan voice kurang → milik kita
                 ("tidak terinstall", None)],          # pustaka belum terpasang → milik kita
        "kita_teks": {"belum ter-resolve", "tidak terinstall"},
    },
}


def _spek(penyedia: str) -> dict:
    s = PENYEDIA.get((penyedia or "").strip().lower(), {})
    return PENYEDIA.get(s["alias"], {}) if "alias" in s else s


def penyedia_terpetakan() -> set[str]:
    """Nama penyedia yang punya baris di registry (termasuk alias). Dipakai pagar uji."""
    return set(PENYEDIA.keys())


def _cocok_kode(spek: dict, kode) -> tuple[ErrorClass, bool] | None:
    if kode is None:
        return None
    for kandidat in ({kode, str(kode).strip().lower()} if not isinstance(kode, int) else {kode}):
        if kandidat in (spek.get("kita") or set()):
            return _AMAN, True
        k = (spek.get("kode") or {}).get(kandidat)
        if k is not None:
            return k, False
    return None


def _cukup_khas(tok) -> bool:
    """Boleh dicari di dalam TEKS BEBAS? Hanya penanda yang khas.

    ⚠️ REGRESI NYATA yang melahirkan aturan ini: tabel Gemini memuat kode pendek `internal` dan
    `not_found`. Dicari sebagai potongan teks, `internal` ikut tercocok pada kalimat biasa
    "Error code: 500 - internal server error" dan "fal submit HTTP 500: internal error" → galat
    server biasa berubah golongan. Keputusan owner yang berlaku: yang RAGU tetap UNKNOWN.
    Kode pendek TETAP dipakai — tapi hanya lewat pencocokan kode PERSIS, bukan sapuan teks.
    """
    return isinstance(tok, str) and "_" in tok and len(tok) >= 10


def _cocok_teks(spek: dict, teks: str) -> tuple[ErrorClass, bool] | None:
    if not teks:
        return None
    for tok in (spek.get("kita") or set()):
        if _cukup_khas(tok) and tok in teks:
            return _AMAN, True
    for tok in (spek.get("kita_teks") or set()):
        if tok in teks:                       # kalimat bebas yang sengaja dicatat, bukan kode
            return _AMAN, True
    for tok, kelas in (spek.get("teks") or []):
        if tok in teks and kelas is not None:  # daftar `teks` = kalimat PASTI, dipakai apa adanya
            return kelas, False
    for tok, kelas in ((spek.get("kode") or {}).items()):
        if _cukup_khas(tok) and tok in teks:
            return kelas, False
    return None


def golongkan(penyedia: str, *, status: int | None = None, kode=None,
              teks: str = "", pesan: str | None = None) -> Putusan:
    """Golongkan satu kegagalan penyedia AI. SATU-SATUNYA jalur; jangan bikin penilai kedua.

    Urutan sengaja, dari paling spesifik ke paling umum:
      1. kode resmi vendor          — membedakan "jatah pulih sendiri" dari "saldo harus diisi"
      2. kalimat pasti vendor       — untuk vendor yang tak menerbitkan kode (mis. Groq)
      3. terusan agregator          — galat milik vendor di balik agregator, disisir lintas-vendor
      4. kalimat batas BERKALA      — "tokens per day" dst. → pulih saat jatah berganti
      5. semantik HTTP umum         — jaring terakhir yang berlaku utk vendor yang BELUM ADA hari ini
      6. UNKNOWN                    — boleh diulang, aman, perilaku lama
    """
    spek = _spek(penyedia)
    teks = teks or ""

    for pencocok in (_cocok_kode(spek, kode), _cocok_teks(spek, teks)):
        if pencocok:
            return Putusan(pencocok[0], pesan, pencocok[1], "kode/teks-vendor")

    # Terusan agregator: galat sebenarnya milik lapis bawah → sisir penanda SEMUA vendor.
    if spek.get("agregator") and (str(kode or "").strip().lower() in _TERUSAN
                                  or any(t in teks for t in _TERUSAN)):
        for nama, lain in PENYEDIA.items():
            if nama == penyedia or "alias" in lain or lain.get("agregator"):
                continue
            hasil = _cocok_teks(lain, teks)
            if hasil:
                return Putusan(hasil[0], pesan, hasil[1], f"terusan-agregator:{nama}")

    if _RX_BERKALA.search(teks):
        return Putusan(ErrorClass.RATE_LIMIT, pesan, False, "batas-berkala")

    if status is not None:
        if int(status) in _STATUS_MILIK_KITA:
            return Putusan(_AMAN, pesan, True, "status-http-milik-kita")
        k = _STATUS_UMUM.get(int(status))
        if k is not None:
            return Putusan(k, pesan, False, "status-http-umum")

    return Putusan(_AMAN, pesan, False, "tak-dikenal")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# PENYIMPANAN MILIK KITA (S3/NEO BiznetGio) — BUKAN penyedia AI tenant.
#
# KENAPA ADA DI BERKAS INI. Berkas ini adalah SATU-SATUNYA rumah yang sah untuk mengubah galat
# mentah menjadi golongan (dijaga `tests/test_galat_generik.py` — pemetaan di berkas lain =
# pelanggaran). Penyimpanan bukan penyedia AI, karena itu ia TIDAK masuk `PENYEDIA` (tabel §4
# dokumen = penyedia AI tenant, dan mencampurnya akan membuat dokumen itu berbohong). Ia berdiri
# sendiri di bawah ini.
#
# KENAPA LAHIR (terukur, 13-Agu 2026). Akun penyimpanan kami diblokir penyedia 04:24–10:21 karena
# tagihan belum dibayar. Pukul 06:00 jam tayang tiba, video tak bisa diambil, dan tenant menerima
# pesan ini apa adanya:
#     "❌ [RAD The Explorer] Publish gagal, akan diulang: download gagal
#      (a410251c-.../410d4538-.../a410251c-..._1786489240.mp4): An error occurred (403) when
#      calling the HeadObject operation: Forbidden"
# Tiga cacat sekaligus: kode mentah yang tak bisa ditindak · nama berkas internal bocor · dan yang
# paling tidak adil — **kegagalan ini 100% MILIK KITA**, tapi pesannya membiarkan tenant mengira
# dirinyalah yang bermasalah. Owner: *"pesan errornya tidak jelas hanya kode saja. ANEH"*.
#
# ATURAN YANG MENGIKAT: apa pun kodenya, penyimpanan ini milik MesinViral ⇒ `milik_kita=True`
# SELALU, dan kalimat untuk tenant tidak pernah memuat kode/nama berkas. Kode aslinya tetap utuh
# di catatan server + alarm ADMIN (§9: tenant dapat MAKNA, kami dapat KODE).
# ═══════════════════════════════════════════════════════════════════════════════════════════════
_PENYIMPANAN_KODE: dict[str, ErrorClass] = {
    # Dari dokumen resmi galat S3 (kosakata yang sama dipakai NEO BiznetGio karena ber-antarmuka S3):
    # https://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html — dibaca 2026-08-13.
    "accountproblem":        ErrorClass.ACCOUNT_BILLING,   # akun kami diblokir (sampel NYATA 13-Agu)
    "accessdenied":          ErrorClass.AUTH_INVALID,
    "invalidaccesskeyid":    ErrorClass.AUTH_INVALID,
    "signaturedoesnotmatch": ErrorClass.AUTH_INVALID,
    "nosuchbucket":          ErrorClass.AUTH_INVALID,
    "403":                   ErrorClass.AUTH_INVALID,      # bentuk yang benar-benar muncul 13-Agu
    "slowdown":              ErrorClass.RATE_LIMIT,
    "requesttimeout":        ErrorClass.TRANSIENT,
    "requesttimetooskewed":  ErrorClass.TRANSIENT,
    "internalerror":         ErrorClass.TRANSIENT,
    "serviceunavailable":    ErrorClass.TRANSIENT,
    "503":                   ErrorClass.TRANSIENT,
    "500":                   ErrorClass.TRANSIENT,
}
# Berkasnya benar-benar tidak ada — satu-satunya golongan yang TIDAK boleh dijanjikan "terbit
# otomatis nanti", karena mengulangnya dijamin gagal lagi. Kalimatnya sengaja berbeda.
_PENYIMPANAN_HILANG: frozenset[str] = frozenset({"nosuchkey", "404"})

_RX_KODE_S3 = re.compile(r"An error occurred \(([^)]{1,60})\)")

_PESAN_TERTUNDA = (
    "Penerbitan tertunda karena gangguan penyimpanan di sisi MesinViral. Video Anda aman dan akan "
    "terbit otomatis di jam tayang berikutnya — tidak ada yang perlu Anda lakukan."
)
_PESAN_HILANG = (
    "Video ini tidak lagi ditemukan di penyimpanan MesinViral, jadi penerbitannya tidak bisa "
    "dilanjutkan. Ini masalah di sisi kami, bukan di akun Anda — tim kami sudah dikabari. "
    "Tidak ada yang perlu Anda lakukan."
)


class PutusanPenyimpanan(NamedTuple):
    """Hasil penggolongan galat penyimpanan KITA. `pesan_tenant` = siap kirim, nol kode."""
    kelas: ErrorClass
    kode: str                 # kode S3 apa adanya (untuk catatan/alarm admin, BUKAN untuk tenant)
    pesan_tenant: str
    berkas_hilang: bool
    milik_kita: bool = True   # selalu: bucket, kunci, dan tagihannya milik MesinViral


def _rantai(exc, batas: int = 6) -> list:
    """Galat penyimpanan sampai ke pemanggil terbungkus (`BufferError(...) from e`), jadi golongannya
    HARAM dinilai dari lapisan terluar saja — itulah sebab kode 403 sempat lolos ke tenant."""
    keluar, e = [], exc
    for _ in range(batas):
        if e is None:
            break
        keluar.append(e)
        e = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
    return keluar


def golongkan_penyimpanan(exc) -> PutusanPenyimpanan | None:
    """Galat ini milik penyimpanan KITA? → putusan siap-pakai. Bukan? → None (penilai lain lanjut).

    Dikenali dari DUA penanda, bukan satu: pustaka `botocore` di rantai sebab, atau `BufferError`
    (pembungkus `src/utils/s3_buffer.py`). Nama kelas dipakai — bukan `import` — supaya berkas
    registry ini tidak tergantung pada lapisan penyimpanan (arah ketergantungan tetap satu arah).
    """
    rantai = _rantai(exc)
    if not any(type(x).__module__.startswith(("botocore", "boto3")) or type(x).__name__ == "BufferError"
               for x in rantai):
        return None
    teks = " | ".join(str(x) for x in rantai)
    m = _RX_KODE_S3.search(teks)
    kode = (m.group(1) if m else "").strip()
    tok = kode.lower().replace(" ", "")
    if tok in _PENYIMPANAN_HILANG:
        return PutusanPenyimpanan(_AMAN, kode or "NoSuchKey", _PESAN_HILANG, True)
    kelas = _PENYIMPANAN_KODE.get(tok, ErrorClass.TRANSIENT)
    return PutusanPenyimpanan(kelas, kode or "tak-bernama", _PESAN_TERTUNDA, False)


__all__ = ["Putusan", "PENYEDIA", "golongkan", "penyedia_terpetakan",
           "PutusanPenyimpanan", "golongkan_penyimpanan"]
