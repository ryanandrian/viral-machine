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
        # Formula dinyatakan tegas (F2): tanpa ini uji menembak DB nyata → hasilnya bergantung urutan.
        with patch.object(ai_cost, "_pricing_map", return_value=harga), \
             patch.object(ai_cost, "_formula_map", return_value={"m-gambar": "gambar_satuan"}):
            h = ai_cost.compute_cost_usd(pakai)
        self.assertAlmostEqual(h["usd"], 10 * 0.01, places=9,
                               msg=f"model ditagih DUA KALI (per-gambar + token): {h['breakdown']}")

    def test_model_ber_harga_huruf_tak_ditagih_lagi_lewat_token(self):
        from src.billing import ai_cost
        from unittest.mock import patch
        harga = {"m-suara": {"per_1m_chars": 50.0, "in_per_1m": 1.0, "out_per_1m": 2.0}}
        pakai = {"tts": {"m-suara": 1_000_000},
                 "tts_tokens": {"m-suara": {"tokens_in": 1_000_000, "tokens_out": 1_000_000}}}
        with patch.object(ai_cost, "_pricing_map", return_value=harga), \
             patch.object(ai_cost, "_formula_map", return_value={"m-suara": "suara_huruf"}):
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


class G8_PenandaHargaMengikutiSatuanTerpakai(unittest.TestCase):
    """Baris ber-objek-harga tapi NOL satuan terpakai WAJIB ditandai.

    Terukur 23-Agu: sesudah sinkron menolak satuan ambigu, `gemini-2.5-flash-preview-tts` memiliki
    objek harga (source/synced_at) TANPA satu pun satuan terpakai. Penanda lama hanya melihat
    ada/tidaknya objek harga ⇒ baris itu tampak NORMAL — lubang senyap yang lahir dari perbaikan
    sendiri. Alarm harian pun jadi tak bisa ditindak: admin tak tahu satuan mana yang harus diisi."""

    PANEL = "apps/web/src/app/admin/(panel)/catalog/page.tsx"

    def test_penanda_dinyalakan_oleh_satuan_terpakai(self):
        isi = _tanpa_komentar(self.PANEL, _isi(self.PANEL))
        # (regex membolehkan tanda kurung bersarang: fmtPricing(pr, String(...)) )
        self.assertRegex(isi, r"\{fmtPricing\([^\n]*\)\s*\?",
                         "penanda harga masih melihat ada/tidaknya objek harga, bukan satuan terpakai")
        self.assertNotRegex(isi, r"\{pr \? <span className=\"muted\"",
                            "kondisi lama (objek harga ada = dianggap berharga) masih dipakai")

    def test_penanda_menyebut_satuan_yang_harus_diisi(self):
        """Alarm harian hanya berguna bila ADA tempat yang menyebut tindakannya."""
        isi = _tanpa_komentar(self.PANEL, _isi(self.PANEL))
        i = isi.index("badge badge-warning")
        blok = isi[i:i + 900]
        self.assertIn("satuanJenis", blok,
                      "penanda tak menyebut satuan mana yang harus diisi → admin menebak")


class G9_FormulaHargaLengkapDanDijelaskan(unittest.TestCase):
    """F1 — tiap model menyebut FORMULA hitungnya, dan formulanya DIJELASKAN ke admin.

    Sebelum 23-Agu cara menghitung DITEBAK dari jenis model, dan pengetahuan itu tersebar di 4
    tempat. Owner menetapkan kategorisasi formula supaya model dengan pola tagih sama dikelompokkan,
    dan supaya penambahan model baru = memilih formula, bukan menulis kode. Yang dijaga:
      (a) katalog formula ADA, tiap entri utuh (kunci · jenis · nama · penjelasan)
      (b) tiap formula yang MENGHITUNG punya satuan harga; yang tidak menghitung memang tak punya
      (c) formula dicerminkan ke DB → panel & validasi tulis membaca SATU sumber
      (d) layar TIDAK menanam daftar/penjelasan formula sendiri (kelas cacat yang sudah terbukti)
    """

    PANEL = "apps/web/src/app/admin/(panel)/catalog/page.tsx"
    API = "apps/web/src/app/api/admin/catalog/route.ts"

    def _katalog(self):
        from src.billing.ai_cost import FORMULA
        return FORMULA

    def test_katalog_formula_ada_dan_utuh(self):
        f = self._katalog()
        self.assertGreaterEqual(len(f), 10, "katalog formula terlalu kurus — jenis tagih pasti ada yang tak tertampung")
        for x in f:
            with self.subTest(x.kunci):
                self.assertTrue(x.kunci and x.nama and x.penjelasan, "entri formula tak utuh")
                self.assertIn(x.jenis, ("llm", "tts", "image", "video", "*"), f"jenis tak dikenal: {x.jenis}")
                self.assertGreater(len(x.penjelasan), 40,
                                   "penjelasan terlalu pendek — admin tetap menebak cara hitungnya")

    def test_keempat_jenis_punya_formula(self):
        from src.config.catalog_sync import COMPONENTS
        from src.billing.ai_cost import formula_untuk_jenis
        for j, _ in COMPONENTS:
            with self.subTest(j):
                self.assertTrue(formula_untuk_jenis(j), f"jenis '{j}' tak punya satu pun formula")

    def test_formula_yang_menghitung_punya_satuan(self):
        """Formula ber-satuan wajib menyebut satuan; yang TIDAK menghitung wajib TIDAK punya satuan
        (kalau punya, ia diam-diam ikut menghitung → sumber angka ganda)."""
        from src.billing.ai_cost import satuan_formula
        TANPA_HITUNG = {"biaya_dilaporkan", "selisih_akun", "gratis", "kuota_gratis",
                        "gambar_megapiksel", "video_token"}   # dua terakhir: rumusnya, bukan tabel satuan
        for x in self._katalog():
            with self.subTest(x.kunci):
                punya = bool(satuan_formula(x.kunci))
                if x.kunci in TANPA_HITUNG:
                    continue
                self.assertTrue(punya, f"formula '{x.kunci}' menghitung tapi tak punya satuan harga")

    def test_formula_dicerminkan_ke_db(self):
        from src.config.catalog_sync import collect_valid_values
        baris = [r for r in collect_valid_values() if r["field"].startswith("pricing_model:")]
        self.assertEqual(len(baris), len(self._katalog()),
                         "jumlah formula di cermin ≠ katalog kode → panel bisa menawarkan yang tak dikenal mesin")
        for r in baris:
            self.assertIn(" — ", r["label"], "label cermin tak memuat penjelasan (nama — penjelasan)")

    def test_panel_membaca_formula_dari_cermin_bukan_menanam(self):
        isi = _tanpa_komentar(self.PANEL, _isi(self.PANEL))
        self.assertIn("pricing_model:", isi, "panel tak membaca cermin formula")
        for kunci in ("naskah_token", "suara_huruf", "video_token", "biaya_dilaporkan"):
            self.assertNotIn(f'"{kunci}"', isi,
                             f"nama formula '{kunci}' DITANAM di kode layar — harus dari cermin")

    def test_pilihan_formula_disaring_per_jenis(self):
        """Semua formula ditawarkan untuk semua jenis = admin bisa memilih yang mustahil dihitung."""
        isi = _tanpa_komentar(self.PANEL, _isi(self.PANEL))
        self.assertRegex(isi, r"`pricing_model:\$\{jenis\}`",
                         "pilihan formula tak disaring menurut jenis model baris itu")

    def test_api_memvalidasi_formula(self):
        isi = _tanpa_komentar(self.API, _isi(self.API))
        self.assertRegex(isi, r"pricing_model:\s*\[",
                         "API tak memvalidasi kolom formula → nilai ngawur bisa tersimpan")
        self.assertIn('"pricing_model"', isi, "kolom formula tak diizinkan ditulis dari panel")


class G10_PenghitungMemakaiFormulaYangDINYATAKAN(unittest.TestCase):
    """F2 — biaya dihitung memakai formula yang BARIS MODELNYA nyatakan, bukan ditebak dari jenis.

    Uji pembeda (yang gagal pada perilaku PRA-F2): model ber-harga per-gambar DAN per-token, yang
    formulanya menyatakan **token**. Sebelum F2 penghitung memilih per urutan prioritas → per-gambar
    yang menang. Sesudah F2 → yang dinyatakan baris model yang menang. Bila uji ini hijau di kedua
    keadaan, artinya ia tak menjaga apa pun."""

    from unittest.mock import patch as _patch

    def _hitung(self, harga: dict, formula: dict, pakai: dict):
        from unittest.mock import patch
        from src.billing import ai_cost
        with patch.object(ai_cost, "_pricing_map", return_value=harga), \
             patch.object(ai_cost, "_formula_map", return_value=formula):
            return ai_cost.compute_cost_usd(pakai)

    HARGA_DUA = {"m": {"per_image": 0.01, "in_per_1m": 1.0, "out_per_1m": 2.0}}
    PAKAI_DUA = {"image": {"m": 10},
                 "llm": {"m": {"tokens_in": 1_000_000, "tokens_out": 1_000_000, "calls": 3}}}

    def test_formula_menentukan_bukan_prioritas(self):
        h = self._hitung(self.HARGA_DUA, {"m": "gambar_token"}, self.PAKAI_DUA)
        self.assertAlmostEqual(h["usd"], 3.0, places=9,
                               msg=f"formula 'gambar_token' diabaikan; yang dipakai prioritas: {h['breakdown']}")

    def test_formula_lain_pada_data_yang_sama(self):
        """Arah kedua: data identik, formula beda → hasil beda. Membuktikan formulanya BENAR dibaca."""
        h = self._hitung(self.HARGA_DUA, {"m": "gambar_satuan"}, self.PAKAI_DUA)
        self.assertAlmostEqual(h["usd"], 0.1, places=9, msg=f"{h['breakdown']}")

    def test_tanpa_formula_dilaporkan_jujur(self):
        """Celah DATA (baris tanpa formula) → 'tak terhitung', BUKAN dihitung dengan cara lain."""
        h = self._hitung(self.HARGA_DUA, {}, self.PAKAI_DUA)
        self.assertEqual(h["usd"], 0.0)
        self.assertIn("m", h["unpriced"], "baris tanpa formula malah dihitung diam-diam")

    def test_formula_gratis_nol_dan_bukan_tak_terhitung(self):
        h = self._hitung({"m": {"per_1m_chars": 0}}, {"m": "gratis"}, {"tts": {"m": 999_999}})
        self.assertEqual(h["usd"], 0.0)
        self.assertEqual(h["unpriced"], [], "model GRATIS dilaporkan 'tak terhitung' — alarm palsu")

    def test_formula_belum_didukung_dilaporkan_jujur(self):
        """Formula yang penghitung belum dukung HARAM dihitung dengan cara lain (angka palsu)."""
        from src.billing.ai_cost import FORMULA_BELUM_DIDUKUNG
        self.assertTrue(FORMULA_BELUM_DIDUKUNG, "daftar formula-belum-didukung kosong")
        for f in sorted(FORMULA_BELUM_DIDUKUNG):
            with self.subTest(f):
                h = self._hitung(self.HARGA_DUA, {"m": f}, self.PAKAI_DUA)
                self.assertEqual(h["usd"], 0.0, f"formula '{f}' belum didukung tapi tetap menghitung")
                self.assertIn("m", h["unpriced"])

    def test_gagal_baca_peta_formula_tak_membuat_biaya_nol(self):
        """Gangguan DB = kegagalan KAMI. Biaya tak boleh mendadak nol; jatuh ke perilaku pra-F2."""
        from unittest.mock import patch
        from src.billing import ai_cost
        def meledak(sb=None):
            raise RuntimeError("DB mati")
        with patch.object(ai_cost, "_pricing_map", return_value=self.HARGA_DUA), \
             patch.object(ai_cost, "_formula_map", side_effect=meledak):
            h = ai_cost.compute_cost_usd(self.PAKAI_DUA)
        self.assertGreater(h["usd"], 0, "gangguan baca peta formula membuat biaya NOL — itu senyap & salah")
        self.assertEqual(h["unpriced"], [], "gangguan kami dilaporkan seolah celah data")


class G11_SumberTarifDiaturAdminDanPagarAgregator(unittest.TestCase):
    """F3 — sumber tarif jadi DATA yang diatur admin, dan tiga pagar ditegakkan.

    Owner 23-Agu: *"table pricing diisi secara otomatis sinkronisasi (url sinkronisasi sebaiknya bisa
    dikonfigurasi lewat admin panel)"*. Dan riset hari yang sama membuktikan sumber umum BUKAN
    otoritas untuk semua model — jadi sumbernya harus bisa diganti tanpa deploy, sementara tiga
    pagar mencegah sumber menulis yang bukan haknya."""

    def test_url_umpan_dibaca_dari_kenop_admin(self):
        from unittest.mock import patch
        from src.billing import price_sync
        with patch("src.config.app_config.get_text", return_value="https://contoh.uji/harga.json"):
            self.assertEqual(price_sync._url_umpan(), "https://contoh.uji/harga.json",
                             "URL umpan tak dibaca dari kenop admin → mengganti sumber butuh deploy")

    def test_kenop_kosong_jatuh_ke_bawaan(self):
        """Gagal-aman: kenop kosong TIDAK boleh mematikan sinkron."""
        from unittest.mock import patch
        from src.billing import price_sync
        with patch("src.config.app_config.get_text", return_value=""):
            self.assertTrue(price_sync._url_umpan().startswith("http"),
                            "kenop kosong membuat URL kosong → sinkron mati total")

    def test_penanda_agregator_dari_registry_yang_SUDAH_ADA(self):
        """Nol penanda baru: jalur harga membaca penanda yang dipakai jalur galat."""
        from src.billing.price_sync import _agregator
        from src.providers.galat_registry import PENYEDIA
        agr = [k for k, v in PENYEDIA.items() if isinstance(v, dict) and v.get("agregator")]
        self.assertTrue(agr, "registry galat tak lagi menandai satu pun agregator")
        for k in agr:
            self.assertTrue(_agregator(k), f"jalur harga tak mengenali agregator '{k}'")
        self.assertFalse(_agregator("openai"), "penyedia langsung salah dikira agregator")

    def test_baris_agregator_menolak_kunci_persis_umpan(self):
        """Id model agregator sering berupa nama model VENDOR ('anthropic/claude-haiku-4.5') dan
        kunci itu ADA di umpan dengan tarif ANTHROPIC. Kunci-persis pun harus ditolak."""
        from src.billing.price_sync import _feed_entry
        umpan = {"anthropic/claude-haiku-4.5": {"input_cost_per_token": 1e-06},
                 "fal/anthropic/claude-haiku-4.5": {"input_cost_per_token": 9e-06}}
        biasa = _feed_entry(umpan, "anthropic/claude-haiku-4.5", provider_prefix="fal")
        self.assertIsNotNone(biasa, "penyedia biasa kehilangan kunci-persis — perbaikan jadi merusak")
        agr = _feed_entry(umpan, "anthropic/claude-haiku-4.5", provider_prefix="fal", wajib_prefix=True)
        self.assertEqual(agr, umpan["fal/anthropic/claude-haiku-4.5"],
                         "baris agregator memakai tarif vendor lain (kunci-persis lolos pagar)")

    def test_sumber_cadangan_tak_dipakai_baris_agregator(self):
        """Sumber cadangan mencari BY SUFFIX → yang ditemukan tarif vendor asal. Haram untuk agregator."""
        isi = _tanpa_komentar("src/billing/price_sync.py", _isi("src/billing/price_sync.py"))
        self.assertRegex(isi, r'component"\) == "llm" and not agr',
                         "sumber cadangan masih dipakai baris agregator → tarif vendor lain masuk")


class G12_SumberResmiPenyedia(unittest.TestCase):
    """F4 — penyedia boleh punya API harga resminya sendiri, dan itu DATA.

    Terbukti 23-Agu: fal menerbitkan tarif + SATUAN TAGIHNYA lewat API resmi. Itu satu-satunya sumber
    yang berwenang untuk baris agregator (pagar F3). Yang dijaga di sini:
      (a) peta satuan-vendor → formula adalah DATA (satuan baru = satu baris, bukan cabang if)
      (b) satuan yang belum punya formula TIDAK ditulis — lebih baik kosong daripada tertulis tapi
          mustahil dihitung (baris akan tampak berharga padahal biayanya nol)
      (c) alamat HARGA boleh beda dari penanda model (agregator satu-pintu: fal any-llm)
      (d) tarif & FORMULA ditulis BERSAMA — kalau tidak, bentuk harga berubah sementara formula lama
          tetap, dan biayanya jadi "tak terhitung" (jebakan Kling: basis-per-klip → per-detik)
      (e) ada JEDA antar panggilan API penyedia (fal menolak panggilan berdempet: HTTP 429)
      (f) kunci platform HANYA untuk endpoint harga — haram dipakai menjalankan model
    """

    KODE = "src/billing/price_sync.py"

    def test_peta_satuan_vendor_adalah_data(self):
        from src.billing.price_sync import SATUAN_VENDOR
        from src.billing.ai_cost import FORMULA
        self.assertTrue(SATUAN_VENDOR, "peta satuan vendor kosong")
        from src.billing.ai_cost import kunci_tunggal_formula
        kunci_formula = {f.kunci for f in FORMULA}
        for satuan, (formula, kali) in SATUAN_VENDOR.items():
            with self.subTest(satuan):
                self.assertIn(formula, kunci_formula, f"satuan '{satuan}' menunjuk formula tak dikenal")
                self.assertGreater(kali, 0, "pengali tak sah")
                # Kunci tarifnya WAJIB bisa diturunkan dari formulanya — kalau tidak, sinkron akan
                # terpaksa mengetik nama satuan (kosakata tersebar; itu akar cacat 23-Agu).
                self.assertIsNotNone(kunci_tunggal_formula(formula),
                                     f"formula '{formula}' tak punya kunci tarif tunggal")

    def test_satuan_tanpa_formula_tidak_ditulis(self):
        """Satuan yang belum punya formula (megapixels, 1m tokens) HARAM dipetakan diam-diam."""
        from src.billing.price_sync import SATUAN_VENDOR
        from src.billing.ai_cost import FORMULA_BELUM_DIDUKUNG, FORMULA
        for satuan in ("megapixels", "1m tokens"):
            with self.subTest(satuan):
                peta = SATUAN_VENDOR.get(satuan)
                if peta is None:
                    continue          # tak dipetakan = sikap yang benar hari ini
                self.assertNotIn(peta[0], FORMULA_BELUM_DIDUKUNG,
                                 f"satuan '{satuan}' dipetakan ke formula yang belum bisa dihitung")
        # dan formula yang belum didukung wajib tetap dikenal katalog (bukan nama karangan)
        self.assertTrue(FORMULA_BELUM_DIDUKUNG <= {f.kunci for f in FORMULA})

    def test_alamat_harga_boleh_beda_dari_penanda_model(self):
        isi = _tanpa_komentar(self.KODE, _isi(self.KODE))
        self.assertIn("price_endpoint_id", isi,
                      "alamat harga tak bisa berbeda dari model_id → agregator satu-pintu (fal "
                      "any-llm) selalu 404 dan tarifnya tak pernah terbaca")

    def test_tarif_dan_formula_ditulis_bersama(self):
        isi = _tanpa_komentar(self.KODE, _isi(self.KODE))
        self.assertRegex(isi, r'patch\["pricing_model"\]\s*=\s*formula_baru',
                         "formula tak ikut ditulis bersama tarif → bentuk harga berubah tapi formula "
                         "lama tetap, biayanya jadi 'tak terhitung' (jebakan Kling)")

    def test_sumber_resmi_dicoba_sebelum_umpan_umum(self):
        """Umpan umum tak berwenang untuk baris agregator; sumber resmi harus menang."""
        isi = _tanpa_komentar(self.KODE, _isi(self.KODE))
        i_api = isi.index("_harga_vendor(url_api")
        i_umpan = isi.index("_feed_entry(feed,")
        self.assertLess(i_api, i_umpan, "umpan umum dicoba lebih dulu daripada sumber resmi penyedia")
        self.assertRegex(isi, r"if e and pricing is None:",
                         "umpan umum bisa MENIMPA hasil sumber resmi penyedia")

    def test_ada_jeda_antar_panggilan_api_penyedia(self):
        from src.billing import price_sync
        self.assertGreater(price_sync.VENDOR_API_DELAY, 0,
                           "tak ada jeda → fal menolak panggilan berdempet (429) dan baris terlewat")
        isi = _tanpa_komentar(self.KODE, _isi(self.KODE))
        self.assertRegex(isi, r"sleep\(max\(0\.0, VENDOR_API_DELAY",
                         "jeda didefinisikan tapi tak dipakai (kode mati)")

    def test_kunci_platform_hanya_untuk_harga(self):
        """Kunci Test Lab owner HARAM dipakai menjalankan model (itu membakar kreditnya)."""
        akar = AKAR
        pemakai = []
        for dp, _, fs in os.walk(os.path.join(akar, "src")):
            if "__pycache__" in dp:
                continue
            for f in fs:
                if not f.endswith(".py"):
                    continue
                rel = os.path.relpath(os.path.join(dp, f), akar)
                if "_kunci_platform" in _isi(rel) and rel != self.KODE:
                    pemakai.append(rel)
        self.assertEqual(pemakai, [], f"kunci platform dipakai di luar jalur harga: {pemakai}")
