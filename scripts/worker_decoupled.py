"""
Worker v2 DECOUPLED (Phase 5.3 cutover) — Producer + Publisher loop konkuren.

Menggantikan model lama produce+publish-satu-tarikan (`scripts/worker.py`). DESAIN §12c:
  • PRODUCER  : loop persisten, jaga stok buffer per-channel; rem semaphore = jumlah core
                (MAX_CONCURRENT_RENDER) → anti-OOM. Render → upload Biznet S3 → content_inventory.
  • PUBLISHER : loop 30s, publish video ready dari buffer saat slot (TIMEZONE TENANT).

Self-driven (producer baca `channels`, publisher baca slot) → TIDAK perlu pg_cron dispatcher
(itu yang treat publish_slots sbg UTC = Bug 1; di sini timezone-aware).

⚠️ Deploy v2 (saat cutover, bukan sekarang) — env WAJIB:
  SUPABASE_URL=<v2>  SUPABASE_KEY=<service_role>  ENCRYPTION_KEY=<...>  S3_*=<Biznet>
  @reboot cd ~/viral-machine && python3.11 scripts/worker_decoupled.py >> logs/worker.log 2>&1
"""

import faulthandler
import json
import os
import sys
import time
import signal
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# KEMATIAN MENDADAK TIDAK BOLEH BISU  —  ditambah 2026-08-13
#
# KEADAAN YANG DIOBATI (terukur dari catatan inti sistem operasi, bukan dugaan):
# mesin ini **mati mendadak 11 kali** — 1 kali 3-Jul, lalu **10 kali dalam 18 hari** sejak 27-Jul,
# terakhir 13-Agu 07:54. Server menghidupkannya lagi dalam 10 detik (`Restart=always`), jadi dari
# luar semuanya tampak normal. **Tidak ada satu pun kabar, catatan, atau penghitung** di aplikasi
# kita. Kerusakan yang terukur sejauh ini kecil (3 produksi mati di tengah, satu di antaranya
# kasus 12-Agu yang sudah diperbaiki) — tapi **sebabnya tidak diketahui** dan lajunya naik tajam,
# jadi kita tak punya cara tahu apakah akibat terburuknya sudah terlihat.
#
# Catatan inti sistem menunjuk kematian itu terjadi **di dalam mesin bahasa Python sendiri** (satu
# di antaranya melompat ke alamat kosong), BUKAN di pustaka gambar/font — dugaan itu sudah dicabut.
# Hanya proses INI yang mati; proses webhook nol kali, proses lain di server nol kali.
#
# DUA HAL DI BAWAH, DAN KENAPA BENTUKNYA SEPERTI INI:
#
#   1. `faulthandler.enable()` — pada DETIK mesin mati, ia menuliskan apa yang sedang dikerjakan
#      SETIAP bagian mesin (berkas + nomor baris), plus penunjuk bagian mana yang benar-benar mati.
#      DIBUKTIKAN, bukan dipercayai dari dokumentasi: dijalankan pada tiruan mesin ini (beberapa
#      bagian serentak) lalu dimatikan dengan sebab yang SAMA jenisnya → rekamannya memuat keempat
#      bagian lengkap dengan nomor baris. Tulisannya keluar ke stderr, dan setelan layanan
#      (`StandardError=append:worker.log`) sudah mengarahkannya ke catatan server — terbukti dari
#      peringatan pustaka lain yang memang muncul di sana.
#      Nol biaya jalan: ia hanya memasang penangkap sinyal, tidak bekerja apa pun selama mesin sehat.
#
#   2. Penanda keadaan — supaya kematian **diketahui**, bukan cuma terekam. Mesin menulis
#      "berhenti wajar" HANYA bila ia melewati baris penutupnya. Diuji ke data nyata: **4 dari 4
#      tepat** (07:54 & 12-Agu 19:00 mati mendadak → tak ada baris penutup · 10:21 & 15:05 restart
#      wajar → ada).
#      **Disimpan di BERKAS, bukan basis data**, dengan dua alasan: (a) ia tetap bisa dibaca saat
#      basis data/jaringan bermasalah — justru keadaan yang paling mungkin bertepatan dengan
#      kematian; (b) nol tambahan tulisan ke basis data (owner: *"pastikan ini tidak memberatkan
#      mesin itu sendiri"*).
#      Letaknya `/var/tmp` — sengaja BUKAN di dalam repo (tak mengotori `git status` di server) dan
#      BUKAN `/tmp` (yang bisa dibersihkan saat server dinyalakan ulang → alarm palsu).
#      TIGA keadaan, bukan dua: berkas belum ada = **jalan pertama kali** (bukan kematian) ·
#      "jalan" = mati sebelum sempat berhenti wajar · "bersih" = berhenti wajar. Tanpa keadaan
#      ketiga, pemasangan pertama akan selalu melapor kematian palsu.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
faulthandler.enable()

_BERKAS_KEADAAN = os.getenv("WORKER_EXIT_MARKER", "/var/tmp/mv-worker-keadaan.json")
_JEDA_KABAR_JAM = float(os.getenv("WORKER_CRASH_ALARM_COOLDOWN_H", "1"))


def _baca_keadaan() -> dict:
    """Keadaan terakhir yang tercatat. Gagal baca/berkas rusak → {} (dianggap jalan pertama kali:
    lebih baik diam sekali daripada melapor kematian yang tak pernah terjadi)."""
    try:
        with open(_BERKAS_KEADAAN, encoding="utf-8") as f:
            isi = json.load(f)
        return isi if isinstance(isi, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.warning(f"[WorkerV2] penanda keadaan tak terbaca ({e}) — dianggap jalan pertama kali")
        return {}


def _tulis_keadaan(keadaan: str, kabar_terakhir=None) -> None:
    """Simpan keadaan. Fail-soft: gagal menulis TIDAK boleh menghalangi mesin bekerja — paling buruk
    kita kehilangan satu kabar, dan itu jauh lebih ringan daripada produksi tidak jalan."""
    try:
        isi = {"keadaan": keadaan}
        if kabar_terakhir is not None:
            isi["kabar_terakhir"] = kabar_terakhir
        else:
            lama = _baca_keadaan().get("kabar_terakhir")
            if lama is not None:
                isi["kabar_terakhir"] = lama
        tmp = _BERKAS_KEADAAN + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(isi, f)
        os.replace(tmp, _BERKAS_KEADAAN)      # ganti utuh — jangan pernah tinggalkan berkas separuh
    except Exception as e:
        logger.warning(f"[WorkerV2] tulis penanda keadaan gagal (non-fatal): {e}")


def periksa_kematian_sebelumnya(kirim_kabar=None) -> str:
    """Bandingkan keadaan tercatat dengan kenyataan bahwa kita baru saja dinyalakan.

    Return: `"pertama"` · `"wajar"` · `"mendadak"` · `"mendadak-ditahan"` (kena jeda kabar).
    Selalu menyetel keadaan jadi "jalan" sesudahnya. Fail-soft menyeluruh.
    """
    st = _baca_keadaan()
    keadaan = st.get("keadaan")
    if keadaan is None:
        _tulis_keadaan("jalan")
        return "pertama"
    if keadaan == "bersih":
        _tulis_keadaan("jalan")
        return "wajar"

    # keadaan == "jalan" → mesin sebelumnya TIDAK pernah sampai ke baris penutupnya.
    sekarang = time.time()
    terakhir = st.get("kabar_terakhir")
    ditahan = bool(terakhir) and (sekarang - float(terakhir)) < _JEDA_KABAR_JAM * 3600
    logger.error("[WorkerV2] MESIN SEBELUMNYA MATI MENDADAK — tidak pernah berhenti dengan wajar. "
                 "Rekaman detik kematiannya ada di catatan server (cari 'Fatal Python error').")
    if ditahan:
        # Jeda ini penting: bila mesin mati berulang-ulang, kabar tiap 10 detik = teror, bukan info.
        _tulis_keadaan("jalan")
        return "mendadak-ditahan"
    if kirim_kabar is None:
        def kirim_kabar(teks):
            from src.utils.telegram_notifier import TelegramNotifier
            TelegramNotifier().notify_admin(teks)
    try:
        kirim_kabar(
            "🔌 <b>Mesin produksi berhenti mendadak lalu hidup kembali sendiri</b>\n"
            "Produksi dan penerbitan sudah berjalan lagi otomatis — tidak ada yang perlu Anda "
            "lakukan sekarang.\n"
            "Yang berbeda kali ini: catatan server sekarang MEREKAM apa yang sedang dikerjakan mesin "
            "pada detik ia berhenti, jadi sebabnya bisa ditelusuri.")
    except Exception as e:
        logger.warning(f"[WorkerV2] kabar kematian gagal dikirim (non-fatal): {e}")
    _tulis_keadaan("jalan", kabar_terakhir=sekarang)
    return "mendadak"


def main() -> None:
    from src.utils.db_log_sink import setup_db_logging
    from src.orchestrator import producer, publisher, buffer_janitor, self_learning, email_outbox, heartbeat, trend_refresher, niche_request_sweeper, payment_reconciler, telegram_linker
    from src.billing import renewal as billing_renewal

    setup_db_logging()

    # Diperiksa SEBELUM bagian-bagian mesin dinyalakan: kabarnya harus keluar lebih dulu, dan
    # pemeriksaan ini tak boleh menunggu apa pun. Fail-soft — apa pun yang terjadi di sini TIDAK
    # boleh menghalangi produksi (§0.6: gagal jujur, tapi jangan sampai menghentikan mesin).
    try:
        _sebab = periksa_kematian_sebelumnya()
        logger.info(f"[WorkerV2] keadaan mesin sebelumnya: {_sebab}")
    except Exception as e:
        logger.warning(f"[WorkerV2] periksa kematian sebelumnya gagal (non-fatal): {e}")

    stop = threading.Event()

    def _shutdown(sig, _frame):
        logger.info(f"[WorkerV2] Signal {sig} — stop (loop daemon berhenti saat proses exit)")
        stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("[WorkerV2] ══════════════════════════════════════════")
    logger.info("[WorkerV2] DECOUPLED — Producer + Publisher + Janitor loop konkuren (§12c)")
    logger.info(f"[WorkerV2] MAX_CONCURRENT_RENDER={producer.max_concurrent_render()} (core)")
    logger.info("[WorkerV2] ══════════════════════════════════════════")

    # Cermin nilai-sah katalog (adapter/enum) dari registry KODE → DB (self-heal, anti-drift).
    try:
        from src.config.catalog_sync import sync_catalog_valid_values
        sync_catalog_valid_values()
    except Exception as e:
        logger.warning(f"[catalog_sync] startup sync gagal (non-fatal): {e}")

    threads = [
        threading.Thread(target=producer.run_forever, name="producer", daemon=True),
        threading.Thread(target=publisher.run_forever, name="publisher", daemon=True),
        threading.Thread(target=buffer_janitor.run_forever, name="janitor", daemon=True),
        threading.Thread(target=self_learning.run_forever, name="self_learning", daemon=True),
        threading.Thread(target=billing_renewal.run_forever, name="billing_renewal", daemon=True),
        threading.Thread(target=email_outbox.run_forever, name="email_outbox", daemon=True),
        threading.Thread(target=trend_refresher.run_forever, name="trend_refresher", daemon=True),
        threading.Thread(target=niche_request_sweeper.run_forever, name="niche_sweeper", daemon=True),
        threading.Thread(target=payment_reconciler.run_forever, name="payment_reconciler", daemon=True),
        # [TG-LINK] Hubungkan Telegram 1-klik (long-poll getUpdates; webhook bot kosong = aman)
        threading.Thread(target=telegram_linker.run_forever, name="telegram_linker", daemon=True),
    ]
    for t in threads:
        t.start()

    # Heartbeat ke worker_heartbeats (E3 System Health) — tiap HEARTBEAT_INTERVAL_SEC.
    sb_hb = None
    try:
        from supabase import create_client
        sb_hb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    except Exception as e:
        logger.warning(f"[Heartbeat] init gagal: {e}")
    beat_interval = int(os.getenv("HEARTBEAT_INTERVAL_SEC", "15"))

    n = 0
    while not stop.is_set():
        time.sleep(1)
        n += 1
        if sb_hb is not None and n % beat_interval == 0:
            heartbeat.record(sb_hb, threads)
    logger.info("[WorkerV2] shutdown selesai")
    # PENANDA BERHENTI WAJAR — hanya baris ini yang membedakan "dimatikan" dari "mati mendadak".
    # Diverifikasi pada data nyata: baris di atas TIDAK PERNAH tercapai pada 11 kematian mendadak,
    # dan SELALU tercapai pada restart wajar (4 dari 4 kasus yang diperiksa). Karena itu penanda ini
    # ditulis DI SINI, sesudahnya — bukan di penangkap sinyal (yang bisa berjalan lalu prosesnya
    # tetap mati di tengah pembersihan).
    _tulis_keadaan("bersih")


if __name__ == "__main__":
    main()
