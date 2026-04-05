"""
Music Library Seeder — seed_music_library.py
Upload track dari folder lokal → Cloudflare R2 → INSERT Supabase music_library.

Cara pakai:
  1. Siapkan file MP3 dengan nama: {niche}__{mood}__{nama_track}.mp3
     Contoh: universe_mysteries__dramatic__dark_space_orchestra.mp3
  2. Taruh semua file di satu folder
  3. Jalankan: python3.11 scripts/seed_music_library.py --folder /path/to/folder

Niche yang valid: diambil dari tabel niches di Supabase (niche_id, is_active=true)
Mood yang valid : diambil dari tabel moods  di Supabase (mood_id,  is_active=true)
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ── Supabase helpers ───────────────────────────────────────────────────────────

def _get_supabase():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def load_valid_niches() -> set:
    """Load niche_id aktif dari Supabase."""
    try:
        sb  = _get_supabase()
        res = sb.table("niches").select("niche_id").eq("is_active", True).execute()
        return {r["niche_id"] for r in res.data} if res.data else set()
    except Exception as e:
        print(f"[ERROR] Gagal load niches dari Supabase: {e}")
        sys.exit(1)


def load_valid_moods() -> set:
    """Load mood_id aktif dari Supabase."""
    try:
        sb  = _get_supabase()
        res = sb.table("moods").select("mood_id").eq("is_active", True).execute()
        return {r["mood_id"] for r in res.data} if res.data else set()
    except Exception as e:
        print(f"[ERROR] Gagal load moods dari Supabase: {e}")
        sys.exit(1)


# ── Audio metadata ─────────────────────────────────────────────────────────────

def get_audio_duration(file_path: Path) -> int:
    """Ambil durasi audio dalam detik via ffprobe."""
    try:
        cmd    = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data   = json.loads(result.stdout)
        return int(float(data["format"]["duration"]))
    except Exception as e:
        print(f"  [WARN] ffprobe error: {e} — duration set to 0")
        return 0


def get_audio_bpm(file_path: Path) -> int:
    """Detect BPM dari file audio via librosa."""
    try:
        import librosa
        y, sr = librosa.load(str(file_path), duration=60)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm_val = tempo[0] if hasattr(tempo, "__len__") else tempo
        return int(round(float(bpm_val)))
    except Exception as e:
        print(f"  [WARN] BPM detection error: {e} — BPM set to 0")
        return 0


# ── R2 + Supabase ops ─────────────────────────────────────────────────────────

def upload_to_r2(file_path: Path, r2_key: str) -> bool:
    """Upload file ke Cloudflare R2."""
    try:
        import boto3
        from botocore.client import Config

        s3 = boto3.client(
            "s3",
            endpoint_url          = os.getenv("R2_ENDPOINT"),
            aws_access_key_id     = os.getenv("R2_ACCESS_KEY"),
            aws_secret_access_key = os.getenv("R2_SECRET_KEY"),
            config                = Config(signature_version="s3v4"),
            region_name           = "auto",
        )
        s3.upload_file(
            str(file_path),
            os.getenv("R2_BUCKET", "viral-machine"),
            r2_key,
            ExtraArgs={"ContentType": "audio/mpeg"},
        )
        return True
    except Exception as e:
        print(f"  [ERROR] R2 upload: {e}")
        return False


def insert_to_supabase(record: dict) -> bool:
    """INSERT record ke Supabase music_library."""
    try:
        sb  = _get_supabase()
        res = sb.table("music_library").insert(record).execute()
        return bool(res.data)
    except Exception as e:
        print(f"  [ERROR] Supabase insert: {e}")
        return False


def check_duplicate(name: str) -> bool:
    """Cek apakah track sudah ada berdasarkan nama."""
    try:
        sb  = _get_supabase()
        res = sb.table("music_library").select("id").eq("name", name).execute()
        return len(res.data) > 0
    except Exception:
        return False


# ── Filename parser ────────────────────────────────────────────────────────────

def parse_filename(file_path: Path, valid_niches: set, valid_moods: set) -> dict | None:
    """
    Parse niche, mood, dan nama dari filename.
    Format wajib: {niche}__{mood}__{nama_track}.mp3
    """
    stem  = file_path.stem
    parts = stem.split("__")

    if len(parts) < 3:
        print(f"  [WARN] Format nama salah: '{file_path.name}'")
        print(f"         Wajib: {{niche}}__{{mood}}__{{nama_track}}.mp3")
        return None

    niche = parts[0].strip().lower()
    mood  = parts[1].strip().lower()
    name  = "__".join(parts[2:]).strip()

    if niche not in valid_niches:
        print(f"  [WARN] Niche tidak valid: '{niche}'")
        print(f"         Valid: {', '.join(sorted(valid_niches))}")
        return None

    if mood not in valid_moods:
        print(f"  [WARN] Mood tidak valid: '{mood}'")
        print(f"         Valid: {', '.join(sorted(valid_moods))}")
        return None

    return {"niche": niche, "mood": mood, "name": name}


# ── Main seeder ────────────────────────────────────────────────────────────────

def seed_music_library(music_folder: str, dry_run: bool = False):
    """Scan folder, upload R2, insert Supabase."""
    folder = Path(music_folder)
    if not folder.exists():
        print(f"[ERROR] Folder tidak ditemukan: {folder}")
        return

    mp3_files = sorted(folder.glob("*.mp3"))
    if not mp3_files:
        print(f"[ERROR] Tidak ada file .mp3 di: {folder}")
        return

    print(f"\n{'='*60}")
    print(f"MUSIC LIBRARY SEEDER")
    print(f"{'='*60}")
    print(f"Folder : {folder}")
    print(f"Files  : {len(mp3_files)} track")
    print(f"Mode   : {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    print("Loading valid niches dan moods dari Supabase...")
    valid_niches = load_valid_niches()
    valid_moods  = load_valid_moods()
    print(f"  Niches: {', '.join(sorted(valid_niches))}")
    print(f"  Moods : {', '.join(sorted(valid_moods))}\n")

    success = skipped = failed = 0

    for i, file_path in enumerate(mp3_files, 1):
        print(f"[{i}/{len(mp3_files)}] {file_path.name}")

        parsed = parse_filename(file_path, valid_niches, valid_moods)
        if not parsed:
            failed += 1
            continue

        niche = parsed["niche"]
        mood  = parsed["mood"]
        name  = parsed["name"]

        if check_duplicate(name):
            print(f"  [SKIP] Sudah ada di library: '{name}'")
            skipped += 1
            continue

        print(f"  Extracting duration...")
        duration_s = get_audio_duration(file_path)
        print(f"  Duration : {duration_s}s")

        print(f"  Detecting BPM...")
        bpm = get_audio_bpm(file_path)
        print(f"  BPM      : {bpm}")

        r2_key = f"music/{niche}/{mood}/{file_path.name}"
        print(f"  R2 key   : {r2_key}")

        if dry_run:
            print(f"  [DRY RUN] niche={niche} mood={mood} name={name} duration={duration_s}s bpm={bpm}")
            success += 1
            print()
            continue

        print(f"  Uploading to R2...")
        if not upload_to_r2(file_path, r2_key):
            failed += 1
            continue
        print(f"  R2 OK")

        record = {
            "niche":      niche,
            "mood":       mood,
            "name":       name,
            "r2_key":     r2_key,
            "duration_s": duration_s,
            "bpm":        bpm if bpm > 0 else None,
            "source":     "upload",
            "is_active":  True,
            "play_count": 0,
        }

        print(f"  Inserting to Supabase...")
        if not insert_to_supabase(record):
            failed += 1
            continue

        print(f"  [OK] {niche} / {mood} / {name} ({duration_s}s, {bpm}bpm)")
        success += 1
        print()

    print(f"\n{'='*60}")
    print(f"SELESAI — OK:{success}  Skip:{skipped}  Gagal:{failed}  Total:{len(mp3_files)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed music library dari folder lokal")
    parser.add_argument("--folder", required=True, help="Folder berisi file MP3")
    parser.add_argument("--dry-run", action="store_true", help="Dry run tanpa upload/insert")
    args = parser.parse_args()

    seed_music_library(music_folder=args.folder, dry_run=args.dry_run)
