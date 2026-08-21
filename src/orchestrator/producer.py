"""
Producer — loop persisten jaga buffer per-channel (Phase 5.3, DESAIN §12c).

JANTUNG anti-OOM: render dibatasi **semaphore = MAX_CONCURRENT_RENDER (jumlah core)**,
dipegang SATU proses loop hidup (BUKAN cron — cron spawn buta = tak ada rem = OOM, terbukti).
produce_one = pipeline.run(publish=False) → upload video+thumbnail ke S3 → simpan SEMUA input
publish (script/metadata) di content_inventory → status ready. Publisher (proses terpisah)
yang melakukan publish dari buffer.
"""

import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from src.orchestrator import inventory
from src.exceptions import FAST_FAIL, ErrorClass

# [ERROR-MGMT] nilai string ErrorClass yang memicu rem-segera (persis set FAST_FAIL exceptions.py).
_FAST_FAIL_VALUES = frozenset(ec.value for ec in FAST_FAIL)

from src.utils import s3_buffer

# [2026-08-13] Channel yang sudah dicatat "langganan tidak aktif" — supaya tidak dicatat ulang tiap
# siklus (±15,6 detik). Isinya hanya id channel (11 channel hari ini), jadi tak ada beban memori
# berarti. Sengaja di tingkat proses: pekerja hidup terus, dan bila ia direstart wajar bila keadaan
# itu dicatat sekali lagi — satu baris per restart, bukan ribuan per hari.
_SKIP_SUDAH_DICATAT: set[str] = set()
# [2026-08-21] Penanda TERPISAH untuk cabang "belum READY". SENGAJA bukan `_SKIP_SUDAH_DICATAT`:
# penanda itu di-`discard` tepat SEBELUM cek kesiapan (baris `_SKIP_SUDAH_DICATAT.discard(cid)`),
# jadi memakainya di sini = penanda dibuang tiap siklus = banjir log tetap terjadi.
# Terukur sebelum perbaikan: 20.979 baris dalam 5 hari (±1 baris/17 detik) untuk 4 channel yang sama —
# sinyal tenggelam, dan setiap diagnosa harus mengaduk berkas puluhan MB berisi pengulangan.
_READY_SUDAH_DICATAT: dict[str, str] = {}


def _yt_video_id(url: str) -> str | None:
    """Ekstrak video_id dari URL YouTube (shorts / youtu.be / watch?v=). Robust — URL selalu memuat id."""
    if not url:
        return None
    m = re.search(r"(?:youtube\.com/shorts/|youtu\.be/|[?&]v=)([\w-]{6,})", url)
    return m.group(1) if m else None


def max_concurrent_render() -> int:
    """Rem anti-OOM: = jumlah core (config-driven PRODUCER_MAX_RENDER). Lihat §12c."""
    v = os.getenv("PRODUCER_MAX_RENDER")
    if v and v.isdigit():
        return max(1, int(v))
    return max(1, os.cpu_count() or 2)


def target_stock(ch: dict) -> int:
    """Target stok per-channel SADAR-JADWAL + SADAR-TTL (owner 2026-07-09; pengganti angka statis 2).
    Dasar: (1) stok > kebutuhan → video menunggu > TTL 72j → disapu janitor = compute terbuang;
    (2) tenant model gratis kuota-harian (Groq/Cloudflare) → produksi eager melebihi kuota →
    gagal beruntun → circuit-break. Aturan:
    • `channels.buffer_depth` eksplisit (incl. 0) = keputusan manusia → MENANG apa adanya.
    • NULL → jumlah slot/hari × `app_config.buffer_target_days` (admin-editable, fail-soft 1),
      di-clamp ≤ slot/hari × hari-TTL (stok takkan melebihi yang sempat tayang sebelum basi).
    • Tanpa jadwal slot → 0 (publisher tak pernah menayangkannya; stok pasti berakhir di janitor)."""
    explicit = ch.get("buffer_depth")
    if explicit is not None:
        return max(0, int(explicit))
    slots = len(ch.get("publish_slots") or [])
    if slots == 0:
        return 0
    from src.config.app_config import get_int
    days = max(1, get_int("buffer_target_days", 1))
    ttl_days = max(1, int(float(os.getenv("BUFFER_TTL_HOURS", "72")) // 24))
    return max(1, slots * min(days, ttl_days))


def _resolve_niche(channel_row: dict) -> str | None:
    """Resolusi niche per-channel SEBELUM pipeline (jalur SCHEDULED saja — `run_direct` pakai niche
    EKSPLISIT job & TIDAK lewat sini, jadi niche test/rerun tak pernah ditimpa rotasi).
    `niche_mode='fixed'` → `channels.niche` apa adanya; `'random'` → pilih ACAK dari **`channels.niche_pool`**
    (PILIHAN tenant, BUKAN seluruh entitlement — revisi owner 2026-06-27 agar channel multi-niche tak rusak),
    lalu hindari 1-2 niche TERAKHIR channel (berdekatan) → acak lagi. Entitlement tiap niche pool sudah
    divalidasi saat di-set (RPC set_channel_niche). ([[decisions_niche_model]]: random = dari niche_pool.)
    Fail-soft → `channels.niche`."""
    base = channel_row.get("niche")
    if (channel_row.get("niche_mode") or "fixed").lower() != "random":
        return base
    try:
        import random as _rand
        from supabase import create_client
        channel_id = str(channel_row.get("id") or channel_row.get("channel_id") or channel_row.get("tenant_id"))
        # POOL = pilihan tenant (niche_pool); fallback ke channels.niche bila pool kosong/absen.
        pool = [n for n in (channel_row.get("niche_pool") or []) if n]
        # NICHE_DNA (owner 2026-07-04): hormati niches.is_active — niche yang dinonaktifkan
        # (tenant di Studio / admin) TIDAK ikut rotasi. (Mode 'fixed' = binding eksplisit channel,
        # tak disaring di sini.) Fail-soft: registry tak terbaca → pool apa adanya.
        try:
            from src.intelligence.config import get_niches
            _reg = get_niches()
            pool = [n for n in pool if (_reg.get(n) or {}).get("is_active", True)]
        except Exception:
            pass
        if not pool:
            return base
        if len(pool) == 1:
            return pool[0]
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        # 1-2 niche TERAKHIR channel (content_inventory = sinyal terbaru, mencakup yg baru diproduksi).
        recent = []
        try:
            _r = (sb.table("content_inventory").select("niche")
                  .eq("channel_id", channel_id).order("created_at", desc=True).limit(2).execute())
            recent = [x["niche"] for x in (_r.data or []) if x.get("niche")]
        except Exception:
            recent = []
        chosen = _rand.choice(pool)
        for _ in range(8):                 # acak lagi bila berdekatan; mentok → pakai apa adanya
            if chosen not in recent:
                break
            chosen = _rand.choice(pool)
        if chosen != base:
            logger.info(f"[Producer] niche random dari pool (hindari {recent}): {base} → {chosen} (ch={channel_id})")
        return chosen
    except Exception as e:
        logger.warning(f"[Producer] resolusi niche random gagal ({e}) — pakai channels.niche '{base}'")
        return base


def _record_production_run(channel_row: dict, result: dict, status: str,
                           qc_passed: bool | None, error: str | None = None) -> None:
    """Observability: tulis 1 baris `production_runs` utk produksi SCHEDULED (produce_one) → tampak
    di FE /runs (selama ini hanya `run_direct` yang menulis → produksi terjadwal tak terlihat).
    queue_id NULL (jalur decoupled, bukan pipeline_queue); youtube_url NULL (producer HANYA stok —
    publish oleh publisher saat slot). run_metadata.scheduled=True (bedakan dari direct). Fail-soft."""
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        script = result.get("script", {}) or {}
        sb.table("production_runs").insert({
            "tenant_id":       channel_row["tenant_id"],
            "run_id":          result.get("run_id"),
            "channel_id":      str(channel_row.get("id") or channel_row.get("channel_id") or ""),
            "niche":           result.get("niche"),
            "topic":           script.get("topic", ""),
            "status":          status,
            "qc_passed":       qc_passed,
            "viral_score":     script.get("viral_score"),
            "llm_provider":    script.get("llm_provider_used"),
            # [2026-08-21] Model yang DITOLAK vendor. Dulu hanya `llm_provider` yang disimpan, dan
            # nama modelnya cuma hidup di teks bebas — padahal vendor SUDAH menyebutkannya. Tanpa
            # kolom ini, bukti-silang antar-tenant (satu-satunya bukti karantina yang BEBAS BIAYA)
            # mustahil dihitung. Owner menolak pembuktian berbayar dengan kunci admin (21-Agu).
            "failed_model":    result.get("failed_model") or None,
            "elapsed_seconds": result.get("elapsed_seconds"),
            "error_message":   error,
            "error_class":     result.get("error_class"),   # [ERROR-MGMT] makna → circuit-breaker semantik
            # (karantina katalog dinilai di bawah, SESUDAH baris ini tersimpan — supaya bukti-silang
            #  antar-tenant menghitung kegagalan ini juga)
            # video_title = judul AKHIR (yang tampil di YouTube) — FE Runs menampilkan ini, bukan
            # topik internal (owner 2026-07-10: 1 video sempat tampil beda nama di Runs vs Studio).
            "run_metadata":    {"scheduled": True, "mode": "buffer", "video_title": script.get("title", ""), **_cost_fields(result), **_mutu_fields(result)},
        }).execute()
    except Exception as e:
        logger.warning(f"[Producer] tulis production_runs (scheduled) gagal — non-fatal: {e}")

    # ── KATALOG BELAJAR (AI_ERROR_MGMT §9b) ──────────────────────────────────────────────────
    # Sinyal "model mati" dulu berhenti di baris di atas: katalog tak pernah tahu, jadi model yang
    # TERBUKTI mati tetap ditawarkan ke tenant BERIKUTNYA (Abyss ID diam 24 hari; 17-Agu 4 channel
    # / 2 tenant BERBAYAR diam 4 hari). Dinilai SESUDAH baris tersimpan supaya bukti-silang
    # antar-tenant ikut menghitung kegagalan ini.
    # NOL panggilan berbayar — owner menolak pembuktian dengan kunci admin (21-Agu).
    try:
        if (result.get("error_class") or "") == ErrorClass.MODEL_UNAVAILABLE.value:
            from src.orchestrator.karantina_model import karantina
            karantina(sb, result.get("failed_model") or "",
                      result.get("error_dasar") or "", result.get("error") or "")
    except Exception as e:
        # Fail-soft MUTLAK: karantina adalah pembelajaran katalog, bukan jalur produksi.
        # Kegagalannya HARAM menghentikan apa pun.
        logger.warning(f"[Producer] penilaian karantina model gagal — non-fatal: {e}")


def _cost_fields(result: dict) -> dict:
    """B2 cost-tracking: {ai_usage, cost} utk run_metadata — konsumsi dari pipeline (cost_meter) +
    konversi USD via katalog harga (ai_cost). Fail-soft: gagal hitung → usage tetap tercatat."""
    usage = result.get("ai_usage") or {}
    if not usage:
        return {}
    out = {"ai_usage": usage}
    try:
        from src.billing.ai_cost import compute_cost_usd
        cost = compute_cost_usd(usage)
        if cost:
            out["cost"] = cost
    except Exception as e:
        logger.warning(f"[Producer] hitung biaya AI gagal (usage tetap dicatat): {e}")
    return out


def _mutu_fields(result: dict) -> dict:
    """[§8f · 15-Agu] Penurunan mutu yang TERJADI pada run ini → `run_metadata`, supaya berhenti senyap.

    ═══ KENAPA INI ADA ═══
    Frame PERTAMA adalah tuas viral — penentu penonton berhenti menggulir. Bila pembuatannya gagal,
    video TETAP diterbitkan dengan klip biasa sebagai pembuka: lebih lemah, dan **tak seorang pun
    diberi tahu**. Itu melanggar §0.6 yang sudah diketok owner: *"kegagalan komponen = STOP +
    notifikasi, HARAM fallback senyap"*.

    ═══ KENAPA BARU SEKARANG — pengakuan yang tertulis di kode sendiri ═══
    Sebabnya SUDAH ditangkap sejak 05-Agu (`visual_assembler.hook_frame_error`) dan dimasukkan ke
    `result["steps"]["visuals"]`. Tapi `steps` **tidak pernah ditulis ke tabel mana pun** — komentar
    di `visual_assembler.py` bahkan mengakuinya terang-terangan sejak 08-Agu. Jadi selama sepuluh
    hari nilainya ditangkap lalu dibuang. Terukur 15-Agu: **85 run sejak 8-Agu, NOL yang
    menyimpannya.** Berkas ini menyambung ujung yang menganga itu.

    ⚠️ **AKAR YANG SAMA, TIGA KALI** (dicatat supaya berhenti terulang): keterangan ditangkap lalu
    dibuang sebelum sampai ke siapa pun — (1) golongan galat ada di `production_runs` tapi layar tak
    membacanya · (2) sebab frame pembuka ada di memori tapi tak disimpan · (3) pesan mentah penyedia
    ada di dalam galat tapi ditimpa pesan kita saat menyimpan. **Menangkap ≠ menyampaikan.**

    Yang TIDAK diubah: video tetap diterbitkan. Menghentikan produksi karena frame pembuka =
    keputusan produk (§0.6) dan bukan hak Claude; yang dilarang §0.6 adalah **senyap**-nya, dan
    itulah yang ditutup di sini. Fail-soft: gagal mencatat tak boleh menggagalkan produksi.
    """
    try:
        v = ((result.get("steps") or {}).get("visuals") or {})
        hf = v.get("hook_frame_error")
        if not hf:
            return {}
        # Tanpa pemotongan: §8h — memotong pesan penyedia justru membuang angka & tautan
        # perbaikannya. Nilai tersimpan apa adanya; peringkasan hanya saat DITAMPILKAN.
        return {"mutu": {"frame_pembuka_gagal": str(hf)}}
    except Exception as e:                       # fail-soft: pencatatan tak boleh menghentikan apa pun
        logger.warning(f"[Producer] catat penurunan mutu gagal (non-fatal): {e}")
        return {}


def produce_one(channel_row: dict) -> int | None:
    """Produksi 1 video (TANPA publish) → buffer. Return inv_id ready, atau None bila gagal/QC fail."""
    from src.intelligence.config import tenant_config_from_channel
    from src.orchestrator.pipeline import Pipeline

    tenant_id  = channel_row["tenant_id"]
    channel_id = str(channel_row.get("id") or channel_row.get("channel_id") or "default")
    # Niche per-channel di HULU (scheduled): random → rotasi LRU entitlement / fixed → channels.niche.
    # Inventory + pipeline memakai niche yang SUDAH ter-resolve (single source; pipeline tak merotasi lagi).
    niche      = _resolve_niche(channel_row)
    run_id     = f"{tenant_id}_{int(time.time())}"  # pre-gen → contextualize log SEBELUM pipeline jalan
    inv_id = inventory.record_producing(tenant_id, channel_id, niche,
                                        {"channel": channel_row.get("channel_name")})
    try:
        tc = tenant_config_from_channel(channel_row, niche=niche)
        # Diversity Engine (Phase 6.2, DESAIN §9.1) — hint rotasi per-channel (LRU lookback).
        # PREFERENSI saja (quality tetap di-gate ScriptAnalyzer/skor hook); fail-soft → None.
        try:
            from src.intelligence.diversity import DiversityEngine
            from src.intelligence.config import get_niches
            _div = DiversityEngine()
            tc.preferred_hook_pattern = _div.pick_hook_pattern(channel_id)
            tc.visual_seed = _div.pick_seed(channel_id)
            # Music-mood rotation (§9.1): kandidat = niches.mood_priority (semua niche-appropriate,
            # admin-kurasi) → LRU per-channel. Tak ada pool → None (perilaku lama, non-breaking).
            _mood_pool = (get_niches().get(niche) or {}).get("mood_priority") or []
            tc.preferred_music_mood = _div.pick(channel_id, "music", _mood_pool) if _mood_pool else None
        except Exception as _de:
            logger.debug(f"[Producer] diversity hint skip (ch={channel_id}): {_de}")
        # contextualize → log pipeline buffer-run tersimpan ke pipeline_run_logs (live-tail D5),
        # ber-run_id SAMA dgn production_runs. Sebelumnya log buffer hilang (hanya direct yg ter-log).
        with logger.contextualize(tenant_id=tenant_id, channel_id=channel_id, run_id=run_id):
            result = Pipeline().run(tc, publish=False, run_id=run_id)   # PRODUCE-ONLY (producer TAK pernah publish — §12c)
        qc    = result.get("steps", {}).get("qc", {})
        video = result.get("video_path")
        # HARD-FAIL (crash render/visual, TANPA video jadi) → failed (TIDAK dihitung stok).
        if result.get("status") != "success" or not video or not os.path.exists(video):
            _err = result.get("human_error") or result.get("error") or "produksi gagal (tanpa video)"
            # [ERROR-MGMT] catat production_runs (ber-error_class) DULU, baru mark_failed. mark_failed
            # melepas slot "producing" → deficit muncul lagi; bila baris belum tertulis, siklus producer
            # bisa submit percobaan berikut TANPA melihat error_class → fast-fail kebobolan. Reorder ini
            # menjamin baris ada sebelum slot bebas (2 tabel independen — nol dependensi).
            _record_production_run(channel_row, result, "failed", False, _err)
            inventory.mark_failed(inv_id, _err)
            return None

        run_id = result["run_id"]
        thumb  = result.get("thumbnail_path")
        vkey = f"{tenant_id}/{channel_id}/{run_id}.mp4"
        s3_buffer.upload(video, vkey)
        tkey = None
        if thumb and os.path.exists(thumb):
            tkey = f"{tenant_id}/{channel_id}/{run_id}.jpg"
            s3_buffer.upload(thumb, tkey)

        # Persist SEMUA input publish (publisher = proses terpisah, tak punya file lokal)
        _script = result.get("script", {}) or {}
        _winner = (_script.get("hook_data") or {}).get("winner") or {}
        _meta = {
            "run_id":    run_id,
            "video_s3":  vkey,
            "thumb_s3":  tkey,
            "script":    _script,
            "niche":     result.get("niche"),
            # Dimensi diversity (Phase 6.2) → publisher tulis ke `videos` (histori lookback berikutnya)
            "hook_pattern": _winner.get("formula"),
            "visual_seed":  tc.visual_seed,
            # suara AKTUAL saat PRODUKSI (bukan saat publish — bisa beda bila admin ganti voice
            # selama video di buffer) → sumber videos.voice_id utk compliance voice_diversity.
            "tts_voice":    getattr(tc, "tts_voice", None),
            # mood AKTUAL = mood rotasi yang di-inject ke music_selector (bukan saran LLM
            # background_music_mood yang TAK dipakai music_selector). Null bila niche tanpa mood_priority.
            "music_mood":   tc.preferred_music_mood,
            "viral_score":  _script.get("viral_score"),
            "insights_grade": _script.get("insights_grade", ""),
            "duration_secs": qc.get("duration"),
            "size_mb":       qc.get("size_mb"),
        }

        def _cleanup_local():
            for p in (video, thumb):
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

        # OPSI C (2026-06-17): QC-fail TAPI video JADI → STOK 'ready_with_issues' (ditinjau tenant di
        # dashboard, approve→publish ber-kuota / buang). DIHITUNG stok → rem alami (anti-runaway).
        # Video TIDAK di-upload ke YouTube oleh producer (invariant decouple §12c).
        if not qc.get("passed"):
            inventory.mark_ready_with_issues(
                inv_id, vkey, reason=qc.get("reason", ""),
                recommendation=qc.get("recommendation", ""), metadata=_meta,
                reason_code=qc.get("reason_code"), reason_params=qc.get("reason_params"))
            _cleanup_local()
            _record_production_run(channel_row, result, "qc_failed", False, qc.get("reason"))
            logger.warning(f"[Producer] ready_with_issues (tinjau): {vkey} (inv {inv_id}) — {qc.get('reason','')}")
            # Telegram (owner 2026-07-10): tenant WAJIB tahu ada video menunggu keputusan —
            # tanpa ini video didiamkan → TTL buang senyap → biaya produksi hangus. Fail-soft.
            try:
                from src.utils.telegram_notifier import TelegramNotifier
                TelegramNotifier().notify_review_pending(
                    tenant_id=tenant_id,
                    title=_script.get("title") or _script.get("topic", ""),
                    qc_reason=qc.get("reason", ""),
                    recommendation=qc.get("recommendation", ""),
                    run_config=tc,
                )
            except Exception as _te:
                logger.warning(f"[Producer] notif review-pending gagal — non-fatal: {_te}")
            return inv_id

        # QC-PASS → ready (siap auto-publish saat slot)
        inventory.mark_ready(inv_id, vkey, metadata=_meta)
        _cleanup_local()
        _record_production_run(channel_row, result, "success", True)
        logger.info(f"[Producer] buffer ready: {vkey} (inv {inv_id})")
        return inv_id
    except Exception as e:
        inventory.mark_failed(inv_id, str(e))
        logger.error(f"[Producer] produce gagal (tenant={tenant_id}, ch={channel_id}): {e}")
        return None


# ── DIRECT / ON-DEMAND (V2 "1 mesin, 2 mode") ──────────────────────────────

def run_preview_image(sb, job: dict, ch: dict) -> None:
    """PRATINJAU 1 GAMBAR dari DNA niche — bukan produksi.

    ═══ KENAPA ADA (ketetapan owner 2026-08-15, `SISA_KERJA [B32]` T11) ═══
    Mencocokkan gaya visual sebuah niche menuntut **video penuh**: ±4 menit, ±Rp 1.500 sekali coba.
    Terukur pada sesi 15-Agu: enam putaran video hanya untuk menyetel gaya, dan tiap putaran menunggu
    empat menit. Beban itu akan diwarisi SETIAP tenant yang ingin nichenya terlihat seperti yang ia
    bayangkan. Pratinjau: **±25 detik (terukur), ±Rp 250, nol video, nol kuota, nol jejak di stok konten.**

    ⚠️ **MEMAKAI PERAKIT PROMPT PRODUKSI APA ADANYA** — `_build_image_prompt` lalu corong
    `_generate_image` (yang menempelkan patri larangan & memotong-aman sesuai batas vendor). Merakit
    prompt sendiri di sini = melahirkan KEBENARAN KEDUA yang suatu hari berbeda dari produksi, persis
    kelas cacat yang [B32] tutup seharian ini. Pratinjau yang berbohong lebih berbahaya daripada tidak
    ada pratinjau: pemilik niche akan menyetel DNA-nya berdasarkan gambar yang tak mewakili hasil asli.

    Yang SENGAJA tidak disentuh: naskah · suara · render · `content_inventory` · `production_runs` ·
    kuota publish. Ini satu gambar, titik.
    """
    from datetime import datetime, timezone
    from pathlib import Path
    import asyncio, tempfile
    from src.intelligence.config import tenant_config_from_channel

    jid = job["id"]
    _now = lambda: datetime.now(timezone.utc).isoformat()
    niche = job.get("niche") or ch.get("niche")

    # Adegan contoh yang NETRAL: cukup untuk menampakkan gaya, tanpa mendikte isi konten niche.
    ADEGAN = "a person going about an ordinary everyday moment at home"

    try:
        tc = tenant_config_from_channel(ch, niche=niche)
        # Konfigurasi provider diambil dari PEMUAT PRODUKSI (`_load_run_config`) lalu dirakit dengan
        # bentuk yang SAMA PERSIS dengan `_try_ai_image` — bukan dikarang di sini. Percobaan pertama
        # saya merakit dict sendiri dan langsung patah ('TenantConfig' tak punya `visual_provider`);
        # itu justru bukti kenapa pratinjau tak boleh punya jalur sendiri.
        from src.production.visual_assembler import VisualAssembler
        from src.providers.visual import build_visual_provider
        rc = VisualAssembler()._load_run_config(tc)
        visual_mode = rc.get("visual_mode") or ""
        if not visual_mode:
            raise RuntimeError("Generator visual belum dipilih di channel ini")
        provider = build_visual_provider(visual_mode, {
            "tenant_id":              tc.tenant_id,
            "niche":                  niche,
            "visual_provider":        visual_mode,
            "visual_ai_model":        visual_mode.split(":", 1)[1] if ":" in visual_mode else "",
            "visual_api_key":         rc.get("visual_api_key"),
            "llm_api_key":            rc.get("llm_api_key") or "",
            "llm_library":            rc.get("llm_library") or "",
            "llm_provider":           rc.get("llm_provider") or "",
            "llm_models":             rc.get("llm_models") or {},
            "llm_model":              rc.get("llm_model") or "",
            "niche_visual_style":     rc.get("niche_visual_style") or {},
            "niche_visual_fallbacks": rc.get("niche_visual_fallbacks") or [],
            "image_quality":          rc.get("image_quality") or "",
            "visual_seed":            getattr(tc, "visual_seed", None),
        })

        # Adegan dirakit dari SELURUH DNA visual (cerminan jalur cadangan produksi) — bukan kalimat
        # mentah. Versi pertama mengirim ADEGAN apa adanya ⇒ hanya 2 dari 15 properti visual ikut,
        # sehingga pratinjaunya TIDAK mewakili hasil asli (temuan owner 15-Agu).
        from src.intelligence.config import muat_niche_segar
        from src.intelligence.script_engine import prompt_adegan_dari_dna
        adegan_ber_dna = prompt_adegan_dari_dna(muat_niche_segar(niche), ADEGAN)
        positif, negatif = provider._build_image_prompt(adegan_ber_dna)   # perakit PRODUKSI
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "pratinjau.png"
            asyncio.run(provider._generate_image(positif, negatif, f))  # corong PRODUKSI (patri ikut)
            from src.utils import s3_buffer
            # KUNCI TETAP per (tenant, niche) — sengaja BUKAN per-job. Tiap pratinjau baru MENIMPA
            # yang lama, jadi penyimpanan tak pernah menumpuk dan **tak perlu penyapu sama sekali**.
            # (Versi pertama memakai kunci per-job ⇒ tiap klik meninggalkan berkas ±2 MB selamanya;
            # kelalaian saya, ditemukan owner 15-Agu. Video uji punya penyapu ber-TTL; pratinjau
            # tidak perlu punya, karena masalahnya dihapus dari akarnya.)
            key = f"{job['tenant_id']}/pratinjau/{niche or 'niche'}.png"
            s3_buffer.upload(str(f), key)

        sb.table("direct_jobs").update({
            "status": "done", "result_key": key, "completed_at": _now(),
        }).eq("id", jid).execute()
        logger.info(f"[Pratinjau] job {jid} niche={niche} → {key}")
    except Exception as e:
        logger.error(f"[Pratinjau] job {jid} GAGAL: {e}")
        sb.table("direct_jobs").update({
            "status": "failed", "error": str(e)[:500], "completed_at": _now(),
        }).eq("id", jid).execute()


def segarkan_dna_sebelum_direct() -> None:
    """Buang potret DNA niche sebelum job yang DIPICU MANUSIA dijalankan.

    ═══ KENAPA (2026-08-15, `SISA_KERJA [B32]` T5) ═══
    Registry niche bercache 300 detik — benar untuk produksi terjadwal (48 niche dibaca ulang tiap run =
    beban DB sia-sia), tapi SALAH untuk jalur yang dipicu orang yang baru saja menekan Simpan. Alur
    tenant: sunting DNA → Simpan → "Jalankan test". Tanpa penyegaran ini, videonya lahir dari DNA LAMA
    dan tenant menyimpulkan "perubahan saya tidak berpengaruh" — lalu mengubahnya ke arah yang salah.

    Berlaku untuk SELURUH direct-job (uji niche · uji admin · ulangi), bukan disaring per-jenis:
    semuanya dipicu manusia yang menunggu hasilnya sekarang, dan menyaring per-jenis hanya menambah
    satu tempat baru untuk salah menggolongkan.

    `invalidate_niches_cache()` sudah ada sejak 2-Agu dengan **nol pemanggil** — mekanisme yang lahir
    mati; inilah pemanggilnya. GAGAL-LUNAK: kegagalan menyegarkan tak boleh menjatuhkan produksi yang
    seharusnya jalan (§0.6) — paling buruk kembali ke perilaku lama (potret ≤300 dtk).
    """
    try:
        from src.intelligence.config import invalidate_niches_cache
        invalidate_niches_cache()
    except Exception as e:
        logger.warning(f"[Direct] gagal menyegarkan DNA niche (lanjut dengan potret lama): {e}")


# Jalur prioritas: tenant/admin minta produksi 1 job SEKARANG (test/retry/admin_test).
# Di-drain SEBELUM stok-buffer, pakai semaphore+pool yang SAMA (anti-OOM utuh). Mesin = pipeline.run().
def run_direct(sb, job: dict) -> None:
    """Eksekusi 1 direct_job: produce + publish (privacy sesuai job) + tulis production_runs.
    Context run_id → pipeline_run_logs (live-tail D5). Tandai status di direct_jobs."""
    from datetime import datetime, timezone
    from src.intelligence.config import tenant_config_from_channel
    from src.orchestrator.pipeline import Pipeline

    # [B32] T5 — job ini dipicu MANUSIA yang baru menekan Simpan: DNA-nya wajib yang terbaru.
    segarkan_dna_sebelum_direct()

    jid = job["id"]
    tenant_id = job["tenant_id"]
    run_id = f"direct-{str(jid)[:8]}"
    _now = lambda: datetime.now(timezone.utc).isoformat()

    ch = (sb.table("channels").select("*").eq("id", job["channel_id"]).limit(1).execute().data or [None])[0]
    if not ch:
        sb.table("direct_jobs").update({"status": "failed", "error": "channel tak ditemukan", "completed_at": _now()}).eq("id", jid).execute()
        return

    # [B24 §10e-3 CELAH B] Channel WAJIB milik tenant pemilik job. Aturan akses tabel kini
    # memeriksanya, tapi jalur kunci-layanan melewati aturan itu — dan tanpa pemeriksaan di sini,
    # satu baris job yang menunjuk channel orang lain akan memakai kunci AI + koneksi YouTube
    # KORBAN: membakar dompet mereka dan mengunggah ke kanal mereka. Terbukti bisa disisipkan
    # (HTTP 201) sebelum ditutup. Nol job historis pernah melakukannya — ditutup sebelum terjadi.
    if str(ch.get("tenant_id") or "") != str(tenant_id):
        logger.error(f"[Direct] job {jid} menunjuk channel {job.get('channel_id')} milik tenant LAIN "
                     f"({ch.get('tenant_id')} ≠ {tenant_id}) — DITOLAK")
        sb.table("direct_jobs").update({
            "status": "failed", "error": "GATE:forbidden", "completed_at": _now(),
        }).eq("id", jid).execute()
        return

    # [B24 §10c LAPIS 3] GERBANG UJI — periksa ULANG tepat sebelum membakar slot render.
    # Job bisa sudah mengantre lalu keadaan berubah di tengah jalan: langganan jatuh tempo, admin
    # men-suspend, atau job lain di antrean yang sama menghabiskan jatah trial. Lapis DB & lapis API
    # memeriksa saat job DIBUAT; hanya lapis ini yang memeriksa saat job DIJALANKAN.
    #
    # [§10e-3 CELAH A] Dulu jenis 'admin_test' DIKECUALIKAN dari pemeriksaan ini — dan itu jadi
    # pintu belakang: tenant tinggal menulis 'admin_test' untuk melewati gerbang DAN melewati
    # penghitung jatah. Pengecualian dicabut; tak diperlukan sama sekali, karena tenant internal
    # admin (`admin_test_internal`) adalah akun comp yang gerbangnya SELALU mengizinkan.
    # Pesan disimpan sebagai KODE (`GATE:...`), bukan kalimat — FE yang menerjemahkan dwibahasa (§3.5).
    from src.billing.limits import test_gate
    _gate = test_gate(sb, tenant_id)
    if not _gate.get("allowed"):
        _alasan = _gate.get("reason") or "subscription"
        _kode = (f"GATE:trial_quota:{_gate.get('used')}:{_gate.get('max')}"
                 if _alasan == "trial_quota" else f"GATE:{_alasan}")
        logger.info(f"[Direct] job {jid} ({job.get('job_type')}) DITOLAK gerbang uji: "
                    f"{_kode} tenant={tenant_id}")
        sb.table("direct_jobs").update({
            "status": "failed", "error": _kode, "completed_at": _now(),
        }).eq("id", jid).execute()
        return

    sb.table("direct_jobs").update({"run_id": run_id}).eq("id", jid).execute()

    # Test niche TANPA publish (keputusan owner 2026-07-04): admin_test (channel internal admin) &
    # test_nopub (F5 — channel+kredensial TENANT sendiri, dari Niche Studio). Video → S3 status='test'
    # (tak pernah diklaim publisher; TTL janitor). Beda dari direct tenant test/retry (publish private).
    # [B32] T11 — pratinjau 1 gambar: bukan produksi, tak menyentuh naskah/suara/render.
    if (job.get("job_type") or "") == "preview_image":
        run_preview_image(sb, job, ch)
        return

    if (job.get("job_type") or "") in ("admin_test", "test_nopub"):
        _run_test_no_publish(sb, job, ch, run_id)
        return

    niche = job.get("niche") or ch.get("niche")
    status, yt_url, err, qc_ok, result = "failed", None, None, False, {}
    try:
        tc = tenant_config_from_channel(ch, niche=niche)
        try:
            tc.publish_privacy = job.get("publish_privacy") or "private"
            tc.run_kind = job.get("job_type") or ""   # "test"/"admin_test" → ditandai di laporan Telegram
        except Exception:
            pass
        with logger.contextualize(tenant_id=tenant_id, run_id=run_id):
            result = Pipeline().run(tc, publish=True)
        # Sumber kebenaran = ADA URL publish + status QC (pipeline set steps.qc.passed).
        # Opsi A: QC-fail TETAP menghasilkan URL (di-publish PRIVAT) → JANGAN dilabeli 'success'.
        yt_url = (result.get("published", {}).get("youtube") or {}).get("url")
        qc     = result.get("steps", {}).get("qc", {})
        qc_ok  = bool(qc.get("passed"))
        if yt_url and qc_ok:
            status = "success"
        elif yt_url and not qc_ok:
            status = "qc_failed"   # di-publish PRIVAT + advisory (tenant putuskan public/take-down)
            err = qc.get("reason") or "QC tak lolos — di-publish privat untuk ditinjau"
        else:
            status = "failed"
            # [ERROR-MGMT] utamakan pesan manusiawi (mis. billing EL) agar tampil bersih di Runs/Telegram.
            err = qc.get("reason") or result.get("human_error") or result.get("error") or "tidak publish (QC/produksi gagal)"
    except Exception as e:
        err = str(e)
        logger.error(f"[Direct] job {jid} gagal: {e}")

    # Tulis production_runs (muncul di Runs/D5). queue_id NULL (bukan jalur pipeline_queue).
    try:
        _script = result.get("script", {}) or {}
        # Tautkan video_id agar kolom Views di /runs ketemu (jalur buffer sudah; jalur direct
        # SEBELUMNYA tak menulisnya → Views selalu "—"). Sumber: hasil publish, fallback ekstrak URL.
        _yt_obj = result.get("published", {}).get("youtube") or {}
        _yt_vid = _yt_obj.get("video_id") or _yt_video_id(yt_url)
        sb.table("production_runs").insert({
            "tenant_id": tenant_id, "run_id": run_id, "channel_id": str(job["channel_id"]),
            "niche": niche, "topic": _script.get("topic", ""), "status": status,
            "youtube_url": yt_url, "youtube_video_id": _yt_vid, "qc_passed": qc_ok,
            "viral_score": _script.get("viral_score"),
            "llm_provider": _script.get("llm_provider_used"),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "error_message": err,
            "error_class": result.get("error_class"),   # [ERROR-MGMT]
            "run_metadata": {"direct": True, "job_type": job.get("job_type"), "video_title": _script.get("title", ""), **_cost_fields(result), **_mutu_fields(result)},
        }).execute()
    except Exception as e:
        logger.warning(f"[Direct] tulis production_runs gagal: {e}")

    # direct_jobs.status CHECK = pending|producing|published|failed → qc_failed (sudah ter-publish
    # PRIVAT) dipetakan ke 'published'; nuansa QC-fail ada di production_runs.status + advisory.
    sb.table("direct_jobs").update({
        "status": "published" if status in ("success", "qc_failed") else "failed",
        "error": err, "completed_at": _now(),
    }).eq("id", jid).execute()

    # Circuit-breaker AUTO-RECOVER (§4b/F7): direct yang MENGHASILKAN video (success/qc_failed) =
    # channel sehat lagi → lepas pause agar producer lanjut jaga buffer.
    if status in ("success", "qc_failed"):
        try:
            sb.table("channels").update({
                "production_paused": False, "production_paused_reason": None,
                "production_paused_at": None, "production_paused_class": None,
                # [0197] titik nol hitungan kegagalan — sama seperti jalur pemulihan lain.
                "production_resumed_at": _now(),
            }).eq("id", job["channel_id"]).execute()
        except Exception as e:
            logger.warning(f"[Direct] gagal lepas pause ch={job.get('channel_id')}: {e}")


def _run_test_no_publish(sb, job: dict, ch: dict, run_id: str) -> None:
    """Test niche ADMIN: pipeline penuh publish=False → S3 + content_inventory (ready/ready_with_issues;
    TTL janitor bersihkan otomatis) + production_runs (run_metadata.video_s3 utk ditonton di drawer).
    direct_jobs → 'done' (video jadi, TANPA YouTube) / 'failed'. Cermin produce_one (jalur teruji §12c)."""
    from datetime import datetime, timezone
    from src.intelligence.config import tenant_config_from_channel
    from src.orchestrator.pipeline import Pipeline

    jid = job["id"]
    tenant_id = job["tenant_id"]
    channel_id = str(job["channel_id"])
    niche = job.get("niche") or ch.get("niche")
    _now = lambda: datetime.now(timezone.utc).isoformat()

    status, err, qc_ok, result = "failed", None, False, {}
    inv_id = inventory.record_producing(tenant_id, channel_id, niche,
                                        {"channel": ch.get("channel_name"), "test": True})
    try:
        tc = tenant_config_from_channel(ch, niche=niche)
        try:
            tc.run_kind = "admin_test"
        except Exception:
            pass
        with logger.contextualize(tenant_id=tenant_id, channel_id=channel_id, run_id=run_id):
            result = Pipeline().run(tc, publish=False, run_id=run_id)

        qc = result.get("steps", {}).get("qc", {})
        qc_ok = bool(qc.get("passed"))
        video = result.get("video_path")
        vkey = None
        if result.get("status") == "success" and video and os.path.exists(video):
            vkey = f"{tenant_id}/{channel_id}/{run_id}.mp4"
            s3_buffer.upload(video, vkey)
            _meta = {"run_id": run_id, "video_s3": vkey, "niche": niche,
                     "viral_score": (result.get("script") or {}).get("viral_score"),
                     "duration_secs": qc.get("duration"), "size_mb": qc.get("size_mb")}
            # status='test' (bukan ready/ready_with_issues): tak diklaim publisher — KRITIS utk
            # test_nopub di channel tenant AKTIF (kalau 'ready', publisher akan mem-publish-nya!).
            inventory.mark_test(inv_id, vkey, qc_passed=qc_ok, reason=qc.get("reason", ""), metadata=_meta)
            try:
                if os.path.exists(video):
                    os.remove(video)
            except Exception:
                pass
            status = "done"   # video jadi (QC pass/fail sama-sama bisa ditonton) — TANPA publish
            err = None if qc_ok else (qc.get("reason") or "QC tak lolos — tonton & nilai di drawer")
        else:
            inventory.mark_failed(inv_id, result.get("error") or "produksi gagal (tanpa video)")
            # [SSOT error] samakan dgn jalur lain (blok scheduled :206 & direct-publish :340):
            # pesan-manusiawi (human_error) DULU → production_runs.error_message = teks yg SAMA di
            # semua jalur & permukaan. UNKNOWN → human_error None → jatuh ke result.error (nol regresi).
            err = result.get("human_error") or result.get("error") or qc.get("reason") or "produksi gagal (tanpa video)"
    except Exception as e:
        err = str(e)
        try:
            inventory.mark_failed(inv_id, err)
        except Exception:
            pass
        logger.error(f"[DirectTest] job {jid} gagal: {e}")

    try:
        _script = result.get("script", {}) or {}
        _qc = result.get("steps", {}).get("qc", {})
        sb.table("production_runs").insert({
            "tenant_id": tenant_id, "run_id": run_id, "channel_id": channel_id,
            "niche": niche, "topic": _script.get("topic", ""), "status": "success" if (status == "done" and qc_ok) else ("qc_failed" if status == "done" else "failed"),
            "qc_passed": qc_ok, "viral_score": _script.get("viral_score"),
            "llm_provider": _script.get("llm_provider_used"),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "error_message": err,
            "error_class": result.get("error_class"),   # [ERROR-MGMT]
            # video_s3 WAJIB di sini juga (drawer memutar video dari run_metadata — insiden 2026-07-04:
            # dulu hanya di inventory metadata → panel tak bisa putar video).
            "run_metadata": {"direct": True, "test": True, "job_type": job.get("job_type") or "admin_test", "inventory_id": inv_id,
                             "video_s3": (f"{tenant_id}/{channel_id}/{run_id}.mp4" if status == "done" else None),
                             "duration_secs": _qc.get("duration"), "size_mb": _qc.get("size_mb"),
                             **_cost_fields(result)},
        }).execute()
    except Exception as e:
        logger.warning(f"[DirectTest] tulis production_runs gagal: {e}")

    # WAJIB ter-log bila gagal (insiden 2026-07-04: update tak jalan → job nyangkut 'producing'
    # selamanya tanpa jejak — exception thread-pool tertelan diam-diam).
    try:
        sb.table("direct_jobs").update({
            "status": status, "error": err, "completed_at": _now(),
        }).eq("id", jid).execute()
        logger.info(f"[DirectTest] job {jid} → {status} (run {run_id})")
    except Exception as e:
        logger.error(f"[DirectTest] update direct_jobs {jid} → {status} GAGAL: {e}")


def drain_direct(sb, pool: ThreadPoolExecutor, sem: threading.Semaphore) -> int:
    """Drain direct_jobs pending SEBELUM stok-buffer. Acquire semaphore yang SAMA (≤core → anti-OOM).
    Idle → diproses tick berikut (≤idle_seconds); sibuk → paling depan saat 1 core bebas. Return jumlah submit."""
    jobs = (sb.table("direct_jobs").select("*").eq("status", "pending").order("created_at").limit(64).execute().data) or []
    from datetime import datetime, timezone
    submitted = 0
    for job in jobs:
        if not sem.acquire(blocking=False):
            break   # semua core sibuk → tunggu tick berikut (rem sama)
        sb.table("direct_jobs").update({"status": "producing", "started_at": datetime.now(timezone.utc).isoformat()}).eq("id", job["id"]).execute()

        def _task(job=job):
            try:
                run_direct(sb, job)
            finally:
                sem.release()

        pool.submit(_task)
        submitted += 1
    return submitted


def _active_channels(sb) -> list:
    return sb.table("channels").select("*").eq("is_active", True).execute().data or []


def _rapikan_alasan(teks: str) -> str:
    """Rapikan alasan rem — **tanpa memotong**. Hanya membuang spasi berlebih di ujung.

    [2026-08-06, §8h] Dulu fungsi ini memotong pada 500 huruf (sebelumnya 300). Batas itu tak
    melindungi apa pun: seluruh riwayat pesan galat sejak proyek lahir hanya 12,6 KB, dan tabel lain
    di database yang SAMA sudah menyimpan 1.855 huruf. Yang ia lakukan hanya membuang keterangan
    penyedia — dan mana yang terbuang tergantung penyedianya: inti pesan Groq ada di UJUNG
    ("try again in 34m37s"), OpenAI di AWAL, Gemini di TENGAH. **Tak ada aturan potong yang bisa
    benar untuk semua penyedia**, jadi satu-satunya pilihan jujur adalah tidak memotong.
    Peringkasan tetap ada — tapi hanya SAAT MENAMPILKAN, dan hanya di Telegram yang memang punya
    batas keras 4.096 huruf, dengan potongan yang DIUMUMKAN (`ringkas_diumumkan`).
    """
    return (teks or "").strip()


def _pause_channel(sb, ch: dict, reason: str, error_class: str | None = None) -> None:
    """Circuit-breaker §4b/F7: hentikan produksi channel + catat alasan DAN KELASNYA.

    `error_class` (migr 0196) = kelas error dari kegagalan yang menyalakan rem. Sistem SUDAH tahu
    nilainya saat memutuskan mengerem — sebelumnya dibuang, sehingga layar & notifikasi hanya bisa
    menganjurkan tebakan dan tenant tak pernah tahu apakah sebabnya PULIH SENDIRI atau butuh tindakan.
    Dampaknya terukur: satu channel tenant berbayar mati ±44 jam karena jatah harian penyedia habis —
    sebab yang pulih sendiri keesokan harinya. SSOT: AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8a/§9.

    Dilepas oleh: produksi direct yang sukses · reaktivasi langganan · tombol "Pulihkan produksi"
    (jalur buka manual, [B24] §10c).
    """
    from datetime import datetime, timezone
    try:
        sb.table("channels").update({
            "production_paused": True,
            "production_paused_at": datetime.now(timezone.utc).isoformat(),
            "production_paused_reason": _rapikan_alasan(reason),
            "production_paused_class": (error_class or None),
        }).eq("id", ch["id"]).execute()
    except Exception as e:
        logger.error(f"[Producer] gagal set pause ch={ch.get('id')}: {e}")


def plan_and_submit(sb, pool: ThreadPoolExecutor, sem: threading.Semaphore) -> int:
    """Satu siklus: hitung defisit buffer per-channel (target = `target_stock`, sadar-jadwal) →
    submit produksi sampai slot core habis. Return jumlah job di-submit. Rem: (1) semaphore=core
    (anti-OOM); (2) buffer penuh — issue DIHITUNG stok = rem alami; (3) circuit-breaker §4b/F7:
    N gagal beruntun → STOP channel + alarm (anti-runaway)."""
    channels = _active_channels(sb)
    from src.billing.limits import gate_for_channel
    from src.orchestrator.readiness import channel_readiness
    fail_stop = int(os.getenv("PRODUCER_FAIL_STREAK_STOP", "3"))
    deficits = []
    for ch in channels:
        cid = str(ch.get("id"))
        # Circuit-breaker: channel ter-pause → JANGAN produksi (tunggu tenant perbaiki + Jalankan Ulang/direct).
        if ch.get("production_paused"):
            continue
        # Phase 8a — gate monetisasi: jangan produksi (buang compute) utk tenant suspended/cancelled.
        if not gate_for_channel(sb, ch)["can_produce"]:
            # [2026-08-13] DICATAT SEKALI, bukan tiap siklus. Terukur: siklus berulang tiap 15,6
            # detik, dan channel yang langganannya mati dicatat ULANG setiap kali — 9.950 baris
            # dalam 24 jam untuk 2 channel, 44% dari seluruh isi log. Akibatnya bukan disk penuh
            # (masih 44 GB kosong) melainkan SINYAL TENGGELAM: setiap diagnosa harus mengaduk
            # berkas puluhan MB berisi pengulangan yang sama, dan itu dibayar waktu + kredit owner.
            # Penanda dihapus lagi begitu channel kembali memenuhi syarat (baris di bawah), jadi
            # PERUBAHAN KEADAAN tetap tercatat — yang hilang hanya pengulangannya.
            # Hanya baris pencatatan yang disentuh: syarat & `continue` TIDAK diubah, sehingga
            # channel mana yang berproduksi mustahil ikut berubah.
            if cid not in _SKIP_SUDAH_DICATAT:
                logger.info(f"[Producer] skip ch={cid} tenant={ch.get('tenant_id')} — subscription tidak aktif")
                _SKIP_SUDAH_DICATAT.add(cid)
            continue
        _SKIP_SUDAH_DICATAT.discard(cid)   # kembali aktif → kelak dicatat lagi bila mati lagi
        # F1-08 GERBANG AKTIVASI: channel belum lengkap (niche/model/voice/credential/OAuth) → skip
        # (no-fallback: jangan produksi pakai default diam-diam). FAIL-OPEN bila cek error transient
        # (lindungi channel sehat — mis. ryan — dari berhenti karena gangguan sesaat).
        _rd = channel_readiness(sb, ch)
        if not _rd["ready"] and not _rd["check_failed"]:
            # DICATAT SEKALI per KEADAAN (bukan tiap siklus) + alasan BERSTRUKTUR ikut disebut.
            # "kurang: model naskah" tak bisa didiagnosa siapa pun; nama model & penyedianya SUDAH
            # ada di tangan pada titik ini (migr 0204) — membuangnya berarti sesi berikutnya menebak.
            # Syarat & `continue` TIDAK diubah ⇒ channel mana yang berproduksi mustahil ikut berubah.
            _sebab = "; ".join(
                f"{r.get('slot')}: {r.get('model')} ({r.get('provider_name') or r.get('provider') or '?'}) "
                f"{r.get('code')}" for r in (_rd.get("reasons") or []))
            _keadaan = f"{','.join(_rd['missing'])}|{_sebab}"
            if _READY_SUDAH_DICATAT.get(cid) != _keadaan:
                logger.info(f"[Producer] skip ch={cid} — channel belum READY (kurang: "
                            f"{', '.join(_rd['missing'])})" + (f" — {_sebab}" if _sebab else ""))
                _READY_SUDAH_DICATAT[cid] = _keadaan
            continue
        _READY_SUDAH_DICATAT.pop(cid, None)   # kembali siap → kelak dicatat lagi bila rusak lagi
        # REM DARURAT (§4b/F7): N produksi beruntun gagal/bermasalah → STOP channel + alarm SEKETIKA.
        # [ERROR-MGMT 2026-07-18] REM SEGERA (setelah 1×) bila kegagalan TERAKHIR = kelas non-retryable
        # (kredit habis / pembayaran gagal) — mustahil sembuh dgn diulang → hemat biaya LLM percobaan
        # ke-2/3. Error lain (transien/unknown) TETAP toleransi `fail_stop` (nol regresi channel sehat).
        # [0197] Hitungan kegagalan dimulai dari titik PEMULIHAN terakhir. Tanpa batas ini,
        # kegagalan hari sebelumnya masih terhitung dan channel yang baru dipulihkan langsung
        # direm lagi pada siklus ini juga — tenant melihat 'dipulihkan lalu mati lagi' berulang.
        _sejak = ch.get("production_resumed_at")
        streak = inventory.recent_nonready_streak(cid, sejak=_sejak)
        _lf = inventory.latest_failure(cid, sejak=_sejak)
        _hard = bool(_lf and _lf.get("error_class") in _FAST_FAIL_VALUES)
        if streak >= fail_stop or (_hard and streak >= 1):
            # Pesan manusiawi dari kegagalan TERAKHIR — kini dipakai untuk KEDUA cabang. Dulu hanya
            # cabang rem-cepat yang menyertakannya; cabang 3-kegagalan hanya menulis kalimat generik,
            # sehingga tenant yang paling sering terkena justru yang paling sedikit diberi tahu.
            _human = (_lf.get("error_message") or "").strip() if _lf else ""
            _kelas = (_lf.get("error_class") or "").strip() if _lf else ""
            if _hard:
                reason = (f"Produksi channel DIHENTIKAN otomatis: {_human or 'kredit/pembayaran provider bermasalah'} "
                          f"(perbaiki penyebabnya, lalu Jalankan Ulang).")
            else:
                _sebab = f" Penyebab terakhir: {_human}" if _human else ""
                reason = (f"{streak}x produksi beruntun gagal/bermasalah → produksi channel DIHENTIKAN "
                          f"otomatis.{_sebab}")
            logger.error(f"[Producer] CIRCUIT-BREAK ch={cid} (hard={_hard}, kelas={_kelas or '-'}): {reason}")
            _pause_channel(sb, ch, reason, error_class=_kelas)
            try:
                from src.utils.telegram_notifier import TelegramNotifier
                TelegramNotifier().notify_circuit_break(tenant_id=ch["tenant_id"], channel_id=cid, reason=reason,
                                                        channel_name=ch.get("channel_name") or "",
                                                        error_class=_kelas)
            except Exception as _te:
                logger.warning(f"[Producer] alarm circuit-break gagal: {_te}")
            continue
        # Stok = ready + ready_with_issues + producing (issue DIHITUNG → rem alami anti-runaway).
        stok = (inventory.buffer_depth(cid, "ready")
                + inventory.buffer_depth(cid, "ready_with_issues")
                + inventory.buffer_depth(cid, "producing"))
        target = target_stock(ch)
        if stok < target:
            deficits.append((target - stok, ch))
    deficits.sort(key=lambda x: -x[0])   # buffer paling tipis dulu (§12c prioritas)

    submitted = 0
    for _, ch in deficits:
        if not sem.acquire(blocking=False):
            break   # semua core sibuk → tunggu siklus berikut (REM anti-OOM)

        def _task(ch=ch):
            try:
                produce_one(ch)
            finally:
                sem.release()

        pool.submit(_task)
        submitted += 1
    return submitted


def run_forever(idle_seconds: int = 10) -> None:
    """Loop persisten Producer (§12c). MAX_CONCURRENT_RENDER = core (semaphore = rem)."""
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    MAX = max_concurrent_render()
    logger.info(f"[Producer] start | MAX_CONCURRENT_RENDER={MAX} (core) | target stok = sadar-jadwal (slot/hari × app_config.buffer_target_days; override channels.buffer_depth)")
    sem = threading.Semaphore(MAX)
    with ThreadPoolExecutor(max_workers=MAX, thread_name_prefix="producer") as pool:
        while True:
            try:
                drain_direct(sb, pool, sem)     # jalur prioritas (test/retry/admin) — semaphore SAMA
                plan_and_submit(sb, pool, sem)  # stok-buffer dgn slot core sisa
            except Exception as e:
                logger.error(f"[Producer] loop error: {e}")
            time.sleep(idle_seconds)
