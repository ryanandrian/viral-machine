"""Hak hapus data (UU PDP): TIAP tabel ber-`tenant_id` wajib punya keputusan sadar.

MASALAH YANG DIJAGA (temuan audit 2026-08-04)
`_PURGE_TABLES` di `src/billing/renewal.py` menentukan data apa yang dihapus ketika tenant memakai hak
hapus datanya. Daftar itu dibekukan **3-Jul** (spec `LIFECYCLE_NURTURE_ARCHITECTURE.md` §98). Sesudahnya
**4 tabel ber-`tenant_id` lahir** — `commission_ledger`, `tenant_attribution` (program agen [B21]),
`channel_decisions` ([B17] kecerdasan), `video_retention_curves` (retensi) — dan tak seorang pun
memperbarui daftarnya. Kodenya PATUH pada spec; spec-nya yang tertinggal.

Bahayanya bukan kerapian: data pribadi tenant BERTAHAN setelah ia minta dihapus, dan celah itu **tumbuh
sendiri** setiap kali tabel ber-`tenant_id` baru ditambah. Tanpa penjaga, tabel ke-25 akan lolos sama
diam-diamnya — dan tak ada yang tahu sampai ada yang menuntut.

Uji ini memaksa keputusan SADAR: tiap tabel ber-`tenant_id` harus masuk salah satu dari
  • `_PURGE_TABLES`         → dihapus
  • `_KEEP_TABLES`          → disimpan, DENGAN alasan tertulis
  • `_PENDING_OWNER_TABLES` → menunggu keputusan owner, DENGAN pertanyaannya tertulis
Tabel yang tak masuk mana pun = MERAH. "Lupa" tidak lagi menjadi pilihan yang mungkin.

CATATAN LINGKUP: uji ini OFFLINE (memindai `migrations/*.sql`) supaya deterministik dan tak menyentuh
produksi. Ia menjaga KELENGKAPAN KATEGORI, bukan kebenaran keputusannya — nasib 4 tabel `_PENDING`
adalah keputusan owner (menghapus data = irreversible, CLAUDE.md §2.3d), bukan keputusan uji ini.
"""
import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.billing.renewal import (  # noqa: E402
    _KEEP_TABLES, _PENDING_OWNER_TABLES, _PURGE_TABLES,
)

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Tabel yang memang TIDAK per-tenant walau namanya mengandung "tenant" / punya kolom mirip.
# Diverifikasi ke DB live 2026-08-04: kolom `tenant_id` TIDAK ADA (tabel sudah di-drop).
SUDAH_DIDROP = {"tenant_credentials", "channel_credentials", "tenant_api_accounts",
                "channel_analytics", "demo_tours", "niche_releases"}

# BASELINE TERUKUR KE DB LIVE 2026-08-04 — 24 tabel yang PUNYA kolom `tenant_id` (diperiksa satu per satu
# lewat `select tenant_id limit 1`, read-only).
#
# Kenapa di-hardcode padahal ada pemindai: pemindai migrasi hanya menemukan **15** dari 24. Sembilan
# sisanya (channels, videos, production_runs, dst.) lahir SEBELUM folder `migrations/` ini ada, jadi tak
# ada `CREATE TABLE`-nya untuk dipindai. Mengandalkan pemindai saja = pagar berlubang tepat di tabel-tabel
# paling besar; dan pagar berlubang lebih berbahaya daripada tanpa pagar karena ia memberi rasa aman.
# Union keduanya = jaring rangkap: tabel LAMA dijaga baseline, tabel BARU dijaga pemindai.
BASELINE_LIVE_2026_08_04 = {
    "channel_decisions", "channel_insights", "channels", "commission_ledger", "content_inventory",
    "direct_jobs", "email_outbox", "feedback_submissions", "music_library", "niche_requests",
    "payments", "pipeline_queue", "pipeline_run_logs", "production_runs", "support_tickets",
    "tenant_ai_accounts", "tenant_attribution", "tenant_configs", "tenant_youtube_accounts",
    "tts_delivery_samples", "video_analytics", "video_retention_curves", "videos", "voice_catalog",
}


def _tabel_ber_tenant_id() -> set[str]:
    """Pindai migrasi: tabel yang punya kolom `tenant_id`, baik dari CREATE maupun ALTER ADD.

    Dua bentuk WAJIB ditangkap — beberapa tabel lahir tanpa `tenant_id` lalu mendapatkannya lewat
    ALTER di migrasi berikutnya. Menangkap hanya CREATE akan melewatkannya, dan uji yang melewatkan
    justru lebih berbahaya daripada tak ada uji (memberi rasa aman yang salah).
    """
    hasil: set[str] = set()
    didrop: set[str] = set()
    for berkas in sorted(glob.glob(os.path.join(AKAR, "migrations", "*.sql"))):
        teks = open(berkas, encoding="utf-8", errors="ignore").read()
        # CREATE TABLE x ( ... tenant_id ... )  — badan diambil sampai ';' terdekat
        for m in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?(\w+)\s*\((.*?)\);",
                             teks, re.I | re.S):
            if re.search(r"\btenant_id\b", m.group(2), re.I):
                hasil.add(m.group(1).lower())
        # ALTER TABLE x ADD [COLUMN] [IF NOT EXISTS] tenant_id
        for m in re.finditer(r"alter\s+table\s+(?:if\s+exists\s+)?(?:public\.)?(\w+)\s+add\s+"
                             r"(?:column\s+)?(?:if\s+not\s+exists\s+)?tenant_id", teks, re.I):
            hasil.add(m.group(1).lower())
        for m in re.finditer(r"drop\s+table\s+(?:if\s+exists\s+)?(?:public\.)?(\w+)", teks, re.I):
            didrop.add(m.group(1).lower())
    return hasil - didrop - SUDAH_DIDROP


class TestSetiapTabelTenantPunyaKeputusan(unittest.TestCase):

    def test_pemindai_benar_benar_menemukan_sesuatu(self):
        """Pagar untuk pagar: pemindai yang mengembalikan himpunan kosong akan membuat uji di bawah
        HIJAU PALSU selamanya. Angka 15 = batas bawah aman (DB live punya 24 per 04-Agu)."""
        ada = _tabel_ber_tenant_id()
        self.assertGreaterEqual(len(ada), 15,
                                f"pemindai migrasi hanya menemukan {len(ada)} tabel ber-tenant_id — "
                                f"polanya rusak, dan uji di bawah jadi hijau-palsu")

    def test_baseline_live_seluruhnya_tertangkap_pemindai_atau_baseline(self):
        """Pemindai migrasi menemukan 15 dari 24 tabel nyata (9 tertua tak punya CREATE TABLE di folder
        ini). Uji utama karena itu memakai UNION pemindai+baseline — dan itu harus tetap begitu."""
        ada = _tabel_ber_tenant_id()
        self.assertTrue(BASELINE_LIVE_2026_08_04 - ada,
                        "pemindai kini menemukan SEMUA tabel baseline — baseline boleh disederhanakan, "
                        "tapi jangan dibuang tanpa memeriksa ulang ke DB live")

    def test_tiap_tabel_ber_tenant_id_terdaftar(self):
        terdaftar = set(_PURGE_TABLES) | set(_KEEP_TABLES) | set(_PENDING_OWNER_TABLES)
        # Jaring RANGKAP: tabel lama dari baseline terukur, tabel baru dari pemindai migrasi.
        tak_terdaftar = (_tabel_ber_tenant_id() | BASELINE_LIVE_2026_08_04) - terdaftar
        self.assertFalse(
            tak_terdaftar,
            "Tabel ber-`tenant_id` TANPA keputusan hapus/simpan/tunggu: "
            f"{sorted(tak_terdaftar)}\n"
            "Data tenant di tabel ini akan BERTAHAN setelah tenant memakai hak hapus datanya (UU PDP).\n"
            "Masukkan ke `_PURGE_TABLES` (dihapus), `_KEEP_TABLES` (disimpan + alasan), atau "
            "`_PENDING_OWNER_TABLES` (menunggu ketok owner + pertanyaannya).")

    def test_tak_ada_tabel_di_dua_kategori(self):
        """Satu tabel di dua daftar = niat yang bertentangan; yang mana yang berlaku jadi kebetulan."""
        p, k, t = set(_PURGE_TABLES), set(_KEEP_TABLES), set(_PENDING_OWNER_TABLES)
        for a, b, na, nb in ((p, k, "PURGE", "KEEP"), (p, t, "PURGE", "PENDING"), (k, t, "KEEP", "PENDING")):
            self.assertFalse(a & b, f"tabel ada di {na} DAN {nb}: {sorted(a & b)}")

    def test_alasan_simpan_dan_tunggu_tidak_kosong(self):
        """Kategori tanpa alasan = 'lupa' yang menyamar jadi 'sengaja'. Sesi berikutnya tak bisa
        membedakannya, lalu meneruskan celahnya sambil merasa sudah diputuskan."""
        for nama, peta in (("_KEEP_TABLES", _KEEP_TABLES), ("_PENDING_OWNER_TABLES", _PENDING_OWNER_TABLES)):
            for tabel, alasan in peta.items():
                self.assertTrue(alasan and len(alasan.strip()) >= 15,
                                f"{nama}['{tabel}'] tanpa alasan yang bisa dibaca manusia")

    def test_alasan_simpan_menyebut_pasal_spec_yang_mengetoknya(self):
        """Tiap tabel yang DISIMPAN harus menyebut PASAL SPEC-nya, bukan alasan karangan Claude.

        Kenapa dijaga: 04-Agu Claude menyodorkan `commission_ledger` & `tenant_attribution` ke owner
        sebagai "keputusan baru yang butuh konsultan" — padahal AGENT §5g.8 & §1.3 SUDAH mengetoknya.
        Menanyakan ulang hal yang sudah diketok = mengundang owner bertentangan dengan dirinya sendiri,
        dan membuang waktunya. Teguran owner: "buat apa file MD dibuat? pajangan?"
        Menyebut pasalnya memaksa sesi berikutnya MEMBACA dokumen, bukan bertanya."""
        for tabel, alasan in _KEEP_TABLES.items():
            self.assertRegex(
                alasan, r"(LIFECYCLE|AGENT|PAYMENT|§)",
                f"_KEEP_TABLES['{tabel}'] tak menyebut pasal SPEC yang mengetoknya — "
                f"alasan tanpa rujukan akan ditanyakan ulang ke owner oleh sesi berikutnya")

    def test_dokumen_lifecycle_selaras_dengan_kode(self):
        """DOKUMEN ↔ KODE. Ini penjaga yang paling menentukan, dan yang paling sering tak dipasang.

        Sebab akar seluruh celah ini bukan kodenya — kodenya PATUH. Yang membusuk adalah DAFTAR DI
        DOKUMEN (`LIFECYCLE_NURTURE_ARCHITECTURE.md` §4.2), yang bahkan menulis "verified" lalu
        tertinggal 4 tabel selama sebulan. Teguran owner 04-Agu: *"anda selalu abai update dokumen
        sehingga dokumen tidak bisa dijadikan SSOT yang valid. selalu begitu cara kerja anda, entah
        kenapa."*

        Jawaban atas "entah kenapa": karena tak ada apa pun yang MEMAKSANYA. Dokumen yang bertahan
        akurat adalah yang dijaga mesin (mis. `test_ssot_error_mgmt.py`); yang membusuk adalah yang
        hanya bergantung pada disiplin. Uji ini memindahkan §4.2 ke kategori pertama: begitu daftar di
        kode berubah tanpa dokumennya ikut, uji ini MERAH.
        """
        doc = os.path.join(AKAR, "LIFECYCLE_NURTURE_ARCHITECTURE.md")
        teks = open(doc, encoding="utf-8").read()
        m = re.search(r"### 4\.2 CAKUPAN HAPUS DATA(.*?)\n### ", teks, re.S)
        self.assertIsNotNone(m, "§4.2 CAKUPAN HAPUS DATA tak ditemukan — struktur dokumen berubah?")
        blok = m.group(1)

        baris_purge = next((b for b in blok.splitlines() if b.lstrip().startswith("🗑️")), "")
        baris_keep = next((b for b in blok.splitlines() if b.lstrip().startswith("📦")), "")
        self.assertTrue(baris_purge and baris_keep, "§4.2 kehilangan baris PURGE/SISAKAN")

        for tabel in _PURGE_TABLES:
            self.assertIn(f"`{tabel}`", baris_purge,
                          f"`{tabel}` DIHAPUS oleh kode tapi TIDAK tercantum di daftar PURGE §4.2 — "
                          f"dokumen membusuk lagi; SSOT tak bisa dipercaya")
        for tabel in _KEEP_TABLES:
            self.assertIn(f"`{tabel}`", baris_keep,
                          f"`{tabel}` DISIMPAN oleh kode tapi TIDAK tercantum di daftar SISAKAN §4.2")
        # Arah sebaliknya: dokumen tak boleh menjanjikan penghapusan yang kodenya tidak lakukan —
        # itu lebih berbahaya daripada dokumen yang kurang lengkap (owner membaca "dihapus", nyatanya tidak).
        for tabel in re.findall(r"`(\w+)`", baris_purge):
            if tabel in BASELINE_LIVE_2026_08_04:
                self.assertIn(tabel, _PURGE_TABLES,
                              f"§4.2 menyatakan `{tabel}` DIHAPUS, tapi kode TIDAK menghapusnya — "
                              f"dokumen menjanjikan sesuatu yang tak terjadi")

    def test_dua_tabel_uang_agen_tidak_pernah_masuk_daftar_hapus(self):
        """Pagar khusus, konsekuensinya UANG PIHAK KETIGA (agen), bukan kerapian data.

        `tenant_attribution` dihapus ⇒ bila tenant kembali & bayar, mesin komisi tak menemukan
        atribusinya → tenant dianggap "bukan bawaan siapa pun" (AGENT §1b) → **agen kehilangan komisi
        SELAMANYA tanpa tahu**. Diverifikasi 04-Agu: akun login tenant TIDAK ikut dihapus (nol
        `deleteUser`), dan atribusi HANYA ditulis saat pendaftaran — jadi tak akan pernah lahir lagi.
        `commission_ledger` dihapus ⇒ hilang jejak kewajiban audit & pajak (AGENT §5g.8)."""
        for t in ("tenant_attribution", "commission_ledger"):
            self.assertNotIn(t, _PURGE_TABLES,
                             f"`{t}` masuk daftar HAPUS — melanggar AGENT §5g.8/§1.3 "
                             f"dan berpotensi menghilangkan komisi agen")
            self.assertIn(t, _KEEP_TABLES, f"`{t}` harus tercatat DISIMPAN beserta pasalnya")

    def test_channels_dihapus_paling_akhir(self):
        """Urutan anak→induk: `channels` dulu = baris anak jadi yatim bila salah satu langkah gagal
        (fungsinya fail-soft per-langkah), dan sisa yatim itu tak akan pernah tersapu lagi."""
        self.assertEqual(_PURGE_TABLES[-1], "channels",
                         "`channels` harus TERAKHIR di _PURGE_TABLES (induk dihapus paling akhir)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
