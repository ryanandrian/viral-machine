"""
Visual Assembler — selector provider visual (GENERATOR AI saja).
v2:
  - Visual mode: 'ai_image:*' | 'ai_video:*' (stock footage Pexels = fosil v1, dibuang 2026-06-24)
  - NO-FALLBACK (§3.8): provider pilihan channel = satu-satunya sumber; gagal → [] → pipeline
    raise → notify → retry manual. Tak ada fallback diam-diam (Pexels/cache/black screen).
  - Real-time reporting setiap kondisi khusus
"""

import asyncio
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

from src.intelligence.config import TenantConfig

load_dotenv()


class VisualAssembler:
    """Selector provider visual (generator AI). NO-FALLBACK: gagal = gagal jujur (return [])."""

    # [ERROR-MGMT §8e 2026-08-04] Sebab kegagalan visual TERAKHIR, apa adanya dari penyedia.
    #
    # KENAPA ADA: jalur visual dulu MEMBUANG sebabnya. Ketiga penangkap di kelas ini hanya menulis ke
    # worker.log lalu `return []`, sehingga pemanggil cuma tahu "daftar klip kosong" dan run tercatat
    # dengan kalimat generik "Visual assembly failed — no clips downloaded". Bukti nyata (worker.log
    # 2026-07-14 19:54/19:56/19:57, 6 kejadian): penyedia video berkata TERANG
    #   fal submit HTTP 403: {"detail":"User is locked. Reason: Exhausted balance.
    #                          Top up your balance at fal.ai/dashboard/billing."}
    # — sebab yang tenant bisa selesaikan dalam 2 menit — tapi yang tersimpan di `production_runs`
    # (dan karenanya yang DILIHAT tenant di layar run) hanya "no clips downloaded". Tiga run terbakar
    # 55-85 detik masing-masing tanpa tenant pernah tahu apa yang harus ia perbuat.
    #
    # Pola ini MENIRU `tts_engine.last_error_class` & `niche_selector.last_error*` yang sudah dipakai
    # jalur suara/naskah — bukan mekanisme baru.
    #
    # SENGAJA hanya TEKS, bukan `error_class`: memberi kelas berarti kelas seperti QUOTA_EXHAUSTED
    # masuk `FAST_FAIL` → channel direm setelah 1 kegagalan (bukan 3). Itu perilaku-saat-gagal =
    # KEPUTUSAN PRODUK (CLAUDE.md §0.6) dan aplikasi ini sudah punya tenant berbayar. Menunggu ketok
    # owner; celahnya tercatat di AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8e.
    #
    # Atribut KELAS (bukan `__init__`) agar cara objek ini dibuat tidak berubah sama sekali.
    last_error: str | None = None

    # [§8f 2026-08-05] Sebab GAGALNYA FRAME PERTAMA (hook-frame), bila terjadi.
    #
    # Frame pertama = penentu penonton berhenti menggulir. Bila pembuatannya gagal, sistem MENERUSKAN
    # dengan klip biasa — video tetap terbit dengan pembuka yang lebih lemah, dan selama ini **nol
    # notifikasi**: hanya `logger.warning` yang tenggelam di worker.log. Terukur 05-Agu: **4 gagal dari
    # 181 percobaan (2,2%)**, empat sebab berbeda, dan **dua di antaranya kode kita sendiri**
    # (berkas hook_frame_img.jpg tak ada · FFmpeg image-to-video gagal).
    #
    # Ini melaksanakan §0.6 yang SUDAH diketok owner ("kegagalan komponen = notifikasi, HARAM fallback
    # senyap") — BUKAN keputusan baru: yang berubah hanya kegagalannya jadi TERLIHAT.
    # SENGAJA tidak menghentikan produksi & tidak mengirim alarm ke tenant: menghentikan video karena
    # frame pembuka = perilaku-saat-gagal (butuh ketok), dan alarm untuk 2,2% kejadian = berisik.
    # Cukup: tercatat, terbawa ke laporan run, terlihat saat diagnosa.
    hook_frame_error: str | None = None

    def assemble(
        self,
        script: dict,
        tenant_config: TenantConfig,
        output_dir: str = "logs",
        audio_duration: float = 0.0,
    ) -> list[str]:
        """
        Generate video clips dari provider GENERATOR AI pilihan channel.

        NO-FALLBACK (§3.8): provider channel (visual_mode) = satu-satunya sumber.
        Gagal → return [] → pipeline raise exception → Telegram notify → user retry manual.

        Returns:
            List path clip (string).
        """
        # [§8e] Kosongkan sebab lama SEBELUM mencoba. `Pipeline()` memang dibuat baru tiap run
        # (3 titik di producer.py) sehingga kebocoran antar-run tidak mungkin hari ini — pagar ini
        # untuk hari ketika seseorang memakai ulang objeknya: sebab run LAMA yang menempel di pesan
        # run BARU adalah bug yang jauh lebih menyesatkan daripada tanpa sebab sama sekali.
        self.last_error = None
        self.hook_frame_error = None      # [§8f] idem: sebab run LAMA tak boleh menempel di run BARU

        run_config  = self._load_run_config(tenant_config)
        visual_mode = run_config.get("visual_mode") or ""
        self._current_audio_duration = audio_duration
        is_dev      = run_config.get("is_developer", False)

        logger.info(f"[VisualAssembler] mode={visual_mode}{' [DEVELOPER]' if is_dev else ''}")

        clips_dir = Path(output_dir) / f"clips_{tenant_config.tenant_id}"

        # Provider GENERATOR AI pilihan channel — satu-satunya sumber clips.
        # NO-FALLBACK: gagal → return [] → pipeline raise → Telegram notify → user retry manual.
        clips = self._try_provider(
            visual_mode=visual_mode,
            script=script,
            tenant_config=tenant_config,
            clips_dir=clips_dir,
            run_config=run_config,
        )

        paths = [str(c) for c in clips]
        logger.info(f"[VisualAssembler] Assembly complete: {len(paths)}/6 clips")
        return paths

    # ──────────────────────────────────────────────
    # Provider handlers
    # ──────────────────────────────────────────────

    def _try_provider(
        self,
        visual_mode: str,
        script: dict,
        tenant_config: TenantConfig,
        clips_dir: Path,
        run_config: dict,
    ) -> list[Path]:
        """Coba provider GENERATOR AI sesuai visual_mode (no-fallback)."""
        try:
            if visual_mode.startswith("ai_image:"):
                return self._try_ai_image(
                    visual_mode, script, tenant_config, clips_dir, run_config
                )
            elif visual_mode.startswith("ai_video:"):
                return self._try_ai_video(
                    visual_mode, script, tenant_config, clips_dir, run_config
                )
            else:
                logger.warning(
                    f"[VisualAssembler] visual_mode '{visual_mode}' tak dikenal — "
                    f"gagal jujur (no-fallback)"
                )
                self.last_error = (f"mode visual '{visual_mode}' tidak dikenali sistem — "
                                   f"periksa setelan Visual di channel")
                return []
        except Exception as e:
            logger.error(f"[VisualAssembler] Provider error: {e}")
            self.last_error = str(e)   # [§8e] jangan dibuang — ini satu-satunya sebab yg tenant punya
            return []

    def _compute_clip_durations(self, script: dict, n_clips: int = 6, audio_duration: float = 0.0) -> list[float]:
        """
        Fase 6C s6c2: hitung durasi per clip dari section_durations script.
        Mapping 6 clips ke 8 sections — sections pendek digabung.
        """
        sd = script.get("section_durations", {})
        if not sd or len(sd) < 6:
            return []  # Fallback ke pembagian rata di renderer

        hook      = float(sd.get("hook", 3))
        mystery   = float(sd.get("mystery_drop", 5))
        buildup   = float(sd.get("build_up", 12))
        interrupt = float(sd.get("pattern_interrupt", 2))
        core      = float(sd.get("core_facts", 15))
        bridge    = float(sd.get("curiosity_bridge", 3))
        climax    = float(sd.get("climax", 8))
        cta       = float(sd.get("cta", 3))

        # Mapping 6 clips: gabung sections pendek agar tiap clip punya durasi wajar
        durations = [
            hook,                          # Clip 1: hook
            mystery,                       # Clip 2: mystery drop
            buildup,                       # Clip 3: build up
            round(interrupt + core / 2, 2),# Clip 4: interrupt + core awal
            round(core / 2 + bridge, 2),   # Clip 5: core akhir + bridge
            round(climax + cta, 2),        # Clip 6: climax + cta
        ]

        total = sum(durations)
        logger.info(
            f"[VisualAssembler] section_durations → clip_durations: "
            f"{durations} = {total:.1f}s"
        )
        # Scale clip durations agar total = audio_duration + xfade_loss
        # xfade_loss = (n-1) × 0.4s — dikompensasi agar Step A xfade output = audio_duration
        if audio_duration > 0:
            xfade_loss = (n_clips - 1) * 0.4 if n_clips >= 2 else 0.0
            target_total = audio_duration + xfade_loss
            total_raw = sum(durations)
            scale     = target_total / total_raw if total_raw > 0 else 1.0
            durations = [round(d * scale, 4) for d in durations]
            logger.info(
                f"[VisualAssembler] Scaled durations: {durations} "
                f"= {sum(durations):.1f}s (audio: {audio_duration:.1f}s + xfade_loss: {xfade_loss:.1f}s)"
            )
        return durations

    def _try_ai_video(
        self,
        visual_mode: str,
        script: dict,
        tenant_config: TenantConfig,
        clips_dir: Path,
        run_config: dict,
    ) -> list[Path]:
        """[B6] F2 — render_mode ai_video: SATU klip text-to-video utuh (preset 8s, MULTI_FORMAT §3).
        Klip diminta ≥ durasi audio (renderer men-trim `-t audio` + tpad trailing) — presisi durasi
        tetap di tangan renderer (gerbang F4 §7.3). NO-FALLBACK: gagal → [] → pipeline raise."""
        try:
            from src.providers.visual import build_visual_provider

            config = {
                "tenant_id":       tenant_config.tenant_id,
                "niche":           tenant_config.niche,
                "visual_provider": visual_mode,
                "visual_api_key":  run_config.get("visual_api_key"),
            }
            provider = build_visual_provider(visual_mode, config)   # F5-06: registry (family ai_video)

            prompt = (script.get("video_prompt") or "").strip()
            if not prompt:
                logger.error("[VisualAssembler] video_prompt kosong (STEP 4.5 varian video tidak jalan?) — gagal jujur")
                return []

            audio_d = float(self._current_audio_duration or 0.0)
            if audio_d <= 0:
                logger.error("[VisualAssembler] audio_duration tidak tersedia utk ai_video — gagal jujur")
                return []

            clips_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[VisualAssembler] Generating AI video: {visual_mode} — 1 klip ≥ {audio_d:.1f}s")
            clips = asyncio.run(
                provider.fetch_clips(
                    keywords=[prompt], count=1,
                    output_dir=clips_dir, clip_durations=[audio_d],
                )
            )
            if clips:
                logger.info(f"[VisualAssembler] ✅ AI Video generated: {len(clips)} klip via {visual_mode}")
            return [clip.path for clip in clips]

        except Exception as e:
            logger.error(f"[VisualAssembler] AI Video error: {e}")
            # [§8e] Penangkap ini menangkap LEBIH DULU daripada `_try_provider` (bersarang) — terbukti
            # di worker.log 14-Jul yang mencetak "AI Video error", bukan "Provider error". Jadi tanpa
            # baris ini sebab penyedia video HILANG sebelum sampai ke mana pun.
            self.last_error = str(e)
            return []

    def _try_ai_image(
        self,
        visual_mode: str,
        script: dict,
        tenant_config: TenantConfig,
        clips_dir: Path,
        run_config: dict,
    ) -> list[Path]:
        """Generate gambar AI + Ken Burns effect."""
        try:
            from src.providers.visual import build_visual_provider

            config = {
                "tenant_id":              tenant_config.tenant_id,
                "niche":                  tenant_config.niche,
                "visual_provider":        visual_mode,
                "visual_ai_model":        visual_mode.split(":", 1)[1] if ":" in visual_mode else "",
                "visual_api_key":         run_config.get("visual_api_key"),
                "llm_api_key":            run_config.get("llm_api_key") or "",
                "llm_library":            run_config.get("llm_library") or "",
                "llm_provider":           run_config.get("llm_provider") or "",
                "llm_models":             run_config.get("llm_models") or {},
                "niche_visual_style":     run_config.get("niche_visual_style") or {},
                "niche_visual_fallbacks": run_config.get("niche_visual_fallbacks") or [],
                "image_quality":          run_config.get("image_quality") or "",
                "visual_seed":            getattr(tenant_config, "visual_seed", None),  # Diversity §9.1
            }
            provider  = build_visual_provider(visual_mode, config)   # F5-06: registry
            # Image-gen PER-PRESET (MULTI_FORMAT §3): jumlah image = N beat (= visual_beats), durasi
            # per-beat dari pipeline (script.beat_durations, SINKRON TTS via word_timestamps). Fallback
            # ke _compute_clip_durations (6) bila beat_durations tak ada (legacy/no-preset).
            #
            # PENTING (sinkron bake↔concat): beat_durations = TTS-synced MENTAH (sum = audio_duration).
            # Source clip WAJIB di-bake dengan kompensasi xfade-loss IDENTIK dgn renderer._create_clip_list
            # (target = audio + (N-1)*0.4s). Tanpa ini: bake sum=audio, tapi clip_list scale ke audio+loss
            # → durasi bake < durasi list → xfade "makan" konten → video pendek (terbukti N=9/90s: -9s).
            # _compute_clip_durations (legacy) SUDAH ter-scale ke target ini, jadi hanya cabang
            # beat_durations yang perlu di-scale di sini.
            beat_durs = script.get("beat_durations")
            if beat_durs:
                clip_durs = [float(d) for d in beat_durs]
                ad = self._current_audio_duration
                if ad and ad > 0:
                    xfade_loss = (len(clip_durs) - 1) * 0.4 if len(clip_durs) >= 2 else 0.0
                    target     = ad + xfade_loss
                    raw_sum    = sum(clip_durs)
                    if raw_sum > 0:
                        clip_durs = [round(d * target / raw_sum, 4) for d in clip_durs]
            else:
                clip_durs = self._compute_clip_durations(
                    script, n_clips=6, audio_duration=self._current_audio_duration)
            n_img     = len(clip_durs) if clip_durs else 6
            keywords  = provider.extract_keywords_from_script(script, tenant_config.niche, n=n_img)
            beats     = script.get("beats") or []

            logger.info(
                f"[VisualAssembler] Generating AI images: "
                f"{visual_mode} — {n_img} scenes (beat-synced per-preset, beat-role motion)"
            )

            clips_dir.mkdir(parents=True, exist_ok=True)   # WAJIB sebelum hook-frame (A5 reorder: hook-frame kini sebelum fetch_clips yg biasanya mkdir)
            # A5 (Opsi A): clip[0] = HOOK-FRAME dari thumbnail_concept (= scene hook, dibuat SEKALI).
            # fetch HANYA scene beats[1:] → tak ada image yang dibuat-lalu-dibuang (boros).
            # A6: motion per-peran beat (beat_roles). Fallback aman: hook-frame gagal → fetch semua N
            # (satu jalur fetch saja → tanpa tabrakan penamaan clip).
            hook_clip = self._generate_hook_frame(
                script=script, clips_dir=clips_dir, config=config, clip_durs=clip_durs,
            )
            if hook_clip:
                scene_kw    = keywords[1:]
                scene_durs  = clip_durs[1:] if len(clip_durs) > 1 else []
                scene_roles = beats[1:] if len(beats) > 1 else []
                scene_clips = asyncio.run(
                    provider.fetch_clips(
                        keywords=scene_kw, count=len(scene_kw),
                        output_dir=clips_dir, clip_durations=scene_durs, beat_roles=scene_roles,
                    )
                ) if scene_kw else []
                clips = [hook_clip] + scene_clips
                logger.info(f"[VisualAssembler] s6c7 ✅ Hook-frame + {len(scene_clips)} scene (no waste)")
            else:
                logger.warning("[VisualAssembler] Hook-frame gagal → fetch semua N (clip0=thumbnail)")
                clips = asyncio.run(
                    provider.fetch_clips(
                        keywords=keywords, count=n_img,
                        output_dir=clips_dir, clip_durations=clip_durs, beat_roles=beats,
                    )
                )

            # [2026-08-08] ADEGAN YANG GAGAL TIDAK BOLEH LEWAT SEBAGAI "BERHASIL".
            # Dulu baris di bawah mencetak "✅ berhasil" meski sebagian adegan dilewati — kerusakan
            # lolos ke hilir, perender menyusun durasi dari JUMLAH klip, dan videonya keluar lebih
            # pendek dari narasi (terukur 3-Agu: berkas 36,7 dtk vs narasi 58,3 dtk). Sebab dari
            # penyedia disimpan di sini supaya pipeline bisa menyebutkannya apa adanya ke tenant.
            _gagal = list(getattr(provider, "scene_errors", []) or [])
            if _gagal:
                self.last_error = _gagal[-1]
                logger.error(f"[VisualAssembler] ⚠️ {len(_gagal)} adegan GAGAL dibuat — sebab terakhir: "
                             f"{_gagal[-1]}")
            if clips:
                logger.info(
                    f"[VisualAssembler] {'⚠️ SEBAGIAN' if _gagal else '✅'} AI Image: "
                    f"{len(clips)} clips via {visual_mode}"
                    + (f" ({len(_gagal)} adegan gagal)" if _gagal else "")
                )

            return [clip.path for clip in clips]

        except Exception as e:
            logger.error(f"[VisualAssembler] AI Image error: {e}")
            self.last_error = str(e)   # [§8e] idem jalur video — bersarang, menangkap lebih dulu
            return []

    def _generate_hook_frame(
        self,
        script: dict,
        clips_dir: Path,
        config: dict,
        clip_durs: list[float],
    ):
        """
        Fase 6C s6c7: Generate hero image khusus untuk frame pertama.
        Prompt dibangun dari hook text aktual — bukan visual_suggestion generik.
        Hanya aktif saat visual_mode = ai_image:*.
        """
        try:
            from src.providers.visual import build_visual_provider

            hook_text = script.get("hook", "").strip()
            # s72: thumbnail_concept = deskripsi visual murni dari script engine
            # Mencegah DALL-E render teks literal dari kalimat hook
            thumbnail_concept = script.get("thumbnail_concept", "").strip() or hook_text
            # (`niche` dicabut 2026-08-02 — dibaca lalu tak pernah dipakai. Ia juga satu-satunya
            #  pembaca `niche_fallback` yang tersisa di jalur produksi; kolomnya sendiri kosong
            #  di seluruh 17 tenant.)

            if not hook_text:
                return None

            # Hook frame prompt — dibangun dari niche visual_style Supabase (tidak hardcode)
            niche_vs   = config.get("niche_visual_style") or {}
            base_style = niche_vs.get("base_style", "documentary photography style, cinematic")
            color_pal  = niche_vs.get("color_palette", "natural cinematic colors")
            atmosphere = niche_vs.get("atmosphere", "dramatic cinematic atmosphere")

            prompt = (
                f"Cinematic vertical 9:16 hero image. "
                f"{thumbnail_concept}. "
                f"Style: {base_style}. "
                f"Color palette: {color_pal}. "
                f"Atmosphere: {atmosphere}. "
                f"Single striking focal point that stops the scroll instantly. "
                f"Photorealistic. "
                f"No text, no words, no letters, no numbers, no signs, no typography. No people."
            )
            provider  = build_visual_provider(config.get("visual_provider") or "ai_image:", config)   # F5-06: registry
            img_path  = clips_dir / "hook_frame_img.jpg"
            clip_path = clips_dir / "clip_01_hook.mp4"

            # Durasi = durasi section hook (default 3 detik)
            hook_duration = clip_durs[0] if clip_durs else 3.0

            import asyncio
            # Fix s1.6: _generate_image(prompt, negative_prompt, output_path) — sebelumnya
            # kurang arg negative_prompt → "missing output_path". Pakai _build_image_prompt
            # (quality tags + negative) konsisten dgn flow normal ai_image.
            positive, negative = provider._build_image_prompt(prompt)
            asyncio.run(provider._generate_image(positive, negative, img_path))
            # Hook-frame ikut config arah (Fase 2) + intensitas niche (Fase 1) — konsisten dgn scene lain.
            from src.content import beats as _beats
            _hm = (_beats.resolve_motion_sequence(["hook"]) or [{"dir": "zoom_in", "rate": 0.05}])[0]
            _cm = (getattr(provider, "niche_visual_style", {}) or {}).get("camera_motion") or {}
            _int = _cm.get("intensity") if _cm.get("intensity") in provider._MOTION_INTENSITY else "normal"
            provider._image_to_video(img_path, clip_path, duration=hook_duration,
                                     direction=_hm["dir"], rate=_hm["rate"], intensity=_int)

            from src.providers.visual.base import VideoClip
            size_mb = clip_path.stat().st_size / (1024 * 1024)
            logger.info(
                f"[s6c7] Hook frame: {clip_path.name} ({size_mb:.1f}MB) "
                f"{hook_duration}s | prompt: '{hook_text[:60]}...'"
            )

            return VideoClip(
                path=clip_path,
                duration=hook_duration,
                width=1080,
                height=1920,
                file_size_mb=round(size_mb, 1),
                source_url="ai_generated:hook_frame",
                provider=config.get("visual_provider", "ai_image"),
            )

        except Exception as e:
            # [§8f] ERROR, bukan warning: frame pertama = tuas viral, turunnya BUKAN peristiwa kecil.
            #
            # ⚠️ KOREKSI 2026-08-08 — KLAIM LAMA DI SINI TIDAK BENAR. Komentar & log versi 05-Agu
            # berbunyi "Sebab direkam ke laporan run". **Tidak sampai ke mana pun.** Sebabnya hanya
            # masuk `result["steps"]` di memori, dan `steps` TIDAK PERNAH ditulis ke tabel mana pun
            # (diverifikasi: nol penyebutan di producer & supabase_writer). Jadi selama tiga hari
            # kegagalan ini tetap tak terlihat siapa pun — persis keadaan sebelum "diperbaiki".
            # §8f di dokumen SSOT memang masih menulis "BELUM diperbaiki"; dokumennya benar, kalimat
            # di kode inilah yang mengklaim lebih. Klaim itu dicabut; nilainya tetap direkam supaya
            # siap dipakai saat jalur penyimpanannya dibangun (menunggu ketok owner, §8f).
            self.hook_frame_error = str(e)
            logger.error(f"[s6c7] FRAME PERTAMA GAGAL dibuat ({e}) — video tetap dibuat dengan klip "
                         f"biasa, tapi pembukanya LEBIH LEMAH. Sebab BARU tercatat di log ini saja "
                         f"(belum tersimpan ke laporan run — §8f masih terbuka).")
            return None

    # ──────────────────────────────────────────────
    # Config loader
    # ──────────────────────────────────────────────

    def _load_run_config(self, tenant_config: TenantConfig) -> dict:
        """Baca config dari Supabase, fallback ke defaults."""
        try:
            from src.config.tenant_config import load_tenant_config
            rc = load_tenant_config(tenant_config.tenant_id, getattr(tenant_config, "channel_id", None), getattr(tenant_config, "niche", None))
            return {
                "visual_mode":            getattr(rc, "visual_mode", "") or "",
                "visual_api_key":         rc.visual_api_key,
                "llm_api_key":            rc.llm_api_key,
                "llm_library":            getattr(rc, "llm_library", None) or "",
                "llm_provider":           getattr(rc, "llm_provider", None) or "",
                "llm_models":             getattr(rc, "llm_models", None) or {},
                "niche_visual_style":     getattr(rc, "niche_visual_style", {}) or {},
                "niche_visual_fallbacks": getattr(rc, "niche_visual_fallbacks", []) or [],
                "is_developer":           getattr(rc, "is_developer", False),
                "image_quality":          getattr(rc, "image_quality", None) or "",
            }
        except Exception:
            return {
                "visual_mode":            "",
                "visual_api_key":         None,
                "llm_api_key":            None,
                "llm_library":            "",
                "llm_provider":           "",
                "llm_models":             {},
                "niche_visual_style":     {},
                "niche_visual_fallbacks": [],
                "is_developer":           False,
                "image_quality":          "low",
            }
