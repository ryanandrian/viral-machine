"""Seluruh aset/media HANYA di S3 — Supabase = database saja.

SSOT: `CLAUDE.md` §6.7 — *"Semua aset/media HANYA di S3 `mesinviral-assets`; Supabase = database saja."*

MASALAH YANG DIJAGA (diukur 2026-08-05 — aturan ini BELUM PERNAH diukur sebelumnya)
Keadaan BERSIH:
  • **nol** pemakaian Supabase Storage di seluruh `src/` dan `apps/web/src/`
  • backend: **satu** jalur unggah (`s3_buffer.upload` → `upload_file`), bucket dari env **tanpa default**
    (gagal jujur bila `S3_BUCKET` tak diset — bukan diam-diam menulis ke tempat lain)
  • FE: 5 rute unggah (logo channel · musik · sampul konten · font · showcase) — **semuanya**
    `PutObjectCommand` ke `mesinviral-assets`, nol tulis ke disk sebagai penyimpanan

Kenapa aturan ini penting bagi owner: aset tersebar = biaya ganda, backup tak lengkap, dan saat tenant
memakai hak hapus datanya (UU PDP) ada berkas pribadi yang TERTINGGAL di tempat yang tak diketahui
`_hard_delete_tenant` (ia hanya menyapu prefix S3). Satu unggahan ke Supabase Storage saja sudah membuat
penghapusan data menjadi tidak lengkap — dan tak ada yang tahu sampai ada yang menuntut.

Uji ini HERMETIK (memindai kode, nol jaringan/DB).
"""
import glob
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BE = os.path.join(AKAR, "src")
FE = os.path.join(AKAR, "apps", "web", "src")

# Pola penyimpanan yang DILARANG untuk aset (Supabase Storage & simpan-permanen ke disk server).
DILARANG = [
    (r"\.storage\s*\.\s*from_", "Supabase Storage (python)"),
    (r"storage\s*\.\s*from\s*\(", "Supabase Storage (js)"),
    (r"createBucket|listBuckets", "Supabase Storage bucket API"),
]

# Berkas yang WAJAR memakai disk lokal: semuanya SEMENTARA (render lalu diunggah/dibuang),
# bukan penyimpanan. Diverifikasi satu per satu 2026-08-05.
DISK_SEMENTARA_WAJAR = {
    # Berkas SEMENTARA untuk dirender lalu diunggah S3 & dibersihkan (diperiksa satu per satu 05-Agu):
    "src/production/video_renderer.py":   "render mp4 ke logs/ lalu diunggah S3 & dibersihkan",
    "src/production/visual_assembler.py": "unduh klip ke clips_/ untuk dirender, dibersihkan setelahnya",
    "src/production/tts_engine.py":       "tulis audio sementara untuk dirender, dibersihkan setelahnya",
    "src/utils/storage_cleaner.py":       "justru MEMBERSIHKAN berkas sementara — bukan penyimpan",
    "src/providers/tts/edge_tts.py":      "tulis audio ke output_path sementara (dirender lalu dibuang)",
    "src/providers/tts/elevenlabs.py":    "tulis audio ke output_path sementara (dirender lalu dibuang)",
    "src/providers/tts/fal_tts.py":       "tulis audio ke output_path sementara (dirender lalu dibuang)",
    "src/providers/visual/ai_image.py":   "tulis gambar ke output_path sementara (dirender lalu dibuang)",
    "src/providers/visual/ai_video.py":   "tulis klip ke out_path sementara (dirender lalu dibuang)",
    # Cache katalog & berkas DIAGNOSA. Bukan aset tenant, TAPI memuat konten tenant (naskah/judul/hook)
    # ⇒ WAJIB ikut terhapus saat hak-hapus-data. Ditutup 05-Agu di `renewal._hard_delete_tenant`.
    "src/intelligence/config.py":         "cache katalog niche (data/niches_cache.json) — regenerable, nol data tenant",
    "src/intelligence/hook_optimizer.py": "diagnosa logs/optimized_<tenant>.json — ikut dihapus saat hard-delete",
    "src/intelligence/niche_selector.py": "diagnosa logs/topics_<tenant>.json — ikut dihapus saat hard-delete",
    "src/intelligence/script_engine.py":  "diagnosa logs/scripts_<tenant>.json — ikut dihapus saat hard-delete",
    "src/orchestrator/pipeline.py":       "diagnosa logs/pipeline_<run_id>.json + salin thumbnail — ikut dihapus saat hard-delete",
}


def _berkas(akar: str, *ekst: str) -> list[str]:
    keluar = []
    for e in ekst:
        keluar += [p for p in glob.glob(os.path.join(akar, "**", f"*{e}"), recursive=True)
                   if "node_modules" not in p and "__pycache__" not in p]
    return keluar


class TestNolPenyimpananSelainS3(unittest.TestCase):

    def test_ada_berkas_untuk_diperiksa(self):
        """Pagar untuk pagar: bila pemindai rusak, uji di bawah hijau-palsu selamanya."""
        n = len(_berkas(BE, ".py")) + len(_berkas(FE, ".ts", ".tsx"))
        self.assertGreaterEqual(n, 100, f"pemindai hanya menemukan {n} berkas — polanya rusak")

    def test_nol_pemakaian_supabase_storage(self):
        """Satu unggahan ke Supabase Storage = aset di luar jangkauan penghapusan data (UU PDP)."""
        temuan = []
        for p in _berkas(BE, ".py") + _berkas(FE, ".ts", ".tsx"):
            teks = open(p, encoding="utf-8", errors="ignore").read()
            for pola, nama in DILARANG:
                if re.search(pola, teks):
                    temuan.append(f"{os.path.relpath(p, AKAR)} → {nama}")
        self.assertFalse(
            temuan,
            "Aset disimpan DI LUAR S3 (melanggar CLAUDE.md §6.7):\n  " + "\n  ".join(temuan)
            + "\nAkibat: `_hard_delete_tenant` hanya menyapu prefix S3 ⇒ berkas pribadi tenant "
              "TERTINGGAL setelah ia memakai hak hapus datanya.")


class TestSemuaJalurUnggahKeBucketAset(unittest.TestCase):

    def test_backend_punya_satu_jalur_unggah_dan_bucketnya_dari_env(self):
        p = os.path.join(BE, "utils", "s3_buffer.py")
        s = open(p, encoding="utf-8").read()
        self.assertIn("upload_file(", s, "jalur unggah backend hilang dari s3_buffer")
        self.assertRegex(s, r'os\.getenv\("S3_BUCKET"\)',
                         "bucket backend tak lagi dari env — nilai bisnis jadi terpatri")
        self.assertRegex(s, r"raise\s+BufferError",
                         "bucket tak diset seharusnya GAGAL JUJUR (§0.6), bukan memakai default diam-diam")

    def test_setiap_rute_unggah_fe_menulis_ke_s3(self):
        """Rute unggah baru yang lupa memakai S3 = aset tersebar sejak hari pertama."""
        cacat = []
        for p in _berkas(os.path.join(FE, "app", "api"), ".ts"):
            teks = open(p, encoding="utf-8", errors="ignore").read()
            if "formData" not in teks and "PutObjectCommand" not in teks:
                continue                      # bukan rute unggah berkas
            if "File" not in teks and "PutObjectCommand" not in teks:
                continue
            rel = os.path.relpath(p, AKAR)
            if "PutObjectCommand" not in teks:
                cacat.append(f"{rel}: menerima berkas tapi TIDAK menulis ke S3")
            elif not re.search(r'S3_ASSET_BUCKET|S3_BUCKET', teks):
                cacat.append(f"{rel}: menulis ke S3 tapi bucketnya terpatri (bukan dari env)")
        self.assertFalse(cacat, "Rute unggah bermasalah (§6.7):\n  " + "\n  ".join(cacat))

    def test_pemakai_disk_lokal_hanya_yang_sudah_diverifikasi(self):
        """Menulis ke disk server BOLEH hanya sebagai berkas SEMENTARA (render → unggah → bersihkan).
        Pemakai baru = kemungkinan aset permanen di disk VPS: tak ter-backup, tak ikut terhapus,
        dan habis saat server diganti."""
        pemakai = []
        for p in _berkas(BE, ".py"):
            teks = open(p, encoding="utf-8", errors="ignore").read()
            if re.search(r"open\([^)]*['\"](?:wb|w)['\"]|\.write_bytes\(|shutil\.copy", teks):
                pemakai.append(os.path.relpath(p, AKAR).replace(os.sep, "/"))
        baru = sorted(set(pemakai) - set(DISK_SEMENTARA_WAJAR))
        self.assertFalse(
            baru,
            "Berkas BARU yang menulis ke disk server: " + str(baru) + "\n"
            "Pastikan itu SEMENTARA (dirender lalu diunggah S3 & dibersihkan), lalu daftarkan di "
            "DISK_SEMENTARA_WAJAR beserta alasannya. Aset permanen di disk VPS = tak ter-backup, "
            "tak ikut terhapus saat hak-hapus-data, dan hilang saat server diganti.")

    def test_alasan_disk_sementara_bisa_dibaca_manusia(self):
        for berkas, alasan in DISK_SEMENTARA_WAJAR.items():
            self.assertTrue(alasan and len(alasan.strip()) >= 20,
                            f"DISK_SEMENTARA_WAJAR['{berkas}'] tanpa alasan memadai")


if __name__ == "__main__":
    unittest.main(verbosity=2)
