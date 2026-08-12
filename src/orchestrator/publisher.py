"""
Publisher — ambil video ready dari buffer → publish saat SLOT (Phase 5.3, DESAIN §12c).

RINGAN (~5 dtk upload, no CPU). Slot **timezone-aware tenant** → ini sekaligus **FIX Bug 1**
(dispatcher lama treat publish_slots sebagai UTC). Loop tiap 30s. Buffer kosong saat slot →
skip + Telegram (no silent degradation). Publish gagal → revert ke ready + retry.
"""

import os
import time
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from loguru import logger

from src.orchestrator import inventory
from src.utils import s3_buffer


def slot_due(publish_slots: list, tz_name: str, now_utc: datetime, window_sec: int = 90):
    """Return datetime slot (tz tenant) yang JATUH TEMPO sekarang, atau None.
    FIX Bug 1: bandingkan jam slot di TIMEZONE TENANT, bukan UTC."""
    if not publish_slots:
        return None
    try:
        tz = ZoneInfo(tz_name or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    now_local = now_utc.astimezone(tz)
    for s in publish_slots:
        try:
            hh, mm = [int(x) for x in str(s).split(":")[:2]]
        except Exception:
            continue
        slot_dt = now_local.replace(hour=hh, minute=mm, second=0, microsecond=0)
        # jatuh tempo bila now dalam [slot, slot+window]
        if timedelta(0) <= (now_local - slot_dt) <= timedelta(seconds=window_sec):
            return slot_dt
    return None


def _already_handled(sb, channel_id: str, slot_dt: datetime) -> bool:
    """Dedup: sudah ada item publishing/published utk slot ini (cegah dobel antar-cycle)."""
    lo = (slot_dt - timedelta(minutes=3)).isoformat()
    hi = (slot_dt + timedelta(minutes=5)).isoformat()
    res = (sb.table("content_inventory").select("id", count="exact")
           .eq("channel_id", channel_id).in_("status", ["publishing", "published"])
           .gte("target_slot", lo).lte("target_slot", hi).execute())
    return (res.count or 0) > 0


def _tenant_timezone(sb, tenant_id: str) -> str:
    try:
        r = sb.table("tenant_configs").select("timezone").eq("tenant_id", tenant_id).limit(1).execute()
        return (r.data[0].get("timezone") if r.data else None) or "UTC"
    except Exception:
        return "UTC"


def publish_due_for_channel(sb, channel_row: dict, now_utc: datetime | None = None) -> str | None:
    """Cek slot channel; bila jatuh tempo → ambil ready → publish dari buffer. Return status."""
    now_utc = now_utc or datetime.now(ZoneInfo("UTC"))
    tenant_id  = channel_row["tenant_id"]
    channel_id = str(channel_row.get("id") or "default")
    tz = _tenant_timezone(sb, tenant_id)
    slot_dt = slot_due(channel_row.get("publish_slots") or [], tz, now_utc)
    if slot_dt is None:
        return None
    # Phase 8a — gate monetisasi: status langganan + cap harian (§4/§8). Cek hanya saat ada slot due.
    from src.billing.limits import gate_for_channel, published_today_count
    gate = gate_for_channel(sb, channel_row)
    if not gate["can_produce"]:
        logger.info(f"[Publisher] skip ch={channel_id} — subscription '{gate['status']}' (tidak publish)")
        return "subscription_inactive"
    if published_today_count(sb, channel_id) >= gate["daily_cap"]:
        logger.info(f"[Publisher] cap harian tercapai ch={channel_id} ({gate['daily_cap']}/hari) — skip slot")
        return "daily_cap_reached"
    if _already_handled(sb, channel_id, slot_dt):
        return "already_handled"

    item = inventory.claim_oldest_ready(channel_id)
    if not item:
        logger.warning(f"[Publisher] Buffer KOSONG slot {slot_dt} ch={channel_id} — skip + Telegram")
        _ch_label = channel_row.get("channel_name") or channel_id   # [B11] sebut NAMA channel, bukan id mentah
        _notify(tenant_id, f"⚠️ [{_ch_label}] Buffer kosong, slot {slot_dt:%H:%M} dilewati",
                sb=sb, once_key=f"empty:{channel_id}:{slot_dt.isoformat()}")
        return "buffer_empty"

    # tandai target_slot (dedup) + publish dari buffer
    sb.table("content_inventory").update({"target_slot": slot_dt.isoformat()}).eq("id", item["id"]).execute()
    try:
        _yt = _publish_from_buffer(sb, channel_row, item)
        inventory.mark_published(item["id"])
        # Buang SEMUA aset buffer (video + thumbnail) — cegah .jpg/.mp4 orphan menumpuk.
        for k in (item.get("s3_key"), (item.get("metadata") or {}).get("thumb_s3")):
            if k:
                s3_buffer.delete(k)
        logger.info(f"[Publisher] published ch={channel_id} inv={item['id']} (buffer dibersihkan)")
        # OPSI C: laporan SUKSES dikirim DI SINI (saat publish on-schedule), idempoten (sekali
        # per item — item sudah 'published' → tak diklaim ulang). Producer TIDAK lapor lagi.
        try:
            from src.utils.telegram_notifier import TelegramNotifier
            _meta = item.get("metadata") or {}
            _sc = _meta.get("script") or {}
            # [2026-08-12] ANGKA PRODUKSI IKUT DISERAHKAN. Owner: "mengapa pesan published tidak
            # selengkap pesan video uji?" — sebabnya pesan uji dikirim di dalam mesin produksi
            # (semua angka masih di tangan), sedangkan di sini hanya tautan/judul/niche yang
            # diserahkan. Padahal angkanya SUDAH ADA di metadata item ini (diverifikasi pada baris
            # nyata: duration_secs · size_mb · viral_score · script.word_count) — nol kueri baru.
            # `beat_durations` = jumlah bagian naskah = jumlah adegan (bukan literal mati "/6").
            _beats = _sc.get("beat_durations") or []
            TelegramNotifier().notify_published(
                tenant_id     = channel_row["tenant_id"],
                url           = (_yt or {}).get("url", ""),
                title         = (_yt or {}).get("title") or _sc.get("title", ""),
                niche         = item.get("niche") or channel_row.get("niche", ""),
                channel_name  = channel_row.get("channel_name", ""),   # [B11] multi-channel: sebut channel
                duration_secs = _meta.get("duration_secs"),
                size_mb       = _meta.get("size_mb"),
                clips         = len(_beats) if _beats else None,
                hook_score    = _meta.get("viral_score"),
                words         = _sc.get("word_count"),
            )
        except Exception as _te:
            logger.warning(f"[Publisher] notify_published gagal (non-fatal): {_te}")
        return "published"
    except Exception as e:
        inventory.revert_to_ready(item["id"])           # kembalikan ke buffer (publish ulang saat pulih)
        _ch_label = channel_row.get("channel_name") or channel_id   # [B11] sebut NAMA channel
        # [B11] 3.2 — koneksi YouTube putus PERMANEN (invalid_grant): mark_youtube_account_invalid
        # SUDAH menandai koneksi invalid + notif tenant SEKALI (produksi channel otomatis berhenti
        # via gerbang readiness). JANGAN kirim "akan diulang" yang MENYESATKAN (tak akan sukses
        # sampai reconnect). Cukup log; video ditahan di buffer, terbit otomatis begitu tersambung.
        from src.exceptions import ErrorClass
        if getattr(e, "error_class", None) == ErrorClass.AUTH_INVALID:
            logger.error(f"[Publisher] publish DITAHAN inv={item['id']} ch={_ch_label} — koneksi YouTube putus (sambungkan ulang)")
            return "auth_invalid"
        logger.error(f"[Publisher] publish gagal inv={item['id']} ({e}) — revert ready")
        _notify(tenant_id, f"❌ [{_ch_label}] Publish gagal, akan diulang: {e}",
                sb=sb, once_key=f"fail:{item['id']}:{slot_dt.isoformat()}")
        return "failed"


def _publish_from_buffer(sb, channel_row: dict, item: dict) -> None:
    """Download video+thumbnail dari S3 → publish via youtube_publisher (reuse). Raise bila gagal."""
    from src.intelligence.config import tenant_config_from_channel
    from src.distribution.youtube_publisher import YouTubePublisher

    meta = item.get("metadata") or {}
    script = meta.get("script") or {}
    tc = tenant_config_from_channel(channel_row, niche=item.get("niche") or channel_row.get("niche"))

    tmp = tempfile.mkdtemp()
    video_path = os.path.join(tmp, "video.mp4")
    s3_buffer.download(item["s3_key"], video_path)
    thumb_path = ""
    if meta.get("thumb_s3"):
        thumb_path = os.path.join(tmp, "thumb.jpg")
        s3_buffer.download(meta["thumb_s3"], thumb_path)

    yt = YouTubePublisher().publish(video_path, script, tc,
                                    thumbnail_path=thumb_path, content_type="short")
    if not yt.get("video_id"):
        # [B11] 3.2 — bawa error_class (mis. AUTH_INVALID dari invalid_grant) ke pemanggil, bukan
        # RuntimeError generik yang membuang makna. error_class None → UNKNOWN (perilaku lama).
        from src.exceptions import PublishError, ErrorClass
        _ecv = yt.get("error_class")
        raise PublishError(
            yt.get("error", "YouTube publish gagal"), step="publish",
            error_class=ErrorClass(_ecv) if _ecv else ErrorClass.UNKNOWN,
            human_message=yt.get("human_error"),
        )

    # Tautkan video_id/url BALIK ke production_runs (via run_id). Sebelumnya hanya ditulis ke `videos`
    # → kolom Views di /runs kosong utk run terjadwal. Non-fatal (publish sudah sukses).
    _rid = meta.get("run_id")
    if _rid:
        try:
            (sb.table("production_runs")
               .update({"youtube_video_id": yt["video_id"],
                        "youtube_url": yt.get("url") or f"https://youtu.be/{yt['video_id']}",
                        "status": "success"})
               .eq("run_id", _rid).eq("tenant_id", channel_row["tenant_id"]).execute())
        except Exception as _e:
            logger.warning(f"[Publisher] link video_id→production_runs gagal (non-fatal): {_e}")

    # Tutup gap Phase-5 decoupled: di mode ini PUBLISHER = penulis row `videos` (pipeline.run
    # publish=False tak menulisnya). Sekaligus rekam dimensi diversity (Phase 6.2, migr 0018)
    # → jadi HISTORI lookback rotasi berikutnya. Non-fatal (publish sudah sukses).
    try:
        from src.utils.supabase_writer import SupabaseWriter
        _size_mb = (round(os.path.getsize(video_path) / (1024 * 1024), 2)
                    if os.path.exists(video_path) else None)
        SupabaseWriter().write_video(
            run_id        = meta.get("run_id", ""),
            tenant_id     = channel_row["tenant_id"],
            platform      = "youtube",
            video_id      = yt["video_id"],
            url           = yt.get("url", ""),
            title         = yt.get("title", script.get("title", "")),
            hook          = script.get("hook", ""),
            topic         = script.get("topic", ""),
            niche         = tc.niche,
            viral_score   = float(meta.get("viral_score") or script.get("viral_score") or 0),
            file_size_mb  = _size_mb,
            # [2026-08-05] Durasi AKTUAL hasil QC. Producer SUDAH menyimpannya di metadata stok
            # (produce_one & run_direct), `write_video` SUDAH punya parameternya — hanya baris ini
            # yang hilang, sehingga JALUR UTAMA (terjadwal) tak pernah mencatat durasi:
            # 55 dari 75 video dalam 14 hari (73%) berkolom kosong; yang tercatat hanya jalur uji
            # langsung (pipeline menulis rownya sendiri).
            # Akibatnya presisi durasi — gerbang PALING TERKUNCI menurut kompas owner (CLAUDE.md §7.3,
            # "durasi video = HULU pipeline") — TIDAK BISA DIAUDIT untuk produksi terjadwal.
            # QC tetap menjaga sebelum publish; yang hilang adalah JEJAKNYA. Tanpa jejak, pergeseran
            # durasi hanya terlihat saat tenant mengeluh, bukan saat terjadi.
            duration_secs = meta.get("duration_secs"),
            channel_id    = tc.channel_id,
            # voice_id = suara AKTUAL saat PRODUKSI (meta, ditulis producer). Fallback item buffer
            # lama tanpa jejak = channels.voice_key NYATA (BUKAN tc.tts_voice — konstruktor
            # from_channel tak mengisinya → default dataclass palsu; bug tertangkap audit 2026-07-11).
            voice_id      = meta.get("tts_voice") or channel_row.get("voice_key"),
            insights_grade= meta.get("insights_grade", ""),
            hook_pattern  = meta.get("hook_pattern"),
            visual_seed   = meta.get("visual_seed"),
            music_mood    = meta.get("music_mood"),
        )
    except Exception as _we:
        logger.warning(f"[Publisher] write_video (videos row) gagal — non-fatal: {_we}")

    return yt


_NOTIFY_ONCE: set = set()   # anti-banjir: 1 telegram per kejadian (loop retry 30s ≠ 1 pesan/30s)


def _notify(tenant_id: str, msg: str, sb=None, once_key: str | None = None) -> None:
    """Log + kirim Telegram ke TENANT (notify_tenant — hormati saklar telegram_enabled).
    Dulu FOSIL log-only ("wiring saat cutover" tak pernah ditunaikan) → kegagalan publish jalur
    TERJADWAL senyap total; ketahuan di insiden S3 06:00 WIB 2026-07-13. once_key = kirim SEKALI
    per kejadian (per item/slot) selama proses hidup. Fail-soft: telegram gagal ≠ alur publish stop."""
    logger.info(f"[Publisher][{tenant_id}] {msg}")
    if once_key:
        if once_key in _NOTIFY_ONCE:
            return
        if len(_NOTIFY_ONCE) > 512:   # jaga memori proses long-run
            _NOTIFY_ONCE.clear()
        _NOTIFY_ONCE.add(once_key)
    try:
        from src.utils.telegram_notifier import TelegramNotifier
        TelegramNotifier().notify_tenant(sb, tenant_id, msg)
    except Exception as e:
        logger.warning(f"[Publisher] telegram tenant gagal (non-fatal): {e}")


def run_forever(idle_seconds: int = 30) -> None:
    """Loop persisten Publisher (§12c) — cek slot tiap 30s (granularity menit)."""
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    logger.info("[Publisher] start | cek slot tiap 30s (timezone-aware)")
    while True:
        try:
            channels = sb.table("channels").select("*").eq("is_active", True).execute().data or []
            for ch in channels:
                publish_due_for_channel(sb, ch)
        except Exception as e:
            logger.error(f"[Publisher] loop error: {e}")
        time.sleep(idle_seconds)
