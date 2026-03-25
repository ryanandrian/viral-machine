import os
import time
import subprocess
from loguru import logger
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, system_config

load_dotenv()

class VideoRenderer:
    """
    Menggabungkan audio + video clips + subtitle menjadi MP4 final 9:16.
    Menggunakan FFmpeg untuk semua operasi — zero cost, maximum control.
    Output: 1080x1920, H.264, AAC, siap upload ke semua platform.
    """

    OUTPUT_WIDTH = 1080
    OUTPUT_HEIGHT = 1920
    FPS = 30
    VIDEO_BITRATE = "4000k"
    AUDIO_BITRATE = "192k"

    def _get_audio_duration(self, audio_path: str) -> float:
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            import json
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except Exception as e:
            logger.error(f"Could not get audio duration: {e}")
            return 58.0

    def _get_video_duration(self, video_path: str) -> float:
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            import json
            data = json.loads(result.stdout)
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    return float(stream.get("duration", 5.0))
            return 5.0
        except Exception:
            return 5.0

    def _create_clip_list(self, clips: list, target_duration: float, output_dir: str) -> str:
        list_path = os.path.join(output_dir, "clip_list.txt")
        total = 0.0
        entries = []
        idx = 0
        while total < target_duration:
            clip = clips[idx % len(clips)]
            dur = self._get_video_duration(clip)
            entries.append(f"file '{os.path.abspath(clip)}'\n")
            total += dur
            idx += 1
        with open(list_path, "w") as f:
            f.writelines(entries)
        return list_path

    def _generate_subtitles(self, script: dict, audio_duration: float, output_dir: str) -> str:
        srt_path = os.path.join(output_dir, "subtitles.srt")
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
        total_words = len(words)
        if total_words == 0:
            return ""

        words_per_segment = 7
        segments = []
        for i in range(0, total_words, words_per_segment):
            segments.append(" ".join(words[i:i + words_per_segment]))

        segment_duration = audio_duration / len(segments)

        def fmt_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            ms = int((seconds % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        srt_content = []
        for i, segment in enumerate(segments):
            start = i * segment_duration
            end = (i + 1) * segment_duration
            srt_content.append(f"{i+1}")
            srt_content.append(f"{fmt_time(start)} --> {fmt_time(end)}")
            srt_content.append(segment)
            srt_content.append("")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))

        logger.info(f"Subtitles: {len(segments)} segments, {srt_path}")
        return srt_path

    def render(self, script: dict, audio_path: str, clips: list,
               tenant_config: TenantConfig, output_dir: str = "logs") -> str:
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

        logger.info("Generating subtitles...")
        srt_path = self._generate_subtitles(script, audio_duration, output_dir)

        timestamp = int(time.time())
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"video_{tenant_config.tenant_id}_{timestamp}.mp4")
        temp_path = os.path.join(output_dir, f"temp_{timestamp}.mp4")

        logger.info("Step A: Concatenating and scaling clips to 9:16...")
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", clip_list_path,
            "-t", str(audio_duration),
            "-vf", (
                f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:force_original_aspect_ratio=increase,"
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

        logger.info("Step B: Adding audio + subtitles...")
        subtitle_filter = ""
        if srt_path and os.path.exists(srt_path):
            abs_srt = os.path.abspath(srt_path)
            subtitle_filter = (
                f",subtitles='{abs_srt}':force_style='"
                f"FontName=Arial,FontSize=18,Bold=1,"
                f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                f"BackColour=&H80000000,Outline=2,Shadow=1,"
                f"MarginV=80,Alignment=2'"
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
            cmd_final += ["-vf", f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}{subtitle_filter}"]

        cmd_final.append(output_path)

        result = subprocess.run(cmd_final, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Final render failed: {result.stderr[-500:]}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return ""

        if os.path.exists(temp_path):
            os.remove(temp_path)

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Video rendered: {output_path} ({size_mb:.1f} MB)")
            return output_path

        return ""


if __name__ == "__main__":
    from src.intelligence.trend_radar import TrendRadar
    from src.intelligence.niche_selector import NicheSelector
    from src.intelligence.script_engine import ScriptEngine
    from src.intelligence.hook_optimizer import HookOptimizer
    from src.production.tts_engine import TTSEngine
    from src.production.visual_assembler import VisualAssembler

    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")

    logger.info("Step 1-4: Intelligence pipeline...")
    signals = TrendRadar().scan(tenant)
    topics = NicheSelector().select(signals, tenant)
    scripts = ScriptEngine().generate_batch(topics, tenant, count=1)
    optimized = HookOptimizer().optimize_batch(scripts, tenant)
    script = optimized[0]

    logger.info("Step 5: TTS audio...")
    audio_path = TTSEngine().generate(script, tenant)

    logger.info("Step 6: Visual assembly...")
    clips = VisualAssembler().assemble(script, tenant)

    logger.info("Step 7: Rendering final video...")
    renderer = VideoRenderer()
    video_path = renderer.render(script, audio_path, clips, tenant)

    if video_path:
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"\n{'='*60}")
        print(f"VIDEO RENDER COMPLETE")
        print(f"{'='*60}")
        print(f"Title   : {script.get('title', '')}")
        print(f"Hook    : {script.get('hook', '')}")
        print(f"Video   : {video_path}")
        print(f"Size    : {size_mb:.1f} MB")
        print(f"Format  : 1080x1920 H.264 AAC")
        print(f"{'='*60}")
        print(f"\nReady to upload to YouTube Shorts!")
    else:
        print("Video rendering failed")
