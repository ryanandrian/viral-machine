"""
Video Renderer — FFmpeg pipeline untuk render video final 9:16.
Fase 6C s6c3 upgrade:
  - Karaoke ASS caption: kata aktif kuning, kata lain putih (ElevenLabs ~98%)
  - Caption style dari tenant_configs.caption_style — multi-tenant configurable
  - Fallback SRT estimasi jika word timestamps tidak tersedia
  - Fix: fallback full_script cover 8 section (bukan 5 section lama)
s88:
  - Font config-driven: font_name, outline_color, border_color, position_y_pct
  - Caption & hook style property lengkap untuk branding tenant
  - fonts table di Supabase untuk Admin Panel font management
"""

import json
import os
import subprocess
import time
from loguru import logger
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig

load_dotenv()

# Default caption style — override via tenant_configs.caption_style (partial override OK)
# position_y_pct: % dari atas layar (83% ≈ margin_v 326px untuk 1920px height)
# alignment: ASS alignment — 2=bottom-center, 5=mid-center, 8=top-center
DEFAULT_CAPTION_STYLE = {
    "font_name":            "Anton",
    "font_size":            68,
    "bold":                 True,
    "italic":               False,
    "active_word_color":    "#FFD700",   # Kuning — kata yang sedang diucapkan
    "inactive_word_color":  "#FFFFFF",   # Putih — kata lain
    "outline_color":        "#000000",   # Warna border teks
    "outline":              4,           # Ketebalan border
    "shadow":               2,           # Ukuran bayangan
    "position_y_pct":       83,          # % dari atas layar
    "alignment":            2,           # bottom-center
    "max_words_per_line":   3,
    "max_lines":            2,
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

    FONTS_DIR  = "/usr/local/share/fonts"
    # Map font_name → file name. Admin Panel tambah entry sini saat upload font baru.
    FONT_FILES = {
        "Anton": "Anton-Regular.ttf",
    }

    def _resolve_font_path(self, font_name: str) -> str:
        """Resolve font_name ke absolute path. Fallback ke Anton jika tidak ditemukan."""
        file_name = self.FONT_FILES.get(font_name, f"{font_name}-Regular.ttf")
        path = os.path.join(self.FONTS_DIR, file_name)
        if os.path.exists(path):
            return path
        fallback = os.path.join(self.FONTS_DIR, "Anton-Regular.ttf")
        logger.warning(f"[Font] '{font_name}' tidak ditemukan di {path}, fallback ke Anton")
        return fallback

    def _build_srt_style(self, caption_style: dict) -> str:
        """Build force_style string untuk SRT fallback dari caption_style."""
        font_name   = caption_style.get("font_name", "Anton")
        font_size   = caption_style.get("font_size", 68)
        bold        = 1 if caption_style.get("bold", True) else 0
        pos_y_pct   = caption_style.get("position_y_pct", 83)
        margin_v    = int(self.OUTPUT_HEIGHT * (1 - pos_y_pct / 100))
        outline_c   = _hex_to_ass_color(caption_style.get("outline_color", "#000000"))
        return (
            f"FontName={font_name},"
            f"FontSize={font_size},"
            f"Bold={bold},"
            "PrimaryColour=&H00FFFFFF,"
            f"OutlineColour={outline_c},"
            "BackColour=&H80000000,"
            "Outline=2,"
            "Shadow=1,"
            f"MarginV={margin_v},"
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

    def _load_hook_title_style(self, tenant_config) -> dict:
        """Load hook title style dari Supabase. Fallback ke default."""
        DEFAULT = {
            "enabled":          True,
            "font_name":        "Anton",
            "font_size":        58,
            "bold":             True,
            "italic":           False,
            "font_color":       "#FFD700",
            "border_color":     "#000000",
            "outline":          4,
            "shadow":           3,
            "position_y_pct":   15,
            "alignment":        "center",
            "max_chars_per_line": 25,
        }
        try:
            from src.config.tenant_config import load_tenant_config
            rc = load_tenant_config(tenant_config.tenant_id)
            if rc.hook_title_style and isinstance(rc.hook_title_style, dict):
                style = DEFAULT.copy()
                style.update(rc.hook_title_style)
                return style
        except Exception:
            pass
        return DEFAULT.copy()

    def _add_hook_title(self, clip_path, hook_text: str, style: dict, output_dir: str):
        """s72: Overlay hook title ke clip 1 via FFmpeg drawtext.
        Hook text ditampilkan penuh (tidak dipotong), font Anton, warna kuning.
        Hanya clip 1. Returns path clip baru atau clip asli jika gagal.
        """
        if not hook_text or not style.get("enabled", True):
            return clip_path
        try:
            import textwrap, os
            font_path    = self._resolve_font_path(style.get("font_name", "Anton"))
            font_size    = style.get("font_size", 58)
            font_color   = style.get("font_color", "#FFD700").lstrip("#")
            border_color = style.get("border_color", "#000000").lstrip("#")
            outline      = style.get("outline", 4)
            shadow       = style.get("shadow", 3)
            y_pct        = style.get("position_y_pct", 15) / 100.0
            max_chars    = style.get("max_chars_per_line", 25)

            # Bersihkan karakter problematik FFmpeg drawtext
            clean = hook_text
            clean = clean.replace("\\", "")
            clean = clean.replace("'", "")
            clean = clean.replace(":", " -")
            clean = clean.replace("%", " pct")

            lines = textwrap.wrap(clean, width=max_chars)
            if not lines:
                return clip_path

            out_path    = str(clip_path).replace(".mp4", "_titled.mp4")
            line_height = font_size + 10
            y_start     = int(self.OUTPUT_HEIGHT * y_pct)

            filters = []
            for i, line in enumerate(lines):
                y_pos = y_start + i * line_height
                dt = (
                    "drawtext"
                    f"=fontfile={font_path}"
                    f":text='{line}'"
                    f":fontcolor={font_color}"
                    f":fontsize={font_size}"
                    ":x=(w-text_w)/2"
                    f":y={y_pos}"
                    f":borderw={outline}"
                    f":bordercolor={border_color}@0.80"
                    f":shadowx={shadow}"
                    f":shadowy={shadow}"
                    ":shadowcolor=000000@0.80"
                )
                filters.append(dt)

            vf = ",".join(filters)
            cmd = [
                "ffmpeg", "-y", "-i", str(clip_path),
                "-vf", vf,
                "-c:v", "libx264", "-preset", "fast",
                "-b:v", self.VIDEO_BITRATE,
                "-an", out_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(out_path):
                logger.info(
                    f"[Renderer] s72 Hook title: {len(lines)} baris | y={y_start}"
                )
                # s72e: Extract frame dari titled clip → update hook_frame_img.jpg
                # Agar thumbnail YouTube sama persis dengan clip 1 (ada hook title)
                try:
                    from pathlib import Path as _Path
                    thumb_dst = str(_Path(clip_path).parent / "hook_frame_img.jpg")
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", out_path,
                         "-frames:v", "1", "-q:v", "2", thumb_dst],
                        capture_output=True
                    )
                    logger.info(f"[Renderer] s72e Thumbnail frame extracted: {thumb_dst}")
                except Exception as _e:
                    logger.warning(f"[Renderer] s72e Thumbnail extract gagal (non-critical): {_e}")
                return out_path
            else:
                logger.warning(
                    f"[Renderer] Hook title gagal: {result.stderr[-200:]}"
                    " — pakai clip original"
                )
                return clip_path
        except Exception as e:
            logger.warning(f"[Renderer] Hook title error: {e} — pakai clip original")
            return clip_path

    def _create_clip_list(
        self,
        clips: list,
        target_duration: float,
        output_dir: str,
        clip_durations: list[float] | None = None,
        run_id: str = "",
    ) -> str:
        """
        Fase 6C s6c1+s6c2: durasi per clip presisi, tidak ada loop/repeat.
        """
        fname     = f"clip_list_{run_id}.txt" if run_id else "clip_list.txt"
        list_path = os.path.join(output_dir, fname)
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
        run_id: str = "",
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

        fname    = f"subtitles_{run_id}.ass" if run_id else "subtitles.ass"
        ass_path = os.path.join(output_dir, fname)
        max_per_line   = style.get("max_words_per_line", 3)
        font_name      = style.get("font_name", "Anton")
        font_size      = style.get("font_size", 68)
        bold           = 1 if style.get("bold", True) else 0
        italic         = 1 if style.get("italic", False) else 0
        outline        = style.get("outline", 4)
        shadow         = style.get("shadow", 2)
        alignment      = style.get("alignment", 2)
        outline_color  = _hex_to_ass_color(style.get("outline_color", "#000000"))
        pos_y_pct      = style.get("position_y_pct", 83)
        margin_v       = int(self.OUTPUT_HEIGHT * (1 - pos_y_pct / 100))
        active_color   = _hex_to_ass_color(style.get("active_word_color",   "#FFD700"))
        inactive_color = _hex_to_ass_color(style.get("inactive_word_color", "#FFFFFF"))
        active_size    = int(font_size * 1.12)

        def fmt_ass_time(seconds: float) -> str:
            h  = int(seconds // 3600)
            m  = int((seconds % 3600) // 60)
            s  = int(seconds % 60)
            cs = int((seconds % 1) * 100)
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

        # Step 1: Smart grouping berbasis tanda baca (s71d)
        # Timing per kata TIDAK berubah — hanya pengelompokan tampilan
        # Aturan:
        #   HARD BREAK: kata berakhir . ! ? → mulai grup baru setelah kata ini
        #   SOFT BREAK: kata berakhir , ; : → tutup grup jika sudah >= 2 kata
        #   HARD LIMIT: max_per_line kata per grup (batas keras)
        HARD_END  = set("!?.")     # titik, seru, tanya → akhir kalimat
        SOFT_END  = set(",;:")     # koma, titik koma, titik dua → jeda klausa
        n         = len(word_timestamps)
        groups    = []
        current   = []

        for i, wt in enumerate(word_timestamps):
            current.append(wt)
            word_text  = wt.get("word", "")
            last_char  = word_text[-1] if word_text else ""
            is_last    = (i == n - 1)
            hard_break = last_char in HARD_END
            soft_break = last_char in SOFT_END and len(current) >= 2
            max_hit    = len(current) >= max_per_line

            if hard_break or soft_break or max_hit or is_last:
                groups.append(current)
                current = []

        # Kalau ada sisa (seharusnya tidak terjadi tapi safety net)
        if current:
            groups.append(current)


        # ASS header
        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {self.OUTPUT_WIDTH}
PlayResY: {self.OUTPUT_HEIGHT}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,{outline_color},&H80000000,{bold},{italic},0,0,100,100,0,0,1,{outline},{shadow},{alignment},10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        b_tag = "\\b1" if bold else ""

        # Step 2: Generate ASS events per kata dalam setiap baris
        for group in groups:
            group_size = len(group)

            for active_idx, active_word_data in enumerate(group):
                word_start = active_word_data["start"]

                # End time = awal kata berikutnya dalam group (atau akhir kata ini)
                if active_idx < group_size - 1:
                    word_end = group[active_idx + 1]["start"]
                else:
                    word_end = active_word_data["end"] + 0.05

                # Build satu baris: semua kata dalam group
                # hanya kata aktif yang kuning, sisanya putih
                parts = []
                for j, w in enumerate(group):
                    word_text = w["word"]
                    if j == active_idx:
                        parts.append(
                            f"{{\\c{active_color}\\fs{active_size}{b_tag}}}{word_text}"
                            f"{{\\c{inactive_color}\\fs{font_size}{b_tag}}}"
                        )
                    else:
                        parts.append(f"{{\\c{inactive_color}\\fs{font_size}{b_tag}}}{word_text}")

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
            f"font={font_name} size={font_size} pos_y={pos_y_pct}% "
            f"margin_v={margin_v} words_per_line={max_per_line}"
        )
        return ass_path

    def _generate_subtitles_estimated(
        self,
        script: dict,
        audio_duration: float,
        output_dir: str,
        words_per_segment: int = 4,
        run_id: str = "",
    ) -> str:
        """
        Fallback SRT: estimasi timing dari word count.
        Fix: cover 8 section (bukan 5 section lama).
        Akurasi ~60-70%.
        """
        fname    = f"subtitles_{run_id}.srt" if run_id else "subtitles.srt"
        srt_path = os.path.join(output_dir, fname)

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
        run_id: str = "",
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

        # ── s72b: trailing_silence — baca dari Supabase config ──
        try:
            from src.config.tenant_config import load_tenant_config
            rc = load_tenant_config(tenant_config.tenant_id)
            trailing_silence = float(getattr(rc, "trailing_silence", 2.5))
        except Exception:
            trailing_silence = 2.5
        total_duration = audio_duration + trailing_silence
        logger.info(
            f"[Renderer] trailing_silence={trailing_silence}s "
            f"| total_duration={total_duration:.1f}s"
        )

        # ── s72: Hook title overlay pada clip 1 ─────────────────
        hook_title_style = self._load_hook_title_style(tenant_config)
        hook_text_raw    = script.get("hook", "")
        if clips and hook_text_raw and hook_title_style.get("enabled", True):
            titled_clip_0 = self._add_hook_title(
                clips[0], hook_text_raw, hook_title_style, output_dir
            )
            clips = [titled_clip_0] + list(clips[1:])

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
        clip_list_path = self._create_clip_list(clips, audio_duration, output_dir, clip_durations, run_id=run_id)

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
                word_timestamps, output_dir, caption_style, run_id=run_id
            )
            use_ass = True
        else:
            logger.warning(
                "[Caption] Mode: SRT estimasi (~60-70%) — "
                "aktifkan ElevenLabs untuk karaoke akurat"
            )
            sub_path = self._generate_subtitles_estimated(
                script, audio_duration, output_dir, run_id=run_id
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
                srt_style = self._build_srt_style(caption_style)
                subtitle_filter = (
                    f",subtitles='{abs_sub}':force_style='{srt_style}'"
                )

        # s72b: tpad freeze frame terakhir + apad silence = trailing_silence detik
        # -t explicit agar durasi tepat, bukan -shortest yang potong di video
        tpad_filter = f"tpad=stop_mode=clone:stop_duration={trailing_silence}"
        cmd_final = [
            "ffmpeg", "-y",
            "-i", temp_path,
            "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast",
            "-b:v", self.VIDEO_BITRATE,
            "-c:a", "aac", "-b:a", self.AUDIO_BITRATE,
            "-af", f"apad=pad_dur={trailing_silence}",
            "-t", str(total_duration),
        ]
        if subtitle_filter:
            cmd_final += [
                "-vf",
                f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT},{tpad_filter}{subtitle_filter}"
            ]
        else:
            cmd_final += ["-vf", tpad_filter]
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
                    music_volume=float(getattr(rc, "music_volume", 0.10)),
                )
        except Exception as e:
            logger.warning(f"[Renderer] Music mixing skipped: {e}")

        # ── s83: Loop Ending (jika enabled) ──────────────────────────
        try:
            from src.config.tenant_config import load_tenant_config
            rc_loop = load_tenant_config(tenant_config.tenant_id)
            if getattr(rc_loop, "loop_ending_enabled", True):
                loop_dur = float(getattr(rc_loop, "loop_ending_duration", 1.5) or 1.5)
                output_path = self._add_loop_ending(output_path, loop_dur, output_dir)
        except Exception as e:
            logger.warning(f"[Renderer] Loop ending skipped: {e}")

        return output_path

    def _add_loop_ending(
        self,
        video_path: str,
        loop_duration: float,
        output_dir: str,
    ) -> str:
        """
        s83: Tambah loop ending — ekstrak N detik pertama video, crossfade di akhir.
        Membuat ilusi seamless loop → penonton tidak sadar video restart → watch time naik.

        Flow:
          1. ffprobe → dapat durasi video utama
          2. Extract loop_duration detik pertama (video only, re-encode)
          3. xfade fade 0.5s antara main video dan loop clip
          4. Return path video yang sudah di-loop
        """
        import json as _json

        # Step 1: Get main video duration
        probe_cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path,
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if probe_result.returncode != 0:
            logger.warning("[LoopEnding] ffprobe gagal — skip loop ending")
            return video_path

        try:
            main_duration = float(_json.loads(probe_result.stdout)["format"]["duration"])
        except (KeyError, ValueError, _json.JSONDecodeError) as e:
            logger.warning(f"[LoopEnding] Gagal parse durasi video: {e}")
            return video_path

        # Step 2: Extract loop clip (video only, tanpa audio)
        loop_clip_path = os.path.join(output_dir, "_loop_clip.mp4")
        cmd_extract = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-t", str(loop_duration),
            "-vf", f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}",
            "-c:v", "libx264", "-preset", "fast",
            "-b:v", self.VIDEO_BITRATE,
            "-an",
            loop_clip_path,
        ]
        r_extract = subprocess.run(cmd_extract, capture_output=True, text=True)
        if r_extract.returncode != 0 or not os.path.exists(loop_clip_path):
            logger.warning(f"[LoopEnding] Gagal extract loop clip: {r_extract.stderr[-200:]}")
            return video_path

        # Step 3: xfade — offset = main_duration - xfade_duration
        xfade_dur    = 0.5
        offset       = max(0.0, main_duration - xfade_dur)
        new_duration = round(main_duration + loop_duration - xfade_dur, 3)

        # Naming: strip semua suffix dulu agar tidak double-suffix
        base = video_path
        for suffix in ("_loop.mp4", "_music.mp4"):
            if base.endswith(suffix):
                base = base[: -len(suffix)] + ".mp4"
        output_loop_path = base.replace(".mp4", "_loop.mp4")

        cmd_xfade = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", loop_clip_path,
            "-filter_complex",
            (
                # Video: xfade antara main dan loop clip
                f"[0:v][1:v]xfade=transition=fade:"
                f"duration={xfade_dur}:offset={offset:.3f}[vout];"
                # Audio: pad silence agar cover durasi baru (loop_duration extra)
                f"[0:a]apad=pad_dur={loop_duration}[aout]"
            ),
            "-map", "[vout]",
            "-map", "[aout]",
            "-t", str(new_duration),   # cut tepat — tanpa -shortest
            "-c:v", "libx264", "-preset", "fast",
            "-b:v", self.VIDEO_BITRATE,
            "-c:a", "aac", "-b:a", self.AUDIO_BITRATE,
            output_loop_path,
        ]
        r_xfade = subprocess.run(cmd_xfade, capture_output=True, text=True)

        # Cleanup loop clip
        if os.path.exists(loop_clip_path):
            os.remove(loop_clip_path)

        if r_xfade.returncode != 0 or not os.path.exists(output_loop_path):
            logger.warning(f"[LoopEnding] xfade gagal: {r_xfade.stderr[-300:]}")
            return video_path

        # Step 4: Replace original dengan loop version
        os.remove(video_path)
        os.rename(output_loop_path, video_path)
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        logger.info(
            f"[LoopEnding] ✅ Loop ending added: +{loop_duration}s "
            f"| xfade={xfade_dur}s | {size_mb:.1f} MB"
        )
        return video_path

    def _mix_music(
        self,
        video_path: str,
        script: dict,
        niche: str,
        output_dir: str,
        audio_duration: float,
        music_volume: float = 0.10,
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
                f"[1:a]volume={music_volume:.3f},"
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
