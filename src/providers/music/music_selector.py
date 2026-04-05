"""
Music Selector — pilih track dari library R2 berdasarkan mood script.

s85b: Fully config-driven — tidak ada hardcode.
  - Mood keywords dari tabel moods di Supabase
  - Query: niche + mood → mood only (any niche) → fallback moods → any active
  - mood_priority per niche dari niches.mood_priority (safety net jika tidak ada keyword match)
"""

import os
import random
from pathlib import Path

from loguru import logger


def _load_mood_keywords() -> dict:
    """
    Load mood → keywords dari tabel moods di Supabase.
    Returns dict: {mood_id: [keyword, ...]}
    """
    try:
        from supabase import create_client
        from dotenv import load_dotenv
        load_dotenv()

        sb  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        res = sb.table("moods").select("mood_id,keywords").eq("is_active", True).execute()
        if res.data:
            keywords = {r["mood_id"]: r["keywords"] or [] for r in res.data}
            logger.debug(f"[MusicSelector] Loaded {len(keywords)} moods dari Supabase")
            return keywords
    except Exception as e:
        logger.warning(f"[MusicSelector] Gagal load moods dari Supabase: {e}")
    return {}


def _load_niche_mood_priority(niche: str) -> list:
    """
    Load mood_priority dari Supabase niches table.
    Dipakai sebagai safety net fallback jika tidak ada keyword match.
    """
    try:
        from supabase import create_client
        from dotenv import load_dotenv
        load_dotenv()

        sb  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        res = sb.table("niches").select("mood_priority").eq("niche_id", niche).single().execute()
        if res.data:
            priority = res.data.get("mood_priority") or []
            if priority:
                logger.debug(f"[MusicSelector] mood_priority: {priority}")
                return priority
    except Exception as e:
        logger.warning(f"[MusicSelector] Gagal load mood_priority dari niches: {e}")
    return []


def _detect_mood_from_script(
    script: dict,
    mood_keywords: dict,
    niche_mood_priority: list,
) -> tuple[str, dict]:
    """
    Analisa konten script → deteksi mood terbaik via keyword matching.

    Returns:
        (best_mood, scores_dict) — mood terpilih + semua skor untuk fallback
    """
    text_parts = [
        script.get("hook", ""),
        script.get("mystery_drop", ""),
        script.get("climax", ""),
        script.get("core_facts", ""),
    ]
    full_text = " ".join(p for p in text_parts if p).lower()

    scores = {
        mood: sum(1 for kw in keywords if kw in full_text)
        for mood, keywords in mood_keywords.items()
    }

    best_mood  = max(scores, key=scores.get) if any(scores.values()) else None
    best_score = scores.get(best_mood, 0) if best_mood else 0

    if not best_mood or best_score == 0:
        best_mood = niche_mood_priority[0] if niche_mood_priority else "dramatic"
        logger.info(f"[MusicSelector] No keyword match — pakai mood_priority: {best_mood}")
    else:
        logger.info(f"[MusicSelector] Mood detected: {best_mood} (score={best_score})")

    return best_mood, scores


def _query_tracks(niche: str, mood: str, fallback_moods: list) -> list[dict]:
    """
    Query music_library dengan fallback cascade:
      1. niche + mood (paling spesifik)
      2. mood only, any niche (mood sama, niche lain)
      3. fallback moods (mood berbeda, berurutan dari skor tertinggi)
      4. any active track (last resort)
    """
    try:
        from supabase import create_client
        from dotenv import load_dotenv
        load_dotenv()

        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        # 1. niche + mood
        res = (
            sb.table("music_library")
            .select("*")
            .eq("niche", niche)
            .eq("mood", mood)
            .eq("is_active", True)
            .order("play_count", desc=False)
            .execute()
        )
        if res.data:
            logger.info(f"[MusicSelector] {len(res.data)} tracks — niche={niche} mood={mood}")
            return res.data

        # 2. mood only (any niche)
        res2 = (
            sb.table("music_library")
            .select("*")
            .eq("mood", mood)
            .eq("is_active", True)
            .limit(5)
            .execute()
        )
        if res2.data:
            logger.warning(
                f"[MusicSelector] Fallback mood-only: mood={mood} "
                f"(niche='{niche}' tidak punya track mood='{mood}')"
            )
            return res2.data

        # 3. fallback moods (berurutan dari skor script)
        for fallback_mood in fallback_moods:
            res3 = (
                sb.table("music_library")
                .select("*")
                .eq("mood", fallback_mood)
                .eq("is_active", True)
                .limit(5)
                .execute()
            )
            if res3.data:
                logger.warning(
                    f"[MusicSelector] Fallback mood: {fallback_mood} "
                    f"(mood='{mood}' tidak tersedia di library)"
                )
                return res3.data

        # 4. any active
        res4 = (
            sb.table("music_library")
            .select("*")
            .eq("is_active", True)
            .limit(5)
            .execute()
        )
        if res4.data:
            logger.warning("[MusicSelector] Last resort: track random dari library")
            return res4.data

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
            endpoint_url          = os.getenv("R2_ENDPOINT"),
            aws_access_key_id     = os.getenv("R2_ACCESS_KEY"),
            aws_secret_access_key = os.getenv("R2_SECRET_KEY"),
            config                = Config(signature_version="s3v4"),
            region_name           = "auto",
        )
        bucket = os.getenv("R2_BUCKET", "viral-machine")
        s3.download_file(bucket, r2_key, str(output_path))
        return output_path.exists()

    except Exception as e:
        logger.error(f"[MusicSelector] R2 download error: {e}")
        return False


def _increment_play_count(track_id: str) -> None:
    """Increment play_count di Supabase. Fire-and-forget."""
    try:
        from supabase import create_client
        from dotenv import load_dotenv
        load_dotenv()

        sb  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        res = sb.table("music_library").select("play_count").eq("id", track_id).execute()
        if res.data:
            current = res.data[0].get("play_count", 0) or 0
            sb.table("music_library").update({"play_count": current + 1}).eq("id", track_id).execute()
    except Exception:
        pass


def select_and_download(
    script: dict,
    niche: str,
    output_dir: str = "logs",
    audio_duration: float = 55.0,
) -> str | None:
    """
    Main entry point: pilih track terbaik → download → return local path.

    Mood dideteksi dari konten script via keyword matching (keywords dari moods table).
    Query musik berdasarkan niche + mood — config-driven, tidak ada hardcode.

    Returns:
        str path ke file musik local, atau None jika tidak tersedia.
    """
    logger.info(f"[MusicSelector] Selecting music | niche={niche}")

    # 1. Load mood keywords dari moods table
    mood_keywords = _load_mood_keywords()

    # 2. Load mood_priority dari niches table (safety net)
    niche_mood_priority = _load_niche_mood_priority(niche)

    # 3. Detect mood dari konten script
    mood, scores = _detect_mood_from_script(script, mood_keywords, niche_mood_priority)

    # Fallback moods: urutan dari skor script tertinggi, tambah mood_priority sebagai safety net
    fallback_moods = sorted(
        [m for m, s in scores.items() if s > 0 and m != mood],
        key=lambda m: scores[m],
        reverse=True,
    )
    for m in niche_mood_priority:
        if m not in fallback_moods and m != mood:
            fallback_moods.append(m)

    # 4. Query Supabase
    tracks = _query_tracks(niche, mood, fallback_moods)
    if not tracks:
        logger.warning("[MusicSelector] Tidak ada track di library — skip music")
        return None

    # 5. Prioritaskan track yang durasinya >= audio (tidak perlu loop)
    long_tracks = [t for t in tracks if (t.get("duration_s") or 0) >= audio_duration]
    candidate   = random.choice(long_tracks) if len(long_tracks) > 1 else (long_tracks[0] if long_tracks else tracks[0])

    track_name = candidate.get("name", "unknown")
    track_mood = candidate.get("mood", mood)
    duration_s = candidate.get("duration_s", 0)
    r2_key     = candidate.get("r2_key", "")
    track_id   = candidate.get("id", "")

    logger.info(
        f"[MusicSelector] Selected: '{track_name}' "
        f"(mood={track_mood}, {duration_s}s, bpm={candidate.get('bpm')})"
    )

    if not r2_key:
        logger.error("[MusicSelector] Track tidak punya r2_key")
        return None

    # 6. Download dari R2
    output_path = Path(output_dir) / f"music_{mood}_{track_id[:8]}.mp3"
    if output_path.exists():
        logger.info(f"[MusicSelector] Cache hit: {output_path.name}")
        return str(output_path)

    logger.info(f"[MusicSelector] Downloading from R2: {r2_key}")
    if not _download_from_r2(r2_key, output_path):
        logger.error("[MusicSelector] Download gagal — skip music")
        return None

    size_kb = output_path.stat().st_size / 1024
    logger.info(f"[MusicSelector] Music ready: {output_path.name} ({size_kb:.0f}KB)")

    # 7. Increment play count (non-blocking)
    _increment_play_count(track_id)

    return str(output_path)
