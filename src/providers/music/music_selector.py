"""
Music Selector — pilih track dari library R2 berdasarkan mood script.

s85: Keyword-based mood detection, bukan niche-based.
  - Mood dideteksi dari konten script (keyword matching)
  - Query musik berdasarkan mood saja — niche baru otomatis dapat musik
  - mood_priority per niche diambil dari Supabase niches.mood_priority (tidak hardcode)
  - Fallback: mood dengan skor tertinggi berikutnya → any active track
"""

import os
import random
from pathlib import Path

from loguru import logger


# ── Mood → keyword signal (universal NLP mapping, bukan niche-specific) ──────
# Digunakan untuk deteksi mood dari teks script
MOOD_KEYWORDS = {
    "dramatic":      ["shocking", "incredible", "unbelievable", "changed everything", "nobody expected"],
    "mysterious":    ["unknown", "mystery", "unexplained", "secret", "hidden", "discovered"],
    "tense":         ["danger", "threat", "warning", "critical", "urgent", "countdown"],
    "ominous":       ["dark", "evil", "betrayal", "conspiracy", "cover-up", "forbidden"],
    "dark":          ["death", "massacre", "tragedy", "catastrophe", "destruction"],
    "upbeat":        ["amazing", "fun", "surprising", "interesting", "cool", "wow"],
    "inspirational": ["wonder", "beautiful", "incredible", "miraculous", "stunning"],
    "energetic":     ["fast", "quick", "rapid", "explosive", "powerful", "breakthrough"],
    "calm":          ["peaceful", "gentle", "quiet", "deep", "vast", "infinite"],
    "eerie":         ["strange", "weird", "unsettling", "alien", "bizarre", "uncanny"],
    "epic":          ["enormous", "massive", "universe", "galaxy", "civilization", "ancient"],
    "suspense":      ["what if", "imagine", "but here", "nobody knows", "the truth"],
}


def _detect_mood_from_script(script: dict, niche_mood_priority: list) -> tuple[str, dict]:
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

    # Score semua mood dari keyword match
    scores = {
        mood: sum(1 for kw in keywords if kw in full_text)
        for mood, keywords in MOOD_KEYWORDS.items()
    }

    # Pilih mood tertinggi
    best_mood   = max(scores, key=scores.get) if any(scores.values()) else None
    best_score  = scores.get(best_mood, 0) if best_mood else 0

    # Jika tidak ada keyword match, gunakan mood_priority dari niches table
    if not best_mood or best_score == 0:
        best_mood = niche_mood_priority[0] if niche_mood_priority else "dramatic"
        logger.info(f"[MusicSelector] No keyword match — pakai mood_priority: {best_mood}")
    else:
        logger.info(
            f"[MusicSelector] Mood detected: {best_mood} "
            f"(score={best_score})"
        )

    return best_mood, scores


def _load_niche_mood_priority(niche: str) -> list:
    """
    Load mood_priority dari Supabase niches table.
    Fallback ke list kosong jika kolom belum ada.
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
                logger.debug(f"[MusicSelector] mood_priority dari Supabase: {priority}")
                return priority
    except Exception as e:
        logger.warning(f"[MusicSelector] Gagal load mood_priority dari niches: {e}")
    return []


def _query_supabase_by_mood(mood: str, fallback_moods: list) -> list[dict]:
    """
    Query music_library berdasarkan mood — TIDAK filter per niche.
    Niche baru otomatis dapat musik tanpa perubahan kode.

    Fallback cascade: mood utama → mood dengan skor tinggi berikutnya → any active
    """
    try:
        from supabase import create_client
        from dotenv import load_dotenv
        load_dotenv()

        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        # Query utama: mood exact match
        res = (
            sb.table("music_library")
            .select("*")
            .eq("mood", mood)
            .eq("is_active", True)
            .order("play_count", desc=False)
            .execute()
        )
        if res.data:
            logger.info(f"[MusicSelector] {len(res.data)} tracks untuk mood={mood}")
            return res.data

        # Fallback: coba mood lain berdasarkan skor script (bukan hardcoded niche priority)
        for fallback_mood in fallback_moods:
            if fallback_mood == mood:
                continue
            res2 = (
                sb.table("music_library")
                .select("*")
                .eq("mood", fallback_mood)
                .eq("is_active", True)
                .limit(5)
                .execute()
            )
            if res2.data:
                logger.warning(
                    f"[MusicSelector] Fallback mood: {fallback_mood} "
                    f"(mood '{mood}' tidak tersedia di library)"
                )
                return res2.data

        # Last resort: any active track
        res3 = (
            sb.table("music_library")
            .select("*")
            .eq("is_active", True)
            .limit(5)
            .execute()
        )
        if res3.data:
            logger.warning("[MusicSelector] Last resort: pakai track random dari library")
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
            endpoint_url        = os.getenv("R2_ENDPOINT"),
            aws_access_key_id   = os.getenv("R2_ACCESS_KEY"),
            aws_secret_access_key = os.getenv("R2_SECRET_KEY"),
            config              = Config(signature_version="s3v4"),
            region_name         = "auto",
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

    Mood dideteksi dari konten script (keyword-based).
    Query musik berdasarkan mood — tidak bergantung niche (future-proof).

    Returns:
        str path ke file musik local, atau None jika tidak tersedia.
    """
    logger.info(f"[MusicSelector] Selecting music | niche={niche}")

    # 1. Load mood_priority dari Supabase (fallback jika tidak ada keyword match)
    niche_mood_priority = _load_niche_mood_priority(niche)

    # 2. Detect mood dari konten script
    mood, scores = _detect_mood_from_script(script, niche_mood_priority)

    # Fallback moods: urutan berdasarkan skor script (bukan hardcoded)
    fallback_moods = sorted(
        [m for m, s in scores.items() if s > 0 and m != mood],
        key=lambda m: scores[m],
        reverse=True,
    )
    # Tambah mood_priority dari niches sebagai safety net di akhir
    for m in niche_mood_priority:
        if m not in fallback_moods and m != mood:
            fallback_moods.append(m)

    # 3. Query Supabase (mood-based, tidak filter niche)
    tracks = _query_supabase_by_mood(mood, fallback_moods)
    if not tracks:
        logger.warning("[MusicSelector] Tidak ada track di library — skip music")
        return None

    # 4. Prioritaskan track yang durasinya >= audio (tidak perlu loop)
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

    # 5. Download dari R2
    output_path = Path(output_dir) / f"music_{mood}_{track_id[:8]}.mp3"
    if output_path.exists():
        logger.info(f"[MusicSelector] Cache hit: {output_path.name}")
        return str(output_path)

    logger.info(f"[MusicSelector] Downloading from R2: {r2_key}")
    if not _download_from_r2(r2_key, output_path):
        logger.error("[MusicSelector] Download gagal — skip music")
        return None

    size_kb = output_path.stat().st_size / 1024
    logger.info(f"[MusicSelector] ✅ Music ready: {output_path.name} ({size_kb:.0f}KB)")

    # 6. Increment play count (non-blocking)
    _increment_play_count(track_id)

    return str(output_path)
