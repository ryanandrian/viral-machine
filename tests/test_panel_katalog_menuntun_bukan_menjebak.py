"""PANEL KATALOG WAJIB MENUNTUN ADMIN, BUKAN MENJEBAKNYA — butir B1–B6.

SSOT peta & prasyarat: `ARSITEKTUR_AI_PROVIDER_MODEL.md` §9 (koridor 7 langkah · prasyarat per kolom
+ akibat bila salah · 11 titik lemah terukur). Backlog & aturan kerja: `SISA_KERJA_GO_LIVE.md`.

Latar (jangan diulang): 21-Agu rancangan 6c DIBATALKAN owner karena menambah PINTU BARU di panel,
padahal yang diminta memperbaiki jalur yang ADA. Enam butir di bawah SENGAJA nol tombol/tab/lencana
baru. Dua di antaranya (B5·B6) menutup lubang yang dibuat sesi 21-Agu sendiri.

Hermetik: nol jaringan.
"""
import io
import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

RUTE  = "apps/web/src/app/api/admin/catalog/route.ts"
LAYAR = "apps/web/src/app/admin/(panel)/catalog/page.tsx"


def _baca(rel: str) -> str:
    return io.open(os.path.join(AKAR, rel), encoding="utf-8").read()


def _blok(src: str, awal: str) -> str:
    i = src.find(awal)
    assert i > 0, f"blok `{awal}` tak ditemukan"
    return src[i:src.find("\n};", i) + 3]


def _meta_entri(mapkey: str, kolom: str) -> str | None:
    """Isi satu entri `FIELD_META[mapkey][kolom]`, diurai dengan penghitung KEDALAMAN.

    Regex `\{([^}]*)\}` TIDAK bisa dipakai di sini: arahan yang baik justru memuat contoh JSON
    (mis. `{"size":"1024x1536"}`), dan regex itu berhenti di kurung penutup PERTAMA — lalu
    melaporkan entri yang lengkap sebagai 'tidak ada'. Cacat itu tertangkap 22-Agu."""
    blok = _blok(_baca(LAYAR), "const FIELD_META:")
    i = blok.find(f"  {mapkey}: {{")
    if i < 0:
        return None
    j = blok.find(f"{kolom}: {{", i)
    if j < 0 or j > blok.find("\n  },", i):
        return None
    k = blok.find("{", j)
    d, m = 0, k
    while m < len(blok):
        if blok[m] == "{":
            d += 1
        elif blok[m] == "}":
            d -= 1
            if d == 0:
                return blok[k + 1:m]
        m += 1
    return None


def _help(mapkey: str, kolom: str, bahasa: str) -> str:
    """Nilai `help_id` / `help_en` sebuah entri, TERPISAH per bahasa.

    Dua cacat uji yang tertangkap sabotase 22-Agu, dan keduanya diperbaiki di sini:
    (1) `"help_id" in isi` LOLOS ketika kuncinya diganti `xhelp_id` — substring. Sekarang batas kata.
    (2) memeriksa entri gabungan (id+en) membuat frasa yang dihapus dari `help_id` tetap "ditemukan"
        karena masih ada di `help_en`. Sekarang per bahasa."""
    isi = _meta_entri(mapkey, kolom) or ""
    # Penutup `,`/`}` dibuat OPSIONAL: entri TERAKHIR (biasanya `help_en`) tak diikuti koma, dan
    # `}` penutupnya sudah dipotong `_meta_entri`. Tanpa ini `help_en` selalu terbaca kosong.
    m = re.search(rf"(?<![a-z_]){bahasa}:\s*(['\"])(.*?)\1\s*(?:[,}}]|$)", isi, re.S)
    return m.group(2) if m else ""


def _punya_help(mapkey: str, kolom: str) -> bool:
    """Arahan dianggap ADA hanya bila KEDUA bahasa terisi (layar admin dwibahasa)."""
    return bool(_help(mapkey, kolom, "help_id")) and bool(_help(mapkey, kolom, "help_en"))


def _meta_kolom(mapkey: str) -> dict:
    """{kolom: punya_arahan} untuk seluruh entri FIELD_META[mapkey]."""
    blok = _blok(_baca(LAYAR), "const FIELD_META:")
    i = blok.find(f"  {mapkey}: {{")
    if i < 0:
        return {}
    sub = blok[i:blok.find("\n  },", i)]
    out = {}
    for m in re.finditer(r"^\s{4}([a-z_]+):\s*\{", sub, re.M):
        isi = _meta_entri(mapkey, m.group(1))
        out[m.group(1)] = bool(isi) and _punya_help(mapkey, m.group(1))
    return out


def _kolom_whitelist(tabel: str) -> list[str]:
    m = re.search(rf"\b{tabel}:\s*\{{[^}}]*?cols:\s*\[(.*?)\]", _blok(_baca(RUTE), "const CATALOG:"), re.S)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


class TestB1_JendelaTidakTerpotong(unittest.TestCase):
    """Laporan owner 22-Agu: *"window pop-up nya saja terpotong lebarnya."*
    Terukur: lebar 440px menampung form `voice` ber-15 isian dan baris JSON `default_params`
    yang panjang. Isi tak bisa dikerjakan kalau tak terbaca."""

    def test_jendela_katalog_cukup_lebar(self):
        layar = _baca(LAYAR)
        sempit = re.findall(r'width: "min\((\d{3})px,\s*\d+vw\)"', layar)
        self.assertTrue(sempit, "lebar jendela pop-up katalog tak ditemukan")
        kurang = [w for w in sempit if int(w) < 560]
        self.assertEqual(
            [], kurang,
            f"Jendela pop-up katalog masih {kurang} px. Form `voice` punya 15 isian dan form model "
            "memuat baris JSON panjang — di lebar itu isinya terpotong dan admin mengisi sambil menebak.")

    def test_masih_responsif_di_layar_kecil(self):
        """Melebarkan HARAM merusak layar sempit: `min(px, vw)` wajib dipertahankan."""
        layar = _baca(LAYAR)
        for m in re.finditer(r'width: "min\(\d{3}px,\s*(\d+)vw\)"', layar):
            self.assertLessEqual(int(m.group(1)), 95,
                                 "batas vw hilang/terlalu besar — jendela akan melewati tepi layar kecil")
        # Sabotase membuktikan versi pertama uji ini PALSU: mengubah satu `min(720px,92vw)` menjadi
        # `720px` mengurangi KEDUA hitungan sekaligus, jadi kesamaannya tetap terjaga. Yang dikunci
        # sekarang: NOL lebar telanjang — setiap lebar jendela wajib berpola `min(px, vw)`.
        telanjang = re.findall(r'width: "(\d+px)"', layar)
        self.assertEqual(
            [], telanjang,
            f"Lebar jendela {telanjang} ditulis telanjang tanpa `min(px, vw)` ⇒ jendela melewati "
            "tepi layar kecil dan tombol Simpan tak bisa dijangkau.")


class TestB2_ParameterModelBisaDIKERJAKAN(unittest.TestCase):
    """`default_params` menentukan gambar & video jadi atau tidak, dan dikirim APA ADANYA ke vendor
    (kunci ngawur = 400, dan penolakan parameter berkelas UNKNOWN = BOLEH DIULANG ⇒ kredit tenant
    terbakar — anatomi insiden `seed`, 37 kejadian). Terukur 22-Agu: isian ini **nol label manusiawi,
    nol arahan** — yang tampil hanya satu baris bahasa mesin."""

    def test_default_params_punya_label_dan_arahan(self):
        self.assertTrue(
            _meta_entri("models", "default_params"),
            "`default_params` tak punya label manusiawi — admin hanya melihat nama kolom database "
            "dan satu baris bahasa mesin.")
        self.assertTrue(
            _help("models", "default_params", "help_id"),
            "`default_params` tak punya ARAHAN. Ini isian paling menentukan di seluruh rantai; "
            "tanpa arahan admin mengisi sambil menebak, dan salah isi membakar kredit tenant.")
        self.assertTrue(_help("models", "default_params", "help_en"),
                        "arahan wajib dwibahasa ID/EN — layar admin dipakai dua bahasa")

    def test_arahan_menyebut_KETIGA_jenis_yang_beda_kebutuhannya(self):
        """Satu form melayani 4 jenis dengan kebutuhan berbeda; arahannya wajib menyebut yang mana."""
        # Diperiksa PER BAHASA: sabotase membuktikan bahwa menghapus contoh video dari `help_id`
        # tetap lolos selama `help_en` masih memuatnya — tenant/admin berbahasa Indonesia dirugikan.
        idn = _help("models", "default_params", "help_id").lower()
        eng = _help("models", "default_params", "help_en").lower()
        for wajib_id, wajib_en in (("gambar", "image"), ("video", "video"), ("naskah", "script")):
            self.assertIn(wajib_id, idn, f"arahan ID tak menyebut jenis `{wajib_id}`")
            self.assertIn(wajib_en, eng, f"arahan EN tak menyebut jenis `{wajib_en}`")
        for kunci in ("size", "aspect_ratio", "allowed_durations"):
            self.assertIn(kunci, idn, f"arahan ID tak menyebut parameter `{kunci}`")
            self.assertIn(kunci, eng, f"arahan EN tak menyebut parameter `{kunci}`")


class TestB3_ARAHAN_TidakBolongLagi(unittest.TestCase):
    """Terukur 22-Agu: form `voice` 7 isian tanpa label manusiawi + 4 tanpa arahan · `moods` 2 tanpa
    keduanya · `durations` 2 tanpa label + 3 tanpa arahan. Admin diminta mengisi tanpa dituntun."""

    def _fields(self, mk: str) -> list[str]:
        blok = _blok(_baca(LAYAR), "const ADD_FIELDS:")
        i = blok.find(f"{mk}: {{")
        j = blok.find("fields: [", i) + len("fields: [")
        out, d, buf, k = [], 0, "", j
        while k < len(blok):
            c = blok[k]
            if c == "[":
                d += 1
                if d == 1: buf = ""
            elif c == "]":
                if d == 1:
                    m = re.match(r'\s*"([a-z_]+)"', buf)
                    if m: out.append(m.group(1))
                d -= 1
                if d < 0: break
            elif d == 1:
                buf += c
            k += 1
        return out

    def _meta(self, mk: str) -> dict:
        return _meta_kolom(mk)

    def test_setiap_isian_form_punya_label_manusiawi(self):
        bolong = {}
        for mk in ("providers", "models", "voice", "ttsprof", "languages", "moods", "durations"):
            mt = self._meta(mk)
            kurang = [f for f in self._fields(mk) if f not in mt]
            if kurang: bolong[mk] = kurang
        self.assertEqual(
            {}, bolong,
            f"Isian ini hanya menampilkan nama kolom database, tanpa label manusiawi: {bolong}. "
            "Admin non-teknis diminta mengisi sesuatu yang tak dijelaskan.")

    def test_isian_yang_MEMBAKAR_kalau_salah_punya_arahan(self):
        """Tidak semua isian butuh arahan. Yang WAJIB: yang salah-isinya berakibat nyata."""
        wajib = {
            "voice":     ["provider_key", "preview_url", "gender", "display_name"],
            "durations": ["use_case", "use_case_en", "notes"],
            "moods":     ["mood_id", "keywords"],
            "ttsprof":   ["display_name", "param_schema"],
            "models":    ["provider_key"],
        }
        kurang = {}
        for mk, kols in wajib.items():
            mt = self._meta(mk)
            k = [c for c in kols if mt.get(c) is not True]
            if k: kurang[mk] = k
        self.assertEqual({}, kurang, f"isian ini berlabel tapi TANPA arahan: {kurang}")

    def test_KORIDOR_disebut_di_arahan_yang_sudah_ada(self):
        """Koridor §9.1: jenis `tts` masih butuh langkah 3 (setelan suara + karakter suara), jenis
        `video` masih butuh langkah 4 (preset durasi ai_video). Terukur: panel TIDAK menyebutnya
        sepatah pun ⇒ admin menyangka pekerjaannya selesai padahal model itu tak akan jalan."""
        idn = _help("models", "component", "help_id").lower()
        eng = _help("models", "component", "help_en").lower()
        self.assertTrue(idn and eng, "isian jenis model tak punya arahan dwibahasa")
        # Yang dikunci = NAMA TAB TUJUAN, bukan kata "suara"/"durasi" saja. Sabotase membuktikan
        # kenapa: arahan ini sudah memuat "tts = suara" di kalimat pertamanya, jadi menghapus
        # petunjuk langkah lanjutan tetap lolos. Arahan yang tak menyebut KE MANA harus pergi
        # bukan arahan yang menuntun.
        for teks, bhs in ((idn, "ID"), (eng, "EN")):
            self.assertTrue(
                re.search(r"tab voice|voice tab", teks),
                f"Arahan {bhs} pada isian JENIS tak menunjuk TAB VOICE. Jenis suara masih butuh "
                "setelan suara + minimal 1 karakter suara (langkah 3 koridor); tanpa petunjuk "
                "tempatnya, admin menyangka pekerjaannya selesai dan model itu tak akan berbunyi.")
            self.assertTrue(
                re.search(r"tab durasi|durasi tab", teks),
                f"Arahan {bhs} tak menunjuk TAB DURASI. Jenis video masih butuh preset durasi video "
                "yang aktif (langkah 4 koridor) — tanpa itu model video tak akan terpakai.")


class TestB4_IsianAdminBerhentiDibuang(unittest.TestCase):
    """Form mesin suara mengirim `adapter` & `display_name`; whitelist API tak memuatnya ⇒ nilainya
    hilang sebelum menyentuh DB, dan admin tetap melihat toast "Tersimpan". Efek ikutan:
    `ENUM_COLS.tts_profiles.adapter` = KODE MATI (menjaga kolom yang tak pernah sampai)."""

    def test_dua_kolom_itu_boleh_ditulis(self):
        cols = _kolom_whitelist("tts_profiles")
        for k in ("adapter", "display_name"):
            self.assertIn(k, cols,
                          f"`{k}` masih dibuang sebelum menyentuh DB, sementara layar bilang "
                          "'Tersimpan'. Inilah sebab protokol yang diketik admin hilang.")

    def test_penjaga_salah_ketik_jadi_HIDUP(self):
        rute = _baca(RUTE)
        self.assertIn("tts_profiles:      { adapter:", rute.replace("tts_profiles: {", "tts_profiles:      {"),
                      "validasi enum adapter mesin suara hilang")
        self.assertIn("adapter", _kolom_whitelist("tts_profiles"),
                      "validasi enum ada tapi kolomnya tak pernah lolos whitelist ⇒ KODE MATI, "
                      "dan typo protokol tak pernah tertangkap")

    def test_PARITAS_form_vs_whitelist_untuk_SELURUH_tabel(self):
        """Penjaga KELAS: kelas buang-senyap ini HARAM terulang di tabel lain. Nol uji pernah
        menjaganya — itu sebabnya cacatnya hidup berbulan-bulan."""
        layar = _baca(LAYAR)
        addf = _blok(layar, "const ADD_FIELDS:")
        pkline = layar[layar.find("const PK_OF:"):]
        pkline = pkline[:pkline.find("\n")]
        buang = []
        for mk in re.findall(r"^  ([a-z_]+):\s*\{\s*table:", addf, re.M):
            tabel = re.search(rf"{mk}:\s*\{{\s*table:\s*\"([a-z_]+)\"", addf).group(1)
            wl = _kolom_whitelist(tabel)
            pk = (re.search(rf"\b{mk}:\s*\"([a-z_]+)\"", pkline) or [None, ""])[1]
            self.assertTrue(pk, f"PK `{mk}` tak terurai — uji ini mustahil sah tanpa itu")
            i = addf.find(f"{mk}: {{")
            j = addf.find("fields: [", i) + len("fields: [")
            out, d, buf, k = [], 0, "", j
            while k < len(addf):
                c = addf[k]
                if c == "[":
                    d += 1
                    if d == 1: buf = ""
                elif c == "]":
                    if d == 1:
                        m = re.match(r'\s*"([a-z_]+)"', buf)
                        if m: out.append(m.group(1))
                    d -= 1
                    if d < 0: break
                elif d == 1:
                    buf += c
                k += 1
            buang += [f"{mk}/{tabel}.{f}" for f in out if f != pk and f not in wl]
        self.assertEqual([], buang, f"DIKIRIM form tapi DIBUANG API (toast tetap 'Tersimpan'): {buang}")


class TestB5_JejakKarantinaPunyaJalurBUKA(unittest.TestCase):
    """Migr 0205 menulis sendiri: *"Ditulis mesin; dibersihkan admin saat menghidupkan kembali."*
    Terukur 22-Agu: panel TIDAK bisa menyentuh kedua kolom itu (nol di whitelist, nol di form) ⇒
    jejak melekat selamanya. Itu melanggar mandat "setiap kunci punya jalur buka" (PAYMENT §10e-2),
    dan itu HUTANG sesi 21-Agu — bukan fitur baru."""

    def test_menyalakan_kembali_MEMBERSIHKAN_jejaknya(self):
        rute = _baca(RUTE)
        i = rute.find("export async function PATCH")
        self.assertGreater(i, 0)
        blok = rute[i:rute.find("export async function", i + 10)]
        self.assertIn(
            "unavailable_since", blok,
            "Menyalakan kembali model tak membersihkan jejak karantina ⇒ model hidup tapi tetap "
            "bertanda 'mati di vendor'. Admin tak punya jalur membersihkannya dari panel.")
        self.assertIn("unavailable_reason", blok, "alasan karantina tak ikut dibersihkan")

    def test_HANYA_saat_dinyalakan_bukan_saat_dimatikan(self):
        """Karantina MENULIS jejak saat mematikan. Membersihkannya di jalur yang salah = menghapus
        bukti yang baru saja ditulis mesin."""
        rute = _baca(RUTE)
        i = rute.find("unavailable_since")
        self.assertGreater(i, 0)
        blok = rute[max(0, i - 700):i + 300]
        self.assertTrue(
            re.search(r"is_active\s*===\s*true", blok),
            "Pembersihan jejak tak bersyarat pada `is_active === true` ⇒ ikut jalan saat MEMATIKAN, "
            "dan menghapus jejak yang baru ditulis karantina.")

    def test_admin_tak_bisa_menulis_jejak_itu_sendiri(self):
        """Jejak = tulisan MESIN (bukti). Admin hanya boleh MEMBERSIHKAN lewat penyalaan, tidak
        mengarang isinya — kalau tidak, buktinya tak bisa dipercaya."""
        for k in ("unavailable_since", "unavailable_reason"):
            self.assertNotIn(k, _kolom_whitelist("ai_models"),
                             f"`{k}` masuk whitelist ⇒ admin bisa MENGARANG jejak karantina")


class TestB6_BarisSetelanSuaraLahirDariLangkahYangSUDAHADA(unittest.TestCase):
    """`tts_profiles` = satu-satunya tabel yang boleh DIHAPUS panel tapi tak bisa DIBUAT darinya.
    Itu sebab mesin suara Gemini lahir dari SKRIP, bukan dari layar owner.

    Rancangan 21-Agu (tombol Tambah baru di tab Voice) DITOLAK owner: *"anda membuat jalur baru."*
    Rancangan sekarang: barisnya lahir dari langkah yang admin SUDAH lakukan — membuat model
    ber-`component='tts'` (langkah 2 koridor). NOL tombol, NOL tab, NOL berkas layar tersentuh;
    melengkapinya memakai editor ✎ yang SUDAH ADA di tabel setelan suara."""

    def test_membuat_model_tts_menyiapkan_barisnya(self):
        rute = _baca(RUTE)
        i = rute.find("export async function POST")
        self.assertGreater(i, 0)
        blok = rute[i:rute.find("export async function", i + 10)]
        self.assertIn(
            "tts_profiles", blok,
            "Membuat model suara tidak menyiapkan baris setelan suaranya ⇒ barisnya tetap mustahil "
            "lahir dari panel, dan penyedia suara baru tetap butuh perintah database.")
        self.assertTrue(
            re.search(r'component.*===\s*"tts"|"tts"\s*===.*component', blok),
            "Penyiapan baris tak bersyarat pada jenis `tts` ⇒ model naskah/gambar/video pun ikut "
            "membuat baris setelan suara yang tak ada gunanya.")

    def _blok_penyiapan(self) -> str:
        """Potong CABANG penyiapan itu sendiri, bukan jendela karakter di sekitar kata.

        Versi pertama uji ini memakai jendela ±700 karakter dari kemunculan kata `tts_profiles`
        pertama — dan kemunculan pertama itu ada di KOMENTAR, sehingga jendelanya tak pernah
        mencapai kodenya. Cacat yang sama sudah tertangkap dua kali sebelumnya; jangkar sekarang
        adalah syarat cabangnya."""
        rute = _baca(RUTE)
        i = rute.find('if (table === "ai_models" && String(clean.component')
        self.assertGreater(i, 0, "cabang penyiapan baris setelan suara tak ditemukan")
        return rute[i:rute.find("\n  return NextResponse.json({ ok: true, row: data });", i)]

    def test_lahir_NONAKTIF_dan_tak_menimpa_yang_sudah_ada(self):
        blok = self._blok_penyiapan()
        self.assertTrue(
            re.search(r"is_active:\s*false", blok),
            "Baris setelan suara lahir AKTIF ⇒ penyedia setengah-jadi langsung terpapar pemilih tenant.")
        self.assertTrue(
            re.search(r"maybeSingle|ignoreDuplicates|onConflict", blok),
            "Penyiapan baris tidak memeriksa keberadaannya lebih dulu ⇒ berisiko MENIMPA setelan "
            "suara yang sudah dipakai produksi (tempo, kelas timing, batas huruf).")
        self.assertTrue(
            re.search(r"if\s*\(\s*pk\s*&&\s*!\s*sudahAda\s*\)", blok),
            "Penyisipan tidak dijaga oleh 'belum ada' ⇒ baris yang sudah dipakai bisa tertimpa.")

    def test_protokol_TIDAK_ditebak_sistem(self):
        """Protokol menentukan cara mesin bicara ke vendor. Menebaknya = menanam kegagalan yang
        baru terlihat saat produksi. Ia wajib dibiarkan kosong agar admin mengisinya sadar."""
        blok = self._blok_penyiapan()
        self.assertTrue(
            re.search(r"adapter:\s*null", blok),
            "Sistem MENEBAK protokol mesin suara. Protokol yang salah gagal saat produksi, bukan "
            "saat disimpan — biarkan kosong dan biarkan admin mengisinya lewat editor yang ada.")

    def test_gagal_menyiapkan_HARAM_menggagalkan_pembuatan_model(self):
        """Menyiapkan baris pendamping adalah kemudahan, bukan jalur kerja. Kegagalannya haram
        membatalkan pekerjaan admin yang sudah benar."""
        blok = self._blok_penyiapan()
        # `"catch" in blok` LOLOS dari sabotase yang memakai nama lain berisi kata itu — sabotase
        # 22-Agu membuktikannya. Yang dikunci: penutup `} catch (…) {` yang sungguhan.
        self.assertTrue(re.search(r"try\s*\{", blok), "penyiapan tidak dibungkus try ⇒ tidak fail-soft")
        self.assertTrue(
            re.search(r"\}\s*catch\s*\([^)]*\)\s*\{", blok),
            "Penyiapan baris setelan suara tidak fail-soft ⇒ satu galat kecil membatalkan pembuatan "
            "model yang sudah benar.")
        i = blok.find("catch")
        self.assertNotIn(
            "return NextResponse", blok[i:i + 300],
            "Cabang gagal MENGEMBALIKAN galat ⇒ pembuatan model yang sudah berhasil dilaporkan gagal.")


if __name__ == "__main__":
    unittest.main()
