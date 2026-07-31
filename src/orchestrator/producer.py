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
from src.exceptions import FAST_FAIL

# [ERROR-MGMT] nilai string ErrorClass yang memicu rem-segera (persis set FAST_FAIL exceptions.py).
_FAST_FAIL_VALUES = frozenset(ec.value for ec in FAST_FAIL)
from src.utils import s3_buffer


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
            "elapsed_seconds": result.get("elapsed_seconds"),
            "error_message":   error,
            "error_class":     result.get("error_class"),   # [ERROR-MGMT] makna → circuit-breaker semantik
            # video_title = judul AKHIR (yang tampil di YouTube) — FE Runs menampilkan ini, bukan
            # topik internal (owner 2026-07-10: 1 video sempat tampil beda nama di Runs vs Studio).
            "run_metadata":    {"scheduled": True, "mode": "buffer", "video_title": script.get("title", ""), **_cost_fields(result)},
        }).execute()
    except Exception as e:
        logger.warning(f"[Producer] tulis production_runs (scheduled) gagal — non-fatal: {e}")


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
# Jalur prioritas: tenant/admin minta produksi 1 job SEKARANG (test/retry/admin_test).
# Di-drain SEBELUM stok-buffer, pakai semaphore+pool yang SAMA (anti-OOM utuh). Mesin = pipeline.run().
def run_direct(sb, job: dict) -> None:
    """Eksekusi 1 direct_job: produce + publish (privacy sesuai job) + tulis production_runs.
    Context run_id → pipeline_run_logs (live-tail D5). Tandai status di direct_jobs."""
    from datetime import datetime, timezone
    from src.intelligence.config import tenant_config_from_channel
    from src.orchestrator.pipeline import Pipeline

    jid = job["id"]
    tenant_id = job["tenant_id"]
    run_id = f"direct-{str(jid)[:8]}"
    _now = lambda: datetime.now(timezone.utc).isoformat()

    ch = (sb.table("channels").select("*").eq("id", job["channel_id"]).limit(1).execute().data or [None])[0]
    if not ch:
        sb.table("direct_jobs").update({"status": "failed", "error": "channel tak ditemukan", "completed_at": _now()}).eq("id", jid).execute()
        return
    sb.table("direct_jobs").update({"run_id": run_id}).eq("id", jid).execute()

    # Test niche TANPA publish (keputusan owner 2026-07-04): admin_test (channel internal admin) &
    # test_nopub (F5 — channel+kredensial TENANT sendiri, dari Niche Studio). Video → S3 status='test'
    # (tak pernah diklaim publisher; TTL janitor). Beda dari direct tenant test/retry (publish private).
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
            "run_metadata": {"direct": True, "job_type": job.get("job_type"), "video_title": _script.get("title", ""), **_cost_fields(result)},
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
            sb.table("channels").update(
                {"production_paused": False, "production_paused_reason": None}
            ).eq("id", job["channel_id"]).execute()
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


def _pause_channel(sb, ch: dict, reason: str) -> None:
    """Circuit-breaker §4b/F7: hentikan produksi channel + catat alasan. Auto-recover saat 1 produce
    sukses (run_direct membersihkan flag). Kolom channels.production_paused* (migr 0050)."""
    from datetime import datetime, timezone
    try:
        sb.table("channels").update({
            "production_paused": True,
            "production_paused_at": datetime.now(timezone.utc).isoformat(),
            "production_paused_reason": reason[:300],
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
            logger.info(f"[Producer] skip ch={cid} tenant={ch.get('tenant_id')} — subscription tidak aktif")
            continue
        # F1-08 GERBANG AKTIVASI: channel belum lengkap (niche/model/voice/credential/OAuth) → skip
        # (no-fallback: jangan produksi pakai default diam-diam). FAIL-OPEN bila cek error transient
        # (lindungi channel sehat — mis. ryan — dari berhenti karena gangguan sesaat).
        _rd = channel_readiness(sb, ch)
        if not _rd["ready"] and not _rd["check_failed"]:
            logger.info(f"[Producer] skip ch={cid} — channel belum READY (kurang: {', '.join(_rd['missing'])})")
            continue
        # REM DARURAT (§4b/F7): N produksi beruntun gagal/bermasalah → STOP channel + alarm SEKETIKA.
        # [ERROR-MGMT 2026-07-18] REM SEGERA (setelah 1×) bila kegagalan TERAKHIR = kelas non-retryable
        # (kredit habis / pembayaran gagal) — mustahil sembuh dgn diulang → hemat biaya LLM percobaan
        # ke-2/3. Error lain (transien/unknown) TETAP toleransi `fail_stop` (nol regresi channel sehat).
        streak = inventory.recent_nonready_streak(cid)
        _lf = inventory.latest_failure(cid)
        _hard = bool(_lf and _lf.get("error_class") in _FAST_FAIL_VALUES)
        if streak >= fail_stop or (_hard and streak >= 1):
            if _hard:
                _human = (_lf.get("error_message") or "").strip()
                reason = (f"Produksi channel DIHENTIKAN otomatis: {_human or 'kredit/pembayaran provider bermasalah'} "
                          f"(perbaiki penyebabnya, lalu Jalankan Ulang).")
            else:
                reason = (f"{streak}x produksi beruntun gagal/bermasalah → produksi channel DIHENTIKAN "
                          f"otomatis. Periksa kredensial/konfigurasi, lalu Jalankan Ulang (direct).")
            logger.error(f"[Producer] CIRCUIT-BREAK ch={cid} (hard={_hard}): {reason}")
            _pause_channel(sb, ch, reason)
            try:
                from src.utils.telegram_notifier import TelegramNotifier
                TelegramNotifier().notify_circuit_break(tenant_id=ch["tenant_id"], channel_id=cid, reason=reason,
                                                        channel_name=ch.get("channel_name") or "")
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
