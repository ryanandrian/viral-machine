"""SEMUA ADAPTOR SUARA WAJIB PATUH SATU KONTRAK — properti tetap properti, fungsi tetap fungsi.

Cacat yang ditutup 2026-08-02: `fal_tts` menulis `provider_name` dan `supports_word_timestamps`
sebagai fungsi biasa, padahal `TTSProvider` (base.py) dan kelima adaptor lain mendeklarasikannya
`@property`. Akibatnya tidak ada cara memanggilnya yang benar untuk semua:

  • `prov.supports_word_timestamps`   → fal mengembalikan METODE (selalu dianggap benar, bahkan untuk
                                        penyedia yang tak mendukung penanda waktu)
  • `prov.supports_word_timestamps()` → meledak `'bool' object is not callable` di lima adaptor lain

Python tidak menegakkan ini: `@abstractmethod` hanya menuntut NAMA-nya ada, bukan bentuknya. Jadi
cacat begini lolos impor, lolos build, dan baru meledak pada pemanggil PERTAMA — dalam kasus ini alat
ukur jeda, sepuluh hari setelah adaptornya ditulis. `provider_name` belum meledak hanya karena belum
ada yang me-log-nya; begitu ada, keluarannya "<bound method …>".

Uji ini memeriksa BENTUK anggota kelas (bukan perilaku), jadi ia menangkap adaptor baru yang salah
bentuk sejak hari pertama — sebelum ada pemanggilnya.
"""

import importlib
import inspect
import pkgutil

from src.providers.tts.base import TTSProvider

# Bentuk yang benar diambil dari kontraknya sendiri, bukan diketik ulang — kalau base berubah,
# uji ini ikut berubah dan tidak menjadi fosil yang menuntut aturan lama.
_HARUS_PROPERTI = {n for n, v in vars(TTSProvider).items() if isinstance(v, property)}
_HARUS_FUNGSI = {n for n, v in vars(TTSProvider).items()
                 if callable(v) and not isinstance(v, property) and not n.startswith("__")}


def _adaptor():
    import src.providers.tts as paket
    out = []
    for m in pkgutil.iter_modules(paket.__path__):
        if m.name in ("base", "__init__"):
            continue
        mod = importlib.import_module(f"src.providers.tts.{m.name}")
        for _nama, obj in vars(mod).items():
            if (inspect.isclass(obj) and issubclass(obj, TTSProvider) and obj is not TTSProvider
                    and obj.__module__ == mod.__name__):
                out.append(obj)
    return out


def test_ada_adaptor_yang_diperiksa():
    kelas = _adaptor()
    assert len(kelas) >= 4, f"hanya menemukan {len(kelas)} adaptor — penemuannya rusak"


def test_bentuk_anggota_sama_dengan_kontrak():
    salah = []
    for kelas in _adaptor():
        for nama in _HARUS_PROPERTI:
            anggota = inspect.getattr_static(kelas, nama, None)
            if anggota is None:
                salah.append(f"{kelas.__name__}.{nama} TIDAK ADA")
            elif not isinstance(anggota, property):
                salah.append(f"{kelas.__name__}.{nama} harus @property, kini {type(anggota).__name__}")
        for nama in _HARUS_FUNGSI:
            anggota = inspect.getattr_static(kelas, nama, None)
            if anggota is None:
                salah.append(f"{kelas.__name__}.{nama} TIDAK ADA")
            elif isinstance(anggota, property):
                salah.append(f"{kelas.__name__}.{nama} harus fungsi biasa, kini @property")
    assert not salah, "adaptor menyimpang dari kontrak TTSProvider:\n  " + "\n  ".join(salah)


def test_penanda_dukungan_benar_benar_boolean():
    """`supports_word_timestamps` dibaca sebagai NILAI. Kalau ia metode, nilainya selalu 'benar'."""
    salah = []
    for kelas in _adaptor():
        p = inspect.getattr_static(kelas, "supports_word_timestamps", None)
        if isinstance(p, property):
            try:
                hasil = p.fget(object.__new__(kelas))
            except Exception:
                continue                      # butuh state instance — cukup, bentuknya sudah benar
            if not isinstance(hasil, bool):
                salah.append(f"{kelas.__name__} mengembalikan {type(hasil).__name__}, bukan bool")
    assert not salah, salah
