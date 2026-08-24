"""GLADI BERSIH rantai biaya — TANPA menyentuh produksi, TANPA memanggil vendor, TANPA biaya.

KENAPA ADA (owner 25-Agu: *"maksud anda, anda trial error di production server?"*).
Menunggu produksi nyata untuk tahu apakah biaya terhitung = coba-coba di server tenant. Itu tidak
pantas. Yang benar: menjalankan rantai yang SAMA — pencatat biaya → penghitung biaya — memakai
**katalog NYATA** dan **setelan channel tenant yang SESUNGGUHNYA**, dengan jawaban vendor ditiru.

Yang dibuktikan untuk TIAP channel aktif: dengan model naskah/suara/gambar yang benar-benar ia pakai,
satu produksi menghasilkan **angka biaya**, bukan "belum terhitung".

Read-only mutlak: hanya membaca `channels` dan `ai_models`. Nol tulisan, nol panggilan vendor.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from supabase import create_client  # noqa: E402

from src.billing.ai_cost import compute_cost_usd  # noqa: E402
from src.utils import cost_meter  # noqa: E402


def main() -> int:
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    model = {m["model_key"]: m for m in
             sb.table("ai_models").select("model_key,model_id,provider_key,component").execute().data}
    channels = [c for c in sb.table("channels").select(
        "channel_name,is_active,llm_model,llm_library,tts_provider,tts_model,visual_mode"
    ).execute().data if c.get("is_active")]

    print(f"channel AKTIF diperiksa: {len(channels)}\n")
    gagal = []
    for ch in sorted(channels, key=lambda x: x["channel_name"] or ""):
        # ── Model yang SUNGGUH dipakai channel ini ────────────────────────────
        m_llm = model.get(ch.get("llm_model") or "")
        m_tts = model.get(ch.get("tts_model") or "")
        vm = (ch.get("visual_mode") or "")
        m_img = model.get(vm.split(":", 1)[1]) if ":" in vm else None

        # ── Pencatat yang SAMA dengan produksi (jawaban vendor ditiru) ────────
        cost_meter.reset()
        if m_llm:
            # penyedia naskah = channels.llm_library (itulah yang diserahkan adapter)
            cost_meter.add_llm(m_llm["model_id"], 21_000, 6_000,
                               penyedia=ch.get("llm_library") or m_llm["provider_key"])
        if m_tts:
            cost_meter.add_tts(m_tts["model_id"], 1_640, penyedia=ch.get("tts_provider") or
                               m_tts["provider_key"])
            if m_tts["provider_key"] == "gemini":       # vendor ini melaporkan token audio
                cost_meter.add_tts_tokens(m_tts["model_id"], 194, 1_186,
                                          penyedia=ch.get("tts_provider"))
        if m_img:
            cost_meter.add_image(m_img["model_id"], 5, penyedia=m_img["provider_key"])
            cost_meter.add_image_megapiksel(m_img["model_id"], 1024 * 1024,
                                            penyedia=m_img["provider_key"])
            if m_img["provider_key"] in ("openai", "gemini"):   # gambar ber-tagih token
                cost_meter.add_llm(m_img["model_id"], 1_500, 6_400,
                                   penyedia=m_img["provider_key"])

        pakai = cost_meter.summary()
        biaya = compute_cost_usd(pakai, sb=sb) or {}
        belum = biaya.get("unpriced") or []
        tanda = "✅" if (biaya.get("usd") and not belum) else "❌"
        print(f"{tanda} {ch['channel_name']}")
        print(f"     naskah={ch.get('llm_model')} · suara={ch.get('tts_model')} · gambar={vm}")
        print(f"     biaya 1 produksi = ${biaya.get('usd', 0):.6f}  rincian={biaya.get('breakdown')}")
        if belum:
            print(f"     ⚠️ BELUM TERHITUNG: {belum}")
            gagal.append((ch["channel_name"], belum))
        print()

    print("=" * 70)
    if gagal:
        print(f"❌ {len(gagal)} channel aktif biayanya TIDAK terhitung penuh — JANGAN deploy:")
        for nama, b in gagal:
            print(f"   {nama}: {b}")
        return 1
    print(f"✅ {len(channels)} channel aktif: biaya 1 produksi TERHITUNG PENUH, nol yang belum terhitung.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
