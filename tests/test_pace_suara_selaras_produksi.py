"""ANGKA KECEPATAN BICARA DI KATALOG WAJIB SELARAS DENGAN PRODUKSI NYATA.

CACAT YANG DIJAGA — dan ini bug yang SAYA SENDIRI tanam 18-Agu, ditemukan owner 19-Agu lewat
pertanyaan *"mengapa tessartea banyak konten yang terkena qc_failed"*:

Saya mengukur kecepatan bicara suara Gemini dengan **SATU teks 32 kata**, lalu memasang angkanya ke
katalog (Kore 1,93 · Aoede 2,05). Produksi nyata memakai **120–207 kata**, dan di sana suaranya
jauh lebih cepat. Terukur pada 4 produksi 19-Agu:

    Kore   dipakai 1,93 → nyata 2,38  (+23%)
    Aoede  dipakai 2,05 → nyata 2,67  (+30%)
    Aoede  dipakai 2,05 → nyata 2,34  (+14%)
    Aoede  dipakai 2,05 → nyata 2,45  (+20%)

RANTAI KERUSAKANNYA: mesin menyangka suaranya lambat ⇒ resep naskah menuntut LEBIH SEDIKIT kata
(preset 90 dtk: 181–207 kata pada 1,93 wps, padahal seharusnya ~215–250) ⇒ suara yang sebenarnya
cepat menyelesaikannya lebih awal ⇒ **video kependekan** ⇒ **QC MENOLAK**. Terukur: 8 dari 9 QC
gagal tenant itu berbunyi "kependekan", **nol** "kepanjangan" — satu arah, jadi bukan kebetulan.

Contoh satu run (BISIK NUSANTARA 19-Agu 12:18): resep 181–207 kata → naskah 156w → refit 3 putaran
mentok di 75s → audio nyata 72,3s vs target 86,5s → QC menolak. Tiga putaran perbaikan naskah
terbakar mengejar target yang dihitung dari angka yang salah.

KENAPA UJI INI, BUKAN "LEBIH TELITI LAIN KALI": pengukuran tangan saya sudah GAGAL sekali, dan
sumber kebenarannya sudah tersedia — mesin mengumpulkan sampel produksi sendiri
(`tts_delivery_samples`). Kalibrasi otomatis butuh 14 sampel per suara; selama belum cukup, angka
KATALOG yang dipakai. Uji ini mengikat angka katalog itu ke sampel yang SUDAH ADA.

BATAS UJI INI (jujur): ia hanya menilai suara yang sudah punya ≥3 sampel produksi. Suara baru tanpa
sampel tak bisa ia nilai — dan justru di situ pengukuran tangan wajib memakai teks sepanjang
produksi, bukan 32 kata.
"""
import os
import statistics
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOLERANSI_PCT = 15      # di luar ±15% ⇒ resep naskah meleset cukup jauh untuk menembus band QC
MIN_SAMPEL    = 3


def _sb():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(AKAR, ".env"))
    from supabase import create_client
    u = os.getenv("SUPABASE_URL")
    k = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(u, k) if (u and k) else None


class TestPaceSelarasProduksi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sb = _sb()
        if cls.sb is None:
            raise unittest.SkipTest("kredensial DB tak tersedia — bukan kegagalan")
        cls.suara = {v["voice_key"]: v for v in cls.sb.table("voice_catalog")
                     .select("voice_key,provider_key,delivery_wps,is_active")
                     .eq("is_active", True).execute().data}
        cls.sampel = {}
        for s in cls.sb.table("tts_delivery_samples").select("voice_key,words,audio_secs").execute().data:
            if (s.get("audio_secs") or 0) > 0 and (s.get("words") or 0) > 0:
                cls.sampel.setdefault(s["voice_key"], []).append(s["words"] / s["audio_secs"])

    def test_angka_katalog_tak_meleset_dari_produksi(self):
        meleset = []
        for vk, v in self.suara.items():
            wps_katalog = v.get("delivery_wps")
            contoh = self.sampel.get(vk) or []
            if not wps_katalog or len(contoh) < MIN_SAMPEL:
                continue
            nyata = statistics.median(contoh)
            selisih = (nyata / float(wps_katalog) - 1) * 100
            if abs(selisih) > TOLERANSI_PCT:
                meleset.append(f"{vk}: katalog {wps_katalog} vs produksi {nyata:.2f} "
                               f"({selisih:+.0f}%, {len(contoh)} sampel)")
        self.assertEqual(
            meleset, [],
            "Angka kecepatan bicara di katalog meleset dari produksi nyata: " + " · ".join(meleset) +
            ". Akibatnya resep naskah salah panjang ⇒ video kependekan/kepanjangan ⇒ QC MENOLAK, dan "
            "putaran perbaikan naskah terbakar mengejar target yang dihitung dari angka yang salah.")

    def test_pace_dasar_mesin_juga_selaras_produksi(self):
        """Suara TANPA angka sendiri jatuh ke pace DASAR mesin — itu RANCANGAN yang sah (banyak suara
        lama memakainya dengan sengaja), jadi tak boleh dituduh cacat. Yang WAJIB benar: pace dasar
        itu sendiri, karena ia yang dipakai setiap suara baru yang belum punya sampel."""
        prof = {t["provider_key"]: t for t in self.sb.table("tts_profiles")
                .select("provider_key,delivery_wps,is_active").eq("is_active", True).execute().data}
        meleset = []
        for pk, p in prof.items():
            contoh = [w for vk, v in self.suara.items() if v.get("provider_key") == pk
                      for w in (self.sampel.get(vk) or [])]
            if len(contoh) < MIN_SAMPEL or not p.get("delivery_wps"):
                continue
            nyata = statistics.median(contoh)
            selisih = (nyata / float(p["delivery_wps"]) - 1) * 100
            if abs(selisih) > TOLERANSI_PCT:
                meleset.append(f"{pk}: dasar {p['delivery_wps']} vs produksi {nyata:.2f} "
                               f"({selisih:+.0f}%, {len(contoh)} sampel)")
        self.assertEqual(
            meleset, [],
            "Pace DASAR mesin meleset dari produksi: " + " · ".join(meleset) +
            ". Angka ini dipakai SETIAP suara baru yang belum punya sampel — kalau ia salah, "
            "setiap suara baru langsung mewarisi kesalahannya (persis insiden 18-Agu).")


class TestSSOTDurasiTakBolehDiam(unittest.TestCase):
    """SSOT durasi WAJIB memuat larangan yang dilanggar 18-Agu + insidennya.

    Owner 20-Agu: *"salah satu gerbang aturan kerja terkait dokumen arsitektur sebagai SSOT, apakah
    harus selalu saya ingatkan? saya lelah kalau begini terus."* — Larangan **"JANGAN dikalibrasi
    ulang membuta"** SUDAH tertulis di `QC_CONTENT_ARCHITECTURE.md` sebelum insiden, dan tetap
    dilanggar karena tak ada yang menolak. Uji ini membuat dokumen itu **tak bisa kehilangan**
    larangan maupun catatan insidennya — sehingga sesi berikutnya membacanya, bukan diingatkan owner.
    """

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(AKAR, "QC_CONTENT_ARCHITECTURE.md"), encoding="utf-8") as f:
            cls.doc = f.read()

    def test_larangan_kalibrasi_membuta_masih_di_TEMPATNYA(self):
        """KOREKSI ATAS PENJAGA PALSU SAYA SENDIRI (20-Agu): versi pertama hanya memeriksa apakah
        kalimat larangan ADA di dokumen — dan ia SELALU ada, sebab teks insiden yang saya tulis
        MENGUTIPnya. Sabotase (menghapus larangan dari baris ROOT-CAUSE) tetap hijau ⇒ penjaga yang
        tak bisa gagal. Kini yang diperiksa: larangan itu ada di BARIS ROOT-CAUSE — tempat mengikat
        yang dibaca sesi baru — bukan di mana pun."""
        baris_root = [l for l in self.doc.splitlines() if "ROOT-CAUSE FINAL" in l]
        self.assertTrue(baris_root, "baris ROOT-CAUSE FINAL hilang dari SSOT durasi")
        self.assertIn(
            "JANGAN dikalibrasi ulang membuta", baris_root[0],
            "Larangan itu hilang dari baris ROOT-CAUSE — inilah kalimat yang seharusnya mencegah "
            "insiden 18-Agu (8 produksi tenant terbuang, Rp 37.956). Mengutipnya di tempat lain "
            "TIDAK menggantikan: sesi baru membaca baris root-cause.")

    def test_insidennya_tercatat_agar_tak_terulang(self):
        self.assertIn(
            "INSIDEN 18/19-Agu", self.doc,
            "Insiden pelanggaran larangan itu tak tercatat di SSOT durasi. Tanpa catatan, sesi "
            "berikutnya mengulang jalan yang sama dan owner lagi yang harus mengingatkan.")

    def test_cara_sah_mengukur_disebut(self):
        """Dua cara sah menurut rancangan — supaya sesi berikutnya tak mengarang cara ketiga."""
        for jalan in ("ukur_jeda_suara.py", "tts_delivery_samples"):
            self.assertIn(jalan, self.doc,
                          f"cara sah mengukur pace '{jalan}' tak disebut di SSOT durasi")


if __name__ == "__main__":
    unittest.main()
