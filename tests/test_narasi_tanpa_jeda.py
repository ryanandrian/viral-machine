"""NARASI SATU TARIKAN NAPAS HARUS DITANGKAP — ini "potongan yang merusak" versi paling halus.

Kejadian NYATA di pipeline sungguhan (BISIK NUSANTARA, 2026-08-02 03:01): llama-3.3 mengirim naskah
76 kata dengan **NOL kalimat** — tak satu pun titik. Pemeriksa mekanis hanya menandai "naskah tidak
berakhir dengan tanda baca" (gejala di ujung), bukan penyakitnya: seluruh naskah adalah satu kalimat
yang tak pernah ditutup. Narator membacanya tanpa jeda sampai kehabisan napas.

Penyebabnya UMPAN BALIK KITA SENDIRI: "Every sentence end costs real silence — merge sentences instead
of adding them." Benar secara durasi, dan itulah bahayanya — model lemah menelannya mentah lalu
membuang SELURUH titik. Dua-duanya diperbaiki: instruksinya kini menyebut batas bawah, dan pemeriksa
mekanis menangkapnya secara deterministik (aturan, bukan permintaan).
"""

import src.intelligence.script_checker as sc


def _jenis(temuan):
    return {t["jenis"] for t in temuan}


_NORMAL = ("Kota itu hilang tanpa jejak pada tahun 1923. Penyelam menemukan tembok batu di dasar "
           "danau. Usianya diperkirakan dua belas ribu tahun. Tak seorang pun bisa menjelaskannya. "
           "Sampai hari ini penelitian masih berlanjut di sana.")


def test_naskah_tanpa_satu_pun_titik_ditandai_cacat_PARAH():
    teks = ("kota itu hilang tanpa jejak pada tahun 1923 lalu penyelam menemukan tembok batu di "
            "dasar danau yang usianya diperkirakan dua belas ribu tahun dan tak seorang pun bisa "
            "menjelaskan bagaimana bangunan setua itu bisa berada di sana sampai hari ini")
    t = sc.periksa_naskah(teks)
    assert "narasi_tanpa_jeda" in _jenis(t), f"tidak tertangkap: {_jenis(t)}"
    assert any(x["jenis"] == "narasi_tanpa_jeda" and x["parah"] for x in t), (
        "hanya dicatat sebagai peringatan ringan — ini merusak narasi, harus PARAH"
    )


def test_kalimat_kepanjangan_ditandai_walau_ada_titik():
    """Satu titik di ujung tidak menyelamatkan kalimat 60 kata."""
    teks = " ".join(["kata"] * 60) + "."
    assert "narasi_tanpa_jeda" in _jenis(sc.periksa_naskah(teks))


def test_naskah_normal_TIDAK_ditandai():
    t = _jenis(sc.periksa_naskah(_NORMAL))
    assert "narasi_tanpa_jeda" not in t, f"naskah wajar ikut ditandai — akan menolak naskah sehat: {t}"


def test_naskah_pendek_tidak_dinilai():
    """Hook 8 kata tanpa titik bukan 'satu tarikan napas' — jangan salah tuduh."""
    assert "narasi_tanpa_jeda" not in _jenis(sc.periksa_naskah("kota itu hilang tanpa jejak"))


def test_tanda_kutip_tidak_dihitung_sebagai_akhir_kalimat():
    """Menghitung kalimat memakai daftar tanda AKHIR (yang memuat kutip/kurung) akan melipatgandakan
    hitungannya dan membuat naskah run-on lolos. Kutip di dalam naskah tak boleh menutup kalimat."""
    teks = ('dia berkata "aku melihatnya" lalu semua diam dan tak ada yang berani bertanya lagi '
            'karena mereka tahu apa yang terjadi malam itu di rumah tua yang sudah lama kosong')
    assert "narasi_tanpa_jeda" in _jenis(sc.periksa_naskah(teks))


def test_instruksi_ke_model_menyebut_batas_bawah():
    """Penjaga akar: umpan balik durasi tak boleh lagi menyuruh 'gabungkan kalimat' tanpa pagar."""
    import inspect

    import src.intelligence.script_engine as se
    src = inspect.getsource(se.ScriptEngine.generate)
    assert "must still END" in src, "instruksi tak menyebut kalimat wajib diakhiri titik"
    assert "script_maks_kata_per_kalimat" in src, "instruksi tak menyebut batas panjang kalimat"
