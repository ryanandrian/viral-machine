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


# ── 5. throttle penyedia bukan "balasan rusak" ────────────────────────────────────────────────────

def test_perbaikan_MENUNGGU_saat_penyedia_throttle_bukan_menyerah():
    """Terukur di Bang Us-Dat: Groq membalas 429, dua percobaan habis dalam dua detik karena dicatat
    sebagai 'balasan rusak', perbaikan menyerah, video keluar band. 429 hanya berarti 'tunggu'.
    Tenant tingkat GRATIS — persona utama produk — menabrak batas ini setiap hari, dan jalur baru
    memakai banyak panggilan kecil."""
    from src.exceptions import ErrorClass, PipelineError

    class _Throttle:
        def __init__(self):
            self.n = 0

        def complete(self, **kw):
            self.n += 1
            if self.n == 1:
                e = PipelineError("Error code: 429 rate limit")
                e.error_class = ErrorClass.RATE_LIMIT
                raise e
            return json.dumps({"hook": "Pada tahun 1923 kota Kanto runtuh. " * 4,
                               "core_facts": "Pada tahun 1923 kota Kanto runtuh. " * 8})

    r = _resep_uji(60)
    asal = "Pada tahun 1923 kota Kanto runtuh. " * 3
    script = {"full_script": asal, "hook": asal[:40], "core_facts": asal[40:]}
    v_awal = {"status": "terlalu_pendek", "kata_selisih": 60, "video_prediksi": 20.0,
              "band_video": r["band_video"]}
    prov = _Throttle()
    _, jejak = se._refit_naskah(prov, "m", script, ["hook", "core_facts"], r, v_awal, maks_putaran=1)
    assert prov.n >= 2, "throttle membuat perbaikan menyerah — padahal cukup menunggu"
    assert any("throttle" in j for j in jejak), f"throttle tidak dikenali sebagai throttle: {jejak}"


def test_error_yang_TIDAK_bisa_ditunggu_berhenti_seketika():
    """Kredit habis / kunci ditolak: menunggu tak menolong — jangan buang waktu & uang tenant."""
    from src.exceptions import ErrorClass, PipelineError

    class _Mati:
        def __init__(self):
            self.n = 0

        def complete(self, **kw):
            self.n += 1
            e = PipelineError("insufficient credit")
            e.error_class = ErrorClass.ACCOUNT_BILLING
            raise e

    r = _resep_uji(60)
    asal = "Pada tahun 1923 kota Kanto runtuh. " * 3
    script = {"full_script": asal, "hook": asal[:40], "core_facts": asal[40:]}
    v_awal = {"status": "terlalu_pendek", "kata_selisih": 60, "video_prediksi": 20.0,
              "band_video": r["band_video"]}
    prov = _Mati()
    _, jejak = se._refit_naskah(prov, "m", script, ["hook", "core_facts"], r, v_awal, maks_putaran=2)
    assert prov.n == 1, f"error non-retryable diulang {prov.n}× — buang waktu & uang tenant"


# ── 6. jalur per-bagian dipicu DUA ARAH ───────────────────────────────────────────────────────────

def test_naskah_KEPANJANGAN_juga_memicu_tulis_per_bagian():
    """Terukur di Abyss ID (preset 30 dtk, band 22–38): satu panggilan menghasilkan 148 kata untuk
    jatah ±75 → video 57 dtk. Jalur per-bagian — satu-satunya mekanisme yang terbukti bekerja — tak
    pernah dipicu karena pemicunya hanya melihat naskah KEPENDEKAN. Akibatnya seluruh beban jatuh ke
    perbaikan akhir, yang harus memotong separuh naskah sekaligus dan ditolak 3× karena fakta ikut
    terbuang."""
    src = inspect.getsource(se.ScriptEngine.generate)
    assert "script_perbeat_trigger_atas_pct" in src, "pemicu arah KEPANJANGAN tidak ada"
    assert "_kepanjangan" in src and "_kependekan" in src, "pemicu tidak dua arah"
    assert "abs(_w_pb - _bidik) < abs(_w_now - _bidik)" in src, \
        "hasil per-bagian masih dinilai 'lebih panjang', bukan 'lebih dekat ke jatah' — salah arah " \
        "untuk naskah yang kepanjangan"


# ── 7. cacat mekanis diperbaiki, bukan cuma dilaporkan ────────────────────────────────────────────

def test_cacat_mekanis_yang_TERDETEKSI_diperbaiki_penulis():
    """Terukur di BISIK NUSANTARA: naskah mendarat tepat di band (meleset 0,1 dtk) tapi memuat
    elipsis — tanda yang DILARANG prompt. Pemeriksa menemukannya, lalu tak ada yang menindaklanjuti:
    cacat hanya jadi umpan-balik retry, dan naskah ini tak pernah di-retry karena skornya lolos di
    percobaan pertama. Narasi adalah ISI produk — cacat yang sudah KITA KETAHUI tak boleh sampai ke
    penonton."""
    src = inspect.getsource(se.ScriptEngine.generate)
    assert "CACAT MEKANIS YANG TERDETEKSI HARUS DIPERBAIKI" in src, \
        "cacat mekanis kembali hanya dilaporkan"
    blok = src[src.index("CACAT MEKANIS YANG TERDETEKSI HARUS DIPERBAIKI"):]
    blok = blok[:blok.index("SATU PERHITUNGAN AKHIR")]
    assert "_fakta_hilang(_teks_lama, _tb)" in blok, "perbaikan cacat tidak memeriksa fakta hilang"
    # DIPERBARUI 2026-08-02: dulu barisnya `_parah_baru < len(_cacat)` — perbandingan JUMLAH belaka,
    # sehingga menukar dua cacat ringan dengan satu cacat PARAH tetap diterima (1 < 2). Aturannya
    # kini berbasis KEPARAHAN (`_perbaikan_lebih_baik`), dan perilakunya diuji sungguhan di
    # `tests/test_perbaikan_cacat_hormati_keparahan.py`.
    assert "_perbaikan_lebih_baik(_cacat, _c_baru)" in blok, \
        "hasil yang tak mengurangi cacat — atau yang menambah cacat PARAH — bisa diterima"
    assert "_panjang_ok" in blok, "perbaikan cacat bisa merusak durasi"
    assert 'status"] == "ok"' in blok, \
        "penerimaan diukur dari jumlah KATA, bukan dari vonis DURASI — perbaikan sah akan ditolak " \
        "(terukur: elipsis berhasil dibuang tapi ditolak karena 19 kata dari 185 bergeser)"


# ── 8. tunggu SESUAI YANG DIMINTA PENYEDIA ────────────────────────────────────────────────────────

import pytest as _pytest


@_pytest.mark.parametrize("pesan,harap", [
    ("Error 429: Please try again in 8.523s", 9.023),
    ("rate limit. Please try again in 1m2.5s", 63.0),   # per-menit → tunggu, jauh lebih murah
    ("Please try again in 35m51.36s", None),         # kuota harian → JANGAN tunggu, berhenti
    ("Rate limit reached (no hint)", 4.0),            # tanpa petunjuk → pakai bawaan
])
def test_lama_tunggu_dibaca_dari_pesan_penyedia(pesan, harap):
    """Penyedia hampir selalu menyebutkan kapan boleh mencoba lagi; sampai 2026-08-01 pesan itu tidak
    dibaca. Terukur di RETRO REWIND: empat bagian naskah sudah jadi (135 kata), bagian kelima kena
    batas laju, kita menunggu 2/4/8 detik lalu menyerah — seluruh 135 kata dibuang dan videonya jadi
    27 detik untuk preset 60 detik. Penyedianya hanya minta ditunggu beberapa detik lagi."""
    hasil = se._tunggu_dari_pesan(Exception(pesan), 4.0)
    if harap is None:
        assert hasil is None, ("permintaan tunggu yang kelewat lama tetap ditunggu — 3×90 detik utas "
                               "pekerja tertahan untuk kuota yang baru pulih belasan menit lagi")
    else:
        assert hasil == _pytest.approx(harap, abs=0.01)


def test_pekerjaan_yang_DIBUANG_harus_terlihat_di_log():
    """Membuang bagian yang sudah jadi tanpa menyebutkannya = kegagalan yang tak bisa dilacak.

    DIPERBARUI 2026-08-02. Versi pertama uji ini mengunci perilaku "buang semuanya lalu catat
    error" — dan itu memang perilaku saat itu. Pipeline SUNGGUHAN lalu menunjukkan harganya: enam
    dari tujuh bagian berhasil (76→149 kata), bagian ke-7 kena kuota, semuanya hangus, naskah kembali
    29 dtk untuk preset 90.

    Sekarang jalur normalnya TIDAK membuang: bagian yang gagal ditambal teks ASAL-nya (naskah asal
    dijamin punya teks tiap adegan — syarat A2). Membuang hanya tersisa untuk kasus benar-benar
    buntu (asal pun tak punya bagian itu) — dan di situ ia tetap wajib `logger.error`.

    Jadi yang dijaga kini DUA hal sekaligus: penambalan itu ADA, dan pembuangan yang tersisa tetap
    keras terdengar. Uji perilakunya sendiri = `tests/test_perbagian_tak_hangus.py`.
    """
    src = inspect.getsource(se._generate_per_beat)
    assert "_teks_asal" in src, (
        "tak ada penambalan dari naskah asal — kegagalan satu bagian akan menghanguskan semuanya lagi"
    )
    assert "terpaksa dibuang" in src, "jalur buntu tidak menyebut bahwa pekerjaan dibuang"
    blok = src[src.index("terpaksa dibuang") - 400:src.index("terpaksa dibuang")]
    assert "logger.error" in blok, "dibuangnya pekerjaan hanya dicatat sebagai peringatan biasa"
