"""
Storage Cleaner — pembersih file otomatis setelah pipeline selesai.

Strategi (sudah disepakati):
  - Clips mentah    → hapus SEGERA setelah render selesai & output terverifikasi
  - Video final     → hapus setelah semua platform aktif berhasil upload
  - Log JSON        → hapus otomatis setelah 30 hari
  - Audio MP3       → hapus otomatis setelah 7 hari
  - R2              → BUKAN untuk backup video
"""

import shutil
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger


class StorageCleaner:

    def __init__(self, base_dir: str = "logs"):
        self.base_dir = Path(base_dir)

    def cleanup_clips(self, tenant_id: str, video_path: str) -> bool:
        clips_dir = self.base_dir / f"clips_{tenant_id}"
        if not clips_dir.exists():
            return True
        video = Path(video_path)
        if not video.exists():
            logger.warning(f"[StorageCleaner] SKIP cleanup clips — video final tidak ada: {video_path}")
            return False
        size_mb = video.stat().st_size / (1024 * 1024)
        if size_mb < 5:
            logger.warning(f"[StorageCleaner] SKIP cleanup clips — video terlalu kecil ({size_mb:.1f}MB)")
            return False
        total_size_mb = sum(
            f.stat().st_size for f in clips_dir.rglob("*") if f.is_file()
        ) / (1024 * 1024)
        try:
            shutil.rmtree(clips_dir)
            logger.info(f"[StorageCleaner] Clips deleted: {clips_dir.name} ({total_size_mb:.1f}MB freed)")
            return True
        except Exception as e:
            logger.error(f"[StorageCleaner] Failed to delete clips: {e}")
            return False

    def cleanup_video(
        self,
        video_path: str,
        published_platforms: list[str],
        required_platforms: list[str],
    ) -> bool:
        video = Path(video_path)
        if not video.exists():
            return True
        if not published_platforms:
            logger.warning(f"[StorageCleaner] SKIP delete video — tidak ada platform yang berhasil upload")
            return False
        missing = [p for p in required_platforms if p not in published_platforms]
        if missing:
            logger.warning(f"[StorageCleaner] SKIP delete video — platform belum upload: {missing}")
            return False
        size_mb = video.stat().st_size / (1024 * 1024)
        try:
            video.unlink()
            logger.info(f"[StorageCleaner] Video deleted: {video.name} ({size_mb:.1f}MB freed)")
            return True
        except Exception as e:
            logger.error(f"[StorageCleaner] Failed to delete video: {e}")
            return False

    def cleanup_old_logs(
        self,
        max_age_days_json: int = 30,
        max_age_days_audio: int = 7,
    ) -> dict:
        cutoff_json  = datetime.now() - timedelta(days=max_age_days_json)
        cutoff_audio = datetime.now() - timedelta(days=max_age_days_audio)
        deleted_count = 0
        freed_bytes   = 0
        # [2026-08-13] DAFTAR POLA DISUSULKAN — dulu tertinggal saat format berkas berganti.
        # Terukur di server (13-Agu): 634 dari 808 berkas lebih tua dari 7 hari, ±73 MB sisa nyata.
        #   • `.ass` 188 berkas — subtitle. Dulu berformat `.srt` (ADA di daftar); saat berganti ke
        #     `.ass`, daftar ini TIDAK ikut diperbarui → menumpuk sejak 16-Jun.
        #   • `.txt` 188 berkas — daftar klip untuk penyambung video, sisa sesudah render.
        #   • `.jpg` 111 berkas — gambar mini; sudah terunggah ke YouTube & tersimpan di S3.
        #   • `.mp4`   2 berkas, 52,9 MB — tertua 17-Jun (hari pindahan v1→v2).
        # `.srt` DIPERTAHANKAN: berkas lama mungkin masih ada, dan menghapus pola = meninggalkan sampah.
        #
        # ⚠️ KENAPA `.mp4` MEMAKAI AMBANG PANJANG (bukan 7 hari): video adalah satu-satunya berkas di
        # sini yang KEHILANGANNYA tak bisa dipulihkan. Sudah diverifikasi bahwa penerbitan mengunduh
        # dari S3 ke folder sementara — TIDAK pernah membaca folder ini (satu-satunya pembacanya =
        # blok uji manual era v1) — jadi salinan lokal memang sisa. Ambang panjang tetap dipakai
        # sebagai jarak aman: umur simpan stok 72 jam, jadi ambang ini belasan kali lipat di atasnya.
        patterns = {
            "*.json": cutoff_json,
            "*.mp3":  cutoff_audio,
            "*.srt":  cutoff_audio,
            "*.ass":  cutoff_audio,
            "*.txt":  cutoff_audio,
            "*.jpg":  cutoff_audio,
            "*.mp4":  cutoff_json,      # sengaja se-longgar json, bukan 7 hari
        }
        for pattern, cutoff in patterns.items():
            for f in self.base_dir.glob(pattern):
                if not f.is_file():
                    continue
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    size = f.stat().st_size
                    try:
                        f.unlink()
                        deleted_count += 1
                        freed_bytes   += size
                        logger.debug(f"[StorageCleaner] Deleted old log: {f.name}")
                    except Exception as e:
                        logger.error(f"[StorageCleaner] Cannot delete {f.name}: {e}")
        freed_mb = freed_bytes / (1024 * 1024)
        if deleted_count > 0:
            logger.info(f"[StorageCleaner] Old logs cleaned: {deleted_count} files, {freed_mb:.1f}MB freed")
        return {"deleted_files": deleted_count, "freed_mb": round(freed_mb, 2)}

    def report_storage(self) -> dict:
        if not self.base_dir.exists():
            return {"total_mb": 0, "breakdown": {}}
        breakdown   = {}
        total_bytes = 0
        for item in self.base_dir.iterdir():
            if item.is_file():
                size = item.stat().st_size
                ext  = item.suffix or "other"
                breakdown[ext] = breakdown.get(ext, 0) + size
                total_bytes   += size
            elif item.is_dir():
                dir_size = sum(
                    f.stat().st_size for f in item.rglob("*") if f.is_file()
                )
                breakdown[item.name] = dir_size
                total_bytes += dir_size
        total_mb = total_bytes / (1024 * 1024)
        logger.info(f"[StorageCleaner] Storage usage: {total_mb:.1f}MB total")
        return {
            "total_mb":  round(total_mb, 1),
            "breakdown": {
                k: round(v / (1024 * 1024), 1)
                for k, v in sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
            }
        }
