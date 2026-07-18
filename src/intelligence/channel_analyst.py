"""
ChannelAnalyst — [B17 §6 A1] LAPIS 2 "OTAK": analis LLM per-channel + buku keputusan (MODE BAYANGAN).

Siklus (default mingguan, kenop `analyst_*`): rakit DOSIR fakta TERUKUR channel →
LLM tenant sendiri (BYOK, model task 'utility' — pola persis NicheSelector) berpikir →
KEPUTUSAN TERSTRUKTUR menu-tertutup + PREDIKSI terukur → dicatat `channel_decisions`.

HUKUM DESAIN (§6c — dipegang mati):
  1. Fakta & penalaran dipisah: modul ini MENGUKUR (dosir) lalu LLM MEMUTUSKAN;
     yang MENGADILI kelak = hakim mekanik (A2), BUKAN LLM.
  2. BAYANGAN: mode='shadow' → TIDAK ADA konsumen produksi. Wiring eksekusi = A2
     (gerbang ketok owner pasca-review 2 minggu, K4).
  3. Menu keputusan TERTUTUP + ber-batas (validasi skema ketat; gagal → retry 1× dgn
     umpan-balik error → tetap gagal = dicatat status='rejected' JUJUR, bukan diterima diam-diam).
  4. Nilai kebijakan = kenop app_config (no-hardcode); batas menu = konstanta ber-nama ber-uji.
  5. Fail-soft total: kegagalan di sini tak boleh mengganggu rantai self-learning lain.
"""

import json
from datetime import datetime, timezone

from loguru import logger

# ── Menu keputusan TERTUTUP (batas = definisi produk §6d, ber-uji; BUKAN nilai bisnis DB) ──
DECISION_TYPES = {
    "topic_direction",        # arahan tematik utk pemilih topik (maks 3 per siklus)
    "hook_pattern",           # target porsi pola hook (0..MAX_HOOK_SHARE)
    "content_type_mix",       # geser porsi jenis konten (±MAX_MIX_SHIFT_PCT)
    "niche_mix",              # HANYA channel niche_mode='random'; niche ∈ pool
    "duration_note",          # catatan durasi (informasional)
    "focus_recommendation",   # saran fokus niche → HANYA utk tenant (tak pernah auto)
}
MAX_DECISIONS       = 6
MAX_TOPIC_DIRECTION = 3
MAX_HOOK_SHARE      = 0.4
MAX_MIX_SHIFT_PCT   = 20
PREDICTION_METRICS  = {"retention_avg", "views_per_video", "subs_per_video"}
PREDICTION_DIRS     = {"up", "hold"}
HORIZON_DAYS_RANGE  = (7, 30)
RAW_RESPONSE_CAP    = 8000   # audit bayangan; anti baris raksasa

KNOB_DEFAULTS = {"analyst_enabled": 1, "analyst_interval_days": 7, "analyst_min_videos": 20}


def load_knobs(sb) -> dict:
    """Kenop analis dari app_config; fallback per-kunci (fail-soft)."""
    knobs = dict(KNOB_DEFAULTS)
    try:
        rows = (sb.table("app_config").select("key, value")
                .in_("key", list(KNOB_DEFAULTS.keys())).execute().data) or []
        for r in rows:
            k, v = r.get("key"), r.get("value")
            if k in knobs and v is not None and int(v) >= 0:
                knobs[k] = int(v)
    except Exception as e:
        logger.warning(f"[Analyst] baca kenop gagal → default ({e})")
    return knobs


# ── Validasi skema keputusan (murni & ber-uji) ────────────────────────────────

def validate_decisions(decisions, channel_ctx: dict) -> tuple:
    """Return (valid: bool, error: str|None). Menu tertutup + batas keras —
    LLM boleh berpikir bebas, TIDAK boleh memutuskan di luar pagar."""
    if not isinstance(decisions, list) or not (1 <= len(decisions) <= MAX_DECISIONS):
        return False, f"decisions harus list 1..{MAX_DECISIONS}"
    topic_count = 0
    for i, d in enumerate(decisions):
        if not isinstance(d, dict):
            return False, f"#{i}: bukan object"
        dtype  = d.get("type")
        detail = d.get("detail")
        codes  = d.get("reason_codes")
        pred   = d.get("prediction")
        if dtype not in DECISION_TYPES:
            return False, f"#{i}: type '{dtype}' di luar menu {sorted(DECISION_TYPES)}"
        if not isinstance(detail, dict):
            return False, f"#{i}: detail harus object"
        if not (isinstance(codes, list) and codes and all(isinstance(c, str) and c for c in codes)):
            return False, f"#{i}: reason_codes harus list string non-kosong"
        # prediksi WAJIB terukur — tanpa prediksi, hakim mekanik (A2) tak bisa mengadili
        if not isinstance(pred, dict):
            return False, f"#{i}: prediction wajib object"
        if pred.get("metric") not in PREDICTION_METRICS:
            return False, f"#{i}: prediction.metric harus salah satu {sorted(PREDICTION_METRICS)}"
        if pred.get("direction") not in PREDICTION_DIRS:
            return False, f"#{i}: prediction.direction harus {sorted(PREDICTION_DIRS)}"
        h = pred.get("horizon_days")
        if not (isinstance(h, int) and HORIZON_DAYS_RANGE[0] <= h <= HORIZON_DAYS_RANGE[1]):
            return False, f"#{i}: horizon_days harus int {HORIZON_DAYS_RANGE[0]}..{HORIZON_DAYS_RANGE[1]}"
        # Batas per-type
        if dtype == "topic_direction":
            topic_count += 1
            if topic_count > MAX_TOPIC_DIRECTION:
                return False, f"topic_direction maks {MAX_TOPIC_DIRECTION}"
            if not (isinstance(detail.get("directive"), str) and 0 < len(detail["directive"]) <= 200):
                return False, f"#{i}: directive wajib string ≤200"
        elif dtype == "hook_pattern":
            share = detail.get("target_share")
            if not (isinstance(detail.get("pattern"), str) and detail["pattern"]):
                return False, f"#{i}: pattern wajib string"
            if not (isinstance(share, (int, float)) and 0 < share <= MAX_HOOK_SHARE):
                return False, f"#{i}: target_share harus 0..{MAX_HOOK_SHARE}"
        elif dtype == "content_type_mix":
            shift = detail.get("shift_pct")
            if not (isinstance(detail.get("content_type"), str) and detail["content_type"]):
                return False, f"#{i}: content_type wajib string"
            if not (isinstance(shift, (int, float)) and -MAX_MIX_SHIFT_PCT <= shift <= MAX_MIX_SHIFT_PCT):
                return False, f"#{i}: shift_pct harus ±{MAX_MIX_SHIFT_PCT}"
        elif dtype in ("niche_mix", "focus_recommendation"):
            if channel_ctx.get("niche_mode") != "random":
                return False, f"#{i}: {dtype} hanya utk channel niche_mode='random'"
            pool = channel_ctx.get("niche_pool") or []
            if detail.get("niche") not in pool:
                return False, f"#{i}: niche '{detail.get('niche')}' bukan anggota pool {pool}"
            if dtype == "niche_mix":
                share = detail.get("share_hint")
                if not (isinstance(share, (int, float)) and 0 < share <= 0.6):
                    return False, f"#{i}: share_hint harus 0..0.6"
        elif dtype == "duration_note":
            if not (isinstance(detail.get("note"), str) and 0 < len(detail["note"]) <= 300):
                return False, f"#{i}: note wajib string ≤300"
    return True, None


def is_due(last_created_at: str | None, interval_days: int,
           now: datetime | None = None) -> bool:
    """Siklus jatuh tempo? (murni & ber-uji). Tanpa riwayat = due."""
    if not last_created_at:
        return True
    try:
        last = datetime.fromisoformat(str(last_created_at).replace("Z", "+00:00"))
    except Exception:
        return True   # timestamp rusak → jangan memblokir selamanya
    return ((now or datetime.now(timezone.utc)) - last).days >= interval_days


def clean_json_response(raw: str) -> str:
    """Buang pagar markdown ```json ... ``` (pola respons LLM umum; murni & ber-uji)."""
    s = (raw or "").strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s.lstrip("`")
        if s.rstrip().endswith("```"):
            s = s.rstrip().rsplit("```", 1)[0]
    return s.strip()


class ChannelAnalyst:
    """Satu siklus analis utk satu channel. Dipanggil self_learning (fail-soft)."""

    def __init__(self, supabase, tenant_id: str, channel_id: str):
        self._sb  = supabase
        self._tid = tenant_id
        self._cid = channel_id

    # ── Dosir: fakta TERUKUR saja (LLM tidak pernah melihat data mentah raksasa) ──

    def _fetch_paged(self, build, order_cols, page_size=1000, max_pages=20):
        """Paginasi penuh deterministik (pola baku anti cap-1000 senyap)."""
        out, page = [], 0
        while page < max_pages:
            q = build()
            for col in order_cols:
                q = q.order(col, desc=True, nullsfirst=False)
            rows = (q.range(page * page_size, page * page_size + page_size - 1)
                    .execute().data) or []
            out += rows
            if len(rows) < page_size:
                break
            page += 1
        return out

    def build_dossier(self, channel_row: dict, insights: dict | None) -> dict:
        """Rakit dosir dari 4 sumber terukur. Ukuran dijaga ringkas (agregat, bukan mentah)."""
        now = datetime.now(timezone.utc)

        # 1) snapshot analytics TERBARU per video (pola first-seen DESC) + meta video
        videos = self._fetch_paged(
            lambda: (self._sb.table("videos")
                     .select("video_id, niche, hook_pattern, published_at, duration_secs")
                     .eq("channel_id", self._cid).eq("status", "published")
                     .not_.is_("video_id", "null")),
            order_cols=("published_at",))
        vmeta = {v["video_id"]: v for v in videos if v.get("video_id")}
        amap: dict = {}
        ids = list(vmeta.keys())
        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            rows = self._fetch_paged(
                lambda c=chunk: (self._sb.table("video_analytics")
                                 .select("video_id, views, avg_view_pct, subscriber_gain, analytics_date, collected_at")
                                 .in_("video_id", c)),
                order_cols=("analytics_date", "collected_at"))
            for a in rows:
                vid = a.get("video_id")
                if vid and vid not in amap:
                    amap[vid] = a

        # 2) kohort mingguan (10 minggu terakhir; retensi = completion valid >0 cap 100)
        weekly: dict = {}
        per_niche: dict = {}
        for vid, v in vmeta.items():
            a = amap.get(vid)
            if not a or not v.get("published_at"):
                continue
            pub = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
            wk = pub.strftime("%G-W%V")
            ret = a.get("avg_view_pct") or 0.0
            w = weekly.setdefault(wk, {"n": 0, "views": 0, "subs": 0, "ret_sum": 0.0, "ret_n": 0})
            w["n"] += 1; w["views"] += a.get("views") or 0; w["subs"] += a.get("subscriber_gain") or 0
            if ret > 0:
                w["ret_sum"] += min(100.0, ret); w["ret_n"] += 1
            nb = per_niche.setdefault(v.get("niche") or "?", {"n": 0, "views": 0, "subs": 0, "ret_sum": 0.0, "ret_n": 0})
            nb["n"] += 1; nb["views"] += a.get("views") or 0; nb["subs"] += a.get("subscriber_gain") or 0
            if ret > 0:
                nb["ret_sum"] += min(100.0, ret); nb["ret_n"] += 1
        weekly_out = [
            {"week": wk, "videos": w["n"], "views_per_video": round(w["views"] / w["n"], 1),
             "subs_per_video": round(w["subs"] / w["n"], 2),
             "retention_avg": round(w["ret_sum"] / w["ret_n"], 1) if w["ret_n"] else None}
            for wk, w in sorted(weekly.items(), reverse=True)[:10]]
        niche_out = {
            n: {"videos": b["n"], "views_per_video": round(b["views"] / b["n"], 1),
                "subs_per_video": round(b["subs"] / b["n"], 2),
                "retention_avg": round(b["ret_sum"] / b["ret_n"], 1) if b["ret_n"] else None}
            for n, b in per_niche.items()}

        # 3) fitur kurva retensi per-momen (M1) — agregat per niche + per pola hook
        curves = self._fetch_paged(
            lambda: (self._sb.table("video_retention_curves")
                     .select("video_id, hook_hold, mid_exit, loop_factor, end_ratio, rel_perf_avg")
                     .eq("channel_id", self._cid).eq("status", "ok")),
            order_cols=("video_id",))
        def _agg(rows):
            def avg(key):
                vals = [float(r[key]) for r in rows if r.get(key) is not None]
                return round(sum(vals) / len(vals), 3) if vals else None
            return {"n": len(rows), "hook_hold": avg("hook_hold"), "loop_factor": avg("loop_factor"),
                    "end_ratio": avg("end_ratio"), "vs_youtube": avg("rel_perf_avg"),
                    "mid_exit": avg("mid_exit")}
        by_niche_c: dict = {}
        by_hook_c: dict = {}
        for r in curves:
            v = vmeta.get(r["video_id"]) or {}
            by_niche_c.setdefault(v.get("niche") or "?", []).append(r)
            hp = v.get("hook_pattern")
            if hp:
                by_hook_c.setdefault(hp, []).append(r)
        curve_out = {
            "overall": _agg(curves),
            "per_niche": {n: _agg(rs) for n, rs in by_niche_c.items()},
            "per_hook_pattern": {h: _agg(rs) for h, rs in by_hook_c.items() if len(rs) >= 3},
        }

        # 4) insights terkini + riwayat keputusan+vonis (buku keputusan — bahan belajar-diri)
        past = (self._sb.table("channel_decisions")
                .select("cycle_date, decisions, verdict, status")
                .eq("channel_id", self._cid).order("created_at", desc=True)
                .limit(5).execute().data) or []

        return {
            "generated_at": now.isoformat(),
            "channel": {
                "name": channel_row.get("channel_name"),
                "niche_mode": channel_row.get("niche_mode"),
                "niche_pool": channel_row.get("niche_pool"),
                "primary_niche": channel_row.get("niche"),
                "content_language": channel_row.get("content_language"),
                "duration_preset": channel_row.get("duration_preset"),
                "subscriber_count": channel_row.get("subscriber_count"),
            },
            "weekly_cohorts": weekly_out,
            "per_niche": niche_out,
            "retention_curves": curve_out,
            "insights": {
                "grade": (insights or {}).get("performance_grade") or (insights or {}).get("grade"),
                "videos_analyzed": (insights or {}).get("videos_analyzed"),
                "niche_weights_subs_based": (insights or {}).get("niche_weights"),
                "content_type_perf": (insights or {}).get("content_type_perf"),
                "avoid_patterns": (insights or {}).get("avoid_patterns"),
            },
            "past_decisions": past,
        }

    # ── Prompt + panggilan LLM ─────────────────────────────────────────────

    @staticmethod
    def _build_prompt(dossier: dict, channel_ctx: dict) -> tuple:
        niche_rule = (
            f'- "niche_mix": detail {{"niche": MUST be in pool {channel_ctx.get("niche_pool")}, '
            '"share_hint": number 0..0.6}. '
            f'"focus_recommendation": detail {{"niche": MUST be in pool, "why": string}}. '
            'Both allowed ONLY because this channel has niche_mode="random".'
            if channel_ctx.get("niche_mode") == "random" else
            '- "niche_mix" and "focus_recommendation" are FORBIDDEN for this channel (fixed niche).')
        system = (
            "You are the channel growth analyst of an automated YouTube Shorts machine. "
            "Your ONLY goal chain: higher retention -> higher views -> subscriber growth -> "
            "channel monetization. You reason ONLY from the measured dossier provided — "
            "if the dossier does not support a decision, do not make it. "
            "You MUST return only a valid JSON object. No markdown, no text outside JSON.")
        user = f"""MEASURED DOSSIER (all numbers are real, from YouTube Analytics):
{json.dumps(dossier, ensure_ascii=False, default=str)}

TASK: Decide what the machine should do differently for the NEXT videos of this channel.
Return JSON: {{"decisions": [ ... 1..{MAX_DECISIONS} items ... ]}}
Each decision item:
{{
  "type": one of ["topic_direction","hook_pattern","content_type_mix","niche_mix","duration_note","focus_recommendation"],
  "detail": type-specific (see RULES),
  "reason_codes": [short strings citing dossier evidence, e.g. "per_niche.dark_history.subs_per_video=0.30 lowest"],
  "prediction": {{"metric": "retention_avg"|"views_per_video"|"subs_per_video", "direction": "up"|"hold", "horizon_days": {HORIZON_DAYS_RANGE[0]}..{HORIZON_DAYS_RANGE[1]}}}
}}
RULES (violations are rejected by a strict validator):
- "topic_direction": detail {{"directive": string <=200 chars}} — max {MAX_TOPIC_DIRECTION} items.
- "hook_pattern": detail {{"pattern": string, "target_share": 0..{MAX_HOOK_SHARE}}}.
- "content_type_mix": detail {{"content_type": string, "shift_pct": -{MAX_MIX_SHIFT_PCT}..{MAX_MIX_SHIFT_PCT}}}.
{niche_rule}
- "duration_note": detail {{"note": string <=300}}.
- Every decision MUST include a measurable prediction — it will be judged against real data.
- Fewer, evidence-dense decisions beat many vague ones.
- Retention curve features: hook_hold>1 means the hook is REWATCHED (good); low end_ratio means
  viewers leave before the end (body/payoff problem); vs_youtube is percentile-like vs similar videos."""
        return system, user

    def _call_llm(self, system: str, user: str) -> tuple:
        """LLM BYOK tenant, model task 'utility' (K3; pola NicheSelector). Return (raw, model)."""
        from src.config.tenant_config import load_tenant_config
        rc = load_tenant_config(self._tid, self._cid, None)
        if not rc:
            raise RuntimeError("tenant_config tak termuat")
        provider = rc.get_llm_provider()
        model    = rc.llm_model_for("utility")
        if not provider:
            raise RuntimeError("LLM provider tenant tidak tersedia (BYOK)")
        raw = provider.complete(system=system, user=user, model=model,
                                max_tokens=2000, temperature=0.4, as_json=True).strip()
        return raw, model

    # ── Run ────────────────────────────────────────────────────────────────

    def run(self, channel_row: dict, insights: dict | None) -> dict:
        """Satu siklus penuh (dipanggil HANYA bila due+gerbang lolos — cek di run_if_due)."""
        now = datetime.now(timezone.utc)
        channel_ctx = {"niche_mode": channel_row.get("niche_mode"),
                       "niche_pool": channel_row.get("niche_pool") or []}
        dossier = self.build_dossier(channel_row, insights)
        system, user = self._build_prompt(dossier, channel_ctx)

        raw, model, decisions, reject = "", "", None, None
        try:
            raw, model = self._call_llm(system, user)
            parsed = json.loads(clean_json_response(raw))
            cand = parsed.get("decisions") if isinstance(parsed, dict) else parsed
            ok, err = validate_decisions(cand, channel_ctx)
            if not ok:
                # retry 1× dengan umpan-balik error (LLM sering benar di percobaan kedua)
                logger.info(f"[Analyst] validasi gagal ({err}) — retry 1× dgn umpan-balik")
                raw2, model = self._call_llm(
                    system, user + f"\n\nYOUR PREVIOUS RESPONSE WAS REJECTED: {err}. "
                                   f"Return corrected JSON only.")
                parsed = json.loads(clean_json_response(raw2))
                cand = parsed.get("decisions") if isinstance(parsed, dict) else parsed
                ok, err = validate_decisions(cand, channel_ctx)
                raw = raw2
            if ok:
                decisions = cand
            else:
                reject = f"validasi: {err}"
        except Exception as e:
            reject = f"llm/parse: {str(e)[:300]}"

        row = {
            "tenant_id":    self._tid,
            "channel_id":   self._cid,
            "cycle_date":   now.date().isoformat(),
            "mode":         "shadow",
            "status":       "recorded" if decisions else "rejected",
            "decisions":    decisions,
            "dossier":      dossier,
            "raw_response": (raw or "")[:RAW_RESPONSE_CAP],
            "model_used":   model or None,
            "reject_reason": reject,
        }
        self._sb.table("channel_decisions").upsert(
            row, on_conflict="channel_id,cycle_date").execute()
        n = len(decisions) if decisions else 0
        logger.info(f"[Analyst] ch={self._cid}: {'OK ' + str(n) + ' keputusan' if decisions else 'REJECTED: ' + str(reject)} (model={model})")
        return {"status": row["status"], "n_decisions": n, "reject": reject, "model": model}


def run_if_due(sb, tenant_id: str, channel_id: str) -> dict:
    """Pintu masuk dari self_learning: cek saklar + gerbang data + jatuh-tempo → run.
    Insights SELALU dibaca penuh dari channel_insights (satu sumber — ringkasan return
    compute_and_store TIDAK memuat content_type_perf dsb. yang dosir butuhkan)."""
    knobs = load_knobs(sb)
    if not knobs["analyst_enabled"]:
        return {"status": "disabled"}
    rows = (sb.table("channel_insights").select("*")
            .eq("channel_id", channel_id).order("computed_at", desc=True)
            .limit(1).execute().data) or []
    insights = rows[0] if rows else None
    analyzed = int((insights or {}).get("videos_analyzed") or 0)
    if analyzed < knobs["analyst_min_videos"]:
        return {"status": "insufficient_data", "videos_analyzed": analyzed}
    # jatuh tempo?
    last = (sb.table("channel_decisions").select("created_at")
            .eq("channel_id", channel_id).order("created_at", desc=True)
            .limit(1).execute().data) or []
    if not is_due(last[0]["created_at"] if last else None, knobs["analyst_interval_days"]):
        return {"status": "not_due"}
    # channel row utk konteks menu (niche_mode/pool) + dosir
    ch = (sb.table("channels").select("*").eq("id", channel_id).limit(1).execute().data or [None])[0]
    if not ch:
        return {"status": "no_channel"}
    return ChannelAnalyst(sb, tenant_id, channel_id).run(ch, insights)
