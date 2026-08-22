"""GERBANG RANTAI BIAYA — enam gerbang yang menolak KELAS kesalahan, bukan kasusnya.

KENAPA BERKAS INI ADA (owner 23-Agu-2026)
Sepuluh cacat ditemukan dalam satu sesi di rantai harga+biaya — semuanya karya saya sendiri, semuanya
SENYAP (nol galat, nol uji merah, layar tetap menampilkan angka): harga suara 4× salah · gambar
ditagih 2× · huruf suara dicatat 2× · layar tenant tanpa cabang video · kurs ditanam di kode 2 layar ·
pengetahuan satuan tersebar di 5 tempat · pintu simpan harga tanpa validasi kunci.

Owner: *"SAYA TIDAK PEDULI ANDA MAU TULIS ATAU TIDAK, SAYA PEDULI ANDA TIDAK MENGULANGI KESALAHAN."*
Maka: bukan aturan, bukan catatan — **BENDA yang diperiksa mesin.** Gerbang penyimpanan menolak commit
saat uji merah (`.claude/hooks/gerbang_commit.sh`), jadi kelas-kelas di bawah ini tak bisa lagi
tersimpan diam-diam. Pola yang sudah terbukti: *aturan berupa NIAT dilanggar, aturan berupa BENDA
yang bisa diperiksa dipatuhi* (`test_gerbang_tetap_terpasang.py`).

AKAR yang dijaga (bukan gejalanya):
  G1 pengetahuan satuan harga tersebar → tiap layar/berkas menurunkan sendiri, lalu membusuk sendiri
  G2 daftar satuan tak lengkap        → jenis model yang tak punya satuan = biaya nol senyap
  G3 pemakaian dicatat dua lapis      → tagihan ganda yang tak terlihat karena harganya nol
  G4 satu model ditagih 2 keranjang   → angka ke tenant lebih mahal dari kenyataan
  G5 satuan AMBIGU diterima sinkron   → harga "ada" tapi artinya salah (kasus 4× termurah)
  G6 angka bisnis ditanam di layar    → dua layar bisa menampilkan angka berbeda
"""
import ast
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Satu-satunya rumah yang boleh menyebut kosakata satuan harga (kunci kita + kolom umpan vendor).
RUMAH_SATUAN = "src/billing/ai_cost.py"

KUNCI_SATUAN = ("in_per_1m", "out_per_1m", "per_1m_chars", "per_image", "per_second_usd",
                "per_video_base_usd", "per_extra_second_usd", "base_seconds", "per_request_usd")
KOLOM_UMPAN = ("input_cost_per_character", "output_cost_per_audio_token", "output_cost_per_second",
               "output_cost_per_image", "output_cost_per_image_token", "input_cost_per_token",
               "output_cost_per_token")

AREA = ("src", "apps/web/src")


def _berkas_kode():
    for akar in AREA:
        for dp, _, fs in os.walk(os.path.join(AKAR, akar)):
            if "node_modules" in dp or "__pycache__" in dp or "/.next" in dp:
                continue
            for f in fs:
                if f.endswith((".py", ".ts", ".tsx")):
                    yield os.path.relpath(os.path.join(dp, f), AKAR)


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(rel: str, isi: str) -> str:
    """Komentar pernah MENYELAMATKAN uji palsu — kata yang dijaga dikutip di komentar sebelahnya."""
    isi = re.sub(r"/\*.*?\*/", "", isi, flags=re.S)
    isi = re.sub(r'"""(?:.|\n)*?"""', "", isi)
    baris = []
    for b in isi.splitlines():
        t = b.lstrip()
        if t.startswith("//") or t.startswith("#"):
            continue
        baris.append(b)
    return "\n".join(baris)


class G1_SatuRumahSatuanHarga(unittest.TestCase):
    """Kosakata satuan harga hanya boleh hidup di SATU berkas. Tersebar = tiap tempat membusuk sendiri
    (itu sebab layar tenant tak punya cabang video: cabangnya ditulis saat baru ada 3 jenis)."""

    def test_kunci_satuan_hanya_di_satu_rumah(self):
        penyebar = {}
        for rel in _berkas_kode():
            if rel == RUMAH_SATUAN:
                continue
            isi = _tanpa_komentar(rel, _isi(rel))
            ada = [k for k in KUNCI_SATUAN if re.search(rf"(?<![a-zA-Z_]){k}(?![a-zA-Z_])", isi)]
            if ada:
                penyebar[rel] = ada
        self.assertEqual(penyebar, {},
                         "kosakata satuan harga hidup di luar " + RUMAH_SATUAN + ":\n" +
                         "\n".join(f"  {k} → {v}" for k, v in penyebar.items()))

    def test_kolom_umpan_vendor_hanya_di_satu_rumah(self):
        penyebar = {}
        for rel in _berkas_kode():
            if rel == RUMAH_SATUAN:
                continue
            isi = _tanpa_komentar(rel, _isi(rel))
            ada = [k for k in KOLOM_UMPAN if k in isi]
            if ada:
                penyebar[rel] = ada
        self.assertEqual(penyebar, {},
                         "pemetaan kolom umpan vendor hidup di luar " + RUMAH_SATUAN + ":\n" +
                         "\n".join(f"  {k} → {v}" for k, v in penyebar.items()))


class G2_DaftarSatuanLengkap(unittest.TestCase):
    """Daftar satuan WAJIB ada dan menjangkau KEEMPAT jenis. Jenis tanpa satuan = biaya nol senyap,
    dan itu yang terjadi pada model suara ber-tagih token selama 16 produksi."""

    def _daftar(self):
        from src.billing import ai_cost
        d = getattr(ai_cost, "SATUAN_HARGA", None)
        self.assertIsNotNone(d, "DAFTAR SATUAN belum ada — tak ada sumber tunggal yang bisa dijaga")
        return d

    def test_keempat_jenis_punya_satuan(self):
        from src.config.catalog_sync import COMPONENTS
        d = self._daftar()
        jenis_terdaftar = {s.jenis for s in d}
        kurang = {j for j, _ in COMPONENTS} - jenis_terdaftar
        self.assertEqual(kurang, set(), f"jenis model tanpa satuan harga: {sorted(kurang)}")

    def test_tiap_satuan_utuh_dan_bisa_dihitung(self):
        for s in self._daftar():
            with self.subTest(f"{s.jenis}/{s.kunci}"):
                self.assertTrue(s.kunci, "kunci harga kosong")
                self.assertTrue(s.keranjang, "keranjang pemakaian kosong → satuan tak bisa dihitung")
                self.assertTrue(s.bentuk, "bentuk rumus kosong")
                self.assertTrue(s.label, "label layar kosong → layar terpaksa menanam teks sendiri")

    def test_satuan_ambigu_tak_boleh_terdaftar_untuk_suara_gambar(self):
        """`output_cost_per_token` bermakna DUA hal di umpan (harga audio pd satu baris, harga teks
        pd baris lain) tanpa penanda → menerimanya = menebak."""
        for s in self._daftar():
            if s.jenis in ("tts", "image"):
                self.assertNotIn("output_cost_per_token", tuple(s.umpan or ()),
                                 f"{s.jenis}/{s.kunci} menerima kolom umpan yang bermakna ganda")


class G3_SatuPencatatPerJenisPemakaian(unittest.TestCase):
    """Pemakaian yang sama HARAM dicatat dua lapis. Huruf suara dicatat oleh mesin suara DAN oleh
    adapter Gemini → tercatat 2226 padahal vendor menerima 1113."""

    BATAS = {"add_tts": 1, "add_image": 1, "add_video": 1, "add_tts_tokens": 1,
             "add_tts_seconds": 1}

    def _titik_panggil(self, nama: str):
        titik = []
        for dp, _, fs in os.walk(os.path.join(AKAR, "src")):
            if "__pycache__" in dp:
                continue
            for f in fs:
                if not f.endswith(".py"):
                    continue
                rel = os.path.relpath(os.path.join(dp, f), AKAR)
                try:
                    pohon = ast.parse(_isi(rel))
                except SyntaxError:
                    continue
                for n in ast.walk(pohon):
                    if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == nama:
                        titik.append(f"{rel}:{n.lineno}")
        return titik

    def test_tepat_satu_titik_pencatat(self):
        for nama, batas in self.BATAS.items():
            with self.subTest(nama):
                titik = self._titik_panggil(nama)
                self.assertEqual(len(titik), batas,
                                 f"{nama} dipanggil {len(titik)}x (batas {batas}) → risiko catat ganda: {titik}")


class G4_SatuModelSatuTagihan(unittest.TestCase):
    """Model yang punya harga satuan-jenisnya sendiri HARAM ditagih lagi lewat token.
    Terukur: `gemini-2.5-flash-image` ditagih per-gambar DAN per-token → +7,6% pada run 503."""

    def test_model_ber_harga_gambar_tak_ditagih_lagi_lewat_token(self):
        from src.billing import ai_cost
        from unittest.mock import patch
        harga = {"m-gambar": {"per_image": 0.01, "in_per_1m": 1.0, "out_per_1m": 2.0}}
        pakai = {"image": {"m-gambar": 10},
                 "llm": {"m-gambar": {"tokens_in": 1_000_000, "tokens_out": 1_000_000, "calls": 5}}}
        with patch.object(ai_cost, "_pricing_map", return_value=harga):
            h = ai_cost.compute_cost_usd(pakai)
        self.assertAlmostEqual(h["usd"], 10 * 0.01, places=9,
                               msg=f"model ditagih DUA KALI (per-gambar + token): {h['breakdown']}")

    def test_model_ber_harga_huruf_tak_ditagih_lagi_lewat_token(self):
        from src.billing import ai_cost
        from unittest.mock import patch
        harga = {"m-suara": {"per_1m_chars": 50.0, "in_per_1m": 1.0, "out_per_1m": 2.0}}
        pakai = {"tts": {"m-suara": 1_000_000},
                 "tts_tokens": {"m-suara": {"tokens_in": 1_000_000, "tokens_out": 1_000_000}}}
        with patch.object(ai_cost, "_pricing_map", return_value=harga):
            h = ai_cost.compute_cost_usd(pakai)
        self.assertAlmostEqual(h["usd"], 50.0, places=9,
                               msg=f"biaya suara terhitung dua kali: {h['breakdown']}")


class G5_SinkronMenolakSatuanAmbigu(unittest.TestCase):
    """Pemeta harga WAJIB tahu jenis barisnya. Tanpa itu ia menulis harga TEKS ke baris SUARA —
    persis kejadian `gemini-2.5-flash-preview-tts`: harga tercatat $2,5 padahal resminya $10."""

    def test_pemeta_menerima_jenis_model(self):
        from src.billing import price_sync
        import inspect
        p = list(inspect.signature(price_sync._to_pricing).parameters)
        self.assertIn("component", p,
                      f"_to_pricing tak tahu jenis baris (parameter: {p}) → satuan salah jenis lolos")

    def test_umpan_hanya_harga_token_teks_tak_jadi_harga_suara(self):
        from src.billing import price_sync
        entri = {"mode": "audio_speech", "input_cost_per_token": 3e-07, "output_cost_per_token": 2.5e-06}
        hasil = price_sync._to_pricing(entri, "x", component="tts")
        terpakai = {k: v for k, v in hasil.items() if v is not None and k not in ("source", "synced_at")}
        self.assertEqual(terpakai, {},
                         f"harga TEKS diterima sebagai harga SUARA: {terpakai}")

    def test_umpan_harga_token_AUDIO_diterima_utk_suara(self):
        """Arah kedua: yang TAK ambigu wajib tetap terpakai — jangan over-correction."""
        from src.billing import price_sync
        entri = {"mode": "audio_speech", "output_cost_per_audio_token": 1.2e-05,
                 "output_cost_per_second": 0.00025}
        hasil = price_sync._to_pricing(entri, "x", component="tts")
        self.assertTrue(any(v for k, v in hasil.items() if k not in ("source", "synced_at")),
                        "harga audio yang JELAS malah ditolak — perbaikan jadi merusak")


class G6_NolAngkaBisnisDiLayar(unittest.TestCase):
    """Kurs & tarif = nilai bisnis; tempatnya DB/config. Ditanam di layar → dua layar bisa berbeda.
    Terukur: kurs cadangan 16500 ditanam di dua layar tenant."""

    LAYAR = ("apps/web/src/components/runs-table.tsx",
             "apps/web/src/app/(app)/dashboard/page.tsx",
             "apps/web/src/app/(app)/channels/[id]/page.tsx",
             "apps/web/src/app/admin/(panel)/catalog/page.tsx")

    def test_nol_kurs_ditanam(self):
        tertangkap = {}
        for rel in self.LAYAR:
            isi = _tanpa_komentar(rel, _isi(rel))
            angka = re.findall(r"(?<![\w.])1[0-9]{4}(?![\w.])", isi)   # 10000–19999 = rentang kurs
            if angka:
                tertangkap[rel] = sorted(set(angka))
        self.assertEqual(tertangkap, {},
                         "kurs ditanam di layar (nilai bisnis wajib dari app_config):\n" +
                         "\n".join(f"  {k} → {v}" for k, v in tertangkap.items()))


if __name__ == "__main__":
    unittest.main()


# ── G7 ── ditambahkan 23-Agu bersama S-DOC ────────────────────────────────────────────────────
SSOT_BIAYA = "ARSITEKTUR_AI_PROVIDER_MODEL.md"

# Tarif = angka mata uang yang menempel pada satuan. BUKAN kalimat "ditagih per token" (narasi
# changelog sah), melainkan "$3/M in", "$0.00022/char", "Rp 250/gambar" — itu ACUAN, dan acuan
# yang hidup di dua tempat pasti berbeda pada suatu hari.
POLA_TARIF = re.compile(
    r"(?:\$|Rp\s?)[0-9][0-9.,]*\s*(?:/|per\s)\s*(?:1?M\b|1jt|1 juta|image|img|char|karakter|"
    r"token|detik|second|gambar|klip|clip)", re.I)


class G7_TarifHanyaDiSSOT(unittest.TestCase):
    """Tarif & rumus biaya hanya boleh hidup di SATU dokumen.

    Terukur 23-Agu: `DESAIN_PRODUK_SAAS §656` memuat tabel tarif Juni yang bertentangan TIGA KALI
    dengan katalog hidup — `gpt-image-1-mini` ditulis per-GAMBAR padahal ditagih per-TOKEN,
    ElevenLabs $220/1jt huruf vs katalog $50, dan menyebut Pexels & R2 yang sudah pensiun.
    Sesi berikutnya yang membaca tabel itu akan "memperbaiki" yang sudah benar."""

    def _dokumen(self):
        for f in sorted(os.listdir(AKAR)):
            if f.endswith(".md") and f != SSOT_BIAYA:
                yield f

    # Dokumen RANCANGAN sah memuat tarif sebagai bahan keputusan — tapi wajib MENGAKU bahwa itu
    # cuplikan, bukan acuan. Pola penanda ini sama dengan `PENANDA_KOREKSI` di penjaga dokumen lain:
    # pengecualian yang MENYEBUT DIRINYA tak bisa membusuk diam-diam.
    PENANDA_CUPLIKAN = re.compile(r"bukan acuan|BUKAN ACUAN", re.I)

    def test_tarif_per_satuan_hanya_di_ssot(self):
        tertangkap = {}
        for f in self._dokumen():
            baris = _isi(f).splitlines()
            hit = []
            for i, b in enumerate(baris, 1):
                if not POLA_TARIF.search(b):
                    continue
                konteks = "\n".join(baris[max(0, i - 9):i])   # baris itu + 8 baris di atasnya
                if self.PENANDA_CUPLIKAN.search(konteks):
                    continue
                hit.append(f"{i}: {b.strip()[:90]}")
            if hit:
                tertangkap[f] = hit
        self.assertEqual(tertangkap, {},
                         f"tarif per-satuan hidup di luar {SSOT_BIAYA} (acuan ganda = acuan basi):\n" +
                         "\n".join(f"  {k}\n    " + "\n    ".join(v) for k, v in tertangkap.items()))

    def test_rumus_biaya_hanya_di_ssot(self):
        tertangkap = [f for f in self._dokumen()
                      if re.search(r"biaya_(llm|tts|image|video)\s*=", _isi(f))]
        self.assertEqual(tertangkap, [],
                         f"rumus biaya disalin ke luar {SSOT_BIAYA}: {tertangkap}")

    def test_ssot_ditunjuk_indeks_memori(self):
        """Dokumen yang tak ditunjuk indeks = dokumen yang tak pernah dibaca sesi baru.
        Ini yang terjadi 23-Agu: SSOT-nya ADA sejak 22-Agu, saya sendiri tak menemukannya."""
        indeks = os.path.expanduser(
            "~/.claude/projects/-home-rad-viral-machine/memory/MEMORY.md")
        if not os.path.exists(indeks):
            self.skipTest("indeks memori tak terbaca di mesin ini")
        with open(indeks, encoding="utf-8") as f:
            self.assertIn(SSOT_BIAYA, f.read(),
                          f"{SSOT_BIAYA} tak ditunjuk indeks memori → sesi baru buta terhadapnya")
