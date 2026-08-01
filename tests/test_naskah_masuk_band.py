"""SETIAP NASKAH HARUS MASUK RENTANG PRESET — tiga lubang yang membuatnya gagal (2026-08-01).

Ketiganya tertangkap uji rantai-penuh pada channel NYATA, bukan uji satuan. Uji satuan tidak bisa
melihatnya karena masing-masing komponennya benar; yang salah cara mereka disambung.

  1. `_duration_est` DITAMBAL di tiga tempat dengan bagian berbeda → isinya bercampur antar-generasi
     naskah. Terukur di Bang Us-Dat: est_seconds 26,64 dtk (draf awal) sementara bicara+jeda 51,07 dtk
     (naskah akhir, dan audio nyatanya 51,9 dtk). Angka basi itu dipakai penjaga audio-terpotong dan
     alarm akurasi ke Telegram.
  2. Jalur tulis-per-bagian punya LANTAI tanpa PLAFON → kelebihan menumpuk. Terukur di BJ Yusroon:
     core_facts 68 kata vs jatah 39, curiosity_bridge 34 vs 14, total 220 vs 155 → video 119 dtk.
  3. Penjaga fakta melarang APA PUN hilang, juga saat tugasnya MEMENDEKKAN → perbaikan yang sah
     ditolak dan loop berhenti. Terukur: 'putaran 1: 119s → 108s' lalu 'putaran 2: DITOLAK — fakta
     hilang: Jepang', video akhirnya keluar band.
"""

import inspect
import json

import src.intelligence.script_engine as se
from src.production.duration_model import resep as _resep_fn


class _ProviderPalsu:
    """Mengembalikan naskah yang sudah ditentukan — supaya perilaku KODE yang diuji, bukan model."""

    def __init__(self, balasan: list[dict]):
        self.balasan = list(balasan)
        self.dipanggil = 0
        self.prompt_terakhir = ""

    def complete(self, system=None, user=None, model=None, temperature=None, max_tokens=None,
                 as_json=False):
        self.dipanggil += 1
        self.prompt_terakhir = user or ""
        return json.dumps(self.balasan.pop(0) if self.balasan else {})


def _resep_uji(preset=90):
    tangga = [8, 15, 30, 45, 60, 75, 90]
    r = _resep_fn(preset, tangga, 3.5, None)
    r["_preset"], r["_tangga"], r["_overhead"], r["_kalibrasi"] = preset, tangga, 3.5, None
    return r


# ── 1. satu perhitungan akhir ─────────────────────────────────────────────────────────────────────

def test_angka_durasi_dihitung_SEKALI_dari_naskah_akhir():
    """Tiga tambalan bersyarat diganti satu perhitungan tanpa syarat atas teks final."""
    src = inspect.getsource(se.ScriptEngine.generate)
    assert "SATU PERHITUNGAN AKHIR" in src, "penambalan bersyarat kembali"
    assert src.count('"est_seconds"') <= 2, \
        "est_seconds ditulis di lebih dari satu tempat lagi — angka bisa bercampur antar-generasi"
    assert "taksiran tidak konsisten" in src, \
        "tidak ada penjaga yang berteriak bila total ≠ bicara+jeda"


# ── 2. plafon per-bagian ──────────────────────────────────────────────────────────────────────────

def test_bagian_yang_KEPANJANGAN_dirapikan_seketika():
    src = inspect.getsource(se._generate_per_beat)
    assert "script_perbeat_maks_rasio_pct" in src, "plafon per-bagian tidak ada — kelebihan menumpuk lagi"
    assert "script_perbeat_min_rasio_pct" in src, "lantai per-bagian hilang"
    i_min = src.index("script_perbeat_min_rasio_pct")
    i_maks = src.index("script_perbeat_maks_rasio_pct")
    assert i_min < i_maks, "urutan lantai→plafon berubah (perapatan bisa jalan sebelum pelengkapan)"


def test_perapatan_bagian_DITOLAK_bila_membuang_fakta():
    """Memendekkan tak boleh dibayar dengan isi — pelajaran termahal: kode yang memangkas sendiri
    membuang kalimat terkuat naskah."""
    src = inspect.getsource(se._generate_per_beat)
    blok = src[src.index("script_perbeat_maks_rasio_pct"):]
    assert "_fakta_hilang(teks, _t3)" in blok, "perapatan bagian tidak memeriksa fakta hilang"
    assert "len(_t3.split()) < len(teks.split())" in blok, \
        "hasil yang TIDAK lebih pendek bisa diterima sebagai 'perapatan'"


# ── 3. penjaga fakta sadar-arah ───────────────────────────────────────────────────────────────────

def test_memendekkan_BOLEH_melepas_sedikit_fakta_dan_loop_TIDAK_berhenti():
    """Kasus nyata BJ Yusroon: satu-satunya jalan ke band ditolak karena satu nama tempat hilang."""
    r = _resep_uji(90)
    panjang = ("Pada tahun 1923 kota Kanto di Jepang runtuh dalam tiga menit. "
               "Getaran itu terasa sampai Osaka dan Nagoya serta Kyoto. ") * 12
    script = {"full_script": panjang, "hook": panjang[:80], "core_facts": panjang[80:]}
    v_awal = {"status": "terlalu_panjang", "kata_selisih": 60, "video_prediksi": 119.0}
    # balasan: lebih pendek, satu nama tempat sengaja dijatuhkan
    pendek = panjang.replace("Nagoya serta ", "").replace(" dan Osaka", "")[: int(len(panjang) * 0.6)]
    prov = _ProviderPalsu([{"hook": pendek[:80], "core_facts": pendek[80:]}])
    hasil, jejak = se._refit_naskah(prov, "m", script, ["hook", "core_facts"], r, v_awal,
                                    maks_putaran=1)
    assert prov.dipanggil == 1
    assert hasil.get("full_script") != panjang, \
        "pemendekan yang sah ditolak — video tak punya jalan lain menuju band"
    assert any("dilepas saat memendekkan" in j for j in jejak), f"jejak tidak menjelaskan: {jejak}"


def test_memanjangkan_TIDAK_boleh_kehilangan_satu_fakta_pun():
    """Arah sebaliknya: kehilangan fakta saat memanjangkan = kemunduran murni, nol toleransi."""
    r = _resep_uji(90)
    asal = ("Pada tahun 1923 kota Kanto di Jepang runtuh. " * 8)
    script = {"full_script": asal, "hook": asal[:60], "core_facts": asal[60:]}
    v_awal = {"status": "terlalu_pendek", "kata_selisih": 80, "video_prediksi": 40.0}
    tanpa_fakta = asal.replace("1923", "dahulu").replace("Jepang", "negeri itu")
    prov = _ProviderPalsu([{"hook": tanpa_fakta[:60], "core_facts": tanpa_fakta[60:]},
                           {"hook": asal[:60], "core_facts": asal[60:]}])
    hasil, jejak = se._refit_naskah(prov, "m", script, ["hook", "core_facts"], r, v_awal,
                                    maks_putaran=2)
    assert any("fakta hilang" in j for j in jejak), f"fakta hilang tidak terdeteksi: {jejak}"
    # yang dikunci: fakta TETAP ADA di naskah hasil — versi tanpa fakta tidak pernah dipakai
    assert "1923" in (hasil.get("full_script") or ""), "naskah tanpa fakta diterima saat memanjangkan"
    assert "Jepang" in (hasil.get("full_script") or "")


def test_putaran_berikutnya_MENYEBUT_fakta_yang_wajib_kembali():
    """Menolak saja tidak cukup: sisa putaran hanya berguna bila model diberi tahu PERSIS apa yang
    harus dikembalikan. Tanpa ini, putaran berikutnya mengulangi kesalahan yang sama."""
    r = _resep_uji(90)
    asal = ("Pada tahun 1923 kota Kanto di Jepang runtuh. " * 8)
    script = {"full_script": asal, "hook": asal[:60], "core_facts": asal[60:]}
    v_awal = {"status": "terlalu_pendek", "kata_selisih": 80, "video_prediksi": 40.0}
    tanpa = asal.replace("1923", "dahulu")
    prov = _ProviderPalsu([{"hook": tanpa[:60], "core_facts": tanpa[60:]},
                           {"hook": asal[:60], "core_facts": asal[60:]}])
    se._refit_naskah(prov, "m", script, ["hook", "core_facts"], r, v_awal, maks_putaran=2)
    assert prov.dipanggil == 2, "loop berhenti setelah satu penolakan — sisa putaran terbuang"
    assert "1923" in prov.prompt_terakhir and "MUST be back" in prov.prompt_terakhir, \
        "putaran berikutnya tidak menyebut fakta yang wajib dikembalikan"


# ── 4. detektor nama diri tidak boleh memblokir perbaikan yang sah ────────────────────────────────

def test_kata_tanya_di_tengah_kalimat_BUKAN_nama_diri():
    """Kasus nyata Bang Us-Dat: naskah 129 kata dalam 2 kalimat dengan 12 koma, sehingga kata tanya
    'Bagaimana' jatuh di tengah kalimat dan dianggap NAMA DIRI. Dua putaran perbaikan terakhir ditolak
    karenanya, dan videonya meleset 0,9 detik dari band — gagal karena kata tanya, bukan karena naskah."""
    t = ("Semua orang bertanya, Bagaimana mungkin kota Kanto di Jepang runtuh dalam tiga menit, "
         "Mengapa tak ada satu pun peringatan.")
    nama = se._nama_diri(t)
    assert "Bagaimana" not in nama and "Mengapa" not in nama, \
        "kata tanya di awal klausa masih dianggap nama diri — perbaikan yang sah akan diblokir lagi"
    assert {"Kanto", "Jepang"} <= nama, "nama tempat sungguhan ikut hilang — penjaga fakta jadi buta"
    assert se._fakta_hilang(t, t.replace("Bagaimana mungkin ", "")) == [], \
        "membuang kata tanya dihitung sebagai kehilangan fakta"


def test_putaran_yang_MENJAUH_dari_band_ditolak():
    """Docstring lama menjanjikan 'vonis durasi membaik' tapi kodenya tak pernah memeriksanya.
    Terukur: 'putaran 1: 52s → 49s' diterima padahal naskah butuh ≥52 dtk — perbaikan memperburuk
    keadaan, lalu sisa putaran habis mengejar ketertinggalan yang kita buat sendiri."""
    r = _resep_uji(60)
    asal = ("Pada tahun 1923 kota Kanto runtuh dalam tiga menit. " * 6)
    script = {"full_script": asal, "hook": asal[:60], "core_facts": asal[60:]}
    v_awal = {"status": "terlalu_pendek", "kata_selisih": 40, "video_prediksi": 40.0,
              "band_video": r["band_video"]}
    lebih_pendek = ("Pada tahun 1923 kota Kanto runtuh dalam tiga menit. " * 3)
    prov = _ProviderPalsu([{"hook": lebih_pendek[:60], "core_facts": lebih_pendek[60:]}])
    hasil, jejak = se._refit_naskah(prov, "m", script, ["hook", "core_facts"], r, v_awal,
                                    maks_putaran=1)
    assert hasil.get("full_script") == asal, "hasil yang MENJAUH dari band diterima"
    assert any("tidak mendekati band" in j for j in jejak), f"jejak tidak menjelaskan: {jejak}"
