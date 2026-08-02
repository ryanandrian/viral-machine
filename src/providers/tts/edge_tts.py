"""
Edge TTS Provider — Microsoft Azure TTS (gratis, tanpa API key).
Provider default untuk semua tenant.

Fix v0.2:
- Word-level timestamps via edge_tts SubMaker (menggantikan estimasi word count)
- Subtitle akurasi naik dari ~60% → ~95%
"""

import asyncio
import re
import time
from pathlib import Path

from loguru import logger

from src.config import ambang as _ambang
from src.exceptions import ErrorClass
from src.providers.tts.base import TTSProvider, TTSError


# Voice mapping per niche — bisa di-override via tenant_configs.tts_voice
# F1-05: NICHE_VOICES (map niche→voice hardcode) DIHAPUS — voice kini single-source
# (channels.voice_key → voice_catalog; niches.voice_* dibuang migr 0083). rate baseline = voice_catalog.default_settings;
# kosong → RATIO 1 (+0%), bukan angka karangan di kode.
# ── BASELINE = RATIO 1 (keputusan owner: "setiap voice sudah dirancang ideal di ratio 1") ─────────
# DULU nilai ini "+10%", ditanam di kode. Akibatnya, untuk kedua suara Indonesia yang
# `voice_catalog.default_settings`-nya KOSONG, setiap video dibacakan 10% LEBIH CEPAT dari rancangan
# suaranya — tanpa terlihat di layar admin, dan tanpa pernah diputuskan siapa pun. Terukur pada satu
# naskah produksi: +0% = 70,3 dtk · +10% = 64,0 dtk · −10% = 78,2 dtk.
# Jadi aturan owner dilanggar DUA kali: tuas kecepatan menggeser suara (sudah dicabut 2026-07-31),
# DAN baselinenya sendiri bukan 1. Nilai netral sekarang +0% = ratio 1; suara yang memang perlu beda
# WAJIB menuliskannya di `voice_catalog.default_settings.rate` supaya terlihat & bisa diubah admin
# (§3.3 config-driven: nol nilai bisnis di kode).
DEFAULT_RATE  = "+0%"


# `_apply_speed_to_rate` DIBUANG 2026-08-01 bersama jalur datanya.
#
# Fungsi itu menggabungkan baseline suara dengan `tts_voice_settings[niche].speed` — lubang tempat
# solver durasi dulu menyuntikkan pengali kecepatan. Solvernya sudah dicabut 31-Jul, TAPI JALUR
# DATANYA TERTINGGAL HIDUP, dan nilai lamanya masih ada di DB setiap tenant (0,83–0,93). Terukur
# 2026-08-01 pada channel yang SEDANG AKTIF:
#
#     BJ Yusroon   (dark_history, preset 90 dtk)  speed 0,83  → dibacakan pada −17%
#     Abyss ID     (ocean_mysteries)              speed 0,86 × baseline +5% → −10%
#
# Jadi keluhan owner "suara sangat lambat, seperti orang malas" MASIH BERLAKU hari ini meski tuasnya
# sudah "dicabut" — karena yang dicabut hanya yang MENULIS, bukan yang MEMBACA. Pelajaran yang sama
# dengan lima generasi perbaikan durasi yang bertumpuk: mencabut separuh rantai membuat separuh sisanya
# jadi ranjau yang lebih sulit dilihat.
#
# Sekarang laju bicara SEMATA-MATA dari `voice_catalog.default_settings` (kenop admin yang terlihat).


class EdgeTTSProvider(TTSProvider):
    """
    Microsoft Edge TTS — gratis, tidak butuh API key.
    Support word-level timestamps via SubMaker untuk subtitle akurat.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        # F1-05: voice ter-resolve di config layer (channels.voice_key → voice_catalog).
        # NO map hardcode, NO fallback (gagal jujur bila kosong). rate = baseline voice_catalog.default_settings.
        self.voice = config.get("tts_voice")
        if not self.voice:
            raise TTSError(
                "Edge TTS: voice belum ter-resolve. Set voice di Channel (channels.voice_key, §10.B FINAL)."
            )
        # LAJU BICARA = HANYA baseline suara dari katalog (kenop admin yang terlihat di layar).
        # Lapisan `tts_voice_settings[niche].speed` TIDAK LAGI DIBACA — lihat catatan di atas: itu lubang
        # tuas kecepatan yang dilarang owner, dan nilai lamanya masih membuat channel aktif dibacakan
        # 17% lebih lambat. Bila lapisan itu masih memuat speed, kita LAPORKAN bahwa ia diabaikan —
        # diam berarti tak seorang pun tahu data basi itu ada.
        from src.production.voice_delivery import rasio_laju, rasio_teks
        _setelan   = (config.get("tts_voice_default_settings") or {})
        self.rate  = _setelan.get("rate") or DEFAULT_RATE
        _niche     = config.get("niche") or ""
        _vs        = config.get("tts_voice_settings") or {}
        _override  = _vs.get(_niche, {}) if isinstance(_vs, dict) else {}
        if _override.get("speed") is not None:
            logger.warning(
                f"[EdgeTTS] setelan lama tts_voice_settings[{_niche}].speed="
                f"{_override.get('speed')} DIABAIKAN — kecepatan suara bukan tuas durasi (aturan owner "
                f"2026-07-29) dan laju bicara hanya boleh dari voice_catalog.default_settings. "
                f"Suara dibacakan pada {self.rate}.")
        # Laju yang BENAR-BENAR dipakai, sebagai RASIO tanpa satuan — direkam ke sampel kalibrasi
        # (0184/0185). Rasio, bukan string penyedia: penjaga kalibrasi harus bisa membandingkan angka
        # dari penyedia mana pun. Kesalahan paling mahal 2026-07-31 lahir dari tidak adanya angka ini.
        from src.config.format_catalog import tts_speed_range as _rng
        self.effective_rate = rasio_teks(rasio_laju(_setelan, _rng(config.get('tts_provider') or 'edge_tts')))
        self._word_timestamps: list[dict] | None = None

    # ──────────────────────────────────────────────
    # Public API (implement abstract methods)
    # ──────────────────────────────────────────────

    async def generate(self, text: str, output_path: Path) -> Path:
        """
        Generate audio MP3 dari teks menggunakan Edge TTS.
        Sekaligus mengumpulkan word-level timestamps untuk subtitle.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            import edge_tts
        except ImportError:
            raise TTSError("edge-tts tidak terinstall. Jalankan: pip install edge-tts")

        logger.info(f"[EdgeTTS] voice={self.voice} rate={self.rate} chars={len(text)}")

        try:
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
            # (FOSIL DICABUT 2026-08-02: `edge_tts.SubMaker()` dibuat lalu tak pernah dipakai —
            #  peninggalan masa Edge masih mengirim WordBoundary. Sejak v7.x hanya SentenceBoundary
            #  yang tersedia, dan penanda kata disusun sendiri di `_parse_sentence_boundaries`.)

            # Stream output — kumpulkan audio + sentence boundary events
            # Edge TTS v7.x: WordBoundary tidak tersedia, pakai SentenceBoundary
            sentence_boundaries = []
            with open(output_path, "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] == "SentenceBoundary":
                        # offset & duration dalam unit 100-nanosecond
                        sentence_boundaries.append({
                            "text":     chunk.get("text", ""),
                            "start":    chunk.get("offset", 0) / 10_000_000,
                            "duration": chunk.get("duration", 0) / 10_000_000,
                        })

            # Konversi sentence boundaries ke word-level timestamps
            self._word_timestamps = self._parse_sentence_boundaries(sentence_boundaries)

            # ── AUDIO TIDAK LENGKAP = GAGAL JUJUR (2026-08-01) ────────────────────────────────────
            # Terbukti nyata: teks 581 huruf menghasilkan audio 27,0 dtk, sementara render ulang teks
            # yang SAMA (dua kali, konsisten) menghasilkan 40,8 dtk — audionya TERPOTONG 13,8 dtk.
            # Sebabnya: aliran dari vendor bisa berhenti di tengah, dan loop di atas hanya berhenti
            # menulis — tanpa error. Berkasnya ada, tak kosong, durasinya "wajar", jadi seluruh
            # pipeline menerimanya. Akibat di produksi: video dengan NARASI TERPUTUS di tengah — dan
            # dulu korektor atempo malah MEREGANGKANNYA agar pas durasi, sehingga cacatnya tersembunyi
            # sempurna. Penonton mendengar cerita yang berhenti mendadak.
            #
            # Pemeriksaan memakai data yang SUDAH ada: penanda kalimat dari vendor. Bila penanda hanya
            # mencakup sebagian teks, sintesis memang tak sampai habis. Tanpa penanda (vendor tak
            # mengirimnya) → tak menuduh apa pun; lapis kedua di `tts_engine` yang menjaga.
            _amb = _ambang.pct("tts_cakupan_min_pct", 85)
            _huruf_teks = len(re.sub(r"\s+", "", text or ""))
            _huruf_penanda = sum(len(re.sub(r"\s+", "", b.get("text") or "")) for b in sentence_boundaries)
            if sentence_boundaries and _huruf_teks > 0:
                _cakupan = _huruf_penanda / _huruf_teks
                if _cakupan < _amb:
                    raise TTSError(
                        f"Suara tidak selesai dibuat: hanya {_cakupan:.0%} naskah yang terucap "
                        f"({_huruf_penanda} dari {_huruf_teks} huruf). Audio tidak lengkap TIDAK "
                        f"dipakai — lebih baik produksi diulang daripada video dengan narasi terputus.",
                        error_class=ErrorClass.TRANSIENT)
                logger.info(f"[EdgeTTS] cakupan naskah {_cakupan:.0%} (ambang {_amb:.0%})")

            size_kb = output_path.stat().st_size / 1024
            logger.info(
                f"[EdgeTTS] Generated: {output_path.name} "
                f"({size_kb:.1f} KB, {len(self._word_timestamps or [])} words)"
            )
            return output_path

        except Exception as e:
            raise TTSError(f"Edge TTS generation failed: {e}") from e

    def get_word_timestamps(self) -> list[dict] | None:
        """
        Return word-level timestamps dari generate() terakhir.
        Format: [{'word': str, 'start': float, 'end': float}]
        start/end dalam satuan detik.
        """
        return self._word_timestamps

    @property
    def provider_name(self) -> str:
        return "edge_tts"

    @property
    def supports_word_timestamps(self) -> bool:
        # v7.x: SentenceBoundary tersedia, dikonversi ke word timestamps
        # Akurasi ~80-85% (bukan true word timestamps, tapi lebih baik dari estimasi)
        return True

    # (FOSIL DICABUT 2026-08-02: `estimate_duration()` — menaksir durasi dari UKURAN BERKAS dengan
    #  asumsi bitrate 128 kbps. Nol pemanggil, dan komentarnya sendiri berbohong: "digunakan oleh
    #  pipeline" — pipeline memakai ffprobe. Rumus durasi ketiga yang menganggur di rantai yang paling
    #  sensitif terhadap durasi = jebakan bagi siapa pun yang kelak mencarinya.)

    # ──────────────────────────────────────────────
    # Internal: parse SubMaker → word timestamp list
    # ──────────────────────────────────────────────

    @staticmethod
    def _parse_sentence_boundaries(boundaries: list[dict]) -> list[dict]:
        """
        Konversi SentenceBoundary events ke word-level timestamps.

        Edge TTS v7.x tidak lagi emit WordBoundary — hanya SentenceBoundary.
        Kita distribute timing per kalimat ke setiap kata secara proporsional.
        Akurasi: ~80-85% (lebih baik dari pure word count estimasi ~60-70%).
        """
        if not boundaries:
            return []

        timestamps = []
        try:
            for sentence in boundaries:
                text     = sentence["text"].strip()
                start    = sentence["start"]
                duration = sentence["duration"]

                if not text or duration <= 0:
                    continue

                words = text.split()
                if not words:
                    continue

                # Distribute durasi kalimat ke setiap kata secara proporsional
                # Kata lebih panjang = durasi lebih lama (lebih akurat dari rata-rata)
                total_chars = sum(len(w) for w in words)
                current_time = start

                for word in words:
                    clean = word.strip()  # s71d: pertahankan tanda baca untuk karaoke natural
                    if not clean:
                        continue
                    # Durasi proporsional berdasarkan panjang karakter
                    word_duration = duration * (len(word) / total_chars) if total_chars > 0 else duration / len(words)
                    timestamps.append({
                        "word":  clean,
                        "start": round(current_time, 3),
                        "end":   round(current_time + word_duration, 3),
                    })
                    current_time += word_duration

        except Exception as e:
            logger.warning(f"[EdgeTTS] Could not parse sentence boundaries: {e}")

        return timestamps


# ──────────────────────────────────────────────────────
# Sync wrapper — untuk kompatibilitas dengan pipeline lama
# yang belum async
# ──────────────────────────────────────────────────────

def generate_sync(text: str, config: dict, output_dir: str = "logs") -> tuple[str, list[dict]]:
    """
    Sync wrapper untuk EdgeTTSProvider.
    Return: (audio_path, word_timestamps)
    Dipanggil dari tts_engine.py (thin wrapper).
    """
    provider    = EdgeTTSProvider(config)
    tenant_id   = config.get("tenant_id", "default")
    timestamp   = int(time.time())
    output_path = Path(output_dir) / f"audio_{tenant_id}_{timestamp}.mp3"

    audio_path  = asyncio.run(provider.generate(text, output_path))
    timestamps  = provider.get_word_timestamps() or []

    return str(audio_path), timestamps


if __name__ == "__main__":
    # Quick test
    test_config = {
        "tts_provider": "edge_tts",
        "tts_voice":    "en-US-GuyNeural",
        "niche":        "universe_mysteries",
        "tenant_id":    "test",
    }
    audio, words = generate_sync(
        "The universe is 13.8 billion years old. Scientists believe dark matter makes up 27 percent of it.",
        test_config,
        output_dir="logs"
    )
    print(f"Audio: {audio}")
    print(f"Words: {words[:5]}...")
