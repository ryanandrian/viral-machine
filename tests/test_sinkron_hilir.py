"""Naskah hasil TULIS-PER-BAGIAN & PERBAIKAN harus tetap sinkron dengan gambar dan suara di HILIR.

Kenapa ini kelas bug yang paling mahal kalau lolos: durasi tiap adegan (`compute_beat_durations`)
menentukan berapa lama tiap GAMBAR tampil, dan itu dihitung dari teks per-beat. Jalur baru
(tulis-per-bagian + perbaikan + penukaran hook) MENGGANTI teks itu setelah naskah pertama jadi.
Kalau `full_script` (yang dibacakan suara) dan teks per-beat (yang menentukan gambar) sampai berbeda,
akibatnya BUKAN error — video jadi, tapi gambar bergeser dari narasinya di setiap adegan, dan tak ada
yang menangkapnya kecuali menonton.
"""

from src.intelligence.script_engine import compute_beat_durations


def _skrip_per_bagian():
    """Bentuk naskah seperti keluaran jalur tulis-per-bagian: tiap beat terisi, full_script = gabungan."""
    beats = ["hook", "build_up", "core_facts", "climax", "cta"]
    isi = {"hook": "Kamu tahu apa yang terjadi pada tahun 1348?",
           "build_up": "Kota-kota Eropa menutup gerbangnya satu per satu selama berminggu-minggu.",
           "core_facts": "Wabah Hitam membunuh sepertiga penduduk benua itu dalam empat tahun saja.",
           "climax": "Yang tersisa hanya catatan seorang juru tulis bernama Marek.",
           "cta": "Simak bagian berikutnya."}
    return {**isi, "beats": beats,
            "full_script": " ".join(isi[b] for b in beats)}


def test_full_script_dan_teks_per_beat_TIDAK_BOLEH_berbeda():
    """Invarian paling penting: yang dibacakan suara = gabungan yang menentukan gambar."""
    sc = _skrip_per_bagian()
    gabung = " ".join((sc.get(b) or "") for b in sc["beats"])
    assert sc["full_script"] == gabung, "naskah yang dibacakan beda dari gabungan per-adegan"


def test_durasi_per_adegan_menjumlah_TEPAT_ke_durasi_audio():
    """Kalau tidak, gambar dan suara pasti bergeser makin jauh menjelang akhir video."""
    sc = _skrip_per_bagian()
    for audio in (8.0, 30.0, 57.3, 90.0, 300.0):
        durs = compute_beat_durations(sc, None, audio)
        assert len(durs) == len(sc["beats"]), "jumlah adegan tak sama dengan jumlah durasi"
        assert abs(sum(durs) - audio) < 0.05, f"Σdurasi {sum(durs)} != audio {audio}"
        assert all(d > 0 for d in durs), f"ada durasi adegan <= 0: {durs}"


def test_porsi_adegan_mengikuti_panjang_teksnya():
    """Adegan yang teksnya lebih panjang WAJIB tampil lebih lama — kalau tidak, gambar bergeser."""
    sc = _skrip_per_bagian()
    durs = compute_beat_durations(sc, None, 60.0)
    kata = [len((sc[b] or "").split()) for b in sc["beats"]]
    urut_kata = sorted(range(len(kata)), key=lambda i: kata[i])
    urut_dur = sorted(range(len(durs)), key=lambda i: durs[i])
    assert urut_kata == urut_dur, f"urutan panjang teks {urut_kata} != urutan durasi {urut_dur}"


def test_adegan_yang_dikosongkan_tak_membuat_durasi_nol_atau_negatif():
    """Perbaikan/penukaran hook bisa menyisakan beat kosong; itu tak boleh melahirkan durasi tak sah."""
    sc = _skrip_per_bagian()
    sc["cta"] = ""
    durs = compute_beat_durations(sc, None, 45.0)
    assert all(d > 0 for d in durs) and abs(sum(durs) - 45.0) < 0.05


def test_penukaran_hook_menjaga_konsistensi_naskah_dan_adegan():
    """Meniru STEP 4: hook ditukar di KEDUA tempat (perbaikan hari ini). Setelah itu durasi adegan
    harus mengikuti panjang hook yang BARU, bukan yang lama."""
    sc = _skrip_per_bagian()
    lama, baru = sc["hook"], "Hook baru yang jauh lebih panjang dari sebelumnya sehingga porsinya naik nyata."
    sc["full_script"] = sc["full_script"].replace(lama, baru, 1)
    sc["hook"] = baru
    gabung = " ".join((sc.get(b) or "") for b in sc["beats"])
    assert sc["full_script"] == gabung, "penukaran hook membuat naskah & adegan tak sinkron"
    d_lama = compute_beat_durations(_skrip_per_bagian(), None, 60.0)[0]
    d_baru = compute_beat_durations(sc, None, 60.0)[0]
    assert d_baru > d_lama, "porsi hook tidak mengikuti panjang teks barunya"


def test_word_timestamps_nyata_dipakai_bila_andal_dan_tetap_menjumlah():
    """Jalur presisi (timestamp nyata dari penyedia suara) juga wajib menjumlah tepat ke audio."""
    sc = _skrip_per_bagian()
    n = len(sc["full_script"].split())
    wt = [{"start": i * 0.4, "end": i * 0.4 + 0.35} for i in range(n)]
    durs = compute_beat_durations(sc, wt, 40.0)
    assert abs(sum(durs) - 40.0) < 0.05 and all(d > 0 for d in durs)
