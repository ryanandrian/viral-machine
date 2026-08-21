"""KARANTINA MODEL — katalog akhirnya BELAJAR dari kematian model, tanpa membakar kredit siapa pun.

SSOT: AI_ERROR_MANAGEMENT_ARCHITECTURE.md §9b · migr 0205 (kolom jejak) · migr 0204 (alasan channel)

═══ PERSOALAN ═══
Mesin SUDAH membuktikan kematian model — 7 run ber-`error_class='model_unavailable'`, termasuk
`gemini-2.5-flash` (18-Agu). Tapi sinyalnya berhenti di `production_runs` + satu Telegram ke tenant.
NOL baris kode pernah menyentuh `ai_models` (penulisnya di seluruh src/ hanya `model_tester`→cost_hint
dan `price_sync`→pricing). Akibatnya model yang TERBUKTI mati tetap `is_active=true`, tetap ditawarkan
ke tenant BERIKUTNYA, tetap lolos gerbang. Abyss ID diam 24 hari; 17-Agu 4 channel (2 tenant BERBAYAR)
diam 4 hari.

═══ KEBERATAN OWNER 21-Agu — MENGIKAT ═══
Rancangan semula: buktikan dengan memanggil vendor memakai kunci admin / pool Test Lab. **DITOLAK**:
*"bisa menghabiskan kredit saya diam-diam, dan biayanya cukup besar ke depannya"*. Untuk image/video
sekali uji ≈$0,27–0,80. ⇒ **NOL panggilan berbayar di seluruh berkas ini.** Bukti diambil dari data
yang SUDAH ada di tangan.

═══ MENGAPA "VENDOR MENYEBUT SENDIRI" BELUM CUKUP ═══
`model_decommissioned` (Groq) = kematian global, tak bisa salah tafsir.
Tapi `model_not_found` (OpenAI/Gemini) berbunyi — terekam apa adanya di log 17-Agu —
*"The model `X` does not exist **or you do not have access to it**"*. Itu bisa berarti akun tenant
tak punya aksesnya (model bertingkat). Mengarantina dari satu kegagalan satu tenant berisiko
**mematikan model yang masih hidup untuk semua tenant** — kerusakan kelas 17-Agu yang dilahirkan oleh
perbaikan ini sendiri.

═══ TANGGA BUKTI (semuanya Rp 0) ═══
    A (WAJIB)  `dasar` = kode/teks-vendor atau terusan-agregator   ← bukan 404 telanjang
    B1  kata GLOBAL di pesan vendor    (decommissioned/no longer available/deprecated/retired/sunset)
    B2  ≥2 TENANT BERBEDA gagal pada model yang sama   (dua kunci API ⇒ bukan soal akses akun)
    B3  hilang dari umpan harga publik  (`price_sync` sudah menghitung `missing` tiap 24 jam)

A + (B1|B2|B3) → KARANTINA. A tanpa B → NOL karantina, alarm admin ber-bukti + tombol 1 klik.
404 telanjang → NOL karantina, alarm admin.

Diuji pada riwayat NYATA: `gemini-2.5-flash` gagal di 2 tenant berbeda ⇒ B2 menyala.
`gemini-flash-lite-latest` hanya 1 tenant ⇒ tidak dikarantina buta.

═══ JALUR BUKA (mandat owner "setiap kunci punya jalur buka") ═══
Karantina TIDAK PERNAH menyala sendiri kembali. Admin menghidupkan model di panel Katalog
(saklar `is_active`) — dua kolom jejak dibersihkan di sana, dan tombol Uji tersedia untuk membuktikan
model hidup lagi. Karantina juga terasa ≤5 menit, bukan seketika: katalog Python ber-cache TTL 300 dtk.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from src.exceptions import ErrorClass

# ── Kata yang menyatakan kematian GLOBAL (B1) ───────────────────────────────────────────────────
# Sengaja SEMPIT. Kata-kata ini tak mungkin berarti "akun Anda tidak punya akses" — berbeda dari
# `model_not_found`/`does not exist` yang justru dokumen vendornya sendiri menyatakan ambigu.
# Menambah kata ke daftar ini = mengubah perilaku-saat-gagal = BUTUH KETOK OWNER.
KATA_GLOBAL: tuple[str, ...] = (
    "decommission",          # Groq: model_decommissioned
    "no longer available",   # Gemini
    "deprecated",
    "retired",
    "sunset",
    "has been removed",
)

# `dasar` (galat_registry.Putusan.dasar) yang boleh dipercaya sebagai "vendor menyebut modelnya".
DASAR_VENDOR: tuple[str, ...] = ("kode/teks-vendor", "terusan-agregator")

# `dasar` yang HARAM dipakai mengarantina: 404 telanjang dari jaring HTTP generik. 404 bisa berarti
# alamat/jalur salah di sisi KITA (`base_url` keliru), bukan bukti model mati.
DASAR_AMBIGU: str = "status-http-umum"

# Bukti-silang antar-tenant: berapa akun BERBEDA yang harus gagal (B2).
MIN_TENANT_SILANG: int = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bukti_global(pesan_vendor: Optional[str]) -> Optional[str]:
    """B1 — kata yang menyatakan kematian GLOBAL di pesan vendor. None bila tak ada."""
    teks = (pesan_vendor or "").lower()
    for k in KATA_GLOBAL:
        if k in teks:
            return k
    return None


def tenant_silang(sb, model_key: str, sejak_hari: int = 30) -> set[str]:
    """B2 — himpunan tenant BERBEDA yang gagal pada model ini (dari `production_runs.failed_model`).

    Dua akun independen tak bisa sama-sama kehilangan akses karena kebetulan; kalau dua kunci API
    berbeda sama-sama ditolak untuk model yang sama, yang bermasalah modelnya. Rp 0 — memakai
    kegagalan yang MEMANG sudah terjadi, bukan memancing kegagalan baru.
    """
    if not model_key:
        return set()
    try:
        from datetime import timedelta
        batas = (datetime.now(timezone.utc) - timedelta(days=sejak_hari)).isoformat()
        r = (sb.table("production_runs").select("tenant_id")
             .eq("failed_model", model_key).eq("error_class", ErrorClass.MODEL_UNAVAILABLE.value)
             .gte("created_at", batas).execute())
        return {x["tenant_id"] for x in (r.data or []) if x.get("tenant_id")}
    except Exception as e:
        logger.warning(f"[Karantina] bukti-silang tenant untuk '{model_key}' gagal dibaca: {e}")
        return set()


def hilang_dari_umpan_harga(sb, model_key: str) -> bool:
    """B3 — model tak punya harga tersinkron. `price_sync` sudah menghitungnya tiap 24 jam (Rp 0).

    Sinyal LEMAH sendirian (banyak model sah memang tak ada di umpan publik) — karena itu ia hanya
    dipakai sebagai PENGUAT bukti A, tak pernah berdiri sendiri.
    """
    try:
        r = sb.table("ai_models").select("pricing").eq("model_key", model_key).limit(1).execute()
        row = (r.data or [None])[0]
        if row is None:
            return False
        pr = row.get("pricing") or {}
        return not pr.get("synced_at")
    except Exception as e:
        logger.warning(f"[Karantina] status harga '{model_key}' gagal dibaca: {e}")
        return False


def nilai_bukti(sb, model_key: str, dasar: str, pesan_vendor: Optional[str]) -> dict:
    """Putuskan: karantina, atau alarm admin saja. NOL panggilan ke vendor.

    Return {'karantina': bool, 'bukti': [str], 'alasan': str} — `alasan` siap disimpan ke
    `ai_models.unavailable_reason` / dikirim ke admin apa adanya (pesan vendor TIDAK diterjemahkan,
    ketetapan owner 08-Agu).
    """
    bukti: list[str] = []
    if not model_key:
        return {"karantina": False, "bukti": [], "alasan": "nama model tak diketahui"}

    # ── A: wajib. 404 telanjang HARAM mengarantina. ──────────────────────────────────────────
    if (dasar or "").startswith(DASAR_AMBIGU) or not (dasar or "").startswith(DASAR_VENDOR):
        return {"karantina": False, "bukti": [],
                "alasan": f"bukti lemah (dasar={dasar or '?'}) — 404 telanjang bisa berarti alamat "
                          f"salah di sisi kami, bukan model mati"}

    # ── B1 ───────────────────────────────────────────────────────────────────────────────────
    kata = bukti_global(pesan_vendor)
    if kata:
        bukti.append(f"B1 kata-global vendor: '{kata}'")

    # ── B2 ───────────────────────────────────────────────────────────────────────────────────
    tenants = tenant_silang(sb, model_key)
    if len(tenants) >= MIN_TENANT_SILANG:
        bukti.append(f"B2 gagal di {len(tenants)} tenant berbeda")

    # ── B3 ───────────────────────────────────────────────────────────────────────────────────
    if hilang_dari_umpan_harga(sb, model_key):
        bukti.append("B3 tak ada harga tersinkron dari umpan publik")

    if bukti:
        return {"karantina": True, "bukti": bukti,
                "alasan": f"vendor: {(pesan_vendor or '').strip()[:300]} | " + " · ".join(bukti)}
    return {"karantina": False, "bukti": [],
            "alasan": f"vendor menyebut modelnya, tapi belum ada penguat (1 tenant, tanpa kata "
                      f"global, harga masih tersinkron) — menunggu bukti kedua. "
                      f"vendor: {(pesan_vendor or '').strip()[:200]}"}


def karantina(sb, model_key: str, dasar: str, pesan_vendor: Optional[str] = None) -> dict:
    """Titik masuk tunggal. Menilai bukti, lalu mengarantina ATAU melaporkan ke admin.

    Idempoten: model yang sudah nonaktif tak ditulis ulang. Fail-soft di setiap langkah — kegagalan
    di sini HARAM menghentikan produksi tenant lain.
    """
    hasil = nilai_bukti(sb, model_key, dasar, pesan_vendor)
    hasil["ditulis"] = False
    try:
        r = sb.table("ai_models").select("model_key,is_active,component,provider_key") \
            .eq("model_key", model_key).limit(1).execute()
        row = (r.data or [None])[0]
    except Exception as e:
        logger.warning(f"[Karantina] '{model_key}' gagal dibaca dari katalog: {e}")
        return hasil
    if row is None:
        logger.info(f"[Karantina] '{model_key}' tak ada di katalog — nol tindakan")
        return hasil
    if not row.get("is_active"):
        logger.info(f"[Karantina] '{model_key}' sudah nonaktif — nol tindakan (idempoten)")
        return hasil

    if not hasil["karantina"]:
        # Bukti belum cukup: JANGAN mengubah katalog. Admin diberi buktinya + bisa memutuskan.
        logger.warning(f"[Karantina] '{model_key}' TIDAK dikarantina — {hasil['alasan']}")
        _kabari_admin(model_key, row, hasil, dikarantina=False)
        return hasil

    try:
        sb.table("ai_models").update({
            "is_active": False,
            "unavailable_since": _now(),
            "unavailable_reason": hasil["alasan"][:1000],
        }).eq("model_key", model_key).execute()
        hasil["ditulis"] = True
        logger.error(f"[Karantina] '{model_key}' DIKARANTINA — {' · '.join(hasil['bukti'])}")
    except Exception as e:
        logger.error(f"[Karantina] '{model_key}' gagal dikarantina: {e}")
        return hasil

    _kabari_admin(model_key, row, hasil, dikarantina=True)
    return hasil


def _kabari_admin(model_key: str, row: dict, hasil: dict, *, dikarantina: bool) -> None:
    """Kabar ke ADMIN (bukan tenant) — fail-soft. Tenant sudah mendapat pesannya sendiri dari
    jalur galat biasa (`MODEL_UNAVAILABLE` → sebut nama model + penyedia + "pilih model lain")."""
    try:
        # Pola yang SUDAH dipakai di repo ini (renewal.py:134 · pace_calibration.py:551 ·
        # price_sync.py:129) — `notify_admin` adalah METODE kelas, bukan fungsi modul.
        from src.utils.telegram_notifier import TelegramNotifier
    except Exception:
        return
    komp = row.get("component") or "?"
    prov = row.get("provider_key") or "?"
    judul = ("🛑 Model dikarantina otomatis" if dikarantina
             else "⚠️ Model diduga mati — butuh keputusan Anda")
    ekor = ("Model ini berhenti ditawarkan ke tenant. Tenant yang memakainya sudah diberi tahu untuk "
            "memilih pengganti. Untuk menghidupkan kembali: panel Katalog → nyalakan `is_active`."
            if dikarantina else
            "Katalog TIDAK diubah — bukti belum cukup. Periksa di panel Katalog; bila Anda yakin "
            "model ini memang dipensiunkan vendor, matikan `is_active` di sana.")
    try:
        TelegramNotifier().notify_admin(
            f"{judul}\n\nModel: {model_key} ({komp} · {prov})\n{hasil['alasan']}\n\n{ekor}")
    except Exception as e:
        logger.warning(f"[Karantina] kabar admin gagal (non-fatal): {e}")
