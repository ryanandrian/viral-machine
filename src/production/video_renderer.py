"""
Video Renderer — FFmpeg pipeline untuk render video final 9:16.
Fase 6C s6c3 upgrade:
  - Karaoke ASS caption: kata aktif kuning, kata lain putih (ElevenLabs ~98%)
  - Caption style dari tenant_configs.caption_style — multi-tenant configurable
  - Fallback SRT estimasi jika word timestamps tidak tersedia
  - Fix: fallback full_script cover 8 section (bukan 5 section lama)
"""

import json
import os
import subprocess
import time
from loguru import logger
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig

load_dotenv()

# Default caption style — override via tenant_configs.caption_style
DEFAULT_CAPTION_STYLE = {
    "active_word_color":   "#FFD700",  # Kuning — kata yang sedang diucapkan
    "inactive_word_color": "#FFFFFF",  # Putih — kata lain
    "font_size":           14,
    "max_words_per_line":  4,
    "max_lines":           2,
    "margin_v":            150,
    "bold_keywords":       True,
}


def _hex_to_ass_color(hex_color: str) -> str:
    """
    Konversi hex color (#RRGGBB) ke format ASS (&HBBGGRR&).
    ASS menggunakan format BGR bukan RGB.
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
        return f"&H00{b}{g}{r}&"
    return "&H00FFFFFF&"  # fallback putih


class VideoRenderer:
    """
    FFmpeg pipeline: clips + audio + subtitle → MP4 1080x1920.
    """

    OUTPUT_WIDTH  = 1080
    OUTPUT_HEIGHT = 1920
    FPS           = 30
    VIDEO_BITRATE = "4000k"
    AUDIO_BITRATE = "192k"

    # SRT fallback style — dipakai jika tidak ada word timestamps
    SRT_CAPTION_STYLE = (
        "FontName=Arial,"
        "FontSize=14,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H80000000,"
        "Outline=2,"
        "Shadow=1,"
        "MarginV=150,"
        "Alignment=2,"
        "WrapStyle=1"
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

    def _load_caption_style(self, tenant_config: TenantConfig) -> dict:
        """Load caption style dari Supabase tenant_configs. Fallback ke default."""
        try:
            from src.config.tenant_config import load_tenant_config
            rc = load_tenant_config(tenant_config.tenant_id)
            if rc.caption_style and isinstance(rc.caption_style, dict):
                style = DEFAULT_CAPTION_STYLE.copy()
                style.update(rc.caption_style)
                return style
        except Exception:
            pass
        return DEFAULT_CAPTION_STYLE.copy()

    def _create_clip_list(
        self,
        clips: list,
        target_duration: float,
        output_dir: str,
        clip_durations: list[float] | None = None,
    ) -> str:
        """
        Fase 6C s6c1+s6c2: durasi per clip presisi, tidak ada loop/repeat.
        """
        list_path = os.path.join(output_dir, "clip_list.txt")
        n         = len(clips)
        entries   = []

        if clip_durations and len(clip_durations) == n:
            total_raw = sum(clip_durations)
            scale     = target_duration / total_raw if total_raw > 0 else 1.0
            durations = [round(d * scale, 4) for d in clip_durations[:-1]]
            durations.append(round(target_duration - sum(durations), 4))
            mode = "section-synced"
        else:
            dur_each  = round(target_duration / n, 4)
            durations = [dur_each] * (n - 1)
            durations.append(round(target_duration - sum(durations), 4))
            mode = "equal-split"

        for clip, dur in zip(clips, durations):
            abs_path = os.path.abspath(clip)
            entries.append(f"file '{abs_path}'\n")
            entries.append(f"duration {dur}\n")

        with open(list_path, "w") as f:
            f.writelines(entries)

        logger.info(
            f"[Renderer] clip_list ({mode}): {n} clips = {sum(durations):.3f}s"
            f" (target: {target_duration:.3f}s) — no repeat"
        )
        return list_path

    def _generate_karaoke_ass(
        self,
        word_timestamps: list[dict],
        output_dir: str,
        style: dict,
    ) -> str:
        """
        Karaoke ASS caption — fixed line group, bukan sliding window.

        Algoritma:
        1. Grup kata ke baris fixed (max_words_per_line kata/baris)
        2. Setiap kata dalam baris → 1 ASS event yang tampilkan SELURUH baris
           dengan hanya kata aktif berwarna kuning
        3. Baris TIDAK berubah sampai semua kata dalam baris selesai diucapkan
        4. Baris baru muncul saat kata pertama baris berikutnya mulai diucapkan
        """
        if not word_timestamps:
            return ""

        ass_path     = os.path.join(output_dir, "subtitles.ass")
        max_per_line = style.get("max_words_per_line", 3)
        font_size    = style.get("font_size", 68)
        margin_v     = style.get("margin_v", 320)
        active_color   = _hex_to_ass_color(style.get("active_word_color",   "#FFD700"))
        inactive_color = _hex_to_ass_color(style.get("inactive_word_color", "#FFFFFF"))
        active_size    = int(font_size * 1.12)

        def fmt_ass_time(seconds: float) -> str:
            h  = int(seconds // 3600)
            m  = int((seconds % 3600) // 60)
            s  = int(seconds % 60)
            cs = int((seconds % 1) * 100)
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

        # Step 1: Grup kata ke baris fixed
        n      = len(word_timestamps)
        groups = []
        for i in range(0, n, max_per_line):
            groups.append(word_timestamps[i:i + max_per_line])

        # ASS header
        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {self.OUTPUT_WIDTH}
PlayResY: {self.OUTPUT_HEIGHT}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []

        # Step 2: Generate ASS events per kata dalam setiap baris
        for group in groups:
            group_size = len(group)

            for active_idx, active_word_data in enumerate(group):
                word_start = active_word_data["start"]

                # End time = awal kata berikutnya dalam group (atau akhir kata ini)
                if active_idx < group_size - 1:
                    word_end = group[active_idx + 1]["start"]
                else:
                    # Kata terakhir dalam group: end = start kata pertama group berikutnya
                    # Atau end = end kata ini + sedikit padding
                    word_end = active_word_data["end"] + 0.05

                # Build satu baris: semua kata dalam group
                # hanya kata aktif yang kuning, sisanya putih
                parts = []
                for j, w in enumerate(group):
                    word_text = w["word"]
                    if j == active_idx:
                        parts.append(
                            f"{{\c{active_color}\fs{active_size}\b1}}{word_text}"
                            f"{{\c{inactive_color}\fs{font_size}\b1}}"
                        )
                    else:
                        parts.append(f"{{\c{inactive_color}\fs{font_size}\b1}}{word_text}")

                line_text = " ".join(parts)
                events.append(
                    f"Dialogue: 0,{fmt_ass_time(word_start)},{fmt_ass_time(word_end)},"
                    f"Default,,0,0,0,,{line_text}"
                )

        ass_content = ass_header + "\n".join(events)
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        logger.info(
            f"[Caption] Karaoke ASS (fixed-line): {len(groups)} baris, "
            f"{len(events)} events | "
            f"font={font_size} margin_v={margin_v} "
            f"words_per_line={max_per_line}"
        )
        return ass_path


        def fmt_ass_time(seconds: float) -> str:
            h   = int(seconds // 3600)
            m   = int((seconds % 3600) // 60)
            s   = int(seconds % 60)
            cs  = int((seconds % 1) * 100)  # centiseconds (ASS pakai H:MM:SS.cc)
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

        # ASS header
        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {self.OUTPUT_WIDTH}
PlayResY: {self.OUTPUT_HEIGHT}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        n = len(word_timestamps)

        for i, word_data in enumerate(word_timestamps):
            word_start = word_data["start"]
            word_end   = word_data["end"]

            # Tentukan window kata yang ditampilkan di baris
            # Ambil konteks: beberapa kata sebelum dan sesudah kata aktif
            half     = max_per_line // 2
            win_start = max(0, i - half)
            win_end   = min(n, win_start + max_per_line)
            if win_end - win_start < max_per_line:
                win_start = max(0, win_end - max_per_line)

            window = word_timestamps[win_start:win_end]

            # Build teks dengan color tag per kata
            parts = []
            for j, w in enumerate(window):
                global_idx = win_start + j
                word_text  = w["word"]
                if global_idx == i:
                    # Kata aktif — kuning, sedikit lebih besar
                    parts.append(
                        f"{{\\c{active_color}\\fs{active_size}}}{word_text}"
                        f"{{\\c{inactive_color}\\fs{font_size}}}"
                    )
                else:
                    parts.append(f"{{\\c{inactive_color}}}{word_text}")

            line_text = " ".join(parts)

            events.append(
                f"Dialogue: 0,{fmt_ass_time(word_start)},{fmt_ass_time(word_end)},"
                f"Default,,0,0,0,,{line_text}"
            )

        ass_content = ass_header + "\n".join(events)
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        logger.info(
            f"[Caption] Karaoke ASS: {len(events)} events → {ass_path} "
            f"(active={style.get('active_word_color')}, "
            f"inactive={style.get('inactive_word_color')})"
        )
        return ass_path

    def _generate_subtitles_estimated(
        self,
        script: dict,
        audio_duration: float,
        output_dir: str,
        words_per_segment: int = 4,
    ) -> str:
        """
        Fallback SRT: estimasi timing dari word count.
        Fix: cover 8 section (bukan 5 section lama).
        Akurasi ~60-70%.
        """
        srt_path    = os.path.join(output_dir, "subtitles.srt")

        # Cover 8 section — fix dari versi lama yang hanya 5 section
        full_script = script.get("full_script", "")
        if not full_script:
            sections = [
                "hook", "mystery_drop", "build_up", "pattern_interrupt",
                "core_facts", "curiosity_bridge", "climax", "cta"
            ]
            parts = [script.get(s, "").strip() for s in sections if script.get(s)]
            full_script = " ".join(parts)

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

        logger.warning(
            f"[Caption] SRT estimasi (fallback): {len(segments)} segments "
            f"— akurasi ~60-70%. Gunakan ElevenLabs untuk karaoke akurat."
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

        Caption mode (otomatis dipilih):
          - word_timestamps tersedia (ElevenLabs) → ASS karaoke (~98% akurasi)
          - word_timestamps kosong                → SRT estimasi (~60-70%)
        Caption style dibaca dari tenant_configs.caption_style — multi-tenant.
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
        section_durs   = script.get("section_durations", {})
        clip_durations = None
        if section_durs and len(section_durs) >= 6:
            sd        = section_durs
            hook      = float(sd.get("hook", 3))
            mystery   = float(sd.get("mystery_drop", 5))
            buildup   = float(sd.get("build_up", 12))
            interrupt = float(sd.get("pattern_interrupt", 2))
            core      = float(sd.get("core_facts", 15))
            bridge    = float(sd.get("curiosity_bridge", 3))
            climax    = float(sd.get("climax", 8))
            cta       = float(sd.get("cta", 3))
            clip_durations = [
                hook,
                mystery,
                buildup,
                round(interrupt + core / 2, 2),
                round(core / 2 + bridge, 2),
                round(climax + cta, 2),
            ]
            logger.info(f"[Renderer] section_durations: {clip_durations}")
        clip_list_path = self._create_clip_list(clips, audio_duration, output_dir, clip_durations)

        # Load caption style dari tenant_configs
        caption_style = self._load_caption_style(tenant_config)

        # Generate subtitle — pilih mode berdasarkan ketersediaan timestamps
        logger.info("Generating captions...")
        use_ass = False
        if word_timestamps and len(word_timestamps) > 0:
            logger.info(
                f"[Caption] Mode: KARAOKE ASS "
                f"({len(word_timestamps)} words, ~98% akurasi)"
            )
            sub_path = self._generate_karaoke_ass(
                word_timestamps, output_dir, caption_style
            )
            use_ass = True
        else:
            logger.warning(
                "[Caption] Mode: SRT estimasi (~60-70%) — "
                "aktifkan ElevenLabs untuk karaoke akurat"
            )
            sub_path = self._generate_subtitles_estimated(
                script, audio_duration, output_dir
            )
            use_ass = False

        timestamp   = int(time.time())
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir, f"video_{tenant_config.tenant_id}_{timestamp}.mp4"
        )
        temp_path = os.path.join(output_dir, f"temp_{timestamp}.mp4")

        # ── Step A: Concat + scale clips dengan crossfade transition ────
        logger.info("Step A: Concatenating clips with crossfade transition...")

        # Baca durasi per clip dari clip_list.txt
        clip_durations_actual = []
        try:
            with open(clip_list_path) as f:
                lines_cl = f.readlines()
            for cl_line in lines_cl:
                cl_line = cl_line.strip()
                if cl_line.startswith("duration"):
                    clip_durations_actual.append(float(cl_line.split()[1]))
        except Exception as e:
            logger.warning(f"[Renderer] Could not read clip durations: {e}")
            clip_durations_actual = [audio_duration / len(clips)] * len(clips)

        # Jika hanya 1 clip atau gagal baca durasi — fallback ke concat biasa
        if len(clips) < 2 or len(clip_durations_actual) != len(clips):
            logger.warning("[Renderer] Fallback to simple concat")
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
                "-an", temp_path
            ]
            result = subprocess.run(cmd_concat, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Concat failed: {result.stderr[-500:]}")
                return ""
        else:
            # Xfade crossfade 0.5 detik antar clip
            XFADE_DUR = 0.4  # detik crossfade
            XFADE_TRANSITION = "fade"

            # Build FFmpeg command dengan xfade filter chain
            cmd_xfade = ["ffmpeg", "-y"]

            # Input: setiap clip sebagai input terpisah
            for clip_path in clips:
                cmd_xfade += ["-i", str(clip_path)]

            # Scale filter untuk setiap input
            scale_filter = (
                f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}"
                f":force_original_aspect_ratio=increase,"
                f"crop={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT},"
                f"setsar=1,fps={self.FPS}"
            )

            # Build xfade filter chain
            filter_parts = []

            # Scale semua input dulu
            for idx in range(len(clips)):
                filter_parts.append(f"[{idx}:v]{scale_filter}[v{idx}]")

            # Chain xfade antar clip
            # offset = durasi_clip_sebelumnya - xfade_duration
            offset    = 0.0
            prev_label = "v0"
            for idx in range(1, len(clips)):
                offset += clip_durations_actual[idx-1] - XFADE_DUR
                offset  = max(0, round(offset, 3))
                if idx < len(clips) - 1:
                    out_label = f"xf{idx}"
                else:
                    out_label = "vout"
                filter_parts.append(
                    f"[{prev_label}][v{idx}]xfade=transition={XFADE_TRANSITION}"
                    f":duration={XFADE_DUR}:offset={offset}[{out_label}]"
                )
                prev_label = out_label

            filter_complex = ";".join(filter_parts)

            cmd_xfade += [
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-t", str(audio_duration),
                "-c:v", "libx264", "-preset", "fast",
                "-b:v", self.VIDEO_BITRATE,
                "-an", temp_path
            ]

            logger.info(
                f"[Renderer] Xfade: {len(clips)} clips, "
                f"{XFADE_DUR}s crossfade, transition={XFADE_TRANSITION}"
            )
            result = subprocess.run(cmd_xfade, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"[Renderer] Xfade failed — fallback to concat: {result.stderr[-300:]}")
                # Fallback ke concat biasa jika xfade gagal
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
                    "-an", temp_path
                ]
                result = subprocess.run(cmd_concat, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"Concat fallback failed: {result.stderr[-500:]}")
                    return ""

        logger.info("Clips concatenated successfully")


        # ── Step B: Add audio + subtitles ─────────────────────────────
        logger.info("Step B: Adding audio + captions...")

        subtitle_filter = ""
        if sub_path and os.path.exists(sub_path):
            abs_sub = os.path.abspath(sub_path)
            if use_ass:
                # ASS karaoke — gunakan filter 'ass='
                subtitle_filter = f",ass='{abs_sub}'"
            else:
                # SRT fallback — gunakan filter 'subtitles=' dengan force_style
                subtitle_filter = (
                    f",subtitles='{abs_sub}':force_style='{self.SRT_CAPTION_STYLE}'"
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

        if not os.path.exists(output_path):
            return ""

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        caption_mode = "karaoke ASS" if use_ass else "SRT estimasi"
        logger.info(
            f"Video rendered: {output_path} ({size_mb:.1f} MB) "
            f"| caption: {caption_mode}"
        )

        # ── s6c4: Music mixing (jika music_enabled) ────────────────
        try:
            from src.config.tenant_config import load_tenant_config
            rc = load_tenant_config(tenant_config.tenant_id)
            if getattr(rc, "music_enabled", False):
                output_path = self._mix_music(
                    video_path=output_path,
                    script=script,
                    niche=tenant_config.niche,
                    output_dir=output_dir,
                    audio_duration=audio_duration,
                )
        except Exception as e:
            logger.warning(f"[Renderer] Music mixing skipped: {e}")

        return output_path

    def _mix_music(
        self,
        video_path: str,
        script: dict,
        niche: str,
        output_dir: str,
        audio_duration: float,
    ) -> str:
        """
        Fase 6C s6c4: Mix background music ke video.
        Level: -18dB ducking — musik terdengar tapi tidak kalahkan narasi.
        """
        from src.providers.music.music_selector import select_and_download

        music_path = select_and_download(
            script=script,
            niche=niche,
            output_dir=output_dir,
            audio_duration=audio_duration,
        )

        if not music_path or not os.path.exists(music_path):
            logger.warning("[Renderer] Music tidak tersedia — video tanpa musik")
            return video_path

        mixed_path = video_path.replace(".mp4", "_music.mp4")

        # FFmpeg: mix narasi (stream 1) + musik -18dB (stream 2)
        # amix: input[0] = narasi penuh, input[1] = musik fade in/out
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex",
            (
                # Narasi: volume tetap
                "[0:a]volume=1.0[narasi];"
                # Musik: -18dB (≈12.5% volume), fade in 1s, fade out 2s
                f"[1:a]volume=0.125,"
                f"afade=t=in:st=0:d=1,"
                f"afade=t=out:st={max(0, audio_duration-2):.1f}:d=2,"
                f"atrim=0:{audio_duration:.1f}[musik];"
                # Mix keduanya
                "[narasi][musik]amix=inputs=2:duration=first[aout]"
            ),
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", self.AUDIO_BITRATE,
            "-shortest",
            mixed_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[Renderer] Music mix failed: {result.stderr[-300:]}")
            return video_path  # fallback ke video tanpa musik

        if os.path.exists(mixed_path):
            # Hapus video tanpa musik, ganti dengan yang sudah di-mix
            os.remove(video_path)
            os.rename(mixed_path, video_path)
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            logger.info(
                f"[Renderer] ✅ Music mixed: -18dB ducking "
                f"| {size_mb:.1f} MB"
            )

        return video_path
