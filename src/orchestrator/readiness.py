"""
Gerbang aktivasi channel (F1-08 / kredensial per-channel 2026-06-24).

Channel READY (boleh diaktifkan + diproduksi) bila SEMUA lengkap & valid PER-CHANNEL:
  niche · penyedia+model+kunci tiap elemen (LLM/TTS/Visual, provider-aware) · voice · YouTube OAuth.

SUMBER KEBENARAN TUNGGAL = fungsi DB `channel_missing(channels)` (via RPC `channel_missing_by_id`).
Worker, RPC FE, dan trigger DB pakai LOGIKA YANG SAMA PERSIS → akar bug "BE vs DB beda lapisan" hilang.

NO-FALLBACK (§3.8): channel tak lengkap → tak produksi (bukan produksi pakai default diam-diam).
Dipakai producer (skip channel non-ready) — FAIL-OPEN saat cek ERROR transient (lindungi channel sehat).
"""

from loguru import logger


def channel_readiness(sb, ch: dict) -> dict:
    """Return {ready: bool, missing: [str], check_failed: bool, reasons: [dict]}.
    check_failed=True → cek tak tuntas (error transient) → producer FAIL-OPEN (jangan skip channel sehat).
    `reasons` = alasan BERSTRUKTUR (migr 0204) untuk keadaan yang bisa diukur pasti: baris katalog yang
    ditunjuk channel sudah tidak aktif / tidak ada. Kosong bila channel siap atau sebabnya di luar itu."""
    cid = str(ch.get("id") or ch.get("channel_id") or "")
    if not cid:
        return {"ready": False, "missing": ["akses/channel"], "check_failed": True, "reasons": []}
    try:
        r = sb.rpc("channel_missing_by_id", {"p_channel_id": cid}).execute()
        missing = list(r.data or [])
        # ── ALASAN BERSTRUKTUR (migr 0204) ─────────────────────────────────────────────────────
        # Label `missing` adalah KUNCI MESIN (checklist layar tenant mencocokkan katanya) — ia tak
        # boleh diubah. `reasons` menjawab pertanyaan yang label tak bisa jawab: "belum dipilih" vs
        # "pilihan Anda sudah dipensiunkan penyedianya". Tanpa ini, log skip producer hanya berbunyi
        # "kurang: model naskah" — tak bisa didiagnosa siapa pun, dan itulah sebab 4 channel
        # (2 tenant BERBAYAR) diam 4 hari pada 17-Agu.
        #
        # Diambil HANYA saat channel tidak siap. Producer memutari SELURUH channel tiap ±16 detik;
        # mengambilnya untuk channel sehat = satu panggilan DB sia-sia per channel per siklus.
        reasons: list = []
        if missing:
            try:
                b = sb.rpc("channel_blockers_by_id", {"p_channel_id": cid}).execute()
                reasons = list(b.data or [])
            except Exception as e:
                # FAIL-SOFT: alasan hanyalah keterangan tambahan. Kegagalannya HARAM mengubah
                # `ready`/`check_failed` — kalau ikut mengubah, channel sehat bisa berhenti karena
                # hiasan yang gagal dibaca.
                logger.warning(f"[Readiness] alasan channel {cid} tak terbaca (non-fatal): {e}")
        return {"ready": len(missing) == 0, "missing": missing, "check_failed": False,
                "reasons": reasons}
    except Exception as e:
        logger.warning(f"[Readiness] cek channel {cid} gagal: {e}")
        return {"ready": False, "missing": [], "check_failed": True, "reasons": []}
