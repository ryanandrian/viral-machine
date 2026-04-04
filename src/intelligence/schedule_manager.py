"""
ScheduleManager — Resolusi niche + focus per slot produksi.

s84: Setiap pipeline run, resolve niche yang harus diproduksi berdasarkan:
  1. production_schedules (niche_id eksplisit dari user)
  2. default_niche_rotation (round-robin jika slot tidak di-assign)
  3. Random dari niches table (last resort)

Multi-tenant ready. Fire-and-forget untuk semua Supabase write.
"""

import os
import random
from datetime import datetime, timezone
from typing import Optional, Tuple

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


class ScheduleManager:
    """
    Resolve niche + focus untuk run pipeline saat ini.

    Waterfall:
      1. production_schedules → cari slot yang cocok dengan jam sekarang
         - niche_id diisi → pakai itu + niche_focus
         - niche_id NULL  → lanjut ke layer 2
      2. default_niche_rotation → round-robin berdasarkan niche_rotation_index
      3. Random dari niches table (is_active = true)
    """

    # Toleransi matching waktu: cron dianggap match jika dalam ±WINDOW_MINUTES
    MATCH_WINDOW_MINUTES = 35

    def __init__(self):
        self._supabase = self._init_supabase()

    def _init_supabase(self):
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if url and key:
                return create_client(url, key)
            logger.warning("[ScheduleManager] SUPABASE_URL/KEY tidak ada")
            return None
        except Exception as e:
            logger.warning(f"[ScheduleManager] Supabase init gagal: {e}")
            return None

    # ── Public API ─────────────────────────────────────────────────────────

    def resolve_slot(
        self,
        tenant_id: str,
        channel_id: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        Resolve niche + focus untuk slot produksi saat ini.

        Returns:
            (niche_id: str, niche_focus: str | None)
            niche_id selalu terisi — tidak pernah None.
            niche_focus bisa None jika tidak ada fokus khusus.
        """
        channel_id = channel_id or tenant_id  # fallback: channel_id = tenant_id

        # Layer 1: production_schedules
        result = self._resolve_from_schedules(tenant_id, channel_id)
        if result:
            niche_id, niche_focus = result
            logger.info(
                f"[ScheduleManager] Layer 1 — schedule: "
                f"niche={niche_id} | focus={niche_focus or '-'}"
            )
            return niche_id, niche_focus

        # Layer 2: default_niche_rotation
        result = self._resolve_from_rotation(tenant_id)
        if result:
            niche_id, niche_focus = result
            logger.info(
                f"[ScheduleManager] Layer 2 — rotation: "
                f"niche={niche_id}"
            )
            return niche_id, niche_focus

        # Layer 3: random dari niches table
        result = self._resolve_random(tenant_id)
        if result:
            niche_id, niche_focus = result
            logger.info(
                f"[ScheduleManager] Layer 3 — random: "
                f"niche={niche_id}"
            )
            return niche_id, niche_focus

        # Absolute fallback — tidak pernah return None
        logger.warning("[ScheduleManager] Semua layer gagal — pakai universe_mysteries")
        return "universe_mysteries", None

    # ── Layer 1: production_schedules ──────────────────────────────────────

    def _resolve_from_schedules(
        self,
        tenant_id: str,
        channel_id: str,
    ) -> Optional[Tuple[str, Optional[str]]]:
        """
        Query production_schedules, cari slot yang paling dekat dengan jam sekarang.
        Jika niche_id diisi → return (niche_id, niche_focus).
        Jika niche_id NULL → return None (fall through ke layer 2).
        """
        if not self._supabase:
            return None

        try:
            result = (
                self._supabase
                .table("production_schedules")
                .select("niche_id, niche_focus, cron_expression")
                .eq("channel_id", channel_id)
                .eq("is_active", True)
                .execute()
            )
            schedules = result.data or []
            if not schedules:
                logger.debug(f"[ScheduleManager] Tidak ada schedule untuk channel: {channel_id}")
                return None

            # Cari schedule yang paling cocok dengan jam sekarang (UTC)
            now_utc   = datetime.now(timezone.utc)
            best      = self._find_best_schedule(schedules, now_utc)

            if best is None:
                return None

            niche_id    = best.get("niche_id")
            niche_focus = best.get("niche_focus") or None

            if niche_id:
                return niche_id, niche_focus

            # niche_id NULL — slot ada tapi tidak di-assign niche
            # niche_focus mungkin masih ada (fokus tanpa niche eksplisit)
            # fall through ke layer 2, tapi simpan focus untuk dipakai nanti
            # → return None agar layer 2 resolve niche, focus dari schedule tetap dipakai
            logger.debug(
                f"[ScheduleManager] Schedule cocok tapi niche_id NULL "
                f"(focus={niche_focus or '-'}) — lanjut ke rotation"
            )
            # Store focus for later use even if niche is resolved by layer 2/3
            self._pending_focus = niche_focus
            return None

        except Exception as e:
            logger.warning(f"[ScheduleManager] Schedule query gagal: {e}")
            return None

    def _find_best_schedule(self, schedules: list, now_utc: datetime) -> Optional[dict]:
        """
        Dari daftar schedules, cari yang cron_expression-nya paling dekat
        dengan waktu sekarang (dalam MATCH_WINDOW_MINUTES menit ke belakang).

        Hanya support format cron sederhana: '0 HH * * *' dan '*/N * * * *'
        Untuk format lain → ambil schedule pertama sebagai fallback.
        """
        now_minutes = now_utc.hour * 60 + now_utc.minute
        best_schedule = None
        best_delta    = float("inf")

        for sched in schedules:
            cron = sched.get("cron_expression", "")
            cron_minutes = self._parse_cron_to_minutes(cron)
            if cron_minutes is None:
                continue

            # Delta dalam menit (berapa menit yang lalu cron ini seharusnya jalan)
            delta = (now_minutes - cron_minutes) % (24 * 60)

            if delta <= self.MATCH_WINDOW_MINUTES and delta < best_delta:
                best_delta    = delta
                best_schedule = sched

        if best_schedule:
            return best_schedule

        # Fallback: tidak ada yang match dalam window → ambil schedule pertama
        logger.debug(
            f"[ScheduleManager] Tidak ada schedule dalam window {self.MATCH_WINDOW_MINUTES}m "
            f"— pakai schedule pertama"
        )
        return schedules[0] if schedules else None

    @staticmethod
    def _parse_cron_to_minutes(cron: str) -> Optional[int]:
        """
        Parse cron expression → menit dalam sehari (0-1439).
        Support: '0 HH * * *' → HH * 60
                 'MM HH * * *' → HH * 60 + MM
        Return None jika format tidak dikenal.
        """
        try:
            parts = cron.strip().split()
            if len(parts) != 5:
                return None
            minute_part = parts[0]
            hour_part   = parts[1]
            # Hanya support angka integer (bukan */N, ranges, dll)
            if not minute_part.isdigit() or not hour_part.isdigit():
                return None
            return int(hour_part) * 60 + int(minute_part)
        except Exception:
            return None

    # ── Layer 2: default_niche_rotation ────────────────────────────────────

    def _resolve_from_rotation(self, tenant_id: str) -> Optional[Tuple[str, Optional[str]]]:
        """
        Ambil niche berikutnya dari default_niche_rotation (round-robin).
        Increment niche_rotation_index di Supabase (fire-and-forget).
        """
        if not self._supabase:
            return None

        try:
            result = (
                self._supabase
                .table("tenant_configs")
                .select("default_niche_rotation, niche_rotation_index")
                .eq("tenant_id", tenant_id)
                .single()
                .execute()
            )
            row = result.data
            if not row:
                return None

            rotation = row.get("default_niche_rotation") or []
            if not rotation or not isinstance(rotation, list):
                return None

            idx      = int(row.get("niche_rotation_index") or 0)
            niche_id = rotation[idx % len(rotation)]

            # Validasi niche_id ada di NICHES dict
            from src.intelligence.config import NICHES
            if niche_id not in NICHES:
                logger.warning(
                    f"[ScheduleManager] Niche '{niche_id}' dari rotasi tidak ada di NICHES — skip"
                )
                return None

            # Increment index (fire-and-forget)
            next_idx = (idx + 1) % len(rotation)
            try:
                self._supabase.table("tenant_configs").update(
                    {"niche_rotation_index": next_idx}
                ).eq("tenant_id", tenant_id).execute()
                logger.debug(
                    f"[ScheduleManager] Rotation index: {idx} → {next_idx} "
                    f"(dari {len(rotation)} niche)"
                )
            except Exception as _e:
                logger.warning(f"[ScheduleManager] Gagal update rotation index: {_e}")

            # Ambil pending_focus dari Layer 1 jika ada
            niche_focus = getattr(self, "_pending_focus", None)
            self._pending_focus = None
            return niche_id, niche_focus

        except Exception as e:
            logger.warning(f"[ScheduleManager] Rotation query gagal: {e}")
            return None

    # ── Layer 3: random dari niches table ──────────────────────────────────

    def _resolve_random(self, tenant_id: str) -> Optional[Tuple[str, Optional[str]]]:
        """
        Pilih niche random dari niches table (is_active = true).
        Hindari niche yang sama dengan produksi terakhir tenant ini.
        """
        niche_focus = getattr(self, "_pending_focus", None)
        self._pending_focus = None

        # Ambil daftar niche aktif dari niches table
        if self._supabase:
            try:
                result = (
                    self._supabase
                    .table("niches")
                    .select("niche_id")
                    .eq("is_active", True)
                    .execute()
                )
                active_niches = [r["niche_id"] for r in (result.data or [])]
            except Exception as e:
                logger.warning(f"[ScheduleManager] Niches table query gagal: {e}")
                active_niches = []
        else:
            active_niches = []

        # Fallback ke NICHES dict jika table kosong
        if not active_niches:
            from src.intelligence.config import NICHES
            active_niches = list(NICHES.keys())

        if not active_niches:
            return None

        # Hindari consecutive duplicate — ambil niche terakhir tenant
        last_niche = self._get_last_niche(tenant_id)
        candidates = [n for n in active_niches if n != last_niche]
        if not candidates:
            candidates = active_niches  # semua sama → tidak ada pilihan lain

        return random.choice(candidates), niche_focus

    def _get_last_niche(self, tenant_id: str) -> Optional[str]:
        """Ambil niche dari produksi terakhir untuk hindari consecutive duplicate."""
        if not self._supabase:
            return None
        try:
            result = (
                self._supabase
                .table("videos")
                .select("niche")
                .eq("tenant_id", tenant_id)
                .order("published_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            return rows[0]["niche"] if rows else None
        except Exception:
            return None
