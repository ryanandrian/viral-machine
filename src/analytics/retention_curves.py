"""
RetentionCurveCollector — [B17 §6 M1] LAPIS 1 "MATA": kurva retensi per-momen per video.

Menarik laporan resmi YouTube Audience Retention (100 titik `elapsedVideoTimeRatio`;
metrik `audienceWatchRatio` + `relativeRetentionPerformance`) → simpan mentah + 4 fitur
turunan ke `video_retention_curves` (migr 0171). Rata-rata retensi tak bisa mengajarkan
CRAFT; kurva bisa (probe 18-Jul: hook hebat ≠ badan video menahan penonton).

Aturan operasi (semua kebijakan angka = kenop `app_config`, no-hardcode):
  - Video eligible: status='published', ber-video_id, umur ≥ retention_curve_min_age_days
    (kurva video terlalu muda KOSONG — bukti probe; bukan error).
  - Maks 2 fetch seumur hidup video: sekali saat eligible, sekali lagi saat melewati
    retention_curve_refresh_age_days (kurva matang) → final.
  - Jawaban kosong = status 'empty' (dicatat, retry ≥24 jam berikutnya) sampai
    retention_curve_give_up_age_days → berhenti (anti-request sia-sia).
  - Batas retention_curve_max_per_run request per channel per siklus.
  - 1 request API = 1 video (syarat resmi laporan retensi).

Identitas: klien Analytics WAJIB milik koneksi channel ini (pelajaran akar saga
retensi-0 2026-07-13: token terikat per-IDENTITAS channel; salah token = jawaban
sukses-tapi-kosong yang menipu). Fail-soft total: kegagalan di sini tidak boleh
mengganggu rantai self-learning lain. ADDITIVE murni — tidak mengubah komputasi
insight/analytics eksisting.
"""

import time
from datetime import datetime, timezone

from loguru import logger

# ── Definisi matematis fitur (BUKAN nilai bisnis → konstanta ber-nama + ber-uji;
#    lihat PROGRAM_BUKTI_KECERDASAN.md §6e2 baris no-hardcode M1) ─────────────────
HOOK_BUCKETS       = 5     # hook_hold = rata watchRatio 5 titik pertama (t ≤ 0,05)
MID_EXIT_THRESHOLD = 0.5   # mid_exit = elapsed_ratio pertama saat watchRatio < 0,5

# Default kenop — dipakai HANYA bila baris app_config tak terbaca (fail-soft; nilai
# resmi hidup di DB, migr 0171). Kunci = nama kenop persis.
KNOB_DEFAULTS = {
    "retention_curve_min_age_days":     3,
    "retention_curve_refresh_age_days": 14,
    "retention_curve_max_per_run":      50,
    "retention_curve_give_up_age_days": 45,
}

# Jeda antar-attempt utk baris 'empty' (jam) — cadence loop harian; bukan nilai bisnis.
EMPTY_RETRY_MIN_HOURS = 24
# Rate-limit antar request (selaras pola ChannelAnalytics.fetch_and_store).
REQUEST_SLEEP_SEC = 0.5


def load_knobs(supabase) -> dict:
    """Baca 4 kenop dari app_config; fallback per-kunci ke default (fail-soft, log jelas)."""
    knobs = dict(KNOB_DEFAULTS)
    try:
        rows = (supabase.table("app_config").select("key, value")
                .in_("key", list(KNOB_DEFAULTS.keys())).execute().data) or []
        for r in rows:
            k, v = r.get("key"), r.get("value")
            if k in knobs and v is not None and int(v) > 0:
                knobs[k] = int(v)
    except Exception as e:
        logger.warning(f"[RetentionCurves] baca kenop app_config gagal → pakai default ({e})")
    return knobs


def compute_features(rows: list) -> dict:
    """Fitur turunan dari titik kurva [[ratio, watchRatio, relPerf|None], ...].
    Murni & deterministik (diuji unit). rows kosong → semua None."""
    if not rows:
        return {"hook_hold": None, "mid_exit": None, "loop_factor": None,
                "end_ratio": None, "rel_perf_avg": None, "points": 0}
    awr = [float(r[1]) for r in rows]
    hook_hold = round(sum(awr[:HOOK_BUCKETS]) / len(awr[:HOOK_BUCKETS]), 4)
    mid_exit = None
    for r in rows:
        if float(r[1]) < MID_EXIT_THRESHOLD:
            mid_exit = round(float(r[0]), 4)
            break
    loop_factor = round(sum(max(0.0, v - 1.0) for v in awr) / len(awr), 4)
    end_ratio   = round(awr[-1], 4)
    rel_vals = [float(r[2]) for r in rows if len(r) > 2 and r[2] is not None]
    rel_perf_avg = round(sum(rel_vals) / len(rel_vals), 4) if rel_vals else None
    return {"hook_hold": hook_hold, "mid_exit": mid_exit, "loop_factor": loop_factor,
            "end_ratio": end_ratio, "rel_perf_avg": rel_perf_avg, "points": len(rows)}


def decide_action(video_age_days: int, existing: dict | None, knobs: dict,
                  now: datetime | None = None) -> str:
    """Keputusan per video (murni & diuji unit):
      'fetch'      → ambil/ambil-ulang sekarang
      'too_young'  → belum eligible (umur < min_age)
      'final'      → sudah punya kurva matang (fetch saat umur ≥ refresh_age) — selesai selamanya
      'wait_refresh' → punya kurva muda; tunggu video melewati refresh_age
      'give_up'    → empty terus & video melewati give_up_age — berhenti mencoba
      'cooldown'   → empty, tapi attempt terakhir < EMPTY_RETRY_MIN_HOURS lalu
    """
    if video_age_days < knobs["retention_curve_min_age_days"]:
        return "too_young"
    if existing is None:
        return "fetch"
    if existing.get("status") == "ok":
        age_at_fetch = existing.get("video_age_days") or 0
        if age_at_fetch >= knobs["retention_curve_refresh_age_days"]:
            return "final"
        if video_age_days >= knobs["retention_curve_refresh_age_days"]:
            return "fetch"          # refresh sekali: kurva matang menggantikan kurva muda
        return "wait_refresh"
    # status == 'empty'
    if video_age_days > knobs["retention_curve_give_up_age_days"]:
        return "give_up"
    fetched_at = existing.get("fetched_at")
    if fetched_at:
        try:
            dt = datetime.fromisoformat(str(fetched_at).replace("Z", "+00:00"))
            hours = ((now or datetime.now(timezone.utc)) - dt).total_seconds() / 3600.0
            if hours < EMPTY_RETRY_MIN_HOURS:
                return "cooldown"
        except Exception:
            pass  # timestamp tak terbaca → jangan blokir retry
    return "fetch"


class RetentionCurveCollector:
    """Kolektor per-channel. `analytics_client` WAJIB klien Analytics v2 milik koneksi
    channel ini (dibangun ChannelAnalytics — kredensial pool per-channel)."""

    def __init__(self, tenant_id: str, channel_id: str, analytics_client, supabase):
        self._tenant_id  = tenant_id
        self._channel_id = channel_id
        self._analytics  = analytics_client
        self._sb         = supabase

    # ── Data dasar ────────────────────────────────────────────────────────

    def _published_videos(self) -> list:
        """Video published channel ini (paginasi penuh — pola baku anti cap-1000 senyap)."""
        out, page = [], 0
        while page < 20:
            res = (self._sb.table("videos")
                   .select("video_id, published_at")
                   .eq("tenant_id", self._tenant_id).eq("channel_id", self._channel_id)
                   .eq("status", "published").not_.is_("video_id", "null")
                   .order("published_at", desc=True)
                   .range(page * 1000, page * 1000 + 999).execute())
            rows = res.data or []
            out += [v for v in rows if v.get("video_id") and v.get("published_at")]
            if len(rows) < 1000:
                break
            page += 1
        return out

    def _existing_rows(self) -> dict:
        """Baris video_retention_curves channel ini, keyed video_id (paginasi penuh)."""
        out, page = {}, 0
        while page < 20:
            res = (self._sb.table("video_retention_curves")
                   .select("video_id, status, video_age_days, fetched_at, attempt_count, first_attempt_at")
                   .eq("channel_id", self._channel_id)
                   .order("video_id")
                   .range(page * 1000, page * 1000 + 999).execute())
            rows = res.data or []
            for r in rows:
                out[r["video_id"]] = r
            if len(rows) < 1000:
                break
            page += 1
        return out

    @staticmethod
    def _age_days(published_at: str, now: datetime) -> int:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return (now - pub).days

    # ── API ───────────────────────────────────────────────────────────────

    def _fetch_curve(self, video_id: str, published_at: str) -> list:
        """1 request = 1 video (syarat resmi). Return [[ratio, awr, relPerf|None], ...]."""
        resp = (self._analytics.reports().query(
            ids="channel==MINE",
            startDate=published_at[:10],
            endDate=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            metrics="audienceWatchRatio,relativeRetentionPerformance",
            dimensions="elapsedVideoTimeRatio",
            filters=f"video=={video_id}",
        ).execute())
        rows = resp.get("rows") or []
        return [[float(r[0]), float(r[1]), (float(r[2]) if len(r) > 2 and r[2] is not None else None)]
                for r in rows]

    def _views_now(self, video_id: str) -> int | None:
        """Views snapshot terbaru dari video_analytics (konteks; fail-soft None)."""
        try:
            res = (self._sb.table("video_analytics").select("views")
                   .eq("video_id", video_id)
                   .order("analytics_date", desc=True).order("collected_at", desc=True)
                   .limit(1).execute())
            rows = res.data or []
            return int(rows[0]["views"]) if rows else None
        except Exception:
            return None

    # ── Run ───────────────────────────────────────────────────────────────

    def run(self) -> dict:
        """Satu siklus utk channel ini. Return ringkasan (dipakai log + validasi)."""
        result = {"eligible": 0, "fetched": 0, "ok": 0, "empty": 0, "errors": 0,
                  "final": 0, "waiting": 0, "give_up": 0}
        if not self._analytics or not self._sb:
            logger.info(f"[RetentionCurves] klien analytics/DB tak tersedia ch={self._channel_id} — lewati")
            return result

        knobs = load_knobs(self._sb)
        now = datetime.now(timezone.utc)
        videos = self._published_videos()
        existing = self._existing_rows()

        # Kandidat + prioritas deterministik: belum-pernah-dicoba dulu (terbaru→terlama:
        # video matang terbaru paling relevan utk belajar), lalu retry 'empty', lalu refresh.
        todo = []
        for v in videos:
            age = self._age_days(v["published_at"], now)
            action = decide_action(age, existing.get(v["video_id"]), knobs, now)
            if action == "fetch":
                row = existing.get(v["video_id"])
                prio = 0 if row is None else (1 if row.get("status") == "empty" else 2)
                todo.append((prio, v["video_id"], v["published_at"], age, row))
                result["eligible"] += 1
            elif action == "final":
                result["final"] += 1
            elif action in ("wait_refresh", "too_young", "cooldown"):
                result["waiting"] += 1
            elif action == "give_up":
                result["give_up"] += 1
        todo.sort(key=lambda t: t[0])
        todo = todo[: knobs["retention_curve_max_per_run"]]

        for _, vid, published_at, age, row in todo:
            try:
                curve = self._fetch_curve(vid, published_at)
                feats = compute_features(curve)
                payload = {
                    "video_id":       vid,
                    "tenant_id":      self._tenant_id,
                    "channel_id":     self._channel_id,
                    "status":         "ok" if curve else "empty",
                    "curve":          curve if curve else None,
                    **{k: feats[k] for k in ("hook_hold", "mid_exit", "loop_factor",
                                             "end_ratio", "rel_perf_avg", "points")},
                    "views_at_fetch": self._views_now(vid),
                    "video_age_days": age,
                    "attempt_count":  (row.get("attempt_count") or 0) + 1 if row else 1,
                    "fetched_at":     now.isoformat(),
                }
                if row and row.get("first_attempt_at"):
                    payload["first_attempt_at"] = row["first_attempt_at"]
                self._sb.table("video_retention_curves").upsert(payload).execute()
                result["fetched"] += 1
                result["ok" if curve else "empty"] += 1
                time.sleep(REQUEST_SLEEP_SEC)
            except Exception as e:
                result["errors"] += 1
                logger.warning(f"[RetentionCurves] gagal video {vid} (non-fatal): {e}")

        logger.info(
            f"[RetentionCurves] ch={self._channel_id}: eligible={result['eligible']} "
            f"fetch={result['fetched']} (ok={result['ok']} empty={result['empty']} "
            f"err={result['errors']}) | final={result['final']} waiting={result['waiting']} "
            f"give_up={result['give_up']}"
        )
        return result
