"""Uji-NYATA satu model katalog lewat adapter produksi (menegakkan butir-1: aktif = terbukti jalan).

Dipanggil endpoint admin `/api/admin/catalog/test-model`. Menjalankan panggilan MINIMAL nyata ke vendor
memakai KUNCI UJI yang admin tempel (TIDAK disimpan). Vendor tanpa-kunci (auth_type='none', mis. edge)
diuji tanpa kunci. Hasil (LULUS/GAGAL+alasan) di-stamp ke ai_models.cost_hint.audit (jejak permanen).

Sync (dipanggil via run_in_threadpool dari endpoint async) — pakai asyncio.run untuk adapter async.
"""
from __future__ import annotations
import os, asyncio, tempfile
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger


def _service_sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _stamp_audit(sb, model_key: str, note: str) -> None:
    """Merge cost_hint.audit (pertahankan kunci lain)."""
    try:
        row = sb.table("ai_models").select("cost_hint").eq("model_key", model_key).single().execute().data or {}
        ch = row.get("cost_hint") or {}
        ch["audit"] = note
        sb.table("ai_models").update({"cost_hint": ch}).eq("model_key", model_key).execute()
    except Exception as e:
        logger.warning(f"[model_tester] stamp audit gagal {model_key}: {e}")


def test_model(model_key: str, key: str = "") -> dict:
    """Return {ok, result|error}. SYNC — panggil via run_in_threadpool dari FastAPI."""
    key = (key or "").strip()
    sb = _service_sb()
    m = (sb.table("ai_models").select("model_key,model_id,component,provider_key,default_params")
         .eq("model_key", model_key).limit(1).execute().data or [])
    if not m:
        return {"ok": False, "error": "Model tidak ditemukan di katalog."}
    m = m[0]
    comp, model_id, pk = m["component"], (m.get("model_id") or model_key), m["provider_key"]
    prov = (sb.table("ai_providers").select("auth_type,is_active").eq("provider_key", pk).limit(1).execute().data or [{}])[0]
    if not prov.get("is_active"):
        return {"ok": False, "error": f"Provider '{pk}' non-aktif — aktifkan dulu sebelum uji."}
    needs_key = (prov.get("auth_type") == "api_key")
    used_pool = False
    if needs_key and not key:
        # A6 (owner 2026-07-08): kunci kosong → coba kunci Test Lab (pool admin_test_internal, key_group vendor).
        try:
            kg = (sb.table("ai_providers").select("key_group").eq("provider_key", pk).limit(1).execute().data or [{}])[0].get("key_group") or pk
            acc = (sb.table("tenant_ai_accounts").select("key_enc").eq("tenant_id", "admin_test_internal")
                   .eq("key_group", kg).eq("status", "valid").limit(1).execute().data or [])
            if acc:
                from src.utils.crypto import decrypt
                key = decrypt(acc[0]["key_enc"]); used_pool = True
        except Exception as e:
            logger.warning(f"[model_tester] baca kunci Test Lab gagal: {e}")
    if needs_key and not key:
        return {"ok": False, "error": "Provider ini butuh API token — tempel token uji (tidak disimpan), atau simpan kunci vendor ini di Test Lab."}

    stamp_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        if comp == "llm":
            from src.providers.llm import build_llm_provider
            p = build_llm_provider({"llm_library": pk, "llm_model": model_id, "llm_api_key": key})
            out = p.complete(system="", user="Reply with exactly one word: OK", model=model_id, max_tokens=16, temperature=0)
            ok = bool(out and out.strip())
            result = f"LULUS — model menjawab: {out.strip()[:50]}" if ok else "GAGAL — balasan kosong"

        elif comp == "tts":
            from src.providers.tts import build_tts_provider
            vc = (sb.table("voice_catalog").select("voice_key").eq("provider_key", pk)
                  .eq("is_active", True).limit(1).execute().data or [])
            voice = vc[0]["voice_key"] if vc else None
            p = build_tts_provider(pk, {"tts_api_key": key, "tts_model": model_id, "tts_voice": voice})
            tmp = Path(tempfile.mkstemp(suffix=".mp3")[1])
            try:
                asyncio.run(p.generate("This is a short voice test.", tmp))
                sz = tmp.stat().st_size if tmp.exists() else 0
            finally:
                if tmp.exists(): tmp.unlink()
            ok = sz > 0
            result = f"LULUS — audio dihasilkan ({sz} byte)" if ok else "GAGAL — audio kosong"

        elif comp == "image":
            from src.providers.visual.ai_image import AIImageProvider
            # model_row diinjeksi langsung dari baris DB (tanpa filter aktif) — model nonaktif
            # HARUS bisa diuji sebelum aktivasi; get_models() produksi = aktif-only (telur-ayam).
            p = AIImageProvider({"visual_provider": f"ai_image:{model_key}", "visual_api_key": key, "image_quality": "low",
                                 "model_row": {"provider_key": pk, "model_id": model_id, "component": comp,
                                               "default_params": m.get("default_params") or {}}})
            tmp = Path(tempfile.mkstemp(suffix=".png")[1])
            try:
                asyncio.run(p._generate_image("a simple red circle centered on a plain white background", "", tmp))
                sz = tmp.stat().st_size if tmp.exists() else 0
            finally:
                if tmp.exists(): tmp.unlink()
            ok = sz > 0
            result = f"LULUS — gambar dihasilkan ({sz} byte)" if ok else "GAGAL — gambar kosong"

        elif comp == "video":
            return {"ok": False, "error": "Uji video belum didukung (generator video belum aktif)."}
        else:
            return {"ok": False, "error": f"Jenis komponen tak dikenal: {comp}"}
    except Exception as e:
        note = f"GAGAL uji manual admin {stamp_date}: {str(e)[:160]}"
        _stamp_audit(sb, model_key, note)
        logger.warning(f"[model_tester] {model_key} GAGAL: {e}")
        return {"ok": False, "error": str(e)[:220]}

    _stamp_audit(sb, model_key, f"{'LULUS' if ok else 'GAGAL'} uji manual admin {stamp_date}")
    if used_pool and ok:
        result += " (memakai kunci Test Lab)"
    return {"ok": ok, "result": result} if ok else {"ok": False, "error": result}
