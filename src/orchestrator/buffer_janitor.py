"""
Buffer Janitor — jaga buffer S3 (Biznet) BERSIH, cegah sampah menumpuk (Phase 5.3).

Dua tugas (idempotent, aman dijalankan berkala):
  1. sweep_stale       : item content_inventory ABANDONED → hapus aset S3 + baris.
       • ready/failed yang lewat `expires_at`
       • producing yang NYANGKUT (created_at > PRODUCING_TTL_HOURS — render crash)
  2. reconcile_orphans : objek S3 yang TIDAK direferensikan baris inventory aktif
       (ready/producing/publishing) DAN lebih tua dari grace → hapus.

Grace period (ORPHAN_GRACE_MINUTES) mencegah penghapusan upload IN-FLIGHT
(producer upload → mark_ready ada jeda detik). Config-driven, no-hardcode.
Dipanggil worker_decoupled via thread `run_forever`.
"""

import os
import time
from datetime import datetime, timedelta, timezone

from loguru import logger

from src.utils import s3_buffer


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _parse(ts) -> datetime | None:
    """ISO timestamp (Supabase / boto3) → datetime tz-aware UTC."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _keys_of(row: dict) -> list:
    """Semua key S3 milik 1 baris inventory (video + thumbnail)."""
    keys = [row.get("s3_key"), (row.get("metadata") or {}).get("thumb_s3")]
    return [k for k in keys if k]


def sweep_stale(sb=None) -> dict:
    sb = sb or _sb()
    now = datetime.now(timezone.utc)
    producing_cutoff = now - timedelta(hours=float(os.getenv("PRODUCING_TTL_HOURS", "3")))

    rows = sb.table("content_inventory").select("*").in_(
        "status", ["ready", "ready_with_issues", "failed", "test"]).execute().data or []   # 'test' = video uji (TTL ±3 hari)
    stale = [r for r in rows if (_parse(r.get("expires_at")) or now + timedelta(days=3650)) < now]

    prod = sb.table("content_inventory").select("*").eq("status", "producing").execute().data or []
    stuck = [r for r in prod if (_parse(r.get("created_at")) or now) < producing_cutoff]

    deleted_assets = purged_rows = 0
    for r in stale + stuck:
        for k in _keys_of(r):
            s3_buffer.delete(k); deleted_assets += 1
        sb.table("content_inventory").delete().eq("id", r["id"]).execute()
        purged_rows += 1
        # TUTUP LOOP sinyal (owner 2026-07-10; simetris `discard_inventory_item`): item ready_with_issues
        # yang kedaluwarsa TTL = auto-dibuang → run asalnya WAJIB ikut padam (qc_failed → 'discarded'),
        # kalau tidak: angka "perlu ditinjau" (dashboard/Runs) menghitungnya SELAMANYA padahal
        # tak ada lagi yang bisa ditinjau. Fail-soft (jangan gagalkan sweep karena update ledger).
        if r.get("status") == "ready_with_issues":
            _rid = (r.get("metadata") or {}).get("run_id")
            if _rid:
                try:
                    sb.table("production_runs").update({"status": "discarded"}) \
                      .eq("run_id", _rid).eq("status", "qc_failed").execute()
                except Exception as e:
                    logger.warning(f"[janitor] padamkan sinyal run {_rid} gagal — non-fatal: {e}")
    if purged_rows:
        logger.info(f"[janitor] sweep_stale: {purged_rows} baris abandoned + {deleted_assets} aset S3 dihapus")
    return {"purged_rows": purged_rows, "deleted_assets": deleted_assets}


def reconcile_orphans(sb=None, grace_minutes=None) -> dict:
    sb = sb or _sb()
    grace = float(grace_minutes if grace_minutes is not None else os.getenv("ORPHAN_GRACE_MINUTES", "60"))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=grace)

    rows = sb.table("content_inventory").select("s3_key,metadata,status").in_(
        "status", ["ready", "ready_with_issues", "producing", "publishing", "test"]).execute().data or []   # 'test' dilindungi s/d TTL
    referenced = set()
    for r in rows:
        referenced.update(_keys_of(r))

    deleted = 0
    for key, _size, lm in s3_buffer.list_keys():
        if key in referenced:
            continue
        lm = _parse(lm)
        if lm and lm > cutoff:        # in-flight → lindungi (grace)
            continue
        s3_buffer.delete(key); deleted += 1
    if deleted:
        logger.info(f"[janitor] reconcile_orphans: {deleted} objek S3 yatim dihapus (grace={grace}m)")
    return {"deleted_orphans": deleted}


def prune_logs(sb) -> dict:
    """Retensi pipeline_run_logs — hapus log lebih tua dari LOG_RETENTION_DAYS (default 30 hari) →
    cegah tabel bloat. Live-tail (D5) hanya butuh log run baru; histori lama tak bernilai.
    Idempotent, best-effort (gagal tak ganggu janitor). Global (lintas-tenant, service_role)."""
    days = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        res = sb.table("pipeline_run_logs").delete().lt("created_at", cutoff).execute()
        n = len(res.data or [])
        if n:
            logger.info(f"[janitor] prune_logs: {n} baris pipeline_run_logs >{days}hari dihapus")
        return {"logs_pruned": n}
    except Exception as e:
        logger.warning(f"[janitor] prune_logs gagal: {e}")
        return {"logs_pruned": 0}


def reap_stuck_direct_jobs(sb=None) -> dict:
    """Job direct 'producing' yang melewati batas-waktu (worker mati/hang saat run) → tandai 'failed'
    + alasan, supaya FE (TestNichePanel) lapor gagal bukan menggantung, dan tenant bisa uji ulang.
    TTL via env DIRECT_JOB_TTL_MINUTES (default 30; uji normal ~2-5 mnt). Konsisten pola janitor lain."""
    sb = sb or _sb()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=float(os.getenv("DIRECT_JOB_TTL_MINUTES", "30")))
    rows = sb.table("direct_jobs").select("id, started_at, created_at").eq("status", "producing").execute().data or []
    stuck = [r for r in rows if (_parse(r.get("started_at")) or _parse(r.get("created_at")) or now) < cutoff]
    for r in stuck:
        sb.table("direct_jobs").update({
            "status": "failed",
            "error": "Uji melewati batas waktu (proses macet). Silakan coba lagi.",
            "completed_at": now.isoformat(),
        }).eq("id", r["id"]).execute()
    if stuck:
        logger.info(f"[janitor] reap_stuck_direct_jobs: {len(stuck)} job direct macet → failed")
    return {"direct_reaped": len(stuck)}


# ── [2026-08-13] STOK YANG NYANGKUT DI "SEDANG DITERBITKAN" ─────────────────────────────────────
#
# LUBANG YANG DITUTUP. Penyapu mengenal stok siap (lewat `expires_at`), stok sedang-diproduksi
# (TTL 3 jam), video uji, dan uji-manual (TTL 30 menit) — tapi TIDAK PERNAH mengenal
# 'publishing'. Padahal itu satu-satunya status yang bisa ditinggalkan oleh mesin yang mati
# mendadak, dan `reconcile_orphans` justru MELINDUNGI asetnya selama status itu ⇒ nyangkut
# permanen, aset kekal, dan videonya hilang dari seluruh pembukuan.
#
# KORBAN NYATA (12-Agu 19:00, channel BISIK NUSANTARA — tenant BERBAYAR): mesin mati 7 detik
# setelah unggahan selesai. Video xa3Rbi-SbXM hidup, PUBLIK, 1.024 penonton, 11 suka, 1 komentar —
# dan bagi sistem kita video itu tidak pernah ada: `videos` tanpa barisnya, tautan YouTube di
# catatan produksi kosong, tenant tak pernah dikabari, aset menumpuk, dan mesin pembelajaran tak
# pernah melihat video yang justru paling laku.
#
# KENAPA TIGA CABANG, BUKAN DUA. Godaannya: "tak ada nomor YouTube ⇒ belum terunggah ⇒ terbitkan
# ulang". Itu SALAH dan sempat saya tulis sebagai rencana. Unggahan dikirim bertahap; ada celah
# sempit di mana YouTube sudah menerima potongan terakhir tapi mesin kita belum tahu nomornya.
# Menerbitkan ulang di keadaan itu = VIDEO KEMBAR di channel tenant. Karena itu keadaan yang tak
# bisa dipastikan TIDAK ditebak: ia dilaporkan ke owner dan menunggu keputusan manusia (§0.6 —
# perilaku-saat-gagal = gagal jujur, bukan improvisasi).
def sweep_publishing_nyangkut(sb=None) -> dict:
    sb = sb or _sb()
    now = datetime.now(timezone.utc)
    batas = now - timedelta(minutes=float(os.getenv("PUBLISHING_TTL_MINUTES", "30")))
    rows = sb.table("content_inventory").select("*").eq("status", "publishing").execute().data or []
    rapi = kembali = ambigu = 0
    for r in rows:
        meta = r.get("metadata") or {}
        # JANGKAR WAKTU. `updated_at` SENGAJA tidak dipakai: terbukti tidak ikut berubah saat status
        # berganti (baris nyata inv=231 — updated_at == created_at padahal statusnya sudah
        # 'publishing'). `target_slot` diisi publisher tepat saat item diklaim → paling dekat dengan
        # kejadiannya. Penanda unggahan lebih presisi lagi bila ada.
        jangkar = (_parse(meta.get("yt_upload_started_at")) or _parse(r.get("target_slot"))
                   or _parse(r.get("created_at")))
        if jangkar and jangkar > batas:
            continue                      # masih dalam waktu wajar — penerbitan sedang berjalan
        if meta.get("yt_video_id"):
            rapi += _rapikan_terbit_tertinggal(sb, r)
        elif not meta.get("yt_upload_started_at"):
            # Unggahan BELUM pernah dimulai → 100% aman dikembalikan ke stok; terbit di slot berikutnya.
            sb.table("content_inventory").update({"status": "ready"}).eq("id", r["id"]).execute()
            kembali += 1
            logger.info(f"[janitor] inv={r['id']} nyangkut sebelum unggah → dikembalikan ke stok")
        else:
            ambigu += _laporkan_ambigu(sb, r)
    if rapi or kembali or ambigu:
        logger.info(f"[janitor] sweep_publishing: {rapi} dirapikan · {kembali} kembali ke stok · "
                    f"{ambigu} perlu ditinjau manusia")
    return {"publishing_rapi": rapi, "publishing_kembali": kembali, "publishing_ambigu": ambigu}


def _rapikan_terbit_tertinggal(sb, row: dict) -> int:
    """Video TERBUKTI sudah terbit (nomor YouTube tercatat) tapi pembukuannya tertinggal → tuntaskan.

    IDEMPOTEN: bila baris `videos` untuk nomor itu sudah ada, penulisan dilewati. Tanpa ini, satu
    kegagalan di tengah akan membuat siklus berikutnya menulis baris kedua untuk video yang sama.
    Urutan sengaja: catat dulu (yang tak tergantikan), baru bersihkan aset, `mark_published` PALING
    AKHIR — supaya percobaan yang terputus di tengah masih bisa diulang siklus berikutnya.
    """
    from src.utils.supabase_writer import SupabaseWriter
    meta = row.get("metadata") or {}
    vid  = str(meta.get("yt_video_id"))
    url  = meta.get("yt_url") or f"https://youtu.be/{vid}"
    sc   = meta.get("script") or {}
    rid  = meta.get("run_id") or ""
    terbit_pada = meta.get("yt_upload_started_at") or row.get("target_slot")
    try:
        ada = (sb.table("videos").select("id", count="exact").eq("video_id", vid).execute().count or 0)
        if not ada:
            SupabaseWriter().write_video(
                run_id=rid, tenant_id=row["tenant_id"], platform="youtube", video_id=vid, url=url,
                title=sc.get("title") or "", hook=sc.get("hook") or "",
                topic=sc.get("topic") or "", niche=row.get("niche") or meta.get("niche") or "",
                viral_score=float(meta.get("viral_score") or 0),
                duration_secs=meta.get("duration_secs"), file_size_mb=meta.get("size_mb"),
                channel_id=row.get("channel_id"), topic_scores=sc.get("topic_scores") or {},
                insights_grade=meta.get("insights_grade") or "", voice_id=meta.get("tts_voice"),
                hook_pattern=meta.get("hook_pattern"), music_mood=meta.get("music_mood"),
                visual_seed=meta.get("visual_seed"))
            # WAKTU TERBIT YANG BENAR. `write_video` memberi cap waktu SEKARANG — betul untuk publish
            # normal, salah di sini karena video ini terbit sebelumnya. Analitik & kuota harian
            # membaca kolom ini, jadi salah hari = angka salah.
            if terbit_pada:
                sb.table("videos").update({"published_at": terbit_pada}).eq("video_id", vid).execute()
        if rid:
            (sb.table("production_runs")
               .update({"youtube_video_id": vid, "youtube_url": url, "status": "success"})
               .eq("run_id", rid).eq("tenant_id", row["tenant_id"]).execute())
        for k in _keys_of(row):
            s3_buffer.delete(k)
        # SAMBUNGAN YANG DIBERIKAN, bukan bikin sendiri. `inventory.mark_published()` membuat klien
        # Supabase-nya SENDIRI dari env — dan itu sempat membuat uji lokal menulis ke baris PRODUKSI
        # sungguhan (13-Agu, baris inv=231 berubah status dari sebuah uji). Seluruh berkas ini memang
        # sudah menulis `content_inventory` lewat `sb` (lihat sweep_stale & cabang "kembali ke stok"),
        # jadi ini sekaligus menyeragamkannya: satu sambungan, satu jalur, bisa diuji tanpa jaringan.
        sb.table("content_inventory").update({"status": "published"}).eq("id", row["id"]).execute()
        logger.info(f"[janitor] inv={row['id']} pembukuan dituntaskan — video {vid} memang sudah terbit")
        try:
            from src.utils.telegram_notifier import TelegramNotifier
            TelegramNotifier().notify_admin(
                "🧾 <b>Pembukuan penerbitan dirapikan</b>\n"
                f"Video {url} ternyata SUDAH terbit, tapi pencatatannya tertinggal (mesin berhenti di "
                f"tengah). Sekarang sudah tercatat lengkap dan ikut dihitung mesin pembelajaran.")
        except Exception as e:
            logger.debug(f"[janitor] kabar rapi gagal (non-fatal): {e}")
        return 1
    except Exception as e:
        logger.error(f"[janitor] merapikan inv={row['id']} GAGAL: {e} — dicoba lagi siklus berikutnya")
        return 0


def _laporkan_ambigu(sb, row: dict) -> int:
    """Unggahan sudah DIMULAI tapi nomor YouTube tak tercatat → tak bisa dipastikan.

    HARAM diterbitkan ulang (risiko video kembar) dan haram dibuang (mungkin video itu hidup).
    Statusnya DIBIARKAN 'publishing' dengan sadar: itu menahan asetnya dari pembersihan dan menahan
    penerbitan ulang. Yang berubah hanya satu: owner diberi tahu SEKALI, supaya keadaan ini tidak
    lagi menjadi keadaan yang tak seorang pun tahu.
    """
    meta = dict(row.get("metadata") or {})
    if meta.get("ambigu_dilaporkan_at"):
        return 0
    meta["ambigu_dilaporkan_at"] = datetime.now(timezone.utc).isoformat()
    meta["perlu_ditinjau_manusia"] = True
    try:
        sb.table("content_inventory").update({"metadata": meta}).eq("id", row["id"]).execute()
    except Exception as e:
        logger.error(f"[janitor] tandai ambigu inv={row['id']} gagal: {e}")
        return 0
    sc = meta.get("script") or {}
    logger.error(f"[janitor] inv={row['id']} AMBIGU — unggahan dimulai tapi nomor YouTube tak "
                 f"tercatat; TIDAK diterbitkan ulang, menunggu keputusan manusia")
    try:
        from src.utils.telegram_notifier import TelegramNotifier
        TelegramNotifier().notify_admin(
            "⚠️ <b>Satu penerbitan perlu diperiksa manusia</b>\n"
            f"Judul: <b>{TelegramNotifier.aman(sc.get('title') or '(tanpa judul)')}</b>\n"
            "Unggahan ke YouTube sempat dimulai tapi mesin berhenti sebelum nomor videonya tercatat, "
            "jadi belum bisa dipastikan videonya sudah tayang atau belum.\n"
            "Sengaja TIDAK diterbitkan ulang supaya tidak muncul dua kali di channel. "
            "Mohon cek channel-nya: bila videonya sudah ada, biarkan; bila belum ada, kabari saya.")
    except Exception as e:
        logger.debug(f"[janitor] kabar ambigu gagal (non-fatal): {e}")
    return 1


def run_once(sb=None) -> dict:
    sb = sb or _sb()
    # B2: sinkron harian harga model AI (feed komunitas → ai_models.pricing; guard internal 24h). Fail-soft.
    try:
        from src.billing.price_sync import sync_prices
        sync_prices(sb)
    except Exception as e:
        logger.warning(f"[janitor] price_sync gagal (non-fatal): {e}")
    # Laporan harian: model yang GAGAL DIHITUNG biayanya pada produksi NYATA (bukti, bukan teori
    # katalog) → alarm admin 1×/hari. Tanpa ini, biaya yang tak terhitung tetap senyap: mesin sudah
    # menuliskannya di tiap run sejak lama, tapi tak ada yang membacanya (insiden 22-Agu). Fail-soft.
    try:
        from src.billing.price_sync import report_unpriced_models
        report_unpriced_models(sb)
    except Exception as e:
        logger.warning(f"[janitor] laporan biaya-tak-terhitung gagal (non-fatal): {e}")
    # Kurs USD→IDR harian (tampilan biaya BYOK; hormati usd_idr_rate_locked). Fail-soft.
    try:
        from src.billing.price_sync import sync_fx_rate
        sync_fx_rate(sb)
    except Exception as e:
        logger.warning(f"[janitor] sync kurs gagal (non-fatal): {e}")
    # sweep_publishing_nyangkut DULUAN, sebelum reconcile_orphans: penyapu-yatim melindungi aset
    # yang statusnya 'publishing', jadi baris yang baru saja dituntaskan (dan asetnya dihapus) tidak
    # boleh menunggu satu siklus penuh untuk ikut terhitung.
    return {**sweep_stale(sb), **sweep_publishing_nyangkut(sb), **reconcile_orphans(sb),
            **reap_stuck_direct_jobs(sb), **prune_logs(sb)}


# ── ALARM PENYIMPANAN (P3 pasca-insiden S3 2026-07-13: NEO tersuspend 04:24, janitor gagal 12×
#    TANPA satu alarm pun — melanggar "gagal = beri tahu, bukan senyap"). Streak error storage
#    beruntun ≥ ambang → Telegram ADMIN (1× per cooldown, penanda system_state — tahan restart);
#    pulih → kabar pulih 1×. Knob infra via env (pola price_sync). ─────────────────────────────
_S3_ALARM_STREAK   = int(os.getenv("S3_ALARM_FAIL_STREAK", "2"))
_S3_ALARM_COOLDOWN = float(os.getenv("S3_ALARM_COOLDOWN_HOURS", "6")) * 3600

# ── [2026-08-13] STATUS ALARM PINDAH KE BASIS DATA — INGATAN PROSES TIDAK BISA DIPERCAYA ────────
#
# KEJADIAN NYATA (13-Agu): akun penyimpanan diblokir 04:24–10:21 (tagihan belum dibayar). Alarm
# "BERMASALAH" terkirim 04:54 ✅. Penyimpanan lalu pulih — dan **kabar PULIH TIDAK PERNAH
# terkirim.** Terukur: hari itu HANYA 2 notifikasi keluar dari mesin (04:54 dan 06:00), tidak ada
# yang ketiga. Owner ditinggal percaya semua channel masih mati padahal sudah normal berjam-jam.
#
# SEBABNYA: hitungan "sudah gagal berapa kali" hidup di ingatan proses, sementara penanda "alarm
# sudah dikirim" hidup di basis data. Ingatan itu terhapus DUA kali hari itu — sekali oleh mesin
# yang mati mendadak 07:54, sekali oleh restart bersih 10:21. Saat penyimpanan akhirnya pulih,
# hitungannya tinggal 1 (< ambang 2) sehingga mesin menyimpulkan "tak pernah ada masalah" → diam.
# Jadi alarm BAHAYA selamat dari restart, kabar PULIH tidak. Asimetri itulah bugnya.
#
# OBATNYA BUKAN BARU: alarm drift durasi sudah menyelesaikan sebab yang PERSIS SAMA (ketok owner
# 16-Jul: *"memori proses hilang saat restart — itulah akarnya"*) dengan menyimpan status di DB.
# Pola itu dipakai ulang di sini, di tabel yang memang sudah dipakai janitor (`system_state`).
# `system_state` DIPILIH, bukan `app_config`: ini status mesin, bukan kenop admin — jadi tak perlu
# (dan tak boleh) muncul sebagai setelan di layar admin.
_S3_KUNCI_STREAK = "s3_fail_streak"     # berapa kali gagal beruntun — TAHAN restart
_S3_KUNCI_ALARM  = "s3_alarm_active"    # "1" = alarm BAHAYA sudah dikirim & belum dikabari pulih

# Cadangan HANYA untuk keadaan status di DB tak terbaca (bukan "tak ada", tapi gagal dibaca).
# Prinsip yang sudah berlaku di berkas alarm lain: lebih baik dering ganda daripada bisu senyap.
_streak_cadangan = 0


def _state_get(sb, key: str) -> str | None:
    """Nilai penanda di system_state. `""` = belum ada · `None` = GAGAL dibaca (dua hal berbeda:
    yang pertama berarti bersih, yang kedua berarti kita sedang buta)."""
    try:
        r = sb.table("system_state").select("value").eq("key", key).limit(1).execute()
        return str(r.data[0]["value"]) if r.data else ""
    except Exception as e:
        logger.warning(f"[janitor] baca system_state {key} gagal (pakai cadangan): {e}")
        return None


def _state_set(sb, key: str, value: str) -> None:
    try:
        sb.table("system_state").upsert({"key": key, "value": str(value),
                                         "updated_at": datetime.now(timezone.utc).isoformat()}).execute()
    except Exception as e:
        logger.debug(f"[janitor] tulis system_state {key} gagal: {e}")


def _state_epoch_get(sb, key: str) -> int:
    """Penanda epoch di system_state (pola price_sync — status mesin, BUKAN config admin)."""
    v = _state_get(sb, key)
    try:
        return int(v) if v else 0
    except Exception:
        return 0


def _state_epoch_set(sb, key: str) -> None:
    _state_set(sb, key, str(int(time.time())))


def _on_loop_error(sb, e: Exception) -> None:
    """Klasifikasi error storage (botocore) → naikkan streak (DI DB) → alarm admin ber-cooldown."""
    global _streak_cadangan
    try:
        from botocore.exceptions import BotoCoreError, ClientError
        if not isinstance(e, (BotoCoreError, ClientError)):
            return
        _streak_cadangan += 1
        tersimpan = _state_get(sb, _S3_KUNCI_STREAK)
        if tersimpan is None:                     # DB tak terbaca → jangan sampai bisu
            streak = _streak_cadangan
        else:
            try:
                streak = int(tersimpan or 0) + 1
            except ValueError:
                streak = _streak_cadangan
            _state_set(sb, _S3_KUNCI_STREAK, str(streak))
        if streak < _S3_ALARM_STREAK:
            return
        if time.time() - _state_epoch_get(sb, "s3_failure_alerted_at") < _S3_ALARM_COOLDOWN:
            return
        from src.utils.telegram_notifier import TelegramNotifier
        TelegramNotifier().notify_admin(
            f"🛑 <b>Penyimpanan S3/NEO BERMASALAH</b> ({streak}× gagal beruntun)\n"
            # [2026-08-12] DIBERSIHKAN + tak lagi dipotong senyap. Balasan galat S3 berbentuk XML
            # (`<Error><Code>…`); tanpa dibersihkan, Telegram MENOLAK seluruh pesan dan owner tidak
            # menerima apa pun — justru pada alarm paling penting (semua channel berhenti).
            f"💥 <code>{TelegramNotifier.aman(e)}</code>\n"
            f"⚠️ Produksi & publish SEMUA channel akan gagal sampai pulih — cek akun/endpoint NEO BiznetGio.")
        _state_epoch_set(sb, "s3_failure_alerted_at")
        # Ditandai HANYA setelah alarm benar-benar TERKIRIM. Kalau alarmnya tertahan rem cooldown,
        # penanda ini tidak dinyalakan — supaya kita tak pernah mengabarkan "PULIH" untuk sesuatu
        # yang tak pernah diumumkan.
        _state_set(sb, _S3_KUNCI_ALARM, "1")
    except Exception as _ae:
        logger.debug(f"[janitor] alarm storage gagal (non-fatal): {_ae}")


def _on_loop_success(sb) -> None:
    """Alarm BAHAYA pernah dikirim lalu penyimpanan sukses → kabar PULIH sekali. Keputusannya
    dibaca dari BASIS DATA, jadi ia selamat dari mesin mati mendadak maupun restart deploy."""
    global _streak_cadangan
    _streak_cadangan = 0
    aktif = _state_get(sb, _S3_KUNCI_ALARM)
    if aktif == "1":
        try:
            from src.utils.telegram_notifier import TelegramNotifier
            TelegramNotifier().notify_admin("✅ <b>Penyimpanan S3/NEO PULIH</b> — janitor kembali normal; "
                                            "video tertunda akan diproses di slot berikutnya.")
        except Exception as _ae:
            logger.debug(f"[janitor] kabar pulih gagal (non-fatal): {_ae}")
        _state_set(sb, _S3_KUNCI_ALARM, "0")
    # Nol-kan hitungan hanya bila memang belum nol → jangan menulis ke DB tiap 30 menit tanpa sebab.
    if (_state_get(sb, _S3_KUNCI_STREAK) or "0") != "0":
        _state_set(sb, _S3_KUNCI_STREAK, "0")


def run_forever(interval_seconds=None) -> None:
    """Loop persisten janitor — dipanggil worker_decoupled sebagai thread."""
    sb = _sb()
    interval = int(interval_seconds or os.getenv("JANITOR_INTERVAL_SEC", "1800"))
    logger.info(f"[janitor] start | tiap {interval}s (sweep stale + reconcile orphan)")
    while True:
        try:
            run_once(sb)
            _on_loop_success(sb)
        except Exception as e:
            logger.error(f"[janitor] loop error: {e}")
            _on_loop_error(sb, e)
        time.sleep(interval)
