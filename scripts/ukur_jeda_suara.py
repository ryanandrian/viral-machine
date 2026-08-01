#!/usr/bin/env python3
"""Ukur biaya jeda per tanda baca untuk SATU atau BEBERAPA suara — alat operasional.

KENAPA MANUAL, BUKAN OTOMATIS
Alat ini MEMANGGIL penyedia suara. Untuk ElevenLabs/fal itu uang tenant/owner, jadi ia tidak pernah
dijalankan sendiri oleh pemeliharaan berkala — hanya saat seseorang memintanya. Edge gratis.

KAPAN DIPAKAI
  • suara BARU dipakai channel dan `tts_pace_calibration`-nya masih kosong → ramalan durasi memakai
    angka bawaan yang bisa meleset jauh (sebaran antar-suara: jeda kalimat 0,85–1,37 dtk);
  • setelah `voice_catalog.default_settings` sebuah suara diubah (laju berubah = seluruh angkanya basi);
  • saat menambah penyedia suara baru.

DUA CARA, dipilih otomatis menurut sifat penyedianya:
  1. PASANGAN TERKONTROL — lima versi teks ber-HURUF IDENTIK yang hanya berbeda tandanya. Dipakai
     untuk penyedia yang deterministik (Edge: sebaran antar-teks ±0,05 dtk).
  2. PENANDA WAKTU — jarak antar-kata di DALAM satu render. Wajib untuk penyedia yang TIDAK
     deterministik (ElevenLabs: `stability` 0,3 membuat prosodinya diambil sampel tiap render, dan
     cara (1) menghasilkan nilai koma −0,244…+0,505 dtk — separuhnya negatif).

Pemakaian:
    python3 scripts/ukur_jeda_suara.py id-ID-ArdiNeural en-US-JennyNeural
    python3 scripts/ukur_jeda_suara.py --lihat            # tampilkan keadaan sekarang, nol biaya
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv

load_dotenv(str(Path(__file__).resolve().parent.parent / ".env"))
from supabase import create_client

from src.production.pause_probe import simpan_jeda, ukur_jeda


def _sb():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def lihat(sb) -> None:
    """Keadaan kalibrasi tiap suara — nol panggilan penyedia, nol biaya."""
    vc = (sb.table("voice_catalog").select("voice_key,provider_key,locale,is_active")
            .eq("is_active", True).order("provider_key").execute().data or [])
    pc = {r["voice_key"]: r for r in
          (sb.table("tts_pace_calibration").select("voice_key,pause_source,sec_per_char,sample_n")
             .eq("niche", "*").execute().data or [])}
    dipakai = {r["voice_key"] for r in
               (sb.table("channels").select("voice_key").not_.is_("voice_key", "null")
                  .execute().data or []) if r.get("voice_key")}
    print(f"{'suara':30}{'penyedia':12}{'dipakai channel':17}{'jeda':12}{'huruf':10}{'sampel':>7}")
    for v in vc:
        k = pc.get(v["voice_key"]) or {}
        print(f"  {v['voice_key'][:27]:28}{v['provider_key'][:10]:12}"
              f"{('YA' if v['voice_key'] in dipakai else '-'):17}"
              f"{(k.get('pause_source') or 'belum'):12}"
              f"{('ada' if k.get('sec_per_char') else 'bawaan'):10}{str(k.get('sample_n') or 0):>7}")
    print("\n'jeda: measured' = biaya jeda DIUKUR langsung · 'fitted' = hasil regresi · "
          "'belum' = memakai angka bawaan.")


def ukur(sb, daftar: list[str]) -> int:
    vc = {r["voice_key"]: r for r in
          (sb.table("voice_catalog")
             .select("voice_key,provider_key,locale,default_settings,vendor_voice_id")
             .in_("voice_key", daftar).execute().data or [])}
    gagal = 0
    for vk in daftar:
        row = vc.get(vk)
        if not row:
            print(f"⛔ {vk}: tidak ada di voice_catalog"); gagal += 1; continue
        cfg = {"tts_voice": row.get("vendor_voice_id") or vk, "niche": "probe",
               "tts_voice_default_settings": row.get("default_settings") or {},
               "tts_voice_settings": {}}
        # kunci & model hanya perlu untuk penyedia berbayar
        if row["provider_key"] in ("elevenlabs", "fal", "openai_tts"):
            from src.utils.crypto import decrypt
            akun = (sb.table("tenant_ai_accounts").select("key_enc")
                      .eq("provider_key", "elevenlabs" if row["provider_key"] == "elevenlabs"
                          else row["provider_key"]).eq("status", "valid").limit(1).execute().data or [])
            if not akun:
                print(f"⛔ {vk}: tak ada kunci {row['provider_key']} berstatus valid"); gagal += 1; continue
            cfg["tts_api_key"] = decrypt(akun[0]["key_enc"])
            m = (sb.table("ai_models").select("model_id").eq("provider_key", row["provider_key"])
                   .eq("component", "tts").eq("is_active", True).order("sort_order")
                   .limit(1).execute().data or [])
            if not m:
                print(f"⛔ {vk}: katalog ai_models tak punya model TTS aktif untuk "
                      f"{row['provider_key']}"); gagal += 1; continue
            cfg["tts_model"] = m[0]["model_id"]
            print(f"⚠ {vk}: penyedia BERBAYAR — pengukuran ini memakai kuota {row['provider_key']}.")

        print(f"\n=== {vk} ({row['provider_key']}, {row.get('locale')}) ===", flush=True)
        h = ukur_jeda(vk, row["provider_key"], cfg, sb=sb, lang=row.get("locale") or "id")
        if not h.get("ok"):
            print(f"  GAGAL: {h.get('error')}")
            if h.get("dibuang"):
                print(f"  tanda yang ditolak: {h['dibuang']}")
            if h.get("catatan_ts"):
                print(f"  jalur penanda waktu: {h['catatan_ts']}")
            gagal += 1
            continue
        for d in h["rincian"]:
            print("   ", d)
        # Metode per-tanda ditampilkan APA ADANYA: dua jalur pengukuran boleh bercampur dalam satu
        # suara (penyedia tak-deterministik sering hanya lolos di jalur penanda waktu), dan operator
        # berhak tahu angka mana datang dari mana — bukan sekadar "terukur".
        _met = h.get("metode") or {}
        for k, v in h["nilai"].items():
            print(f"  {k:20} {v:<10} ← {_met.get(k, 'pasangan_terkontrol')}")
        if h.get("dibuang"):
            print(f"  ditolak jalur pertama: {h['dibuang']}")
        if h.get("catatan_ts"):
            print(f"  jalur penanda waktu: {h['catatan_ts']}")
        print(f"  NILAI: {h['nilai']} (dari {h['n_teks']} teks)")
        simpan_jeda(sb, vk, h["nilai"], h["n_teks"])
        print("  ✔ tersimpan")
    return gagal


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("suara", nargs="*", help="voice_key yang mau diukur")
    ap.add_argument("--lihat", action="store_true", help="tampilkan keadaan kalibrasi (nol biaya)")
    a = ap.parse_args()
    sb = _sb()
    if a.lihat or not a.suara:
        lihat(sb)
        if not a.suara:
            print("\nSebutkan voice_key untuk mengukur. Contoh:\n"
                  "  python3 scripts/ukur_jeda_suara.py id-ID-ArdiNeural")
        return 0
    return 1 if ukur(sb, a.suara) else 0


if __name__ == "__main__":
    raise SystemExit(main())
