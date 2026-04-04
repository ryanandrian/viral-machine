"""
Telegram Notifier — MesinViral.com
Kirim laporan hasil produksi ke Telegram Bot.

Prinsip:
- Fire-and-forget: error TIDAK pernah menghentikan pipeline
- Per-tenant: chat_id dari tenant_config, fallback ke env TELEGRAM_CHAT_ID
- Satu bot (TELEGRAM_BOT_TOKEN) untuk semua tenant
"""

import os
import requests
from loguru import logger


class TelegramNotifier:
    """
    Kirim notifikasi pipeline ke Telegram Bot API.

    Config hierarchy:
      bot_token : env TELEGRAM_BOT_TOKEN (sistem, satu bot)
      chat_id   : tenant_config.telegram_chat_id → env TELEGRAM_CHAT_ID
    """

    _API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        self.bot_token      = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.system_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        if not self.bot_token:
            logger.warning("[Telegram] TELEGRAM_BOT_TOKEN tidak di-set — notifikasi dinonaktifkan")

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    def notify_success(self, result: dict, run_config=None) -> bool:
        """
        Kirim laporan sukses setelah video berhasil dipublish ke YouTube.

        Args:
            result:     dict hasil pipeline (dari Pipeline.run())
            run_config: TenantRunConfig (opsional, untuk chat_id + channel_name)
        """
        chat_id = self._get_chat_id(run_config)
        if not chat_id:
            return False

        channel = self._channel_name(run_config, result)
        elapsed = self._fmt_elapsed(result.get("elapsed_seconds", 0))
        niche   = result.get("niche", "—")

        yt    = result.get("published", {}).get("youtube", {})
        title = (
            yt.get("title")
            or result.get("steps", {}).get("script", {}).get("title", "—")
        )
        url      = yt.get("url", "")
        video_id = yt.get("video_id", "")

        qc           = result.get("steps", {}).get("qc", {})
        duration_s   = qc.get("duration") or 0
        size_mb      = qc.get("size_mb", 0)
        hook_score   = result.get("steps", {}).get("hook", {}).get("score", 0)
        duration_str = self._fmt_duration(duration_s)

        clips = result.get("steps", {}).get("visuals", {}).get("clips", 0)
        ts    = result.get("steps", {}).get("tts", {}).get("timestamps", 0)

        lines = [
            f"✅ <b>[{channel}] Video Published!</b>",
            f"🎬 <i>{self._escape(title)}</i>",
            f"🎯 Hook score: <b>{hook_score}/100</b>  |  🏷 Niche: {niche}",
            f"⏱ Durasi: {duration_str}  |  💾 {size_mb} MB  |  🎞 {clips} clips",
        ]
        if video_id:
            lines.append(f"🔗 {url}")
        lines += [
            f"⏰ Runtime: {elapsed}  |  📝 {ts} kata",
            f"<code>{result.get('run_id', '')}</code>",
        ]

        return self._send(chat_id, "\n".join(lines))

    def notify_qc_fail(self, run_id: str, tenant_id: str, topic: str,
                       qc_reason: str, duration_secs, size_mb: float,
                       run_config=None) -> bool:
        """
        Kirim alert ketika video gagal QC dan tidak dipublish.
        """
        chat_id = self._get_chat_id(run_config)
        if not chat_id:
            return False

        channel      = self._channel_name(run_config, {"tenant_id": tenant_id})
        duration_str = f"{duration_secs:.1f}s" if duration_secs else "—"

        text = (
            f"⚠️ <b>[{channel}] QC GAGAL — Video tidak dipublish</b>\n"
            f"📋 Topik: <i>{self._escape(str(topic)[:100])}</i>\n"
            f"❌ Alasan: {self._escape(qc_reason)}\n"
            f"⏱ Durasi: {duration_str}  |  💾 {size_mb} MB\n"
            f"<code>{run_id}</code>"
        )
        return self._send(chat_id, text)

    def notify_publish_fail(self, run_id: str, tenant_id: str, error: str,
                            run_config=None) -> bool:
        """
        Kirim alert ketika QC lulus tapi upload YouTube gagal.
        """
        chat_id = self._get_chat_id(run_config)
        if not chat_id:
            return False

        channel = self._channel_name(run_config, {"tenant_id": tenant_id})
        text = (
            f"📤 <b>[{channel}] Upload YouTube GAGAL</b>\n"
            f"💥 Error: <code>{self._escape(str(error)[:200])}</code>\n"
            f"ℹ️ Video sudah dirender (QC lulus) tapi tidak terupload.\n"
            f"<code>{run_id}</code>"
        )
        return self._send(chat_id, text)

    def notify_failure(self, run_id: str, tenant_id: str, niche: str,
                       error: str, elapsed_seconds: float,
                       run_config=None) -> bool:
        """
        Kirim alert ketika pipeline crash dengan exception tidak tertangani.
        """
        chat_id = self._get_chat_id(run_config)
        if not chat_id:
            return False

        channel = self._channel_name(run_config, {"tenant_id": tenant_id})
        elapsed = self._fmt_elapsed(elapsed_seconds)

        text = (
            f"❌ <b>[{channel}] Pipeline GAGAL!</b>\n"
            f"🏷 Niche: {niche}\n"
            f"💥 Error: <code>{self._escape(str(error)[:250])}</code>\n"
            f"⏰ Runtime: {elapsed}\n"
            f"<code>{run_id}</code>"
        )
        return self._send(chat_id, text)

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    def _get_chat_id(self, run_config=None) -> str:
        """Per-tenant chat_id dulu, fallback ke system."""
        if run_config:
            per_tenant = getattr(run_config, "telegram_chat_id", None)
            if per_tenant:
                return str(per_tenant)
        return self.system_chat_id

    def _channel_name(self, run_config, result: dict) -> str:
        """Ambil nama channel untuk display di pesan."""
        if run_config:
            name = getattr(run_config, "channel_name", "")
            if name:
                return name
        return result.get("tenant_id", "MesinViral")

    def _send(self, chat_id: str, text: str) -> bool:
        """HTTP POST ke Telegram Bot API. Return True jika berhasil."""
        if not self.bot_token:
            return False
        try:
            url  = self._API_URL.format(token=self.bot_token)
            resp = requests.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info(f"[Telegram] ✓ Notifikasi terkirim ke chat_id={chat_id}")
                return True
            logger.warning(
                f"[Telegram] API error {resp.status_code}: {resp.text[:300]}"
            )
            return False
        except Exception as e:
            logger.warning(f"[Telegram] Gagal kirim: {e}")
            return False

    @staticmethod
    def _fmt_elapsed(seconds: float) -> str:
        s = int(seconds or 0)
        return f"{s // 60}m {s % 60}s"

    @staticmethod
    def _fmt_duration(seconds) -> str:
        if not seconds:
            return "—"
        s = int(float(seconds))
        return f"{s // 60}:{s % 60:02d}"

    @staticmethod
    def _escape(text: str) -> str:
        """Escape karakter HTML agar tidak merusak format pesan."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
