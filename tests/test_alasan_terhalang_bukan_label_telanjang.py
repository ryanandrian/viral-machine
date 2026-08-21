"""CHANNEL TERHALANG WAJIB PUNYA ALASAN — label telanjang membuat tenant diam berhari-hari.

CACAT YANG DIJAGA (insiden 17-Agu, ditemukan 21-Agu saat menelusuri laporan owner):
Model naskah yang dipakai 4 channel dimatikan di katalog karena vendor memensiunkannya. Tiga di
antaranya milik tenant BERBAYAR. Produksi mereka berhenti **4 hari tanpa seorang pun diberi tahu**,
dan log dibanjiri 20.979 baris.

Sebabnya BUKAN kekurangan deteksi — mesin sudah tahu. Ada DUA pintu, dan hanya satu bersuara:

    model mati saat produksi JALAN  → adapter → MODEL_UNAVAILABLE → pesan sebut nama model ✅
    model mati saat channel DIAM    → gerbang kesiapan → label 'model naskah' → skip senyap ❌

Label `'model naskah'` menampung dua keadaan yang tindakannya BEDA JAUH: "belum memilih" vs
"pilihan Anda sudah dipensiunkan penyedianya". Tenant tak bisa membedakannya.

KENAPA LABELNYA TIDAK BOLEH DIUBAH (dan uji ini mengunci itu):
label = KUNCI MESIN. Checklist 7 baris di layar tenant mencocokkan KATANYA
(`channels/[id]/page.tsx` → has("naskah")/has("suara")/has("visual")/…). Mengubah teksnya membuat
checklist itu SALAH — hijau padahal rusak. Itu kelas kerusakan 17-Agu yang terulang.
⇒ Perbaikan wajib ADITIF: label lama utuh, alasan berstruktur ditambahkan di sebelahnya.

Hermetik: nol jaringan (memeriksa berkas). Satu kelas uji memakai DB hidup dan MELEWAT bila
kredensial tak ada — pola sama dengan `tests/test_katalog_suara_tak_menipu.py`.
"""
import io
import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

# Ke-16 label yang boleh dikembalikan `channel_missing()` — KONTRAK, bukan hiasan.
# Diukur dari migrasi 0131 (definisi terakhir) + fungsi DB hidup, 2026-08-21.
LABEL_KONTRAK = frozenset({
    "niche", "bahasa konten",
    "penyedia naskah", "model naskah", "kunci naskah",
    "penyedia suara", "model suara", "karakter suara", "kunci suara",
    "jenis visual", "model visual", "penyedia visual", "kunci visual",
    "jadwal posting", "koneksi YouTube", "Telegram",
})


def _baca(rel: str) -> str:
    return io.open(os.path.join(AKAR, rel), encoding="utf-8").read()


class TestA_KontrakLabelTakBolehPECAH(unittest.TestCase):
    """Satu-satunya hal di jalur ini yang bisa memecahkan layar tenant."""

    def test_migrasi_terakhir_masih_memuat_16_label(self):
        src = _baca("migrations/0131_content_language_wiring.sql")
        ada = set(re.findall(r"array_append\(v_miss,\s*'([^']+)'", src))
        self.assertEqual(
            ada, set(LABEL_KONTRAK),
            "Kontrak label `channel_missing` berubah. Checklist 7 baris di layar tenant "
            "MENCOCOKKAN teks ini — mengubahnya membuat checklist salah (hijau padahal rusak). "
            f"hilang={sorted(set(LABEL_KONTRAK) - ada)} · asing={sorted(ada - set(LABEL_KONTRAK))}")

    def test_migrasi_alasan_TIDAK_mendefinisikan_ulang_channel_missing(self):
        src = _baca("migrations/0204_alasan_channel_terhalang.sql").lower()
        self.assertNotIn(
            "function public.channel_missing", src,
            "Migrasi alasan menyentuh `channel_missing` — perbaikan ini WAJIB aditif.")
        self.assertNotIn("function channel_missing", src)

    def test_dua_kunci_lama_channel_readiness_dipertahankan(self):
        src = _baca("migrations/0204_alasan_channel_terhalang.sql")
        # `ready` & `missing` wajib dibangun dari ekspresi yang SAMA seperti sebelumnya.
        self.assertIn("array_length(v_miss,1) is null", src, "kunci `ready` berubah bentuk")
        self.assertIn("to_jsonb(v_miss)", src, "kunci `missing` berubah bentuk")
        self.assertIn("'reasons'", src, "kunci `reasons` tak ditambahkan")


class TestB_AlasanSampaiKeMESIN(unittest.TestCase):
    """Alasan tak berguna bila lapisan Python membuangnya."""

    def test_readiness_meneruskan_alasan(self):
        src = _baca("src/orchestrator/readiness.py")
        self.assertIn(
            "channel_blockers_by_id", src,
            "`readiness.py` tak pernah mengambil alasan ⇒ log producer tetap label telanjang, "
            "dan sesi berikutnya tetap harus menebak channel mana yang rusak karena apa.")
        self.assertIn("reasons", src, "kunci `reasons` tak diteruskan ke pemanggil")

    def test_alasan_diambil_HANYA_saat_tidak_siap(self):
        """Producer memutari SELURUH channel tiap ±16 detik. Mengambil alasan untuk channel
        yang sehat = satu panggilan DB sia-sia per channel per siklus."""
        src = _baca("src/orchestrator/readiness.py")
        i_ready = src.find("channel_missing_by_id")
        i_alasan = src.find("channel_blockers_by_id")
        self.assertGreater(i_alasan, i_ready, "alasan diambil sebelum kesiapan diketahui")
        potong = src[i_ready:i_alasan]
        self.assertTrue(
            re.search(r"if\s+.*missing|len\(missing\)|if\s+missing", potong),
            "alasan diambil tanpa syarat — boros satu panggilan DB per channel per siklus.")


class TestC_LayarTenantBERBICARA(unittest.TestCase):
    """Tenant harus bisa membaca APA yang rusak, bukan hanya titik merah."""

    LAYAR = "apps/web/src/app/(app)/channels/[id]/page.tsx"

    def test_checklist_menampilkan_alasan(self):
        """Sabotase membuktikan versi pertama uji ini PALSU: ia hanya memeriksa kata "reasons" ADA
        di berkas, jadi mencabut perendernya (→ `{null}`) tetap HIJAU. Yang dikunci sekarang:
        alasan benar-benar DIPANGGIL di dalam daftar checklist yang dilihat tenant."""
        src = _baca(self.LAYAR)
        self.assertIn("reasons", src, "layar tak pernah membaca `reasons`")
        self.assertIn("model_unavailable", src, "golongan `model_unavailable` tak diterjemahkan")

        awal = src.find("const REQS = [")
        self.assertGreater(awal, 0, "daftar checklist tak ditemukan")
        akhir = src.find("</ul>", awal)
        self.assertGreater(akhir, awal)
        blok = src[awal:akhir]
        self.assertTrue(
            re.search(r"alasan\w*\(", blok),
            "Perender alasan tidak DIPANGGIL di dalam checklist ⇒ tenant tetap hanya melihat titik "
            "merah. (Kata 'reasons' ada di berkas ≠ alasannya tampil di layar.)")
        # Sabotase membuktikan versi pertama pemeriksaan ini PALSU: `"r.slot" in blok` tetap hijau
        # walau perendernya dipanggil dengan slot TETAP (`alasanJsx("llm")`), karena `r.slot` masih
        # muncul di syaratnya. Yang dikunci sekarang: ARGUMEN perender = slot baris itu.
        self.assertTrue(
            re.search(r"alasan\w*\(\s*r\.slot\s*\)", blok),
            "Perender alasan tidak dipanggil dengan slot BARIS ITU ⇒ alasan slot suara bisa muncul "
            "di baris naskah, dan tenant diarahkan memperbaiki yang salah.")

    def test_alasan_menyebut_NAMA_model_dan_penyedia(self):
        """Tanpa nama model, kalimat 'pilih model lain' tak bisa dikerjakan — tenant punya 3 slot AI."""
        src = _baca(self.LAYAR)
        blok = src[src.find("reasons"):] if "reasons" in src else ""
        self.assertTrue(
            re.search(r"\.model\b", blok) and re.search(r"provider_name|\.provider\b", blok),
            "Alasan dirender tanpa nama model / penyedianya — tenant tetap harus menebak slot mana.")

    def test_checklist_7_baris_TIDAK_diubah(self):
        """REGRESI: pencocokan teks lama wajib utuh — inilah yang pecah kalau label diubah."""
        src = _baca(self.LAYAR)
        for kata in ('has("naskah")', 'has("suara")', 'has("visual")',
                     'has("jadwal")', 'has("youtube")', 'rd.missing.includes("niche")',
                     'rd.missing.includes("Telegram")'):
            self.assertIn(kata, src, f"pencocokan checklist `{kata}` hilang ⇒ baris itu jadi salah")

    def test_onboarding_juga_berbicara(self):
        src = _baca("apps/web/src/app/onboarding/page.tsx")
        self.assertIn(
            "reason", src.lower(),
            "Layar onboarding menampilkan label MENTAH ke tenant baru; tanpa alasan, tenant baru "
            "membaca jargon mesin.")


class TestD_ModelMatiTERLIHAT_tapi_TERKUNCI(unittest.TestCase):
    """Pemilih menyaring is_active=true ⇒ pilihan tenant HILANG dari daftar begitu dimatikan.
    Tenant melihat titik merah + daftar tanpa pilihannya + nol penjelasan."""

    LAYAR = "apps/web/src/app/(app)/channels/[id]/page.tsx"

    def test_model_terpilih_yang_mati_tetap_tampil(self):
        src = _baca(self.LAYAR)
        self.assertTrue(
            re.search(r"tidak lagi tersedia|no longer available", src),
            "Model yang sedang dipakai tenant hilang dari daftar saat dimatikan — tenant tak bisa "
            "melihat apa yang rusak.")

    def test_dan_TIDAK_BISA_DIPILIH(self):
        """`saveAiPart` menyimpan tanpa memvalidasi katalog (channels/[id]/page.tsx) dan trigger
        aktivasi hanya menyala saat TRANSISI aktif ⇒ opsi yang bisa dipilih MEMPERLEBAR lubang."""
        src = _baca(self.LAYAR)
        i = src.find("tidak lagi tersedia")
        self.assertGreater(i, 0)
        potong = src[max(0, i - 700):i + 300]
        self.assertIn(
            "disabled", potong,
            "Model mati ditawarkan sebagai pilihan yang BISA dipilih. Melihat ≠ memilih: "
            "jalur simpan tak memvalidasi katalog, jadi ini menambah channel menggantung baru.")


class TestD2_PakaiPustakaBukanKomponenBaru(unittest.TestCase):
    """Aturan owner: pakai pustaka komponen yang sudah ada, jangan bikin komponen baru
    (diulangi 21-Agu). Uji ini mengunci keduanya untuk perbaikan ini."""

    LAYAR = "apps/web/src/app/(app)/channels/[id]/page.tsx"

    def test_nol_komponen_baru_di_pustaka_komponen(self):
        import glob
        baru = [os.path.basename(f) for f in glob.glob(os.path.join(AKAR, "apps/web/src/components/*"))
                if "alasan" in os.path.basename(f).lower() or "blocker" in os.path.basename(f).lower()]
        self.assertEqual(baru, [], f"komponen FE baru dibuat: {baru} — pakai yang sudah ada")

    def test_pil_nonaktif_memakai_KELAS_pustaka(self):
        """Gaya tempelan (`opacity`/`cursor` inline) = keluar dari sistem desain. Konvensi nonaktif
        sudah ada di pustaka (`.btn:disabled`) dan diperluas ke `.radio-pill`."""
        css = _baca("apps/web/src/styles/components.css")
        self.assertIn('.radio-pill[aria-disabled="true"]', css,
                      "varian nonaktif tidak ditambahkan ke PUSTAKA — jadi tiap layar akan menempel gaya sendiri")
        src = _baca(self.LAYAR)
        i = src.find('aria-disabled="true"')
        self.assertGreater(i, 0)
        potong = src[max(0, i - 260):i + 260]
        for tempel in ("opacity:", "cursor:", "borderStyle:"):
            self.assertNotIn(tempel, potong,
                             f"gaya tempelan `{tempel}` pada pil nonaktif — pindahkan ke pustaka CSS")


class TestE_LogBerhentiMEMBANJIR(unittest.TestCase):
    """Terukur: 20.979 baris dalam 5 hari (±1 baris/17 detik) untuk 4 channel yang sama."""

    def _cabang_ready(self) -> str:
        """HANYA isi cabang `belum READY` — bukan tetangganya.

        Versi pertama uji ini memotong 900 karakter sebelum baris log dan LOLOS karena melihat
        penjaga cabang SEBELAHNYA ('langganan tidak aktif'). Lolos karena alasan yang salah = uji
        palsu. Potongan di bawah dibatasi tegas: dari syarat cabang sampai `continue`-nya.
        """
        src = _baca("src/orchestrator/producer.py")
        awal = src.find('if not _rd["ready"] and not _rd["check_failed"]:')
        self.assertGreater(awal, 0, "syarat cabang kesiapan tak ditemukan")
        # Batas akhir = PERNYATAAN `continue`, bukan kata "continue" yang kebetulan ada di komentar.
        # (Versi pertama uji ini memotong di komentar `# Syarat & \`continue\` TIDAK diubah` sehingga
        #  seluruh isi cabang tak pernah diperiksa — pemotong yang cacat = uji yang menipu.)
        m = re.search(r"\n\s+continue\b", src[awal:])
        self.assertIsNotNone(m, "`continue` cabang kesiapan tak ditemukan")
        return src[awal:awal + m.end()]

    def test_skip_belum_ready_dicatat_sekali(self):
        cabang = self._cabang_ready()
        self.assertIn("belum READY", cabang, "baris log skip-READY bukan di cabang ini")
        self.assertTrue(
            re.search(r"if\s+.*_[A-Z_]*DICATAT", cabang),
            "Cabang 'belum READY' mencatat SETIAP siklus (±17 detik) — terukur 20.979 baris dalam "
            "5 hari untuk 4 channel yang sama. Pencegah pengulangan sudah dipakai cabang "
            "'langganan tidak aktif' di berkas yang SAMA; cabang ini dilewatkan.")

    def test_penanda_TERPISAH_dari_cabang_langganan(self):
        """`_SKIP_SUDAH_DICATAT` di-`discard` tepat SEBELUM cek kesiapan (baris `.discard(cid)`).
        Memakai set yang sama = penanda dibuang tiap siklus = banjir tetap terjadi."""
        cabang = self._cabang_ready()
        self.assertNotIn(
            "_SKIP_SUDAH_DICATAT", cabang,
            "Cabang kesiapan memakai penanda cabang langganan, padahal penanda itu dibuang "
            "(`discard`) tepat sebelum cek kesiapan ⇒ pencegah banjir tidak akan bekerja.")

    def test_alasan_ikut_dicatat_di_log(self):
        """Log 'kurang: model naskah' tak bisa didiagnosa siapa pun. Nama model + penyedianya
        SUDAH ada di tangan pada titik itu — membuangnya berarti sesi berikutnya menebak lagi."""
        cabang = self._cabang_ready()
        self.assertIn(
            "reasons", cabang,
            "Baris log skip hanya menyebut label telanjang, padahal alasan berstruktur "
            "(nama model + penyedia) sudah tersedia di titik itu.")

    def test_syarat_dan_continue_TIDAK_diubah(self):
        """Pencegah banjir HANYA menyentuh pencatatan. Kalau syaratnya ikut berubah, channel mana
        yang berproduksi bisa berubah — itu bukan lagi perbaikan log."""
        src = _baca("src/orchestrator/producer.py")
        self.assertIn('if not _rd["ready"] and not _rd["check_failed"]:', src,
                      "syarat gerbang kesiapan berubah — ini di luar lingkup perbaikan log")


class TestF_FungsiDBHidup(unittest.TestCase):
    """Diukur pada DB HIDUP. MELEWAT bila kredensial tak ada (pola test_katalog_suara_tak_menipu)."""

    @classmethod
    def setUpClass(cls):
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(AKAR, ".env"))
            from supabase import create_client
            url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
            if not url or not key:
                raise unittest.SkipTest("kredensial Supabase tak ada — uji DB hidup dilewat")
            cls.c = create_client(url, key)
        except unittest.SkipTest:
            raise
        except Exception as e:  # pragma: no cover
            raise unittest.SkipTest(f"Supabase tak terjangkau: {e}")

    def test_fungsi_alasan_ADA_dan_menjawab(self):
        ch = self.c.table("channels").select("id,channel_name").limit(1).execute().data
        self.assertTrue(ch, "nol channel di DB — tak bisa diukur")
        try:
            hasil = self.c.rpc("channel_blockers_by_id", {"p_channel_id": ch[0]["id"]}).execute().data
        except Exception as e:
            self.fail(f"`channel_blockers_by_id` belum ada di DB: {str(e)[:120]}")
        self.assertIsInstance(hasil, list, "alasan harus berbentuk daftar")

    def test_setiap_rujukan_katalog_MATI_menghasilkan_alasan(self):
        """INTI: channel yang menunjuk baris katalog mati WAJIB dapat alasan spesifik,
        bukan label telanjang. Diukur pada data apa adanya — nol data tenant disentuh."""
        kat = {x["model_key"]: x for x in
               self.c.table("ai_models").select("model_key,is_active,component").execute().data}
        chs = self.c.table("channels").select(
            "id,channel_name,llm_model,tts_model,visual_mode").execute().data
        gagal = []
        for r in chs:
            vm = r.get("visual_mode") or ""
            vmodel = vm.split(":", 1)[1] if ":" in vm else None
            menggantung = [v for v in (r.get("llm_model"), r.get("tts_model"), vmodel)
                           if v and (v not in kat or not kat[v]["is_active"])]
            if not menggantung:
                continue
            alasan = self.c.rpc("channel_blockers_by_id", {"p_channel_id": r["id"]}).execute().data or []
            disebut = {a.get("model") for a in alasan}
            for v in menggantung:
                if v not in disebut:
                    gagal.append(f"{r['channel_name']}: `{v}` menggantung tapi tak beralasan")
        self.assertEqual(gagal, [], "Rujukan katalog menggantung tanpa alasan spesifik:\n  " +
                         "\n  ".join(gagal))

    def test_channel_SEHAT_tidak_dituduh(self):
        """Alasan palsu lebih berbahaya daripada tak ada alasan."""
        kat = {x["model_key"]: x for x in
               self.c.table("ai_models").select("model_key,is_active").execute().data}
        vc = {x["voice_key"]: x for x in
              self.c.table("voice_catalog").select("voice_key,is_active").execute().data}
        chs = self.c.table("channels").select(
            "id,channel_name,llm_model,tts_model,voice_key,visual_mode").execute().data
        salah = []
        for r in chs:
            vm = r.get("visual_mode") or ""
            vmodel = vm.split(":", 1)[1] if ":" in vm else None
            sehat = all((not v) or (v in kat and kat[v]["is_active"])
                        for v in (r.get("llm_model"), r.get("tts_model"), vmodel))
            vk = r.get("voice_key")
            sehat = sehat and ((not vk) or (vk in vc and vc[vk]["is_active"]))
            if not sehat:
                continue
            alasan = self.c.rpc("channel_blockers_by_id", {"p_channel_id": r["id"]}).execute().data or []
            if alasan:
                salah.append(f"{r['channel_name']}: dituduh {alasan}")
        self.assertEqual(salah, [], "Channel sehat diberi alasan palsu:\n  " + "\n  ".join(salah))


if __name__ == "__main__":
    unittest.main()
