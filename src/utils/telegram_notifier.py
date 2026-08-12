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

# Batas KERAS milik Telegram untuk satu pesan `sendMessage`. Ini SATU-SATUNYA batas panjang di
# seluruh rantai pesan galat yang berasal dari luar — semua angka lain dulu diketik sendiri tanpa
# dasar (§8h AI_ERROR_MANAGEMENT: 13 angka berbeda di jalur yang sama). Lewat batas ini Telegram
# MENOLAK pesannya ⇒ notifikasinya hilang seluruhnya, jadi meringkas di sini bukan pilihan gaya.
BATAS_TELEGRAM = 4096


def ringkas_diumumkan(teks: str | None, ruang: int) -> str:
    """Ringkas HANYA bila melebihi `ruang`, dan **UMUMKAN** potongannya.

    Kenapa diumumkan, bukan sekadar "…": potongan senyap terbaca PERSIS seperti pesan utuh. Itulah
    sebab pesan Groq yang terputus di *"…on tokens per day (TPD): Li"* lolos berbulan-bulan — tak
    ada satu pun tanda bahwa masih ada "Limit 100000, Used 97045, try again in 34m37s" di baliknya.
    Owner, tenant, dan Claude sendiri sama-sama tertipu olehnya.

    Aturan yang dijaga uji: teks yang MUAT tidak disentuh sama sekali · hasil tak pernah melebihi
    `ruang` · bila diringkas, jumlah huruf yang disembunyikan DISEBUTKAN.
    """
    teks = teks or ""
    if len(teks) <= ruang:
        return teks
    # Penanda dihitung dari panjang FINALnya sendiri (pakai perkiraan lebar angka) supaya hasil
    # dijamin muat — bukan diperkirakan lalu meleset.
    for lebar_angka in (7, 8, 9, 10):
        tanda = f"… [dipotong {'9' * lebar_angka} huruf — teks penuh di halaman run]"
        sisa = ruang - len(tanda)
        if sisa <= 0:
            continue
        hilang = len(teks) - sisa
        if len(str(hilang)) <= lebar_angka:
            return teks[:sisa] + f"… [dipotong {hilang} huruf — teks penuh di halaman run]"
    return teks[:max(0, ruang)]          # ruang terlalu sempit untuk penanda → potong apa adanya


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

        # [2026-08-12] ISTILAH INGGRIS DIGANTI + NOMOR INTERNAL DICABUT.
        # Owner: *"di bawah url ada kode yang tidak dipahami siapapun"* — itu `run_id`, identitas
        # produksi internal, dicetak mentah ke mata tenant. Tautan videonya sudah menjadi identitas
        # yang berarti; nomor itu hanya berguna untuk diagnosa kita, dan diagnosa dibaca dari log/DB,
        # bukan dari Telegram tenant. "Hook score"/"clips"/"Published"/"Runtime" → bahasa Indonesia
        # (§4.1: nol istilah teknis pada teks yang dibaca manusia non-teknis).
        is_test = result.get("run_kind") in ("test", "admin_test")
        _rinci = [
            f"🎬 <i>{self._escape(title)}</i>",
            f"🎯 Skor daya-tarik: <b>{hook_score}/100</b>  |  🏷 Niche: {niche}",
            f"⏱ Durasi: {duration_str}  |  💾 {size_mb} MB  |  🎞 {clips} adegan",
        ]
        if is_test:
            lines = [
                f"🧪 <b>[{channel}] VIDEO UJI (PRIVAT)</b>",
                "⚠️ <i>Pratinjau konfigurasi via tombol \"Uji sekarang\" — di-upload PRIVAT di YouTube (bukan publikasi publik) & memakai kredit AI (BYOK) Anda.</i>",
                *_rinci,
            ]
        else:
            lines = [f"✅ <b>[{channel}] Video terbit</b>", *_rinci]
        if video_id:
            lines.append(f"🔗 {url}")
        lines.append(f"⏰ Lama produksi: {elapsed}  |  📝 {ts} kata")

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
        # [2026-08-12] Nomor produksi internal (`run_id`) TIDAK lagi dicetak ke mata tenant — tak ada
        # gunanya bagi mereka. Parameternya TETAP ada (pemanggil menyerahkannya) dan kini dipakai di
        # LOG, supaya kaitan pesan↔run tetap bisa ditelusuri saat diagnosa — bukan parameter mati.
        logger.info(f"[Telegram] catatan QC dikirim ke tenant={tenant_id} run={run_id}")
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

    @classmethod
    def aman(cls, nilai) -> str:
        """Bersihkan NILAI sebelum diselipkan ke pesan ADMIN. Pakai ini, jangan `str()` mentah.

        [2026-08-12] Kenapa perlu: pesan dikirim dengan `parse_mode=HTML`. Bila nilai yang diselipkan
        memuat `<`, `>` atau `&` — sangat mungkin pada teks galat penyimpanan, yang balasannya
        berbentuk XML — Telegram MENOLAK seluruh pesannya dan owner **tidak menerima apa pun**.
        Alarm terpenting (penyimpanan mati = semua channel berhenti) justru yang paling berisiko hilang.
        Jalur ke TENANT sudah dibersihkan sejak lama (`notify_tenant`); jalur ke OWNER belum.
        Yang dibersihkan hanya NILAI, bukan templatnya — templat memang memuat `<b>`/`<code>` yang sah.
        Catatan jujur: bahaya ini BELUM pernah terjadi (nol pesan ditolak sepanjang riwayat log) —
        ditutup karena murah, bukan karena sudah menimbulkan kerusakan.
        """
        return cls._escape(str(nilai))

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
                         niche: str = "", channel_name: str = "",
                         duration_secs: float | None = None, size_mb: float | None = None,
                         clips: int | None = None, hook_score: float | None = None,
                         words: int | None = None) -> bool:
        """OPSI C: laporan SUKSES dikirim saat PUBLISHER benar-benar mempublish (on-schedule),
        BUKAN saat producer stok. Chat_id resolve dari tenant_configs.
        [B11] Batch 1.5: channel_name PER-CHANNEL — tenant multi-channel tahu channel mana yang terbit.

        [2026-08-12] DILENGKAPI + NOMOR INTERNAL DICABUT. Owner: *"mengapa pesan published tidak
        selengkap pesan video uji?"* Sebabnya bukan pilihan redaksi: pesan uji dikirim DI DALAM mesin
        produksi (semua angka masih di tangan), sedangkan pesan ini dikirim JAUH KEMUDIAN oleh
        penerbit — dan penerbit dulu hanya diberi tautan/judul/niche. Angkanya SUDAH ADA di
        `content_inventory.metadata` (terbukti pada baris nyata: `duration_secs` 54.5 · `size_mb`
        24.7 · `viral_score` 79.8 · `script.word_count`) — hanya belum pernah diserahkan.
        Semua angka OPSIONAL: bila datanya tak ada, barisnya tak muncul (baris lama tetap aman).
        `run_id` DICABUT dari tanda tangan: ia dicetak mentah ke mata tenant tanpa guna, dan
        membiarkannya sebagai parameter tak-terpakai = fosil (§3.2).
        ⚠️ Lama produksi TIDAK ditampilkan di sini — angka itu tidak ada di data yang dipegang
        penerbit, dan menambah kueri DB demi satu angka hiasan tak sepadan.
        """
        chat_id = self._chat_id_for_tenant(tenant_id)
        if not chat_id:
            return False
        head = (f"✅ <b>[{self._escape(str(channel_name))}] Video terbit</b>"
                if channel_name else "✅ <b>Video terbit</b>")
        _angka = []
        if duration_secs:
            _angka.append(f"⏱ Durasi: {self._fmt_duration(duration_secs)}")
        if size_mb:
            _angka.append(f"💾 {size_mb} MB")
        if clips:
            _angka.append(f"🎞 {clips} adegan")
        if words:
            _angka.append(f"📝 {words} kata")
        lines = [
            head,
            f"🎬 <i>{self._escape(str(title)[:120])}</i>" if title else "",
            f"🏷 Niche: {self._escape(str(niche))}" if niche else "",
            f"🎯 Skor daya-tarik: <b>{round(float(hook_score))}/100</b>" if hook_score else "",
            "  |  ".join(_angka) if _angka else "",
            f"🔗 {url}" if url else "",
        ]
        return self._send(chat_id, "\n".join(l for l in lines if l))

    def notify_publish_fail(self, run_id: str, tenant_id: str, error: str,
                            error_class: str = "", run_config=None) -> bool:
        """
        Kirim alert ketika QC lulus tapi upload YouTube gagal.

        [ERROR-MGMT §8b 2026-08-04] Kini SERAGAM dengan `notify_circuit_break`: menjawab satu bit
        yang paling menentukan bagi tenant — **perlu bertindak, atau cukup ditunggu?** Sebelum ini
        notifikasi ini adalah satu-satunya yang tidak bisa menjawabnya, padahal `publish()` sudah
        mengembalikan `error_class` (dibuang di pemanggil). Akibatnya kegagalan yang pulih sendiri
        (mis. jatah unggah harian) terlihat sama gentingnya dengan koneksi YouTube yang putus permanen.

        Sumber jawaban = `SELF_HEALING` (src/exceptions.py) — **per KELAS, bukan per nama penyedia**
        (arahan owner: penyedia & model akan terus bertambah). `error_class` kosong/tak dikenal →
        TIDAK mengarang: cukup katakan akan dicoba ulang otomatis.

        Argumen `error_class` disisipkan SEBELUM `run_config` yang selalu dipanggil sebagai keyword
        (satu-satunya pemanggil: pipeline STEP publish) — aman, tapi tetap keyword-only secara praktik.
        """
        chat_id = self._get_chat_id(run_config)
        if not chat_id:
            return False

        from src.exceptions import SELF_HEALING, ErrorClass
        try:
            _pulih = ErrorClass(error_class) in SELF_HEALING if error_class else None
        except ValueError:
            _pulih = None   # kelas asing (mis. dari versi lebih baru) → jangan mengarang

        if _pulih is True:
            anjuran = ("⏳ Penyebabnya pulih sendiri — tidak ada yang perlu Anda ubah.\n"
                       "Video tetap tersimpan dan akan diunggah ulang otomatis.")
        elif _pulih is False:
            anjuran = ("🔧 Penyebabnya TIDAK pulih sendiri — ada satu hal yang perlu Anda kerjakan.\n"
                       "👉 Periksa <b>Koneksi YouTube</b> pada channel ini di menu Channel.")
        else:
            anjuran = "ℹ️ Video sudah dirender (QC lulus) tapi belum terunggah; akan dicoba ulang otomatis."

        channel = self._channel_name(run_config, {"tenant_id": tenant_id})
        # Ruang untuk pesan galat = sisa jatah Telegram SETELAH bagian tetap — bukan angka yang
        # diketik sendiri. Dulu `str(error)[:200]` memotong diam-diam: 200 tak melindungi apa pun
        # (batas nyatanya 4096) dan potongannya tak diumumkan, jadi pesan setengah terbaca utuh.
        # [2026-08-12] Nomor produksi internal dicabut dari mata tenant — templat pengukur di bawah
        # WAJIB ikut berubah, kalau tidak sisa jatah dihitung terlalu pelit dan ekor pesan penyedia
        # terpotong tanpa sebab.
        _tetap = (f"📤 <b>[{channel}] Unggah ke YouTube GAGAL</b>\n"
                  f"💥 Sebab: <code></code>\n{anjuran}")
        _galat = self._escape(ringkas_diumumkan(str(error), max(0, BATAS_TELEGRAM - len(_tetap))))
        text = (
            f"📤 <b>[{channel}] Unggah ke YouTube GAGAL</b>\n"
            f"💥 Sebab: <code>{_galat}</code>\n"
            f"{anjuran}"
        )
        logger.info(f"[Telegram] kabar gagal-unggah ke tenant={tenant_id} run={run_id}")
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

        # [2026-08-12] TIGA hal dibetulkan sekaligus, semuanya kelas yang sama dengan yang sudah
        # diketok owner:
        #  (1) `str(error)[:250]` = pemotongan SENYAP — pola yang dilarang (§8h: 13 pemotongan
        #      dicabut 06-Agu; "jangan pasang batas panjang pesan"). Fungsi sebelahnya
        #      (`notify_publish_fail`) sudah memakai cara yang benar: hitung sisa jatah Telegram
        #      lalu UMUMKAN bila memang harus dipendekkan. Di sini masih tertinggal.
        #  (2) "Pipeline"/"Runtime" = istilah teknis pada teks yang dibaca tenant (§4.1).
        #  (3) Nomor produksi internal dicabut dari mata tenant; tetap dicatat di log kita.
        _tetap = (f"❌ <b>[{channel}] Produksi GAGAL</b>\n"
                  f"🏷 Niche: {niche}\n"
                  f"💥 Sebab: <code></code>\n"
                  f"⏰ Lama produksi: {elapsed}")
        _galat = self._escape(ringkas_diumumkan(str(error), max(0, BATAS_TELEGRAM - len(_tetap))))
        text = (
            f"❌ <b>[{channel}] Produksi GAGAL</b>\n"
            f"🏷 Niche: {niche}\n"
            f"💥 Sebab: <code>{_galat}</code>\n"
            f"⏰ Lama produksi: {elapsed}"
        )
        logger.info(f"[Telegram] kabar gagal-produksi ke tenant={tenant_id} run={run_id}")
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
