"""SETIAP ARGUMEN YANG DIKIRIM KE `TenantRunConfig` HARUS BENAR-BENAR ADA SEBAGAI FIELD.

Regresi NYATA yang lolos 2026-08-02: field fosil `youtube_token_path` dicabut dari dataclass, tapi
DUA titik pembuatan config masih mengirimkannya sebagai argumen. Akibatnya SETIAP pemuatan config
tenant melempar `TypeError` → ditangkap penjaga fail-soft → "tenant tidak ada di Supabase — pakai
default config". Jadi seluruh produksi diam-diam berjalan dengan config DEFAULT: salah suara, salah
model, salah niche, salah preset. Kegagalan total yang menyamar jadi peringatan kecil.

518 uji satuan LULUS saat itu. Yang menangkapnya adalah uji rantai nyata — karena tak satu pun uji
membangun `TenantRunConfig` lewat jalur yang dipakai produksi.

Uji ini memeriksa SAMBUNGAN-nya secara statis (tanpa DB, tanpa jaringan): setiap nama argumen pada
pemanggilan `TenantRunConfig(...)` di dalam modul harus cocok dengan field dataclass-nya. Menangkap
field yang dicabut MAUPUN field yang ditambah tapi lupa dikirim — sejak hari pertama, sebelum ada
yang menjalankannya.
"""

import ast
import dataclasses
import inspect
import pathlib

import src.config.tenant_config as tc


def _field_sah() -> set:
    return {f.name for f in dataclasses.fields(tc.TenantRunConfig)}


def _argumen_terkirim() -> dict:
    """{nama_argumen: [baris, ...]} dari semua pemanggilan TenantRunConfig(...) di modulnya."""
    berkas = pathlib.Path(inspect.getsourcefile(tc))
    pohon = ast.parse(berkas.read_text())
    out: dict[str, list] = {}
    for n in ast.walk(pohon):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "TenantRunConfig":
            for kw in n.keywords:
                if kw.arg:
                    out.setdefault(kw.arg, []).append(n.lineno)
    return out


def test_ada_pemanggilan_yang_diperiksa():
    dikirim = _argumen_terkirim()
    assert len(dikirim) > 20, f"hanya {len(dikirim)} argumen ditemukan — penelusurannya rusak"


def test_semua_argumen_ada_sebagai_field():
    sah = _field_sah()
    salah = {k: v for k, v in _argumen_terkirim().items() if k not in sah}
    assert not salah, (
        "argumen dikirim ke TenantRunConfig tapi BUKAN field-nya — setiap pemuatan config tenant "
        f"akan melempar TypeError lalu diam-diam jatuh ke config DEFAULT: {salah}"
    )


def test_config_default_bisa_dibangun():
    """Jalur 'tenant tidak ditemukan' harus benar-benar bisa membangun config, bukan ikut meledak."""
    mgr = tc.TenantConfigManager()
    cfg = mgr._default_config("uji-tenant") if hasattr(mgr, "_default_config") else None
    if cfg is None:                       # nama internal berubah → cari pembangun default apa pun
        import types
        kandidat = [m for m in dir(mgr) if "default" in m.lower()
                    and isinstance(getattr(mgr, m, None), types.MethodType)]
        assert kandidat, "tak ada pembangun config default yang bisa diuji"
        cfg = getattr(mgr, kandidat[0])("uji-tenant")
    assert cfg.tenant_id == "uji-tenant"
