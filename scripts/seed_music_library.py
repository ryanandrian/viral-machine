"""
Music Library Seeder — seed_music_library.py
Upload track dari folder lokal → Cloudflare R2 → INSERT Supabase music_library.

Cara pakai:
  1. Download track dari YouTube Audio Library
  2. Beri nama file: {niche}__{mood}__{nama_track}.mp3
     Contoh: universe_mysteries__dramatic__dark_space_orchestra.mp3
  3. Taruh semua file di folder (default: ~/Downloads/music_seed/)
  4. Jalankan: python3.11 scripts/seed_music_library.py

Niche yang valid:
  universe_mysteries, dark_history, ocean_mysteries, fun_facts

Mood yang valid:
  dramatic, mysterious, tense, dark, ominous, calm, eerie,
  upbeat, happy, inspirational, energetic, playful
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Validasi constants ─────────────────────────────────────────────────────────

VALID_NICHES = {
    "universe_mysteries", "dark_history", "ocean_mysteries", "fun_facts"
}

VALID_MOODS = {
    "dramatic", "mysterious", "tense", "dark", "ominous",
    "calm", "eerie", "upbeat", "happy", "inspirational",
    "energetic", "playful", "epic", "ambient", "suspense"
}

# Mood → niche mapping untuk validasi
NICHE_MOOD_MAP = {
    "universe_mysteries": ["dramatic", "mysterious", "tense", "epic", "ambient", "suspense"],
    "dark_history":       ["dark", "ominous", "dramatic", "tense", "suspense"],
    "ocean_mysteries":    ["mysterious", "calm", "eerie", "ambient", "tense"],
    "fun_facts":          ["upbeat", "happy", "inspirational", "energetic", "playful"],
}


def get_audio_duration(file_path: Path) -> int:
    """Ambil durasi audio dalam detik via ffprobe."""
    import subprocess, json
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data   = json.loads(result.stdout)
        return int(float(data["format"]["duration"]))
    except Exception as e:
        print(f"  ⚠️  ffprobe error: {e} — duration set to 0")
        return 0


def get_audio_bpm(file_path: Path) -> int:
    """Detect BPM dari file audio via librosa."""
    try:
        import librosa
        y, sr = librosa.load(str(file_path), duration=60)  # max 60 detik untuk speed
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        return int(round(float(tempo)))
    except Exception as e:
        print(f"  ⚠️  BPM detection error: {e} — BPM set to 0")
        return 0


def upload_to_r2(file_path: Path, r2_key: str) -> bool:
    """Upload file ke Cloudflare R2."""
    try:
        import boto3
        from botocore.client import Config

        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("R2_SECRET_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        bucket = os.getenv("R2_BUCKET", "viral-machine")
        s3.upload_file(
            str(file_path),
            bucket,
            r2_key,
            ExtraArgs={"ContentType": "audio/mpeg"}
        )
        return True
    except Exception as e:
        print(f"  ❌ R2 upload error: {e}")
        return False


def insert_to_supabase(record: dict) -> bool:
    """INSERT record ke Supabase music_library."""
    try:
        from supabase import create_client
        sb  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        res = sb.table("music_library").insert(record).execute()
        return bool(res.data)
    except Exception as e:
        print(f"  ❌ Supabase error: {e}")
        return False


def check_duplicate(pixabay_id: str, name: str) -> bool:
    """Cek apakah track sudah ada di Supabase berdasarkan nama file."""
    try:
        from supabase import create_client
        sb  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        res = sb.table("music_library").select("id").eq("name", name).execute()
        return len(res.data) > 0
    except Exception:
        return False


def parse_filename(file_path: Path) -> dict | None:
    """
    Parse niche, mood, dan nama dari filename.
    Format: {niche}__{mood}__{nama_track}.mp3
    """
    stem = file_path.stem  # tanpa extension

    parts = stem.split("__")
    if len(parts) < 3:
        print(f"  ⚠️  Format nama file salah: '{file_path.name}'")
        print(f"       Harus: {{niche}}__{{mood}}__{{nama_track}}.mp3")
        return None

    niche = parts[0].strip().lower()
    mood  = parts[1].strip().lower()
    name  = "__".join(parts[2:]).strip()  # sisa = nama track

    if niche not in VALID_NICHES:
        print(f"  ⚠️  Niche tidak valid: '{niche}'")
        print(f"       Valid: {', '.join(sorted(VALID_NICHES))}")
        return None

    if mood not in VALID_MOODS:
        print(f"  ⚠️  Mood tidak valid: '{mood}'")
        print(f"       Valid: {', '.join(sorted(VALID_MOODS))}")
        return None

    return {"niche": niche, "mood": mood, "name": name}


def seed_music_library(music_folder: str = None, dry_run: bool = False):
    """
    Main seeder — scan folder, upload R2, insert Supabase.
    dry_run=True: hanya print tanpa upload/insert.
    """
    if music_folder is None:
        music_folder = str(Path.home() / "Downloads" / "music_seed")

    folder = Path(music_folder)
    if not folder.exists():
        print(f"❌ Folder tidak ditemukan: {folder}")
        print(f"   Buat folder dan taruh file MP3 di sana.")
        return

    mp3_files = sorted(folder.glob("*.mp3"))
    if not mp3_files:
        print(f"❌ Tidak ada file .mp3 di: {folder}")
        return

    print(f"\n{'='*60}")
    print(f"🎵 MUSIC LIBRARY SEEDER")
    print(f"{'='*60}")
    print(f"Folder : {folder}")
    print(f"Files  : {len(mp3_files)} track ditemukan")
    print(f"Mode   : {'DRY RUN (tidak upload)' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    success = 0
    skipped = 0
    failed  = 0

    for i, file_path in enumerate(mp3_files, 1):
        print(f"[{i}/{len(mp3_files)}] {file_path.name}")

        # Parse filename
        parsed = parse_filename(file_path)
        if not parsed:
            failed += 1
            continue

        niche = parsed["niche"]
        mood  = parsed["mood"]
        name  = parsed["name"]

        # Cek duplikat
        if check_duplicate("", name):
            print(f"  ⏭️  Skip — sudah ada di library: '{name}'")
            skipped += 1
            continue

        # Extract audio metadata
        print(f"  📊 Extracting metadata...")
        duration_s = get_audio_duration(file_path)
        print(f"     Duration : {duration_s}s")

        print(f"  🎵 Detecting BPM...")
        bpm = get_audio_bpm(file_path)
        print(f"     BPM      : {bpm}")

        # R2 key: music/{niche}/{mood}/{filename}
        r2_key = f"music/{niche}/{mood}/{file_path.name}"
        print(f"  ☁️  R2 key   : {r2_key}")

        if dry_run:
            print(f"  ✅ [DRY RUN] Would upload + insert:")
            print(f"     niche={niche} mood={mood} name={name}")
            print(f"     duration={duration_s}s bpm={bpm}")
            success += 1
            continue

        # Upload ke R2
        print(f"  ⬆️  Uploading to R2...")
        if not upload_to_r2(file_path, r2_key):
            failed += 1
            continue
        print(f"  ✅ R2 upload OK")

        # INSERT ke Supabase
        record = {
            "tenant_id":   None,           # global — semua tenant bisa pakai
            "niche":       niche,
            "mood":        mood,
            "name":        name,
            "r2_key":      r2_key,
            "duration_s":  duration_s,
            "bpm":         bpm if bpm > 0 else None,
            "source":      "youtube_audio_library",
            "is_active":   True,
            "is_default":  (i == 1),       # track pertama per niche = default
            "play_count":  0,
            "pixabay_id":  None,
        }

        print(f"  💾 Inserting to Supabase...")
        if not insert_to_supabase(record):
            failed += 1
            continue

        print(f"  ✅ SUCCESS: {niche} / {mood} / {name} ({duration_s}s, {bpm}bpm)")
        success += 1
        print()

    # Summary
    print(f"\n{'='*60}")
    print(f"SEEDER COMPLETE")
    print(f"{'='*60}")
    print(f"  ✅ Success : {success}")
    print(f"  ⏭️  Skipped : {skipped}")
    print(f"  ❌ Failed  : {failed}")
    print(f"  Total     : {len(mp3_files)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed music library from local folder")
    parser.add_argument(
        "--folder",
        default=str(Path.home() / "Downloads" / "music_seed"),
        help="Folder berisi file MP3 (default: ~/Downloads/music_seed/)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run — hanya print tanpa upload/insert"
    )
    args = parser.parse_args()

    seed_music_library(music_folder=args.folder, dry_run=args.dry_run)
