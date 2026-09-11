"""Pemeriksaan stok yang BERAT tak boleh berirama sama dengan antrean uji yang RINGAN.

LAHIR DARI KEJADIAN 11-SEP 2026: proyek Supabase DIBLOKIR (`402 exceed_egress_quota`) — kuota
gratis 5 GB, terpakai 9,55 GB. Seluruh tenant berhenti produksi.

AKAR (dari statistik DB, bukan tebakan): `producer.run_forever(idle_seconds=10)` = 8.640
putaran/hari, dan TIAP putaran memanggil `plan_and_submit` yang menarik `select("*")` seluruh
channel aktif (19,3 KB) + ±7 panggilan per channel (`gate_for_channel` · `channel_readiness` ·
`buffer_depth` ×3 · streak · latest_failure). Terukur: `content_inventory` 8,0 juta baca ·
`ai_providers` 6,4 juta (tabel 9 BARIS). Database hanya 52 MB ⇒ yang boros FREKUENSI, bukan data.
Stok video berubah beberapa kali sehari, tapi diperiksa 8.640 kali.

RANJAU TERBESAR (hampir saya buat sendiri): memperlambat SELURUH loop ikut memperlambat
`drain_direct` — antrean tombol "Uji sekarang" tenant. Itu memperparah keluhan owner 11-Sep
(uji kalah slot 2×, baru jalan 13,4 menit). Karena itu iramanya WAJIB dipisah:
  • `drain_direct`   → tiap putaran (ringan: 2,1 MB/hari, wajib responsif)
  • `plan_and_submit`→ tiap `producer_stock_interval_sec` (default 300 dtk)

Nilai dibaca lewat `app_config.get_int` yang SUDAH dipakai producer (`buffer_target_days`) —
cache TTL 300 s, satu kueri untuk semua kunci, fail-safe ke default. Nol jalur baca baru.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCER = "src/orchestrator/producer.py"
KUNCI = "producer_stock_interval_sec"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    return "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("#"))


def _blok_loop(isi: str) -> str:
    i = isi.find("def run_forever")
    assert i != -1, "run_forever producer tak ditemukan"
    return isi[i: i + 2200]


class TestIramaDipisah(unittest.TestCase):
    def setUp(self):
        self.p = _tanpa_komentar(_isi(PRODUCER))
        self.blok = _blok_loop(self.p)

    def test_pemeriksaan_stok_TIDAK_lagi_tiap_putaran(self):
        """Inti perbaikan: `plan_and_submit` harus ber-syarat waktu, bukan dipanggil polos."""
        # JANGKAR DIPERBAIKI: versi pertama memeriksa `strip().startswith(...)` — itu TETAP MERAH
        # walau pemanggilannya sudah benar berada di dalam blok bersyarat, sebab strip() membuang
        # indentasi yang justru jadi buktinya. Yang diikat sekarang = PERILAKU: pemanggilan stok
        # harus lebih dalam (bersarang) daripada pemanggilan antrean uji, dan didahului syarat waktu.
        b_drain = next((b for b in self.blok.splitlines() if "drain_direct(" in b), None)
        b_stok = next((b for b in self.blok.splitlines() if "plan_and_submit(" in b), None)
        self.assertIsNotNone(b_drain, "drain_direct tak ditemukan di loop")
        self.assertIsNotNone(b_stok, "plan_and_submit tak ditemukan di loop")
        ind = lambda x: len(x) - len(x.lstrip())
        self.assertGreater(
            ind(b_stok), ind(b_drain),
            "plan_and_submit masih sejajar dengan drain_direct ⇒ dipanggil TIAP putaran "
            "(8.640×/hari) — inilah yang menjebol kuota egress.",
        )
        self.assertRegex(
            self.blok, r"time\.time\(\)\s*-\s*\w+\)?\s*>=",
            "tak ada syarat waktu yang menahan pemeriksaan stok.",
        )

    def test_antrean_uji_TETAP_diperiksa_tiap_putaran(self):
        """RANJAU 1: memperlambat antrean uji = memperparah keluhan owner (uji kalah slot)."""
        baris = [b.strip() for b in self.blok.splitlines() if "drain_direct(" in b]
        self.assertTrue(baris, "drain_direct tak ditemukan di loop")
        self.assertTrue(
            any(b.startswith("drain_direct(") for b in baris),
            f"drain_direct tak lagi dipanggil tiap putaran — tombol 'Uji sekarang' tenant "
            f"jadi lambat: {baris}",
        )

    def test_jeda_stok_dibaca_dari_pengaturan_yang_bisa_diubah_owner(self):
        """Angka tertanam di kode = tiap perubahan menuntut deploy. Pembacanya WAJIB `get_int`
        yang sudah dipakai producer (cache 300 s, satu kueri, fail-safe) — bukan jalur baru."""
        self.assertIn(
            KUNCI, self.blok,
            f"jeda pemeriksaan stok tak dibaca dari pengaturan `{KUNCI}` — masih tertanam di kode.",
        )
        self.assertRegex(
            self.blok, r"get_int\(\s*\"" + KUNCI + r"\"",
            "jeda stok tidak dibaca lewat `get_int` (pembaca ber-cache yang sudah dipakai).",
        )

    def test_nilai_nol_dipagari(self):
        """RANJAU 2: `time.sleep(0)` ⇒ loop tanpa henti, CPU 100%, egress justru MELEDAK.
        Satu salah ketik di panel admin cukup untuk melumpuhkan server."""
        m = re.search(r"get_int\(\s*\"" + KUNCI + r"\"[^)]*\)", self.blok)
        self.assertIsNotNone(m, "pembacaan jeda stok tak ditemukan")
        sekitar = self.blok[max(0, m.start() - 120): m.end() + 60]
        self.assertRegex(
            sekitar, r"max\(\s*\d+\s*,",
            "nilai jeda tak dipagari batas bawah — angka 0 dari panel admin membuat mesin "
            "berputar tanpa henti (CPU 100% + egress meledak).",
        )

    def test_default_aman_bila_pengaturan_tak_terbaca(self):
        """RANJAU 3: DB tak terjangkau ⇒ mesin JANGAN berhenti, pakai default."""
        m = re.search(r"get_int\(\s*\"" + KUNCI + r"\"\s*,\s*(\d+)\s*\)", self.blok)
        self.assertIsNotNone(m, "default jeda stok tak ditemukan")
        self.assertGreaterEqual(
            int(m.group(1)), 60,
            "default jeda stok terlalu kecil — bila DB tak terbaca, pemborosan kembali.",
        )


class TestKenopLahirLengkap(unittest.TestCase):
    """§3: kenop baru wajib lahir lengkap — baris DB + label dwibahasa + satuan."""

    def test_ada_migrasi_yang_menanam_kunci_beserta_keterangannya(self):
        migr = [f for f in os.listdir(os.path.join(AKAR, "migrations")) if f.endswith(".sql")]
        isi = "\n".join(_isi(f"migrations/{f}") for f in migr)
        self.assertIn(KUNCI, isi, f"kunci `{KUNCI}` tak pernah ditanam lewat migrasi.")
        i = isi.find(KUNCI)
        self.assertRegex(
            isi[max(0, i - 400): i + 700], r"description",
            "kunci ditanam tanpa keterangan — admin melihat angka telanjang tanpa tahu artinya.",
        )

    def test_panel_admin_punya_label_dwibahasa_dan_satuan(self):
        fe = _isi("apps/web/src/app/admin/(panel)/app-config/page.tsx")
        self.assertIn(
            KUNCI, fe,
            f"`{KUNCI}` tak punya metadata di panel — ia jatuh ke grup 'Lainnya' tanpa label bermakna.",
        )
        i = fe.find(KUNCI)
        blok = fe[i: i + 700]
        self.assertRegex(blok, r"label:\s*\{\s*id:", "label kenop tidak dwibahasa.")
        self.assertRegex(blok, r"unit:", "kenop tanpa satuan — admin tak tahu detik atau menit.")


if __name__ == "__main__":
    unittest.main()
