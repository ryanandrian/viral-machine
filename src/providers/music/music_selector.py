"""
Music Selector — pilih track dari library R2 berdasarkan niche + mood script.
Fase 6C s6c4:
  - Analisa emotional tone dari script → tentukan mood
  - Query Supabase music_library → pilih track terbaik
  - Download dari Cloudflare R2 → return local path
  - FFmpeg mix di video_renderer: -18dB ducking agar tidak kalahkan narasi
"""

import os
import random
import tempfile
from pathlib import Path

from loguru import logger


# ── Mood mapping per niche ────────────────────────────────────────────────────
# Script emotional arc → mood yang paling cocok
# Urutan = prioritas (index 0 = paling diutamakan)

NICHE_MOOD_PRIORITY = {
    "universe_mysteries": ["dramatic", "mysterious", "tense", "epic", "ambient"],
    "dark_history":       ["ominous", "dark", "dramatic", "tense", "suspense"],
    "ocean_mysteries":    ["mysterious", "eerie", "calm", "ambient", "tense"],
    "fun_facts":          ["upbeat", "energetic", "inspirational", "happy", "playful"],
}

# Script keywords → mood signal
MOOD_KEYWORDS = {
    "dramatic":     ["shocking", "incredible", "unbelievable", "changed everything", "nobody expected"],
    "mysterious":   ["unknown", "mystery", "unexplained", "secret", "hidden", "discovered"],
    "tense":        ["danger", "threat", "warning", "critical", "urgent", "countdown"],
    "ominous":      ["dark", "evil", "betrayal", "conspiracy", "cover-up", "forbidden"],
    "dark":         ["death", "massacre", "tragedy", "catastrophe", "destruction"],
    "upbeat":       ["amazing", "fun", "surprising", "interesting", "cool", "wow"],
    "inspirational":["wonder", "beautiful", "incredible", "miraculous", "stunning"],
    "energetic":    ["fast", "quick", "rapid", "explosive", "powerful", "breakthrough"],
    "calm":         ["peaceful", "gentle", "quiet", "deep", "vast", "infinite"],
    "eerie":        ["strange", "weird", "unsettling", "alien", "bizarre", "uncanny"],
}


def _detect_mood_from_script(script: dict, niche: str) -> str:
    """
    Analisa script → deteksi mood yang paling cocok.
    Scoring: hitung keyword match per mood, pilih tertinggi.
    Fallback: mood pertama dari NICHE_MOOD_PRIORITY.
    """
    # Ambil text yang relevan dari script
    text_parts = [
        script.get("hook", ""),
        script.get("mystery_drop", ""),
        script.get("climax", ""),
        script.get("core_facts", ""),
    ]
    full_text = " ".join(p for p in text_parts if p).lower()

    if not full_text:
        default = NICHE_MOOD_PRIORITY.get(niche, ["dramatic"])[0]
        logger.info(f"[MusicSelector] No script text — default mood: {default}")
        return default

    # Score per mood
    scores = {}
    for mood, keywords in MOOD_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in full_text)
        if score > 0:
            scores[mood] = score

    # Filter hanya mood yang tersedia untuk niche ini
    niche_moods = NICHE_MOOD_PRIORITY.get(niche, ["dramatic"])

    # Pilih mood dengan score tertinggi yang ada di niche
    best_mood = None
    best_score = 0
    for mood in niche_moods:
        s = scores.get(mood, 0)
        if s > best_score:
            best_score = s
            best_mood = mood

    if not best_mood:
        best_mood = niche_moods[0]  # fallback ke prioritas pertama

    logger.info(
        f"[MusicSelector] Mood detected: {best_mood} "
        f"(score={best_score}, niche={niche})"
    )
    return best_mood


def _query_supabase(niche: str, mood: str) -> list[dict]:
    """
    Query Supabase music_library untuk niche + mood.
    Fallback: coba niche lain dengan mood sama jika tidak ada hasil.
    """
    try:
        from supabase import create_client
        from dotenv import load_dotenv
        load_dotenv()

        sb = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

        # Query utama: exact niche + mood match
        res = sb.table("music_library") \
            .select("*") \
            .eq("niche", niche) \
            .eq("mood", mood) \
            .eq("is_active", True) \
            .order("play_count", desc=False) \
            .execute()

        if res.data:
            logger.info(
                f"[MusicSelector] Found {len(res.data)} tracks: "
                f"niche={niche} mood={mood}"
            )
            return res.data

        # Fallback 1: niche sama, mood berbeda (urutan prioritas)
        niche_moods = NICHE_MOOD_PRIORITY.get(niche, [])
        for fallback_mood in niche_moods:
            if fallback_mood == mood:
                continue
            res2 = sb.table("music_library") \
                .select("*") \
                .eq("niche", niche) \
                .eq("mood", fallback_mood) \
                .eq("is_active", True) \
                .limit(3) \
                .execute()
            if res2.data:
                logger.warning(
                    f"[MusicSelector] ⚠️ Fallback mood: {niche}/{fallback_mood} "
                    f"(original mood '{mood}' tidak tersedia)"
                )
                return res2.data

        # Fallback 2: any active track
        res3 = sb.table("music_library") \
            .select("*") \
            .eq("is_active", True) \
            .limit(5) \
            .execute()
        if res3.data:
            logger.warning(
                f"[MusicSelector] ⚠️ Fallback any: tidak ada track untuk "
                f"niche={niche} — pakai track random dari library"
            )
            return res3.data

        return []

    except Exception as e:
        logger.error(f"[MusicSelector] Supabase query error: {e}")
        return []


def _download_from_r2(r2_key: str, output_path: Path) -> bool:
    """Download track dari Cloudflare R2 ke local path."""
    try:
        import boto3
        from botocore.client import Config
        from dotenv import load_dotenv
        load_dotenv()

        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("R2_SECRET_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        bucket = os.getenv("R2_BUCKET", "viral-machine")
        s3.download_file(bucket, r2_key, str(output_path))
        return output_path.exists()

    except Exception as e:
        logger.error(f"[MusicSelector] R2 download error: {e}")
        return False


def _increment_play_count(track_id: str) -> None:
    """Increment play_count di Supabase untuk track yang dipilih."""
    try:
        from supabase import create_client
        from dotenv import load_dotenv
        load_dotenv()

        sb = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        # Baca play_count aktual dulu
        res = sb.table("music_library") \
            .select("play_count") \
            .eq("id", track_id) \
            .execute()
        if res.data:
            current = res.data[0].get("play_count", 0) or 0
            sb.table("music_library") \
                .update({"play_count": current + 1}) \
                .eq("id", track_id) \
                .execute()
    except Exception:
        pass  # Non-critical


def select_and_download(
    script: dict,
    niche: str,
    output_dir: str = "logs",
    audio_duration: float = 55.0,
) -> str | None:
    """
    Main entry point: pilih track terbaik → download → return local path.

    Returns:
        str path ke file musik local, atau None jika tidak tersedia.
    """
    logger.info(f"[MusicSelector] Selecting music for niche={niche}")

    # 1. Detect mood dari script
    mood = _detect_mood_from_script(script, niche)

    # 2. Query Supabase
    tracks = _query_supabase(niche, mood)
    if not tracks:
        logger.warning("[MusicSelector] ⚠️ Tidak ada track di library — skip music")
        return None

    # 3. Filter track yang durasinya cukup (min = audio_duration)
    # Prioritaskan track yang lebih panjang dari audio (tidak perlu loop)
    long_tracks = [t for t in tracks if (t.get("duration_s") or 0) >= audio_duration]
    candidate   = long_tracks[0] if long_tracks else tracks[0]

    # Randomize jika ada beberapa track dengan durasi cukup (variasi)
    if len(long_tracks) > 1:
        candidate = random.choice(long_tracks)

    track_name = candidate.get("name", "unknown")
    track_mood = candidate.get("mood", mood)
    duration_s = candidate.get("duration_s", 0)
    r2_key     = candidate.get("r2_key", "")
    track_id   = candidate.get("id", "")

    logger.info(
        f"[MusicSelector] Selected: '{track_name}' "
        f"({track_mood}, {duration_s}s, bpm={candidate.get('bpm')})"
    )

    if not r2_key:
        logger.error("[MusicSelector] Track tidak punya r2_key")
        return None

    # 4. Download dari R2
    output_path = Path(output_dir) / f"music_{niche}_{mood}_{track_id[:8]}.mp3"
    if output_path.exists():
        logger.info(f"[MusicSelector] Cache hit: {output_path.name}")
        return str(output_path)

    logger.info(f"[MusicSelector] Downloading from R2: {r2_key}")
    if not _download_from_r2(r2_key, output_path):
        logger.error("[MusicSelector] Download gagal — skip music")
        return None

    size_kb = output_path.stat().st_size / 1024
    logger.info(
        f"[MusicSelector] ✅ Music ready: {output_path.name} ({size_kb:.0f}KB)"
    )

    # 5. Increment play count (non-blocking)
    _increment_play_count(track_id)

    return str(output_path)
