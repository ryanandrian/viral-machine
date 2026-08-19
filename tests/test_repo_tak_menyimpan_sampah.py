"""APLIKASI TIDAK BOLEH MENYIMPAN FOLDER SAMPAH — sisa kekeliruan kerja Claude.

LAHIR DARI TEGURAN OWNER 20-Agu: *"jadi sekarang anda meninggalkan fosil-fosil script pengerusakan
yang pernah anda buat, jadi sampah di aplikasi ini?"* — dan **benar**: ada dua folder kosong
tertinggal di gudang kerja, keduanya bekas kekeliruan jalur perintah saya:

    scratchpad/          — 0 berkas, tertanggal 1-Jul
    apps/web/web/        — 0 berkas, 5 subfolder kosong bersarang, tertanggal 17-Jul
                           (kembaran salah dari `apps/web/src/app/api/...`)

Keduanya tak dirujuk kode/dokumen mana pun, dan tak terdeteksi siapa pun selama **sebulan lebih**.
Owner juga menyebut beban yang lebih dalam: *"begitu jadi masalah, minta izin saya untuk beresin
sampah anda... jika saya setujui jadi boomerang buat saya, karena saat anda membersihkan sampah bisa
jadi anda malah membuat pengerusakan baru."* Maka pembersihan dibuktikan: 719 berkas terlacak git
sebelum = 719 sesudah.

KENAPA UJI, BUKAN "LEBIH RAPI LAIN KALI": folder sampah lahir dari perintah yang salah jalur — hal
yang PASTI terulang. Yang bisa mencegahnya menetap hanyalah penolakan mesin.

`apps/web/web` SENGAJA TIDAK dimasukkan `.gitignore`: mengabaikannya berarti MENYEMBUNYIKAN
kekambuhan. Yang benar = terlihat lalu ditolak, bukan disembunyikan.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Jalur yang TERBUKTI pernah lahir dari kekeliruan jalur perintah — bukan daftar tebakan.
JALUR_TERLARANG = ("apps/web/web", "scratchpad", "apps/web/apps", "src/src", "tests/tests")


class TestRepoBersih(unittest.TestCase):

    def test_folder_kembar_salah_jalur_tak_boleh_ada(self):
        ada = [p for p in JALUR_TERLARANG if os.path.isdir(os.path.join(AKAR, p))]
        self.assertEqual(
            ada, [],
            f"Folder sampah lahir kembali: {ada}. Ini bekas perintah yang salah jalur (mis. `cd` "
            "gagal lalu berkas ditulis relatif). Hapus foldernya — JANGAN dimasukkan .gitignore, "
            "karena mengabaikannya berarti menyembunyikan kekambuhan.")

    def test_tak_ada_folder_kosong_bersarang_di_aplikasi_web(self):
        """Sarang folder kosong = sisa jalur salah; ia tak pernah lahir dari pekerjaan yang benar."""
        akar_web = os.path.join(AKAR, "apps", "web", "src")
        kosong = []
        for dirpath, dirnames, filenames in os.walk(akar_web):
            if "node_modules" in dirpath or ".next" in dirpath:
                continue
            if not filenames and not dirnames:
                kosong.append(os.path.relpath(dirpath, AKAR))
        self.assertEqual(kosong, [], f"Folder kosong di dalam aplikasi web: {kosong}")

    def test_skrip_kerja_sementara_tak_ikut_masuk_repo(self):
        """Skrip ukur/uji-coba Claude WAJIB tinggal di folder sementara di luar aplikasi.
        Hari ini 135 skrip kerja dibuat; NOL boleh masuk ke sini."""
        import subprocess
        keluaran = subprocess.run(["git", "ls-files"], cwd=AKAR, capture_output=True,
                                  text=True).stdout.splitlines()
        pola = ("bukti_", "periksa_", "uji_stabil", "uji_jatah", "cek_alasan", "verifikasi_klaim",
                "ukur_pace", "buat_contoh_suara", "model_vs_kata", "uji_penentu", "uji_prompt_asli")
        nyasar = [f for f in keluaran
                  if os.path.basename(f).startswith(pola) and f.endswith(".py")
                  and not f.startswith("tests/")]
        self.assertEqual(nyasar, [], f"Skrip kerja sementara masuk ke aplikasi: {nyasar}")


if __name__ == "__main__":
    unittest.main()
