"""GAMBAR HARUS MENGIKUTI KATA YANG SEDANG DIUCAPKAN — bukan hitungan kata di atas kertas.

Cacat yang ditutup 2026-08-02. `compute_beat_durations` menyusuri penanda waktu SEBANYAK JUMLAH KATA
BEAT AKTIF: adegan-1 mengambil N1 kata pertama, adegan-2 N2 berikutnya, dst. Itu hanya benar bila
audio = gabungan beat aktif. Kenyataannya audio dibuat dari `full_script`, dan `full_script` MEMUAT
LEBIH BANYAK — model mengisi beat yang tidak dipakai preset lalu menulis ulang sambungannya.

Terukur pada 82 video produksi: 47 di antaranya punya `full_script` 9–43 kata lebih panjang dari
gabungan beat aktifnya. Akibatnya setiap batas adegan setelah selisih pertama menempel pada kata yang
salah — pada empat naskah nyata yang dirender ulang, gambar meleset **2,5–7,1 detik** dari kata yang
terdengar. Durasi TOTAL tetap benar (dinormalisasi), jadi cacat ini tak pernah menyalakan alarm.

Uji ini memakai penanda waktu yang dibuat sendiri (deterministik, nol vendor) dan menuntut batas
adegan menempel pada kata pertama tiap beat.
"""

import src.intelligence.script_engine as se


def _penanda(kalimat_per_beat, detik_per_kata=0.5):
    """Bangun deretan penanda waktu dari teks yang BENAR-BENAR diucapkan (urut, tanpa celah)."""
    wt, t = [], 0.0
    for teks in kalimat_per_beat:
        for w in teks.split():
            wt.append({"word": w, "start": round(t, 3), "end": round(t + detik_per_kata, 3)})
            t += detik_per_kata
    return wt, round(t, 3)


# Preset memakai 3 adegan; model JUGA mengisi satu beat yang tidak dipakai (kelas cacat aslinya).
_HOOK = "kota itu hilang tanpa jejak"
_SISIPAN = "dan tidak ada yang berani membicarakannya lagi selama puluhan tahun"   # beat tak aktif
_INTI = "penyelam menemukan tembok batu di dasar danau"
_CTA = "ikuti untuk kisah berikutnya"


def _skrip():
    return {
        "beats": ["hook", "core_facts", "cta"],
        "hook": _HOOK,
        "mystery_drop": _SISIPAN,          # TIDAK aktif, tapi berisi — dan ikut terucap
        "core_facts": _INTI,
        "cta": _CTA,
        "full_script": f"{_HOOK} {_SISIPAN} {_INTI} {_CTA}",
    }


def _mulai(durs):
    out, t = [], 0.0
    for d in durs:
        out.append(round(t, 3)); t += d
    return out


def test_batas_adegan_menempel_pada_kata_pertamanya():
    sc = _skrip()
    wt, total = _penanda([_HOOK, _SISIPAN, _INTI, _CTA])
    durs = se.compute_beat_durations(sc, wt, total)

    assert len(durs) == 3
    assert abs(sum(durs) - total) < 0.05, "total durasi adegan harus sama dengan panjang audio"

    mulai = _mulai(durs)
    n_hook, n_sisip, n_inti = len(_HOOK.split()), len(_SISIPAN.split()), len(_INTI.split())
    harus = [0.0,
             wt[n_hook + n_sisip]["start"],                    # core_facts mulai SETELAH sisipan
             wt[n_hook + n_sisip + n_inti]["start"]]           # cta mulai setelah inti
    for b, m, h in zip(sc["beats"], mulai, harus):
        assert abs(m - h) < 0.26, (
            f"adegan '{b}' mulai {m}s padahal kata pertamanya terdengar {h}s — "
            f"gambar tidak mengikuti narasi"
        )


def test_kata_yang_bukan_milik_adegan_mana_pun_jatuh_ke_adegan_sebelumnya():
    """Sisipan yang tak punya adegan sendiri HARUS terdengar saat gambar sebelumnya masih tampil —
    bukan memotong adegan berikutnya, dan bukan menghilang dari perhitungan."""
    sc = _skrip()
    wt, total = _penanda([_HOOK, _SISIPAN, _INTI, _CTA])
    durs = se.compute_beat_durations(sc, wt, total)
    dur_hook = durs[0]
    lama_hook_saja = len(_HOOK.split()) * 0.5
    assert dur_hook > lama_hook_saja + 1.0, (
        "sisipan tidak ikut dihitung ke adegan mana pun → ada waktu audio yang tak bergambar"
    )


def test_tanpa_sisipan_hasilnya_tetap_tepat():
    """Naskah yang rapi (audio = gabungan beat aktif) tidak boleh jadi lebih buruk oleh perbaikan ini."""
    sc = {"beats": ["hook", "core_facts", "cta"], "hook": _HOOK, "core_facts": _INTI, "cta": _CTA,
          "full_script": f"{_HOOK} {_INTI} {_CTA}"}
    wt, total = _penanda([_HOOK, _INTI, _CTA])
    durs = se.compute_beat_durations(sc, wt, total)
    mulai = _mulai(durs)
    harus = [0.0, wt[len(_HOOK.split())]["start"],
             wt[len(_HOOK.split()) + len(_INTI.split())]["start"]]
    for m, h in zip(mulai, harus):
        assert abs(m - h) < 0.26, f"mulai {m}s vs seharusnya {h}s"


def test_penanda_waktu_tak_bisa_dipercaya_jatuh_ke_jalur_lama():
    """Penanda waktu terlalu sedikit → JANGAN dipaksakan; pakai proporsi jumlah kata (perilaku lama)."""
    sc = _skrip()
    wt, _ = _penanda([_HOOK])          # jauh lebih sedikit dari jumlah kata beat
    durs = se.compute_beat_durations(sc, wt, 30.0)
    assert len(durs) == 3
    assert abs(sum(durs) - 30.0) < 0.05
    assert all(d >= 0.6 for d in durs)


def test_tanpa_penanda_waktu_sama_sekali():
    sc = _skrip()
    durs = se.compute_beat_durations(sc, None, 24.0)
    assert len(durs) == 3 and abs(sum(durs) - 24.0) < 0.05
    assert all(d >= 0.6 for d in durs)


def test_teks_beat_yang_ditulis_ulang_model_tetap_terlacak():
    """Model sering menulis ulang sedikit di `full_script` (terukur: kemiripan kata median 0,86).
    Pencocokan harus tahan terhadap itu, bukan menyerah."""
    sc = _skrip()
    diucapkan = [_HOOK, _SISIPAN, _INTI.replace("menemukan", "menemui"), _CTA]
    wt, total = _penanda(diucapkan)
    durs = se.compute_beat_durations(sc, wt, total)
    mulai = _mulai(durs)
    idx_inti = len(_HOOK.split()) + len(_SISIPAN.split())
    assert abs(mulai[1] - wt[idx_inti]["start"]) < 0.6, (
        "satu kata berubah membuat pencocokan meleset — terlalu rapuh"
    )
