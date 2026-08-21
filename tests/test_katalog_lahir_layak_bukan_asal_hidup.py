"""KATALOG: yang diketik admin WAJIB tersimpan · baris baru lahir NONAKTIF · aktivasi yang
syaratnya belum lengkap DITOLAK ber-alasan · panel bisa membuat MESIN SUARA baru.

Batch C dari rencana yang diketok owner 21-Agu (langkah 6c). Empat cacat yang dijaga di sini,
semuanya bisa ditunjuk barisnya — bukan perasaan:

═══ CACAT 1 — yang diketik admin DIBUANG SENYAP ═══
Form `ttsprof` mengirim `adapter` & `display_name` (`catalog/page.tsx` ADD_FIELDS), tapi whitelist
API `CATALOG.tts_profiles.cols` TIDAK memuatnya ⇒ loop tulis hanya mengiterasi `def.cols`, jadi
nilainya hilang sebelum menyentuh DB. Admin melihat toast **"Tersimpan"**. Validasi enum
`ENUM_COLS.tts_profiles.adapter` yang sudah ada pun jadi **kode mati** — ia menjaga kolom yang
tak pernah sampai.

═══ CACAT 2 — MESIN SUARA baru mustahil dibuat dari panel ═══
`tts_profiles` = SATU-SATUNYA tabel yang ada di `DELETABLE` tapi tak punya tombol Tambah
(terukur: DELETABLE − tabel ber-tab = {tts_profiles}). Panel bisa MENGHAPUS yang tak bisa ia BUAT.
Akibat nyata & diakui: mesin suara Gemini lahir dari SKRIP, bukan dari panel owner.

═══ CACAT 3 — baris baru HIDUP sebelum diuji ═══
POST hanya menulis kolom form; `is_active` mengikuti bawaan DB — dan bawaan itu `true`
(terukur: `0014_tts_profiles.sql:13`, `0038_voice_catalog.sql:12`). ⇒ penyedia/model setengah-jadi
langsung terpapar tenant. Bawaan `ai_models`/`ai_providers` tak bisa diintrospeksi lewat klien,
karena itu `is_active` ditulis EKSPLISIT — bawaan DB dibuat tak relevan, bukan diasumsikan.

═══ CACAT 4 — menyalakan baris yang syaratnya belum lengkap tak ditahan apa pun ═══
Owner memilih: **mematikan tetap bebas** (Batch B), **menghidupkan** yang diperketat.
Terukur sebelum dibangun: **NOL** dari 41 model aktif + 5 mesin suara aktif melanggar gerbang ini
⇒ memasangnya tak memblokir satu pun baris yang sekarang hidup (bukan kerusakan kelas 17-Agu).

Hermetik: nol jaringan.
"""
import io
import os
import re
import sys
import unittest

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AKAR)

RUTE = "apps/web/src/app/api/admin/catalog/route.ts"
LAYAR = "apps/web/src/app/admin/(panel)/catalog/page.tsx"


def _baca(rel: str) -> str:
    return io.open(os.path.join(AKAR, rel), encoding="utf-8").read()


def _tanpa_komentar_sql(rel: str) -> str:
    """SQL TANPA baris komentar. Sabotase membuktikan komentar menyelamatkan uji palsu — DUA kali:
    mengganti syarat transisi jadi `if false then` tetap HIJAU, karena komentar di atas trigger
    MENGUTIP syarat itu apa adanya untuk menjelaskannya. Yang dikunci wajib KODE."""
    return "\n".join(l for l in _baca(rel).splitlines() if not l.lstrip().startswith("--"))


def _blok(src: str, awal: str) -> str:
    """Potong satu deklarasi `const X ... };` — dipakai mengurai peta TS tanpa menjalankan TS."""
    i = src.find(awal)
    assert i > 0, f"blok `{awal}` tak ditemukan"
    return src[i:src.find("\n};", i) + 3]


def _kolom_whitelist(tabel: str) -> list[str]:
    """`CATALOG.<tabel>.cols` dari rute API."""
    blok = _blok(_baca(RUTE), "const CATALOG:")
    m = re.search(rf"\b{tabel}:\s*\{{[^}}]*?cols:\s*\[(.*?)\]", blok, re.S)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def _field_form(mapkey: str) -> list[str]:
    """Kolom yang benar-benar DIKIRIM form `ADD_FIELDS.<mapkey>`.

    Diurai dengan penghitung KEDALAMAN, bukan regex datar. Sebabnya terukur: label sebuah field
    boleh memuat contoh JSON — `keywords` labelnya memuat `["misterius","mysterious"]` — dan regex
    datar membaca `misterius` sebagai NAMA KOLOM, lalu melaporkan cacat yang tidak ada."""
    blok = _blok(_baca(LAYAR), "const ADD_FIELDS:")
    i = blok.find(f"{mapkey}: {{")
    assert i > 0, f"ADD_FIELDS.{mapkey} tak ditemukan"
    j = blok.find("fields: [", i) + len("fields: [")
    out, dalam, buf = [], 0, ""
    k = j
    while k < len(blok):
        c = blok[k]
        if c == "[":
            dalam += 1
            if dalam == 1: buf = ""
        elif c == "]":
            if dalam == 1:
                m = re.match(r'\s*"([a-z_]+)"', buf)     # elemen PERTAMA tuple = nama kolom
                if m: out.append(m.group(1))
            dalam -= 1
            if dalam < 0: break                          # penutup `fields: [` → selesai
        elif dalam == 1:
            buf += c
        k += 1
    assert out, f"fields ADD_FIELDS.{mapkey} gagal diurai"
    return out


def _tabel_dari_mapkey(mapkey: str) -> str:
    blok = _blok(_baca(LAYAR), "const ADD_FIELDS:")
    m = re.search(rf"{mapkey}:\s*\{{\s*table:\s*\"([a-z_]+)\"", blok)
    assert m, f"tabel untuk `{mapkey}` tak ditemukan"
    return m.group(1)


def _pk_dari_mapkey(mapkey: str) -> str:
    """`PK_OF` dideklarasikan SATU baris, jadi ia tak bisa dipotong `_blok` (yang mencari `\n};`).
    Diambil langsung dari deklarasinya — gagal mengurai PK membuat setiap PK terbaca sebagai
    'kolom yang dibuang', yakni tujuh cacat palsu sekaligus."""
    layar = _baca(LAYAR)
    i = layar.find("const PK_OF:")
    assert i > 0, "PK_OF tak ditemukan"
    m = re.search(rf"\b{mapkey}:\s*\"([a-z_]+)\"", layar[i:layar.find("\n", i)])
    return m.group(1) if m else ""


class TestA_YangDiketikAdminBenarBenarTersimpan(unittest.TestCase):
    """Toast 'Tersimpan' yang berbohong = kelas cacat paling mahal: admin percaya, mesin tidak tahu."""

    def test_tts_profiles_menerima_adapter_dan_nama(self):
        cols = _kolom_whitelist("tts_profiles")
        for k in ("adapter", "display_name"):
            self.assertIn(
                k, cols,
                f"Form mesin suara mengirim `{k}`, tapi whitelist API membuangnya sebelum menyentuh "
                "DB — dan admin tetap melihat 'Tersimpan'. Inilah sebab protokol yang diketik hilang.")

    def test_validasi_enum_adapter_BUKAN_kode_mati(self):
        """`ENUM_COLS.tts_profiles.adapter` sudah ada sejak lama, tapi menjaga kolom yang tak pernah
        sampai. Penjaga yang menjaga pintu yang tak dilewati siapa pun = penjaga yang tidur."""
        src = _baca(RUTE)
        self.assertIn("tts_profiles:      { adapter:", src.replace("tts_profiles: {", "tts_profiles:      {"),
                      "validasi enum adapter mesin suara hilang")
        self.assertIn("adapter", _kolom_whitelist("tts_profiles"),
                      "Validasi enum `adapter` ada, tapi kolomnya tak pernah lolos whitelist ⇒ "
                      "validasinya KODE MATI, dan typo protokol tak pernah tertangkap.")

    def test_PARITAS_setiap_field_form_ada_di_whitelist(self):
        """Penjaga KELAS, bukan penjaga satu kolom: kelas buang-senyap ini HARAM terulang untuk
        tabel lain. Nol uji pernah menjaga paritas ini — itu sebabnya cacatnya hidup berbulan."""
        blok = _blok(_baca(LAYAR), "const ADD_FIELDS:")
        mapkeys = re.findall(r"^  ([a-z_]+):\s*\{\s*table:", blok, re.M)
        self.assertGreaterEqual(len(mapkeys), 6, "peta ADD_FIELDS gagal diurai")
        buang = []
        for mk in mapkeys:
            tabel = _tabel_dari_mapkey(mk)
            wl = _kolom_whitelist(tabel)
            pkcol = _pk_dari_mapkey(mk)
            self.assertTrue(pkcol, f"PK untuk `{mk}` tak terurai — uji ini mustahil sah tanpa itu")
            for f in _field_form(mk):
                if f != pkcol and f not in wl:
                    buang.append(f"{mk}/{tabel}.{f}")
        self.assertEqual(
            [], buang,
            "Kolom ini DIKIRIM form tapi TIDAK ADA di whitelist API ⇒ dibuang senyap, dan admin "
            f"tetap melihat 'Tersimpan': {buang}")


class TestB_BarisBaruLahirNONAKTIF(unittest.TestCase):
    """Bawaan DB `is_active` = true (terukur: 0014:13, 0038:12). Model setengah-jadi HARAM
    langsung terpapar tenant hanya karena admin belum sempat mengujinya."""

    def test_POST_menulis_is_active_false_EKSPLISIT(self):
        src = _baca(RUTE)
        i = src.find("export async function POST")
        self.assertGreater(i, 0)
        blok = src[i:src.find("export async function", i + 10)]
        self.assertTrue(
            re.search(r'is_active"?\]?\s*[:=]\s*false', blok),
            "POST tak menyetel `is_active` ⇒ baris baru mengikuti bawaan DB yang `true`. Penyedia "
            "yang belum diuji langsung ditawarkan ke tenant — persis cara model mati bisa lahir.")

    def test_admin_tetap_bisa_menyalakannya_sesudah_diuji(self):
        """Lahir nonaktif HARAM jadi 'kunci tanpa jalur buka' (owner, PAYMENT §10e-2).

        Versi pertama uji ini LOLOS-LEMAH: ia hanya menuntut kata `is_active` muncul di blok PATCH —
        dan kata itu tetap ada selama SATU tabel mana pun memilikinya. Sabotase membuktikannya:
        mencabut `is_active` dari whitelist `ai_models` tetap hijau, padahal setiap model yang
        lahir nonaktif jadi terkunci SELAMANYA. Dikunci per-tabel sekarang."""
        for tabel in ("ai_models", "ai_providers", "tts_profiles", "voice_catalog"):
            self.assertIn(
                "is_active", _kolom_whitelist(tabel),
                f"`{tabel}` tak punya `is_active` di whitelist ⇒ barisnya lahir nonaktif dan tak "
                "pernah bisa dinyalakan lagi dari panel. Setiap kunci wajib punya jalur buka.")


class TestC_MesinSuaraBaruBisaDibuatDariLAYAR(unittest.TestCase):
    """Panel yang bisa MENGHAPUS tapi tak bisa MEMBUAT = panel yang memaksa owner menunggu saya."""

    def test_tak_ada_tabel_yang_bisa_dihapus_tapi_tak_bisa_dibuat(self):
        """Yang dikunci: setiap tabel yang bisa DIHAPUS dari panel wajib punya jalur MEMBUAT dari
        panel. Jalurnya ada dua bentuk yang dua-duanya sah, dan versi pertama uji ini hanya
        mengenali satu — lalu menuduh `fonts` & `music_library` timpang padahal tidak:

          · form ketikan     → `bukaTambah("<mapKey>")`
          · pengunggah berkas → `setFUp` / `setMUp`  (nama & berkasnya LAHIR dari berkas yang
            diunggah, bukan diketik — memang begitu rancangannya, lihat komentar `CATALOG.fonts`)

        Yang tetap dilarang: tabel yang bisa dihapus tapi tak punya jalur membuat SAMA SEKALI.
        Terukur saat Batch C dimulai: `tts_profiles` adalah satu-satunya yang begitu, dan itulah
        sebabnya mesin suara Gemini lahir dari skrip, bukan dari layar owner."""
        rute, layar = _baca(RUTE), _baca(LAYAR)
        m = re.search(r"const DELETABLE = new Set\(\[(.*?)\]\)", rute, re.S)
        self.assertTrue(m, "DELETABLE tak ditemukan")
        deletable = set(re.findall(r'"([a-z_]+)"', m.group(1)))

        bisa_dibuat = set()
        blok = _blok(layar, "const ADD_FIELDS:")
        for mk in re.findall(r"^  ([a-z_]+):\s*\{\s*table:", blok, re.M):
            if re.search(rf'bukaTambah\(\s*"{mk}"', layar):        # form ketikan
                bisa_dibuat.add(_tabel_dari_mapkey(mk))
        if re.search(r"setFUp\(\{", layar):  bisa_dibuat.add("fonts")           # pengunggah berkas
        if re.search(r"setMUp\(\{", layar):  bisa_dibuat.add("music_library")

        timpang = sorted(deletable - bisa_dibuat)
        self.assertEqual(
            [], timpang,
            f"Tabel ini bisa DIHAPUS dari panel tapi tak bisa DIBUAT dari panel: {timpang}. "
            "Panel yang bisa menghapus apa yang tak bisa ia buat memaksa owner menunggu saya, "
            "dan itulah cara mesin suara Gemini lahir dari skrip.")

    def test_tombol_tambah_TIDAK_menebak_dari_tab_aktif(self):
        """`createRow` dulu memakai `ADD_FIELDS[tab]`. Tabel mesin suara tinggal di DALAM tab
        Voice (hierarki engine → voice), jadi menebak dari tab akan mengirim baris mesin suara
        ke tabel `voice_catalog` — kerusakan senyap, bukan galat."""
        layar = _baca(LAYAR)
        i = layar.find("async function createRow")
        self.assertGreater(i, 0)
        blok = layar[i:i + 700]
        self.assertNotIn(
            "ADD_FIELDS[tab]", blok,
            "Tombol Tambah menebak tabel dari TAB yang sedang terbuka. Satu tab memuat DUA tabel "
            "(voice + mesin suara) ⇒ baris bisa masuk ke tabel yang salah tanpa satu galat pun.")
        self.assertTrue(
            re.search(r"ADD_FIELDS\[\s*add\.mapKey\s*\]", blok),
            "Tambah wajib membawa sasarannya sendiri (`add.mapKey`), sepola dengan editor baris "
            "yang sudah ada (`rowEdit.mapKey`) — satu pola, bukan dua.")

    def test_memakai_pustaka_komponen_yang_ADA(self):
        """Aturan owner: pakai pustaka yang ada, jangan bikin komponen baru.
        Dua lapis yang SUDAH menjaga ini dan tak dilapisi ulang di sini: berkas komponen baru
        diblokir gerbang mesin (`test_gerbang_tetap_terpasang.py`), dan konfirmasi dampak wajib
        `ConfirmDialog` (`test_kegagalan_kita_tak_menuduh_tenant.py`). Yang tinggal, dan hanya
        milik Batch C: kalimat kelayakan wajib DWIBAHASA lewat komponen `Bi` yang sudah ada —
        teks satu bahasa di layar admin sudah pernah jadi temuan sendiri."""
        layar = _baca(LAYAR)
        i = layar.find("const KURANG_TEKS")
        self.assertGreater(i, 0, "peta kalimat kelayakan tak ada — kode mentah akan tampil ke admin")
        peta = layar[i:layar.find("};", i)]
        self.assertGreaterEqual(
            len(re.findall(r'\{\s*id:\s*"', peta)), 10,
            "peta kalimat kelayakan terlalu tipis — sebagian kode akan tampil mentah ke admin")
        self.assertEqual(
            len(re.findall(r'\bid:\s*"', peta)), len(re.findall(r'\ben:\s*"', peta)),
            "ada kalimat kelayakan yang hanya SATU bahasa — layar admin wajib dwibahasa ID/EN.")
        blok = layar[layar.find('case "activation_blocked"'):][:900]
        self.assertIn("<Bi ", blok,
                      "penolakan aktivasi dirender tanpa komponen dwibahasa `Bi` milik pustaka")


class TestD_AktivasiYangSyaratnyaBelumLengkapDITOLAK(unittest.TestCase):
    """Owner: 'sistem harus mencegah admin membuat kesalahan yang berdampak ke tenant.'
    Terukur sebelum dibangun: NOL baris aktif hari ini melanggar ⇒ nol yang terkunci."""

    MIGR = "migrations/0206_gerbang_kelayakan_katalog.sql"

    def test_migrasinya_ada(self):
        self.assertTrue(os.path.exists(os.path.join(AKAR, self.MIGR)),
                        "gerbang kelayakan belum dibangun — model setengah-jadi tetap bisa dinyalakan")

    def test_fungsi_pemeriksa_sepola_channel_missing(self):
        """Pola yang sudah terbukti: fungsi mengembalikan DAFTAR KODE, bukan kalimat satu bahasa.
        Kalimatnya milik FE (aturan dwibahasa: API kirim kode, FE menerjemahkan)."""
        src = _baca(self.MIGR)
        self.assertIn("catalog_missing", src, "fungsi pemeriksa kelayakan tak ada")
        self.assertTrue(re.search(r"returns\s+text\[\]", src, re.I),
                        "pemeriksa wajib mengembalikan DAFTAR KODE (text[]) sepola `channel_missing` — "
                        "bukan satu kalimat, supaya layar bisa menerjemahkannya dwibahasa")

    def test_HANYA_saat_transisi_menjadi_aktif(self):
        """Baris LAMA yang sudah aktif HARAM tersentuh (jawaban untuk baris lama, §3). Trigger yang
        menyala pada tiap UPDATE akan mengunci baris yang hari ini sehat = kerusakan 17-Agu ulang.
        Komentar dibuang dulu: komentar penjelas MENGUTIP syarat ini, dan kutipan itu sudah
        terbukti menyelamatkan uji palsu."""
        src = _tanpa_komentar_sql(self.MIGR)
        self.assertTrue(
            re.search(r"old\.is_active\s+is\s+distinct\s+from\s+new\.is_active|not\s+coalesce\(old\.is_active", src, re.I),
            "Gerbang tidak dibatasi pada TRANSISI ke aktif ⇒ menyunting harga sebuah model aktif "
            "bisa ikut ditolak, dan baris yang hari ini sehat jadi terkunci.")
        self.assertTrue(re.search(r"new\.is_active", src),
                        "gerbang tak memeriksa keadaan BARU — mustahil membedakan nyala dari mati")

    def test_MEMATIKAN_tetap_bebas(self):
        """Batch B: kalau vendor mematikan model, admin WAJIB tetap bisa mematikannya.
        Komentar dibuang dulu (lihat uji di atas — kutipan di komentar menyelamatkan uji palsu)."""
        src = _tanpa_komentar_sql(self.MIGR)
        i = src.lower().find("new.is_active")
        blok = src[max(0, i - 400):i + 400]
        # Terima kedua bentuk yang sah: `new.is_active = true` maupun yang dibungkus
        # `coalesce(new.is_active, false) = true` (NULL-safe — bentuk yang dipakai kode ini).
        self.assertTrue(
            re.search(r"(coalesce\(\s*)?new\.is_active\s*(,\s*false\s*\))?\s*(=|is)\s*true", blok, re.I),
            "Gerbang tidak bersyarat pada `new.is_active = true` ⇒ MEMATIKAN baris pun bisa "
            "tertahan. Itu 'kunci tanpa jalur buka' yang sudah ditegur owner (PAYMENT §10e-2).")

    def test_rute_menerjemahkan_penolakan_jadi_KODE(self):
        src = _baca(RUTE)
        self.assertIn(
            "activation_blocked", src,
            "Penolakan gerbang tak diterjemahkan jadi kode ⇒ admin melihat pesan mentah Postgres, "
            "dan aturan dwibahasa (API kirim kode, FE menerjemahkan) dilanggar.")

    def test_layar_menyebut_APA_yang_kurang_sebelum_diklik(self):
        """World-class = MENCEGAH kesalahan, bukan cuma menolaknya sesudah admin menekan."""
        layar = _baca(LAYAR)
        self.assertIn(
            "activation_blocked", layar,
            "Layar tak menerjemahkan penolakan aktivasi ⇒ admin hanya melihat 'Gagal' tanpa tahu "
            "apa yang harus dilengkapi.")
        self.assertTrue(
            re.search(r"belum layak|belum lengkap", layar, re.I),
            "Layar tak pernah menyebut ketidaklayakan SEBELUM saklar diklik — admin dibiarkan "
            "menabrak dinding, padahal syaratnya sudah bisa dihitung lebih dulu.")


class TestE_CerminRegistryGalatHidup(unittest.TestCase):
    """Syarat termahal di gerbang ini — penyedia tanpa baris `galat_registry.PENYEDIA` ⇒ galat
    vendor jatuh ke UNKNOWN = BOLEH DIULANG ⇒ kunci salah/saldo habis diulang 3× dan membakar
    kredit TENANT — hidup di KODE Python, sementara gerbangnya hidup di DB. Keduanya hanya bisa
    bertemu lewat cermin `catalog_valid_values`. Cermin mati = gerbang BUTA pada syarat itu,
    dan kebutaannya tak akan terlihat: gerbang tetap hijau, hanya berhenti memeriksa."""

    def test_registry_galat_ikut_dicerminkan_ke_DB(self):
        src = _baca("src/config/catalog_sync.py")
        self.assertIn(
            "galat_registry_provider", src,
            "Registry galat tak dicerminkan ke DB ⇒ gerbang kelayakan mustahil memeriksanya, dan "
            "penyedia tanpa baris registry tetap bisa dinyalakan — kredit tenant yang terbakar.")
        self.assertIn(
            "galat_registry", src,
            "cermin diisi bukan dari `galat_registry` — nilainya akan drift dari kebenaran di kode")

    def test_yang_dicerminkan_BENAR_benar_dari_registry_hidup(self):
        """Bukan tebakan: bandingkan hasil pengumpul dengan registry yang sesungguhnya."""
        from src.config.catalog_sync import collect_valid_values
        from src.providers import galat_registry as reg
        nilai = {r["value"] for r in collect_valid_values() if r["field"] == "galat_registry_provider"}
        self.assertEqual(
            nilai, set(reg.PENYEDIA.keys()),
            "Isi cermin ≠ isi registry. Gerbang akan menolak penyedia yang sebenarnya terdaftar, "
            "atau meloloskan yang tidak — dua-duanya lebih buruk daripada tak ada gerbang.")

    def test_gerbang_MEMBACA_cermin_itu(self):
        src = _tanpa_komentar_sql("migrations/0206_gerbang_kelayakan_katalog.sql")
        self.assertIn(
            "galat_registry_provider", src,
            "Cermin diisi tapi gerbang tak pernah membacanya — pekerjaan yang tak dipakai siapa pun.")


if __name__ == "__main__":
    unittest.main()
