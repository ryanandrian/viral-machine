"""
Price Sync (B2 + ketahanan, owner 2026-07-04) — sinkron OTOMATIS harga satuan model AI →
`ai_models.pricing`. Tabel harga TANPA beban update manual, DENGAN pengaman:

- Sumber UTAMA: feed komunitas LiteLLM. FALLBACK: API resmi OpenRouter (khusus LLM) bila feed
  gagal/entri tak ada. Keduanya machine-readable — TANPA scraping HTML rapuh. URL via env (replaceable).
- `pricing_locked=true` = override admin → TIDAK ditimpa (harga resmi owner, mis. ElevenLabs).
- SANITY-GUARD: harga baru berubah > AI_PRICE_SANITY_FACTOR (default 3×) dari harga lama → DITAHAN di
  `pricing_pending` + Telegram admin — admin Terapkan/Abaikan di Catalog (kasus nyata: feed EL $180 vs resmi $100).
- ALARM BASI: sinkron macet > AI_PRICE_STALE_DAYS (default 7) → Telegram admin (1×/hari) — matinya
  sumber KETAHUAN, bukan senyap. Feed mati ≠ rusak: harga terakhir tetap dipakai (beku + ber-cap tanggal).
- Berjalan harian via buffer_janitor.run_once (guard `system_state` 'ai_price_synced_at' epoch).
- STATUS MESIN (kapan terakhir sinkron, alarm) = tabel `system_state` (0126) — BUKAN app_config
  (temuan owner 2026-07-05: status nyasar di layar konfigurasi admin = salah tempat).
- + `sync_fx_rate`: kurs USD→IDR (`app_config.usd_idr_rate`, tampilan biaya BYOK) disinkron harian
  dari kurs pasar publik; `usd_idr_rate_locked`=1 → mesin tak menimpa (admin kelola sendiri).
"""

import os
import time as _time
from datetime import datetime, timedelta, timezone

import requests
from loguru import logger

FEED_URL = os.getenv(
    "AI_PRICE_FEED_URL",
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
)
FALLBACK_URL = os.getenv("AI_PRICE_FALLBACK_URL", "https://openrouter.ai/api/v1/models")


def _url_umpan() -> str:
    """URL sumber harga: kenop admin (`app_config.ai_price_feed_url`) → env → bawaan kode.
    [F3, 23-Agu] Owner: *"url sinkronisasi sebaiknya bisa dikonfigurasi lewat admin panel"*. Dibaca
    SAAT SINKRON (bukan saat impor) supaya perubahan berlaku tanpa deploy. Gagal-aman: kosong/gagal
    baca → jatuh ke env lalu bawaan, jadi sinkron tak pernah mati total karena kenop kosong."""
    try:
        from src.config.app_config import get_text
        return get_text("ai_price_feed_url", FEED_URL) or FEED_URL
    except Exception as e:
        logger.warning(f"[price_sync] baca kenop URL umpan gagal ({e}) — pakai bawaan")
        return FEED_URL


def _url_cadangan() -> str:
    """URL sumber cadangan (router, model naskah saja) — kenop admin → env → bawaan."""
    try:
        from src.config.app_config import get_text
        return get_text("ai_price_fallback_url", FALLBACK_URL) or FALLBACK_URL
    except Exception:
        return FALLBACK_URL


# Satuan yang DISEBUT sumber harga vendor → (formula kita, kunci tarif, pengali jumlah).
# DATA, bukan cabang if: satuan baru = satu baris di sini. Satuan yang belum ada formulanya sengaja
# TIDAK dipetakan — tarifnya lebih baik tak ditulis daripada ditulis tapi mustahil dihitung
# (baris akan tampak berharga padahal biayanya nol — kelas cacat 23-Agu).
# Kunci tarifnya TIDAK diketik di sini — diturunkan dari formulanya (`kunci_tunggal_formula`),
# supaya kosakata satuan tetap hidup di SATU berkas saja (dijaga G1; penjaga itu menangkap versi
# pertama peta ini yang mengetik nama kuncinya).
SATUAN_VENDOR: dict[str, tuple[str, float]] = {
    # satuan yang vendor sebutkan → (formula kita,      pengali jumlah)
    "requests":                     ("naskah_panggilan", 1.0),
    "1000 characters":              ("suara_huruf",      1000.0),
    "seconds":                      ("video_detik",      1.0),
    # BELUM dipetakan (formulanya belum punya pencatat pemakaian — F4b):
    #   "megapixels" → gambar_megapiksel · "1m tokens" → video_token
}


def _harga_vendor(url_pola: str, model_id: str, kunci_api: str) -> tuple[str, float] | None:
    """Tanya tarif resmi ke API harga milik PENYEDIA (mis. fal). Return (satuan, tarif) atau None.

    [F4, 23-Agu] Satu-satunya sumber yang berwenang untuk baris agregator (pagar F3 menolak tarif
    vendor lain). Terverifikasi pada API fal: balasan memuat `prices[].unit_price` + `.unit`.
    BATAS JUJUR: tarif utama ini TIDAK menghitung parameter yang KITA pilih (fal menyebut
    $0,15/detik untuk veo = BERAUDIO, sedangkan kita mematikan audio → $0,10). Baris yang tarifnya
    tergantung parameter WAJIB dikunci manual — lihat migr 0212."""
    try:
        r = requests.get(url_pola.replace("{model_id}", model_id),
                         headers={"Authorization": f"Key {kunci_api}"}, timeout=25)
        if r.status_code != 200:
            logger.info(f"[price_sync] harga vendor {model_id}: HTTP {r.status_code}")
            return None
        harga = ((r.json() or {}).get("prices") or [{}])[0]
        satuan, tarif = harga.get("unit"), harga.get("unit_price")
        if not satuan or tarif is None:
            return None
        return str(satuan), float(tarif)
    except Exception as e:
        logger.warning(f"[price_sync] harga vendor {model_id} gagal: {e}")
        return None


def _kunci_platform(sb, key_group: str) -> str:
    """Kunci API MILIK PLATFORM (bukan tenant) untuk memanggil API harga penyedia. Kosong = lewati.

    Hanya dipakai untuk endpoint HARGA — nol model dijalankan, nol kredit terpakai (dibuktikan
    23-Agu: seluruh riset harga fal menghabiskan $0). HARAM dipakai untuk memanggil model."""
    try:
        r = (sb.table("tenant_ai_accounts").select("key_enc")
             .eq("tenant_id", "admin_test_internal").eq("key_group", key_group)
             .eq("status", "valid").limit(1).execute())
        if not r.data:
            return ""
        from src.utils.crypto import decrypt
        return decrypt(r.data[0]["key_enc"]) or ""
    except Exception as e:
        logger.warning(f"[price_sync] ambil kunci platform '{key_group}' gagal: {e}")
        return ""


def _agregator(provider_key: str) -> bool:
    """Apakah penyedia ini AGREGATOR (menyajikan model vendor lain di bawah namanya sendiri)?

    Penanda ini SUDAH ADA dan sudah dipakai jalur penanganan galat
    (`galat_registry.PENYEDIA[...]["agregator"]`) — jalur harga tinggal membacanya, bukan bikin
    penanda baru. [F3, 23-Agu] Kenapa penting untuk HARGA: agregator menetapkan tarifnya SENDIRI,
    jadi tarif vendor di belakangnya TAK PERNAH berlaku. Terbukti: 3 baris naskah fal diberi tarif
    per-token milik Google/OpenAI/Anthropic dari sumber cadangan, padahal fal menagih
    $0,001 PER PERMINTAAN. Gagal-aman: penanda tak terbaca → dianggap BUKAN agregator (perilaku lama)."""
    try:
        from src.providers.galat_registry import PENYEDIA
        return bool((PENYEDIA.get(provider_key or "") or {}).get("agregator"))
    except Exception as e:
        logger.warning(f"[price_sync] baca penanda agregator gagal ({e}) — dianggap bukan agregator")
        return False
SYNC_INTERVAL_HOURS = float(os.getenv("AI_PRICE_SYNC_HOURS", "24"))
SANITY_FACTOR = float(os.getenv("AI_PRICE_SANITY_FACTOR", "3"))
STALE_DAYS = float(os.getenv("AI_PRICE_STALE_DAYS", "7"))
# Jendela bukti untuk laporan "gagal dihitung" (hari). Knob infra (pola STALE_DAYS).
UNPRICED_WINDOW_DAYS = float(os.getenv("AI_UNPRICED_WINDOW_DAYS", "3"))
# Jeda antar panggilan ke API harga PENYEDIA. fal membatasi jumlah panggilan (terbukti 23-Agu:
# HTTP 429 sesudah ±7 panggilan berdempet; jeda 12 dtk aman). Sinkron jalan 1x/hari, jadi
# 12 baris × jeda ini = ±1,5 menit sekali sehari — murah dibanding baris yang terlewat.
VENDOR_API_DELAY = float(os.getenv("AI_PRICE_VENDOR_DELAY_SEC", "8"))


FX_URL = os.getenv("FX_RATE_URL", "https://open.er-api.com/v6/latest/USD")  # kurs pasar publik, tanpa key
FX_SANITY_MIN = float(os.getenv("FX_IDR_SANITY_MIN", "5000"))    # band waras USD→IDR — di luar ini = feed rusak, skip
FX_SANITY_MAX = float(os.getenv("FX_IDR_SANITY_MAX", "60000"))


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


# ── system_state (0126): penanda status mesin — BUKAN config admin ─────────────
def _state_get_epoch(sb, key: str) -> int:
    try:
        r = sb.table("system_state").select("value").eq("key", key).limit(1).execute()
        return int(r.data[0]["value"]) if r.data else 0
    except Exception:
        return 0


def _state_set_epoch(sb, key: str) -> None:
    try:
        sb.table("system_state").upsert({"key": key, "value": str(int(_time.time())),
                                         "updated_at": datetime.now(timezone.utc).isoformat()}).execute()
    except Exception as e:
        logger.debug(f"[price_sync] tulis system_state {key} gagal: {e}")


def _feed_entry(feed: dict, model_id: str, provider_prefix: str | None = None,
                wajib_prefix: bool = False) -> dict | None:
    """Cari entri feed LiteLLM: kunci persis → prefix SPESIFIK provider (DATA: ai_providers.
    price_feed_prefix, fallback provider_key) → daftar prefix legacy (jaring pengaman regresi).
    NO-HARDCODE (owner 2026-07-06): provider BARU tak lagi butuh bongkar skrip ini — cukup baris
    ai_providers (+isi price_feed_prefix bila nama prefix feed ≠ provider_key, mis. openai_tts→openai).
    (Riwayat insiden prefix tertanam: 'elevenlabs/' 2026-07-04; gemini/groq 2026-07-06.)"""
    if not wajib_prefix and model_id in feed:
        return feed[model_id]
    # [23-Agu] Daftar prefix vendor yang DITANAM di kode dibuang. Alasannya bukan kerapian:
    # mencocokkan model ke prefix vendor LAIN berarti memakai HARGA VENDOR LAIN (agregator menagih
    # tarifnya sendiri). Terukur sebelum dibuang: **0 model aktif** bergantung pada daftar itu.
    # Prefix kini murni DATA (`ai_providers.price_feed_prefix`, fallback provider_key).
    if provider_prefix:
        kunci = provider_prefix.rstrip("/") + "/" + model_id
        if kunci in feed:
            return feed[kunci]
    return None


def _openrouter_map() -> dict:
    """FALLBACK resmi (LLM saja): OpenRouter /models → {model_id: {in_per_1m, out_per_1m}}.
    id OpenRouter berbentuk 'vendor/model_id' → dipetakan by suffix."""
    out = {}
    try:
        data = requests.get(FALLBACK_URL, timeout=30).json().get("data") or []
        for e in data:
            mid = str(e.get("id") or "").split("/")[-1]
            pr = e.get("pricing") or {}
            pin, pout = float(pr.get("prompt") or 0), float(pr.get("completion") or 0)
            if mid and (pin > 0 or pout > 0):
                from src.billing.ai_cost import kunci_token_naskah
                k_in, k_out = kunci_token_naskah()
                out[mid] = {k_in: round(pin * 1e6, 4), k_out: round(pout * 1e6, 4)}
    except Exception as e:
        logger.warning(f"[price_sync] fallback OpenRouter gagal: {e}")
    return out


def _to_pricing(e: dict, now: str, component: str | None = None) -> dict:
    """Normalisasi entri umpan → harga kita, **HANYA satuan yang sah untuk JENIS baris itu**.

    [23-Agu] Dulu tanpa `component`: satu pemetaan dipakai untuk semua jenis, sehingga harga TEKS
    ditulis ke baris SUARA — `gemini-2.5-flash-preview-tts` tercatat $2,5/1jt padahal tarif resmi
    audionya **$10** (4x terlalu murah; 4 channel aktif, 16 produksi). Sumber kebenarannya satu:
    DAFTAR SATUAN di `ai_cost` (SSOT `ARSITEKTUR_AI_PROVIDER_MODEL.md` §7b). Kolom umpan yang
    bermakna GANDA sengaja tak terdaftar untuk jenis bersangkutan ⇒ ditolak otomatis, bukan
    ditebak. Jenis tak dikenal → kosong (gagal jujur), bukan menebak dgn pemetaan jenis lain."""
    from src.billing.ai_cost import satuan_untuk

    out: dict = {"source": "litellm", "synced_at": now}
    per_skema: dict = {}
    for sat in satuan_untuk(component or ""):
        for kolom in sat.umpan:
            nilai = e.get(kolom)
            if nilai in (None, 0):
                continue
            angka = float(nilai) * sat.kali
            per_skema.setdefault(sat.skema, {})[sat.kunci] = (
                round(angka, 4) if sat.kali != 1 else float(angka))
            break
    # Skema yang harga ESENSIAL-nya tak ada TIDAK ditulis: baris yang memuat separuh harga akan
    # TAMPAK berharga di panel padahal biayanya mustahil dihitung — itu kelas cacat 23-Agu.
    for sat in satuan_untuk(component or ""):
        if sat.wajib and sat.kunci not in per_skema.get(sat.skema, {}):
            per_skema.pop(sat.skema, None)
    for isi in per_skema.values():
        out.update(isi)
    return out


def _sanity_violation(old: dict | None, new: dict) -> str | None:
    """Perubahan drastis (> SANITY_FACTOR× naik/turun) pada field mana pun → alasan (str), aman → None."""
    if not old:
        return None
    from src.billing.ai_cost import semua_kunci_harga
    for k in semua_kunci_harga():
        o, n = old.get(k), new.get(k)
        if o and n and float(o) > 0 and float(n) > 0:
            ratio = float(n) / float(o)
            if ratio > SANITY_FACTOR or ratio < 1 / SANITY_FACTOR:
                return f"{k}: {o} → {n} ({ratio:.1f}×)"
    return None


def _notify_admin(text: str) -> None:
    try:
        from src.utils.telegram_notifier import TelegramNotifier
        TelegramNotifier().notify_admin(text)
    except Exception:
        pass


def _check_staleness(sb, rows: list) -> None:
    """Alarm basi: model non-locked ber-synced_at lebih tua dari STALE_DAYS → Telegram admin (1×/hari)."""
    try:
        cutoff = _time.time() - STALE_DAYS * 86400
        stale = []
        for m in rows:
            p = m.get("pricing") or {}
            if m.get("pricing_locked") or not p.get("synced_at"):
                continue
            try:
                ts = datetime.fromisoformat(str(p["synced_at"]).replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if ts < cutoff:
                stale.append(m["model_key"])
        if not stale:
            return
        last = _state_get_epoch(sb, "ai_price_stale_alerted_at")
        if _time.time() - last < 86400:
            return
        _notify_admin(f"⚠️ <b>Harga model AI BASI</b> (&gt;{int(STALE_DAYS)} hari tanpa sinkron): "
                      f"<code>{', '.join(stale)}</code>\nSumber feed kemungkinan bermasalah — cek Catalog → AI Models.")
        _state_set_epoch(sb, "ai_price_stale_alerted_at")
    except Exception as e:
        logger.debug(f"[price_sync] cek staleness gagal: {e}")


def sync_prices(sb=None, force: bool = False, only_model_key: str | None = None) -> dict:
    """Tarik feed (LiteLLM → fallback OpenRouter utk LLM) → update ai_models.pricing.
    Skip pricing_locked; perubahan drastis → pricing_pending (keputusan admin). Return ringkasan.
    only_model_key: probe/sinkron SATU model saja (dipakai admin saat simpan model → deteksi
    model_id/prefix salah seketika); tak mengubah stempel sinkron global."""
    sb = sb or _sb()

    if not force and not only_model_key:
        last = _state_get_epoch(sb, "ai_price_synced_at")
        if last and (_time.time() - last) < SYNC_INTERVAL_HOURS * 3600:
            return {"skipped": True}

    rows = sb.table("ai_models").select("model_key, model_id, component, provider_key, pricing, pricing_locked, pricing_pending, default_params").execute().data or []
    if only_model_key:
        rows = [r for r in rows if r.get("model_key") == only_model_key]
    # Prefix feed per-provider = DATA (ai_providers.price_feed_prefix, fallback provider_key).
    try:
        _provs = sb.table("ai_providers").select("provider_key, price_feed_prefix, price_api_url, key_group").execute().data or []
        prefix_map = {r["provider_key"]: (r.get("price_feed_prefix") or r["provider_key"]) for r in _provs}
        # [F4] Sumber harga RESMI milik penyedia (migr 0212) + grup kunci untuk memanggilnya.
        api_map = {r["provider_key"]: (r.get("price_api_url") or "") for r in _provs}
        grup_map = {r["provider_key"]: (r.get("key_group") or r["provider_key"]) for r in _provs}
    except Exception as e:
        logger.warning(f"[price_sync] baca price_feed_prefix gagal ({e}) — pakai fallback legacy")
        prefix_map, api_map, grup_map = {}, {}, {}

    feed = None
    try:
        feed = requests.get(_url_umpan(), timeout=30).json()
    except Exception as e:
        logger.warning(f"[price_sync] feed utama gagal: {e} — coba fallback OpenRouter (LLM saja)")

    orm = None   # lazy: fallback OpenRouter di-fetch hanya bila dibutuhkan
    now = datetime.now(timezone.utc).isoformat()
    updated, held, missing = 0, [], []
    kunci_cache: dict = {}      # kunci platform per penyedia (ambil sekali)
    _vendor_terakhir = [0.0]    # penanda waktu panggilan API penyedia terakhir (untuk jeda)
    formula_baru: dict = {}     # model_key → formula yang ditetapkan sumber resmi penyedia

    for m in rows:
        if m.get("pricing_locked"):
            continue
        pricing = None
        # PAGAR AGREGATOR (F3): baris milik agregator hanya boleh berharga dari RUANG NAMA
        # agregatornya sendiri. Kunci-persis pun ditolak — sebab id model agregator sering berupa
        # nama model vendor ("anthropic/claude-haiku-4.5"), dan kunci itu ADA di umpan dengan tarif
        # ANTHROPIC. Menerimanya = memakai tarif vendor lain untuk penyedia yang menagih sendiri.
        agr = _agregator(m.get("provider_key") or "")
        pk_ = m.get("provider_key") or ""

        # [F4] SUMBER RESMI PENYEDIA lebih dulu — ia satu-satunya yang berwenang untuk baris
        # agregator, dan ia menyebut SATUAN TAGIHNYA sendiri sehingga formula kita bisa ikut disetel.
        url_api = api_map.get(pk_) or ""
        if url_api:
            kunci_api = kunci_cache.get(pk_)
            if kunci_api is None:
                kunci_api = _kunci_platform(sb, grup_map.get(pk_) or pk_)
                kunci_cache[pk_] = kunci_api
            if kunci_api:
                # Alamat HARGA bisa beda dari penanda model — agregator satu-pintu (fal any-llm)
                # memakai nama model sebagai PARAMETER, bukan alamat. Keterangannya = DATA
                # (`default_params.price_endpoint_id`, migr 0213), bukan nama penyedia di kode.
                alamat_harga = ((m.get("default_params") or {}).get("price_endpoint_id")
                                or m.get("model_id") or m["model_key"])
                if _vendor_terakhir[0]:
                    _time.sleep(max(0.0, VENDOR_API_DELAY - (_time.time() - _vendor_terakhir[0])))
                hv = _harga_vendor(url_api, alamat_harga, kunci_api)
                _vendor_terakhir[0] = _time.time()
                if hv:
                    satuan, tarif = hv
                    kunci_tarif = None
                    peta = SATUAN_VENDOR.get(satuan)
                    if not peta:
                        logger.info(f"[price_sync] {m['model_key']}: satuan vendor '{satuan}' belum "
                                    f"punya formula — tarif TIDAK ditulis (lebih baik kosong daripada "
                                    f"tertulis tapi mustahil dihitung)")
                    else:
                        formula, kali = peta
                        # Satuan 'seconds' dipakai video DAN suara — formulanya ikut jenis barisnya.
                        if satuan == "seconds" and m.get("component") == "tts":
                            formula = "suara_detik"
                        from src.billing.ai_cost import kunci_tunggal_formula
                        kunci_tarif = kunci_tunggal_formula(formula)
                        if not kunci_tarif:
                            logger.warning(f"[price_sync] formula '{formula}' memakai lebih dari satu "
                                           f"tarif — tak bisa diisi dari satu angka vendor; dilewati")
                            kunci_tarif = None
                    if kunci_tarif:
                        pricing = {kunci_tarif: round(tarif * kali, 6),
                                   "source": f"{pk_}_api", "synced_at": now,
                                   "note": f"tarif resmi {pk_}: {tarif} per {satuan} (cek {now[:10]})"}
                        formula_baru[m["model_key"]] = formula
        e = _feed_entry(feed, m.get("model_id") or m["model_key"],
                        provider_prefix=prefix_map.get(m.get("provider_key") or ""),
                        wajib_prefix=agr) if feed else None
        if e and pricing is None:
            pricing = _to_pricing(e, now, component=m.get("component"))
            if all(v is None for k, v in pricing.items() if k not in ("source", "synced_at")):
                pricing = None
        # Sumber CADANGAN (router) mencari BY SUFFIX — ia menemukan tarif VENDOR ASAL, bukan tarif
        # agregator. Karena itu baris agregator TIDAK BOLEH memakainya sama sekali.
        if pricing is None and m.get("component") == "llm" and not agr:
            if orm is None:
                orm = _openrouter_map()
            # Daftar sumber cadangan dibangun BY SUFFIX (lihat `_openrouter_map`: id vendor/model →
            # kunci polos). Pencariannya wajib memakai kunci yang sama, kalau tidak model yang
            # penandanya berawalan vendor (seluruh model naskah fal) tak pernah ketemu — harganya
            # mandek di angka manual lama selamanya. Model berpenanda polos: split → dirinya sendiri.
            fo = orm.get((m.get("model_id") or m["model_key"]).split("/")[-1])
            if fo:
                pricing = {**fo, "source": "openrouter", "synced_at": now}
        if pricing is None:
            missing.append(m["model_key"])
            continue

        # SANITY-GUARD: perubahan drastis → tahan di pricing_pending (admin putuskan), JANGAN terapkan.
        reason = _sanity_violation(m.get("pricing"), pricing)
        if reason:
            sb.table("ai_models").update({"pricing_pending": {**pricing, "reason": reason}}).eq("model_key", m["model_key"]).execute()
            held.append(f"{m['model_key']} ({reason})")
            continue
        patch = {"pricing": pricing, "pricing_pending": None}
        # Sumber resmi penyedia menyebut SATUAN tagihnya → formulanya ikut disetel. Tanpa ini,
        # bentuk harga berubah tapi formula lama tetap → biaya jadi "tak terhitung" (mis. Kling
        # pindah dari basis-per-klip ke per-detik).
        if m["model_key"] in formula_baru:
            patch["pricing_model"] = formula_baru[m["model_key"]]
        sb.table("ai_models").update(patch).eq("model_key", m["model_key"]).execute()
        updated += 1

    if (feed is not None or updated) and not only_model_key:
        _state_set_epoch(sb, "ai_price_synced_at")

    if held:
        _notify_admin("⚠️ <b>Usulan harga model DITAHAN</b> (berubah drastis — konfirmasi di Catalog → AI Models):\n"
                      + "\n".join(f"• <code>{h}</code>" for h in held))
        logger.warning(f"[price_sync] usulan harga DITAHAN (sanity-guard): {held}")
    if missing:
        logger.warning(f"[price_sync] model TANPA harga di semua sumber (isi manual + lock di Catalog): {missing}")
    logger.info(f"[price_sync] tersinkron: {updated} update, {len(held)} ditahan, {len(missing)} tanpa-sumber")

    _check_staleness(sb, rows)
    return {"updated": updated, "held": held, "missing": missing}


def report_unpriced_models(sb=None) -> dict:
    """Model yang GAGAL DIHITUNG biayanya pada produksi NYATA → alarm admin 1×/hari.

    KENAPA BERBASIS BUKTI, BUKAN ATURAN PER-JENIS (owner 2026-08-22). Mesin biaya sudah menuliskan
    kegagalannya sendiri di tiap run (`run_metadata.cost.unpriced`) — tapi **nol pembaca**, sehingga
    biaya suara 4 channel aktif dilaporkan Rp 0 selama 16 produksi tanpa seorang pun tahu. Daftar
    aturan "jenis X pakai satuan Y" tak dipakai di sini dengan sengaja: vendor berikutnya bisa
    menagih dengan satuan yang belum ada hari ini, dan daftar semacam itu PASTI tertinggal —
    hasilnya nol senyap yang sama. Produksi nyata tak bisa tertinggal.

    Nol alarm palsu secara konstruksi: hanya menyala bila uang nyata SUDAH tak terhitung.
    Fail-soft total: apa pun yang gagal di sini tak boleh mengganggu petugas harian."""
    try:
        sb = sb or _sb()
        sejak = (datetime.now(timezone.utc) - timedelta(days=UNPRICED_WINDOW_DAYS)).isoformat()
        rows = (sb.table("production_runs").select("run_metadata")
                .gte("created_at", sejak).execute().data or [])
        hitung: dict[str, int] = {}
        for r in rows:
            for mk in (((r.get("run_metadata") or {}).get("cost") or {}).get("unpriced") or []):
                hitung[str(mk)] = hitung.get(str(mk), 0) + 1
        if not hitung:
            return {"unpriced": {}}
        if _time.time() - _state_get_epoch(sb, "ai_unpriced_alerted_at") < 86400:
            return {"unpriced": hitung, "alerted": False}
        from src.utils.telegram_notifier import TelegramNotifier   # lazy: pola berkas ini
        baris = "\n".join(f"• <code>{TelegramNotifier.aman(k)}</code> — {v} produksi"
                           for k, v in sorted(hitung.items(), key=lambda x: -x[1]))
        _notify_admin(
            f"⚠️ <b>Biaya AI TIDAK TERHITUNG</b> ({int(UNPRICED_WINDOW_DAYS)} hari terakhir)\n{baris}\n"
            f"Biaya yang dilaporkan ke tenant jadi LEBIH MURAH dari kenyataan.\n"
            f"➡️ Buka <b>Catalog → AI Models</b>, cari model di atas: barisnya bertanda "
            f"<b>⚠️ satuan harga kosong</b> dan menyebut PERSIS satuan mana yang harus diisi. "
            f"Tekan ✎ lalu isi angkanya dari halaman tarif resmi vendor — menyimpan manual otomatis "
            f"MENGUNCI baris itu, jadi sinkron harian tak bisa menimpanya lagi.")
        _state_set_epoch(sb, "ai_unpriced_alerted_at")
        return {"unpriced": hitung, "alerted": True}
    except Exception as e:
        logger.warning(f"[price_sync] laporan biaya-tak-terhitung gagal (non-fatal): {e}")
        return {"unpriced": {}}


def report_rekonsiliasi_biaya(sb=None) -> dict:
    """[F8] Biaya yang SALAH tanpa mesin menyadarinya → alarm admin 1×/hari.

    BEDA DENGAN `report_unpriced_models`. Yang itu melapor bila penghitung **tahu** ia gagal
    (`cost.unpriced` terisi). Celah yang tersisa justru yang lebih berbahaya: penghitung **tidak
    tahu** — angkanya keluar, tampak wajar, nol alarm menyala. Itu bentuk insiden 22-Agu: biaya suara
    4 channel aktif dilaporkan Rp 0 selama 16 produksi sementara seluruh mesin diam.

    Ground truth yang IDEAL (pemakaian nyata di akun vendor) TIDAK tersedia: tak satu pun dari 9
    penyedia aktif kita menerbitkan penghitung pemakaian yang bisa dibaca dengan kunci biasa, dan
    membaca tagihan akun tenant = keputusan owner, bukan keputusan saya (BYOK: itu akun mereka).
    Maka yang dipakai di sini adalah dua tanda yang bisa diperiksa dari catatan kita sendiri, tanpa
    satu pun panggilan ke vendor, dan keduanya BERARTI uang nyata tak tertagih:
      (a) ada PANGGILAN tercatat tapi token nol → vendor berhenti melaporkan pemakaian
      (b) ada pemakaian, biaya total 0, dan daftar belum-terhitung KOSONG → nol senyap sejati
    Keduanya **nol pada 246 produksi** saat dipasang (23-Agu) ⇒ nol alarm palsu; nilainya menangkap
    REGRESI kelas itu. Jendela buktinya memakai kenop yang sudah ada (`AI_UNPRICED_WINDOW_DAYS`) —
    tujuannya sama (jendela bukti produksi), jadi tak perlu kenop baru.

    Fail-soft mutlak: ini pengawas, bukan jalur kerja. Kegagalannya haram menjatuhkan petugas harian.
    """
    try:
        sb = sb or _sb()
        sejak = (datetime.now(timezone.utc) - timedelta(days=UNPRICED_WINDOW_DAYS)).isoformat()
        rows = (sb.table("production_runs").select("id, run_metadata")
                .gte("created_at", sejak).execute().data or [])
        tanpa_token: dict[str, int] = {}
        nol_senyap: list = []
        for r in rows:
            meta = r.get("run_metadata") or {}
            usage = meta.get("ai_usage") or {}
            biaya = meta.get("cost") or {}
            for mk, v in (usage.get("llm") or {}).items():
                if isinstance(v, dict) and int(v.get("calls") or 0) > 0 \
                        and not int(v.get("tokens_in") or 0) and not int(v.get("tokens_out") or 0):
                    tanpa_token[str(mk)] = tanpa_token.get(str(mk), 0) + 1
            if usage and biaya and float(biaya.get("usd") or 0) == 0 \
                    and not (biaya.get("unpriced") or []):
                nol_senyap.append(r.get("id"))
        hasil = {"panggilan_tanpa_token": tanpa_token, "nol_senyap": nol_senyap}
        if not tanpa_token and not nol_senyap:
            return hasil
        if _time.time() - _state_get_epoch(sb, "ai_rekon_alerted_at") < 86400:
            return {**hasil, "alerted": False}
        from src.utils.telegram_notifier import TelegramNotifier   # lazy: pola berkas ini
        baris = []
        if tanpa_token:
            baris.append("• <b>Panggilan tercatat tapi pemakaiannya NOL</b> — vendor berhenti "
                         "mengirim hitungan, jadi panggilan yang sungguh terjadi ditagih Rp 0:")
            baris += [f"   <code>{TelegramNotifier.aman(k)}</code> — {v} produksi"
                      for k, v in sorted(tanpa_token.items(), key=lambda x: -x[1])]
        if nol_senyap:
            baris.append(f"• <b>Biaya total Rp 0 padahal ada pemakaian</b>, dan mesin TIDAK "
                         f"mengaku gagal — {len(nol_senyap)} produksi "
                         f"(mis. #{nol_senyap[0]}).")
        _notify_admin(
            f"⚠️ <b>Biaya AI tampak wajar tapi TIDAK BENAR</b> "
            f"({int(UNPRICED_WINDOW_DAYS)} hari terakhir)\n" + "\n".join(baris) +
            "\nIni BUKAN kegagalan yang mesin sadari — angkanya keluar dan tampak normal, jadi "
            "tanpa laporan ini ia bisa berjalan berbulan-bulan.\n"
            "➡️ Periksa <b>Catalog → AI Models</b> pada model di atas: formula & satuan harganya "
            "masih cocok dengan cara vendor menagih hari ini?")
        _state_set_epoch(sb, "ai_rekon_alerted_at")
        return {**hasil, "alerted": True}
    except Exception as e:
        logger.warning(f"[price_sync] rekonsiliasi biaya gagal (non-fatal): {e}")
        return {}


def sync_fx_rate(sb=None, force: bool = False) -> dict:
    """Kurs USD→IDR (`app_config.usd_idr_rate`, TAMPILAN biaya BYOK) — sinkron harian dari kurs pasar
    publik. `usd_idr_rate_locked`=1 (diset otomatis saat admin edit manual) → HORMATI, jangan timpa.
    Sanity band FX_SANITY_MIN..MAX: feed gila → skip + log (kurs lama tetap dipakai). Fail-soft total."""
    sb = sb or _sb()
    try:
        r = sb.table("app_config").select("value").eq("key", "usd_idr_rate_locked").limit(1).execute()
        if r.data and int(r.data[0]["value"] or 0) == 1:
            return {"skipped": "locked"}
    except Exception:
        pass
    if not force:
        last = _state_get_epoch(sb, "fx_synced_at")
        if last and (_time.time() - last) < SYNC_INTERVAL_HOURS * 3600:
            return {"skipped": "fresh"}
    try:
        d = requests.get(FX_URL, timeout=20).json()
        idr = float((d.get("rates") or {}).get("IDR") or 0)
    except Exception as e:
        logger.warning(f"[price_sync] sumber kurs gagal ({e}) — kurs lama tetap dipakai")
        return {"error": str(e)}
    if not (FX_SANITY_MIN <= idr <= FX_SANITY_MAX):
        logger.warning(f"[price_sync] kurs di luar band waras ({idr}) — DITOLAK, kurs lama tetap dipakai")
        return {"rejected": idr}
    sb.table("app_config").update({"value": int(round(idr)),
                                   "updated_at": datetime.now(timezone.utc).isoformat()}).eq("key", "usd_idr_rate").execute()
    _state_set_epoch(sb, "fx_synced_at")
    logger.info(f"[price_sync] kurs USD→IDR tersinkron: {int(round(idr))}")
    return {"rate": int(round(idr))}
