"""
Supabase Writer — MesinViral.com
Fase 7 s71: Simpan metadata video dan run log ke Supabase.

Fungsi utama:
  write_video()       — INSERT setelah publish berhasil  (status='published')
  write_qc_failed()   — INSERT jika QC pre-publish gagal (status='qc_failed')
  write_failed_run()  — INSERT jika pipeline crash total (status='failed')
  get_recent_topics() — SELECT untuk duplicate prevention di niche_selector

Prinsip:
  - Fire-and-forget: jika gagal, pipeline TIDAK berhenti
  - Semua error di-log sebagai warning, tidak pernah raise ke caller
  - topic_slug dinormalisasi untuk duplicate detection yang konsisten
"""

import os
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


# ─── Helper: normalisasi topic → slug ────────────────────────────────────────

def _normalize_slug(text: str) -> str:
    """
    Normalisasi teks topik menjadi slug untuk duplicate detection.
    Konsisten lintas run: lowercase, tanpa punctuation, hapus stop words ≤3 char.

    Contoh:
      "The Black Hole at the Edge of Time!" → "black hole edge time"
      "Why NASA Found Something Impossible"  → "nasa found something impossible"
    """
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s]", " ", text)
    words = [w for w in text.split() if len(w) > 3 or w.isdigit()]
    return " ".join(words).strip()


# ─── SupabaseWriter ───────────────────────────────────────────────────────────

class SupabaseWriter:
    """
    Writer untuk semua operasi INSERT/SELECT ke Supabase dari pipeline.
    Di-inisialisasi sekali di Pipeline.__init__() — tidak perlu singleton eksternal.
    """

    def __init__(self):
        self._client = self._init_client()

    def _init_client(self):
        """Init Supabase client. Return None jika tidak tersedia — tidak raise."""
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if not url or not key:
                logger.warning(
                    "[SupabaseWriter] SUPABASE_URL/KEY tidak ada di .env "
                    "— writer disabled, pipeline tetap jalan"
                )
                return None
            client = create_client(url, key)
            logger.info("[SupabaseWriter] Supabase client ready")
            return client
        except Exception as e:
            logger.warning(
                f"[SupabaseWriter] Init gagal: {e} "
                "— writer disabled, pipeline tetap jalan"
            )
            return None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    # ── Write operations ──────────────────────────────────────────────────────

    def write_video(
        self,
        *,
        run_id:         str,
        tenant_id:      str,
        platform:       str,
        video_id:       str,
        url:            str,
        title:          str,
        hook:           str,
        topic:          str,
        niche:          str,
        viral_score:    float,
        duration_secs:  Optional[float] = None,
        file_size_mb:   Optional[float] = None,
        channel_id:     Optional[str]   = None,
        topic_scores:   Optional[dict]  = None,
        insights_grade: Optional[str]   = None,
    ) -> Optional[dict]:
        """
        INSERT video yang berhasil dipublish.
        Returns: inserted record atau None. Pipeline TIDAK berhenti jika None.
        """
        if not self.is_available:
            logger.warning("[SupabaseWriter] Client tidak tersedia — skip write_video")
            return None

        topic_slug = _normalize_slug(topic)
        record = {
            "run_id":         run_id,
            "tenant_id":      tenant_id,
            "platform":       platform,
            "video_id":       video_id,
            "url":            url,
            "title":          title,
            "hook":           hook[:500] if hook else "",
            "topic":          topic,
            "topic_slug":     topic_slug,
            "niche":          niche,
            "viral_score":    viral_score,
            "status":         "published",
            "qc_passed":      True,
            "duration_secs":  duration_secs,
            "file_size_mb":   file_size_mb,
            "published_at":   datetime.utcnow().isoformat(),
            "topic_scores":   topic_scores   or {},
            "insights_grade": insights_grade or "",
        }
        if channel_id:
            record["channel_id"] = channel_id

        try:
            result = self._client.table("videos").insert(record).execute()
            if result.data:
                logger.info(
                    f"[SupabaseWriter] ✅ Video recorded | "
                    f"id={video_id} | niche={niche} | topic='{topic[:50]}'"
                )
                return result.data[0]
            logger.warning("[SupabaseWriter] Insert kosong — periksa schema")
            return None
        except Exception as e:
            logger.warning(f"[SupabaseWriter] write_video gagal (non-fatal): {e}")
            return None

    def write_qc_failed(
        self,
        *,
        run_id:        str,
        tenant_id:     str,
        niche:         str,
        topic:         str,
        qc_reason:     str,
        duration_secs: Optional[float] = None,
        file_size_mb:  Optional[float] = None,
    ) -> None:
        """
        Catat video yang gagal QC pre-publish.
        Dipanggil dari pipeline.py saat _pre_publish_qc() return False.
        """
        if not self.is_available:
            return

        record = {
            "run_id":        run_id,
            "tenant_id":     tenant_id,
            "platform":      "youtube",
            "niche":         niche,
            "topic":         topic if topic else "",
            "topic_slug":    _normalize_slug(topic) if topic else "",
            "status":        "qc_failed",
            "qc_passed":     False,
            "qc_reason":     qc_reason[:500],
            "duration_secs": duration_secs,
            "file_size_mb":  file_size_mb,
            "published_at":  datetime.utcnow().isoformat(),
        }
        try:
            self._client.table("videos").insert(record).execute()
            logger.warning(
                f"[SupabaseWriter] QC failed recorded | run={run_id} | reason={qc_reason}"
            )
        except Exception as e:
            logger.warning(f"[SupabaseWriter] write_qc_failed gagal (non-fatal): {e}")

    def write_failed_run(
        self,
        *,
        run_id:    str,
        tenant_id: str,
        niche:     str,
        error:     str,
    ) -> None:
        """
        Catat pipeline run yang gagal total.
        Dipanggil dari pipeline.py di except block utama.
        """
        if not self.is_available:
            return

        record = {
            "run_id":       run_id,
            "tenant_id":    tenant_id,
            "platform":     "youtube",
            "niche":        niche,
            "status":       "failed",
            "qc_passed":    False,
            "qc_reason":    str(error)[:500] if error else "unknown error",
            "published_at": datetime.utcnow().isoformat(),
        }
        try:
            self._client.table("videos").insert(record).execute()
            logger.info(f"[SupabaseWriter] Failed run recorded: {run_id}")
        except Exception as e:
            logger.warning(f"[SupabaseWriter] write_failed_run gagal (non-fatal): {e}")

    # ── Query untuk duplicate prevention ─────────────────────────────────────

    def get_recent_topics(
        self,
        tenant_id:     str,
        niche:         str,
        lookback_days: int = 30,
    ) -> list:
        """
        Ambil topik yang sudah diproduksi dalam N hari terakhir.
        Returns: list of {topic, topic_slug, published_at}
                 List kosong = tidak block production.
        """
        if not self.is_available:
            logger.warning(
                "[SupabaseWriter] Client tidak tersedia — "
                "duplicate check dilewati, semua topik dianggap baru"
            )
            return []

        try:
            since = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
            result = (
                self._client.table("videos")
                .select("topic, topic_slug, published_at")
                .eq("tenant_id", tenant_id)
                .eq("niche", niche)
                .eq("status", "published")
                .gte("published_at", since)
                .order("published_at", desc=False)
                .execute()
            )
            topics = result.data or []
            logger.info(
                f"[SupabaseWriter] Recent topics | "
                f"niche={niche} | lookback={lookback_days}d | found={len(topics)}"
            )
            return topics
        except Exception as e:
            logger.warning(
                f"[SupabaseWriter] get_recent_topics gagal (non-fatal): {e} "
                "— duplicate check dilewati"
            )
            return []


# ─── Singleton ────────────────────────────────────────────────────────────────

_writer: Optional[SupabaseWriter] = None

def get_writer() -> SupabaseWriter:
    global _writer
    if _writer is None:
        _writer = SupabaseWriter()
    return _writer


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Testing SupabaseWriter...")
    writer = SupabaseWriter()
    print(f"Available     : {writer.is_available}")
    print(f"Slug test 1   : '{_normalize_slug('The Black Hole at the Edge of Time!')}' ")
    print(f"Slug test 2   : '{_normalize_slug('Why NASA Found Something Impossible')}' ")
    if writer.is_available:
        topics = writer.get_recent_topics("ryan_andrian", "universe_mysteries", 30)
        print(f"Recent topics : {len(topics)} (universe_mysteries, 30d)")
        for t in topics:
            print(f"  - {t.get('topic_slug')} ({t.get('published_at', '')[:10]})")
