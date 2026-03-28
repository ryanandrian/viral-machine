"""
Video Renderer — FFmpeg pipeline untuk render video final 9:16.
v0.2 fixes:
  - Caption timing: gunakan word_timestamps nyata dari TTS (bukan estimasi)
  - Font size: diperkecil ke 11 (dari 18)
  - MarginV: dinaikkan ke 120 (dari 80) — caption lebih ke bawah
  - Fallback: estimasi word count jika timestamps tidak tersedia
"""

import json
import os
import subprocess
import time
from loguru import logger
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig

load_dotenv()


class VideoRenderer:
    """
    FFmpeg pipeline: clips + audio + subtitle → MP4 1080x1920.
    """

    OUTPUT_WIDTH  = 1080
    OUTPUT_HEIGHT = 1920
    FPS           = 30
    VIDEO_BITRATE = "4000k"
    AUDIO_BITRATE = "192k"

    # Caption style — v0.2: font diperkecil, posisi lebih bawah
    CAPTION_STYLE = (
        "FontName=Arial,"
        "FontSize=11,"           # ← diperkecil dari 18 ke 11 (~60%)
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H80000000,"
        "Outline=2,"
        "Shadow=1,"
        "MarginV=120,"           # ← dinaikkan dari 80 ke 120
        "Alignment=2,"           # bottom center
        "WrapStyle=1"            # wrap agar tidak keluar layar
    )

    def _get_audio_duration(self, audio_path: str) -> float:
        try:
            cmd    = ["ffprobe", "-v", "quiet", "-print_format", "json",
                      "-show_format", audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data   = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except Exception as e:
            logger.error(f"Could not get audio duration: {e}")
            return 58.0

    def _get_video_duration(self, video_path: str) -> float:
        try:
            cmd    = ["ffprobe", "-v", "quiet", "-print_format", "json",
                      "-show_streams", video_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data   = json.loads(result.stdout)
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    return float(stream.get("duration", 5.0))
            return 5.0
        except Exception:
            return 5.0

    def _create_clip_list(self, clips: list, target_duration: float, output_dir: str) -> str:
        """
        Fase 6C s6c1: durasi per clip = audio_duration / n_clips.
        Clip terakhir = sisa waktu — tidak ada loop/repeat.
        """
        list_path = os.path.join(output_dir, "clip_list.txt")
        n         = len(clips)
        dur_each  = round(target_duration / n, 4)
        entries   = []

        for i, clip in enumerate(clips):
            dur      = dur_each if i < n - 1 else round(target_duration - dur_each * (n - 1), 4)
            abs_path = os.path.abspath(clip)
            entries.append(f"file '{abs_path}'\n")
            entries.append(f"duration {dur}\n")

        with open(list_path, "w") as f:
            f.writelines(entries)

        total_actual = dur_each * (n - 1) + round(target_duration - dur_each * (n - 1), 4)
        logger.info(
            f"[Renderer] clip_list: {n} clips x {dur_each}s = {total_actual:.3f}s"
            f" (target: {target_duration:.3f}s) — no repeat"
        )
        return list_path

    def _generate_subtitles_from_timestamps(
        self,
        word_timestamps: list[dict],
        output_dir: str,
        words_per_segment: int = 5,
    ) -> str:
        """
        Generate SRT dari word-level timestamps nyata (akurat ~95%).
        Grouping: setiap N kata menjadi 1 segmen subtitle.
        """
        srt_path = os.path.join(output_dir, "subtitles.srt")

        if not word_timestamps:
            return ""

        # Group kata-kata ke dalam segmen
        segments = []
        for i in range(0, len(word_timestamps), words_per_segment):
            group  = word_timestamps[i:i + words_per_segment]
            text   = " ".join(w["word"] for w in group)
            start  = group[0]["start"]
            end    = group[-1]["end"]
            segments.append({"text": text, "start": start, "end": end})

        def fmt_time(seconds: float) -> str:
            h  = int(seconds // 3600)
            m  = int((seconds % 3600) // 60)
            s  = int(seconds % 60)
            ms = int((seconds % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        srt_content = []
        for i, seg in enumerate(segments):
            srt_content.append(str(i + 1))
            srt_content.append(f"{fmt_time(seg['start'])} --> {fmt_time(seg['end'])}")
            srt_content.append(seg["text"])
            srt_content.append("")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))

        logger.info(
            f"Subtitles (timestamps): {len(segments)} segments → {srt_path}"
        )
        return srt_path

    def _generate_subtitles_estimated(
        self,
        script: dict,
        audio_duration: float,
        output_dir: str,
        words_per_segment: int = 5,
    ) -> str:
        """
        Fallback: estimasi timing dari word count.
        Akurasi ~60-70% — dipakai jika provider tidak return timestamps.
        """
        srt_path    = os.path.join(output_dir, "subtitles.srt")
        full_script = script.get("full_script", "")
        if not full_script:
            parts = [
                script.get("hook", ""),
                script.get("build_up", ""),
                script.get("core_facts", ""),
                script.get("climax", ""),
                script.get("cta", "")
            ]
            full_script = " ".join(p for p in parts if p)

        words = full_script.split()
        if not words:
            return ""

        segments = []
        for i in range(0, len(words), words_per_segment):
            segments.append(" ".join(words[i:i + words_per_segment]))

        seg_dur = audio_duration / len(segments)

        def fmt_time(seconds: float) -> str:
            h  = int(seconds // 3600)
            m  = int((seconds % 3600) // 60)
            s  = int(seconds % 60)
            ms = int((seconds % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        srt_content = []
        for i, seg in enumerate(segments):
            start = i * seg_dur
            end   = (i + 1) * seg_dur
            srt_content.append(str(i + 1))
            srt_content.append(f"{fmt_time(start)} --> {fmt_time(end)}")
            srt_content.append(seg)
            srt_content.append("")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))

        logger.info(
            f"Subtitles (estimated): {len(segments)} segments → {srt_path}"
        )
        return srt_path

    def render(
        self,
        script: dict,
        audio_path: str,
        clips: list,
        tenant_config: TenantConfig,
        output_dir: str = "logs",
        word_timestamps: list[dict] | None = None,
    ) -> str:
        """
        Render video final.

        Args:
            script:          Script dict
            audio_path:      Path ke file audio MP3
            clips:           List path clip video
            tenant_config:   Config tenant
            output_dir:      Direktori output
            word_timestamps: Word-level timestamps dari TTS (opsional)
                             Jika tersedia → subtitle akurat
                             Jika None     → fallback ke estimasi
        """
        if not clips:
            logger.error("No video clips available")
            return ""
        if not audio_path or not os.path.exists(audio_path):
            logger.error("Audio file not found")
            return ""

        logger.info("Getting audio duration...")
        audio_duration = self._get_audio_duration(audio_path)
        logger.info(f"Audio duration: {audio_duration:.1f}s")

        logger.info("Creating clip list...")
        clip_list_path = self._create_clip_list(clips, audio_duration, output_dir)

        # Generate subtitles — pakai timestamps jika tersedia
        logger.info("Generating subtitles...")
        if word_timestamps:
            logger.info(
                f"[Subtitle] Mode: word timestamps "
                f"({len(word_timestamps)} words) — akurasi ~95%"
            )
            srt_path = self._generate_subtitles_from_timestamps(
                word_timestamps, output_dir
            )
        else:
            logger.warning(
                "[Subtitle] Mode: estimasi word count — akurasi ~60-70%. "
                "Upgrade ke provider dengan word timestamps untuk akurasi lebih baik."
            )
            srt_path = self._generate_subtitles_estimated(
                script, audio_duration, output_dir
            )

        timestamp   = int(time.time())
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"video_{tenant_config.tenant_id}_{timestamp}.mp4")
        temp_path   = os.path.join(output_dir, f"temp_{timestamp}.mp4")

        # ── Step A: Concat + scale clips ──────────────────────────────
        logger.info("Step A: Concatenating and scaling clips to 9:16...")
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", clip_list_path,
            "-t", str(audio_duration),
            "-vf", (
                f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}"
                f":force_original_aspect_ratio=increase,"
                f"crop={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT},"
                f"setsar=1,fps={self.FPS}"
            ),
            "-c:v", "libx264", "-preset", "fast",
            "-b:v", self.VIDEO_BITRATE,
            "-an",
            temp_path
        ]
        result = subprocess.run(cmd_concat, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Concat failed: {result.stderr[-500:]}")
            return ""
        logger.info("Clips concatenated successfully")

        # ── Step B: Add audio + subtitles ─────────────────────────────
        logger.info("Step B: Adding audio + subtitles...")
        subtitle_filter = ""
        if srt_path and os.path.exists(srt_path):
            abs_srt = os.path.abspath(srt_path)
            subtitle_filter = (
                f",subtitles='{abs_srt}':force_style='{self.CAPTION_STYLE}'"
            )

        cmd_final = [
            "ffmpeg", "-y",
            "-i", temp_path,
            "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast",
            "-b:v", self.VIDEO_BITRATE,
            "-c:a", "aac", "-b:a", self.AUDIO_BITRATE,
            "-shortest",
        ]
        if subtitle_filter:
            cmd_final += [
                "-vf",
                f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}{subtitle_filter}"
            ]
        cmd_final.append(output_path)

        result = subprocess.run(cmd_final, capture_output=True, text=True)
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if result.returncode != 0:
            logger.error(f"Final render failed: {result.stderr[-500:]}")
            return ""

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Video rendered: {output_path} ({size_mb:.1f} MB)")
            return output_path

        return ""
