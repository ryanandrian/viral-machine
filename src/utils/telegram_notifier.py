"""
Telegram Notifier — MesinViral.com
Kirim laporan hasil produksi ke Telegram Bot.

Prinsip:
- Fire-and-forget: error TIDAK pernah menghentikan pipeline
- Per-tenant: chat_id WAJIB dari tenant_config/DB (tenant_configs.telegram_chat_id). TANPA fallback env
  (tenant belum connect → notif di-skip, tak nyasar ke chat platform/owner).
- Satu bot (TELEGRAM_BOT_TOKEN) untuk semua tenant (platform)
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
        # NO fallback env TELEGRAM_CHAT_ID: chat_id WAJIB per-tenant dari DB (tenant_configs.telegram_chat_id).
        # Tenant belum connect → notif di-skip (bukan nyasar ke chat platform/owner).

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

        is_test = result.get("run_kind") in ("test", "admin_test")
        if is_test:
            lines = [
                f"🧪 <b>[{channel}] VIDEO UJI (PRIVATE)</b>",
                "⚠️ <i>Pratinjau konfigurasi via tombol \"Test now\" — di-upload PRIVAT di YouTube (bukan publikasi publik) & memakai kredit AI (BYOK) Anda.</i>",
                f"🎬 <i>{self._escape(title)}</i>",
                f"🎯 Hook score: <b>{hook_score}/100</b>  |  🏷 Niche: {niche}",
                f"⏱ Durasi: {duration_str}  |  💾 {size_mb} MB  |  🎞 {clips} clips",
            ]
        else:
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
                       run_config=None, url: str = "", recommendation: str = "",
                       is_test: bool = False) -> bool:
        """
        ADVISORY (Opsi A — QC_CONTENT_ARCHITECTURE.md §3/§6.2): video gagal QC TIDAK dibuang
        → di-publish PRIVAT untuk ditinjau tenant. Sertakan alasan + rekomendasi (dinamis,
        no-hardcode) + URL privat. Tenant putuskan: jadikan publik atau hapus.
        is_test=True (tombol "Test now") → tandai jelas di awal bahwa ini video uji.
        """
        chat_id = self._get_chat_id(run_config)
        if not chat_id:
            return False

        channel      = self._channel_name(run_config, {"tenant_id": tenant_id})
        duration_str = f"{duration_secs:.1f}s" if duration_secs else "—"

        # POLES PESAN (owner 2026-07-15): nada TENANG & bermartabat — video ber-catatan = PILIHAN
        # tenant, bukan "GAGAL". Alasan teknis mentah ('di luar ±15% preset 60s') DITERJEMAHKAN ke
        # bahasa manusia (fallback aman utk alasan tak dikenal — bukan parsing rapuh).
        note = self._humanize_qc_reason(qc_reason)

        lines = []
        if is_test:
            lines.append("🧪 <b>Video uji (privat)</b> — dari tombol \"Test\", memakai kredit AI (BYOK) Anda.")
        lines += [
            f"🎬 <b>[{channel}] 1 video selesai — menunggu keputusan Anda</b>",
            f"📋 Topik: <i>{self._escape(str(topic)[:100])}</i>",
            f"📝 {note}",
            f"⏱ Durasi: {duration_str}",
        ]
        if url:
            lines.append(f"👀 Pratinjau: {url}")
        lines.append("👉 Tinjau lalu putuskan: <b>Terbitkan</b> atau <b>Buat ulang</b>.")
        lines.append(f"<code>{run_id}</code>")
        return self._send(chat_id, "\n".join(lines))

    @staticmethod
    def _humanize_qc_reason(reason: str) -> str:
        """Terjemah alasan QC teknis → kalimat manusiawi menenangkan (fallback aman utk yg tak dikenal).
        Tujuan (owner 2026-07-15): tenant tak melihat jargon '±15% preset 60s' yg bikin panik/menilai mesin buruk."""
        r = (reason or "").lower()
        if "durasi" in r:
            return "Durasinya sedikit berbeda dari target ideal — video tetap layak; Anda yang menentukan."
        if "aspect" in r or "rasio" in r or "9:16" in r:
            return "Format layarnya perlu Anda cek sebentar sebelum tayang."
        if "audio" in r or "suara" in r:
            return "Bagian suaranya perlu Anda cek sebentar sebelum tayang."
        if "kecil" in r or "mb" in r or "render" in r:
            return "Berkas videonya perlu Anda tinjau sebentar sebelum tayang."
        return "Video ini perlu Anda tinjau sebentar sebelum tayang."

    def notify_circuit_break(self, tenant_id: str, channel_id: str, reason: str,
                             channel_name: str = "", error_class: str = "") -> bool:
        """REM DARURAT §4b/F7: produksi channel DIHENTIKAN otomatis (gagal beruntun). Alarm KERAS,
        dikirim SEKETIKA (tak menunggu slot) — cegah loop bakar-kredit.
        Header SERAGAM dgn notif lain: [nama channel] (owner 2026-07-10 — dulu UUID mentah,
        tenant awam tak paham); fallback UUID hanya bila nama tak diberikan (caller lama)."""
        chat_id = self._chat_id_for_tenant(tenant_id)
        if not chat_id:
            return False
        display = self._escape(str(channel_name or channel_id))
        # [B25] Satu bit yang paling menentukan bagi tenant: PERLU BERTINDAK ATAU TIDAK.
        # Dulu anjurannya menebak untuk semua kasus ("mis. saldo/kredensial AI") — dan tenant yang
        # sebabnya sebenarnya pulih sendiri tetap membiarkan channelnya mati berhari-hari.
        # Sumber kebenaran = `SELF_HEALING` (src/exceptions.py), BUKAN nama penyedia.
        from src.exceptions import SELF_HEALING, ErrorClass
        try:
            _pulih = ErrorClass(error_class) in SELF_HEALING if error_class else None
        except ValueError:
            _pulih = None
        if _pulih is True:
            anjuran = ("⏳ Penyebabnya pulih sendiri — Anda tidak perlu mengubah pengaturan apa pun.\n"
                       "👉 Buka channel Anda, lalu tekan <b>Pulihkan produksi</b>.")
        elif _pulih is False:
            anjuran = ("🔧 Penyebabnya TIDAK pulih sendiri — ada satu hal yang perlu Anda kerjakan dulu.\n"
                       "👉 Buka channel Anda: di sana tertulis langkahnya beserta tombol pemulihnya.")
        else:
            anjuran = "👉 Buka channel Anda untuk melihat penyebab & tombol <b>Pulihkan produksi</b>."
        base = (os.getenv("APP_BASE_URL", "") or "").rstrip("/")
        tautan = f"\n🔗 {base}/channels/{channel_id}" if base else ""
        text = (
            f"🛑 <b>[{display}] Produksi DIHENTIKAN otomatis</b>\n"
            f"⚠️ {self._escape(reason)}\n"
            f"{anjuran}{tautan}"
        )
        return self._send(chat_id, text)

    def notify_review_pending(self, tenant_id: str, title: str, qc_reason: str,
                              recommendation: str = "", run_config=None) -> bool:
        """Video JADI tapi ber-catatan QC → masuk antrean Review (jalur TERJADWAL/Opsi C).
        (Owner 2026-07-10): tanpa notif ini tenant tak tahu ada video menunggu keputusan →
        didiamkan → TTL buang otomatis → biaya produksi hangus senyap. Arahan aksi jelas.
        Chat & toggle per-tenant via run_config (pola notify_qc_fail); TTL & URL config-driven."""
        chat_id = self._get_chat_id(run_config)
        if not chat_id:
            return False
        channel  = self._channel_name(run_config, {"tenant_id": tenant_id})
        ttl_days = max(1, round(float(os.getenv("BUFFER_TTL_HOURS", "72")) / 24))
        base     = (os.getenv("APP_BASE_URL", "") or "").rstrip("/")
        lines = [
            f"⚠️ <b>[{self._escape(channel)}] 1 video menunggu keputusan Anda</b>",
            f"📋 Judul: <i>{self._escape(str(title)[:100])}</i>",
            f"📝 Catatan QC: {self._escape(qc_reason)}",
        ]
        if recommendation:
            lines.append(f"💡 Saran: {self._escape(recommendation)}")
        lines.append("👉 Buka menu <b>Review</b> → putuskan <b>Pakai (terbitkan)</b> atau <b>Buang</b>.")
        lines.append(f"⏳ Tanpa keputusan, video terbuang otomatis dalam ±{ttl_days} hari — biaya produksinya hangus.")
        if base:
            lines.append(f"🔗 {base}/review")
        return self._send(chat_id, "\n".join(lines))

    def notify_tenant(self, sb, tenant_id: str, text: str) -> bool:
        """Kirim TEKS bebas ke Telegram TENANT by tenant_id — resolve chat_id + HORMATI saklar
        `telegram_enabled` dari tenant_configs. Untuk jalur yang tak punya run_config (publisher
        terjadwal — wiring pasca-insiden S3 2026-07-13: kegagalan publish slot dulu senyap).
        Teks di-escape (parse_mode HTML). Fail-soft: chat kosong/toggle off/error → False."""
        try:
            if not sb or not tenant_id:
                return False
            r = (sb.table("tenant_configs").select("telegram_chat_id, telegram_enabled")
                 .eq("tenant_id", tenant_id).limit(1).execute())
            row = (r.data or [{}])[0]
            if row.get("telegram_enabled") is False:
                return False   # tenant mematikan notif — hormati
            chat = row.get("telegram_chat_id")
            if not chat:
                return False
            return self._send(str(chat), self._escape(text))
        except Exception as e:
            logger.warning(f"[Telegram] notify_tenant gagal (non-fatal): {e}")
            return False

    def notify_admin(self, text: str) -> bool:
        """Notif ke ADMIN PLATFORM (owner/tim) — mis. LEAD PANAS layak outreach personal (LIFECYCLE nurture).
        chat_id dari company_profile.admin_telegram_chat_id (no-hardcode, editable owner di /admin/company-profile);
        fallback env ADMIN_TELEGRAM_CHAT_ID. BEDA dari notif per-tenant. Fail-soft: skip diam-diam bila kosong."""
        admin_chat = self._admin_chat_id()
        if not admin_chat:
            return False
        return self._send(admin_chat, text)

    def notify_admin_feedback(self, reason: str = "", source: str = "", tenant_id: str = "",
                              email: str = "", message: str = "") -> bool:
        """Masukan baru dari halaman /feedback (B8) → kabari ADMIN (reuse notify_admin/company_profile).
        Fail-soft: dipanggil server-to-server pasca-insert, tak boleh menggagalkan submit tenant."""
        lines = [
            "📝 <b>Masukan baru</b> (/feedback)",
            f"• Alasan: <b>{self._escape(str(reason))}</b>" if reason else "",
            f"• Sumber: {self._escape(str(source))}" if source else "",
            f"• Tenant: <code>{self._escape(str(tenant_id))}</code>" if tenant_id else "• Tenant: anonim",
            f"• Email: {self._escape(str(email))}" if email else "",
            f"💬 {self._escape(str(message)[:500])}" if message else "",
            "👉 Detail: https://mesinviral.com/admin/feedback",
        ]
        return self.notify_admin("\n".join(l for l in lines if l))

    def _admin_chat_id(self) -> str:
        """chat_id admin dari company_profile (utama, editable) → env ADMIN_TELEGRAM_CHAT_ID (fallback). Kosong → ''."""
        try:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            r = sb.table("company_profile").select("admin_telegram_chat_id").limit(1).execute()
            if r.data and r.data[0].get("admin_telegram_chat_id"):
                return str(r.data[0]["admin_telegram_chat_id"]).strip()
        except Exception as e:
            logger.debug(f"[Telegram] baca admin chat_id (company_profile) gagal: {e}")
        return os.getenv("ADMIN_TELEGRAM_CHAT_ID", "").strip()

    def _chat_id_for_tenant(self, tenant_id: str) -> str:
        """Resolve chat_id tenant dari tenant_configs (hormati toggle telegram_enabled). Tak ada fallback sistem."""
        try:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            r = (sb.table("tenant_configs").select("telegram_chat_id,telegram_enabled")
                 .eq("tenant_id", tenant_id).limit(1).execute())
            if r.data:
                row = r.data[0]
                if row.get("telegram_enabled", True) and row.get("telegram_chat_id"):
                    return row["telegram_chat_id"]
        except Exception as e:
            logger.warning(f"[Telegram] resolve chat_id tenant gagal: {e}")
        return ""   # tak ada fallback sistem — tenant belum set chat_id → notif di-skip

    def notify_published(self, tenant_id: str, url: str, title: str = "",
                         niche: str = "", run_id: str = "", channel_name: str = "") -> bool:
        """OPSI C: laporan SUKSES dikirim saat PUBLISHER benar-benar mempublish (on-schedule),
        BUKAN saat producer stok. Chat_id resolve dari tenant_configs.
        [B11] Batch 1.5: channel_name PER-CHANNEL — tenant multi-channel tahu channel mana yang terbit."""
        chat_id = self._chat_id_for_tenant(tenant_id)
        if not chat_id:
            return False
        head = (f"✅ <b>[{self._escape(str(channel_name))}] Video Published!</b>"
                if channel_name else "✅ <b>Video Published!</b>")
        lines = [
            head,
            f"🎬 <i>{self._escape(str(title)[:120])}</i>" if title else "",
            f"🏷 Niche: {self._escape(str(niche))}" if niche else "",
            f"🔗 {url}" if url else "",
            f"<code>{run_id}</code>" if run_id else "",
        ]
        return self._send(chat_id, "\n".join(l for l in lines if l))

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
        """Per-tenant chat_id dari run_config (DB), hormati toggle telegram_enabled.
        Kosong / toggle off → "" (notif di-skip, no fallback)."""
        if run_config:
            if not getattr(run_config, "telegram_enabled", True):
                return ""   # tenant matikan notif Telegram → skip
            per_tenant = getattr(run_config, "telegram_chat_id", None)
            if per_tenant:
                return str(per_tenant)
        return ""   # tak ada fallback sistem — tenant belum set chat_id → notif di-skip

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
