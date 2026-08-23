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

    # [2026-08-16] Stempel menyertakan JAM. Uji model video makan >1 menit dan sambungan ke layar
    # putus lebih dulu (insiden Hailuo: mesin 200 OK di detik ke-90, layar sudah menyerah) — layar
    # kini MENUNGGU jejak ini berubah. Stempel bertanggal saja membuat uji ulang di hari yang sama
    # menghasilkan catatan IDENTIK ⇒ penantian itu takkan pernah berakhir.
    stamp_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    # Penanda MULAI, ditulis sebelum vendor dipanggil: dari sinilah layar tahu ujinya benar-benar
    # berjalan (dan kredit sedang terpakai), bukan sekadar permintaannya hilang di jalan.
    _stamp_audit(sb, model_key, f"SEDANG DIUJI sejak {stamp_date} (uji manual admin)")
    try:
        if comp == "llm":
            from src.providers.llm import build_llm_provider
            from src.providers.llm.base import parse_json_lenient
            from src.config import ambang
            p = build_llm_provider({"llm_library": pk, "llm_model": model_id, "llm_api_key": key})
            # ── [F6, 23-Agu] UJI SEKELAS PRODUKSI ────────────────────────────────────────────
            # Sebelumnya: `user="Reply with exactly one word: OK"`, 512 token, TANPA as_json.
            # Terukur 23-Agu: 4 dari 6 model APIMaster LULUS panggilan pendek itu lalu GAGAL pada
            # perintah naskah sesungguhnya — jawabannya terpotong di batas keluaran, JSON gugur.
            # Artinya lencana "✓ Teruji" bisa BOHONG, dan gerbang aktivasi (migr 0208) yang
            # menegakkan stempel audit ikut tertipu: tenant yang memilih model itu menabrak dinding
            # di produksi pertamanya.
            #
            # Yang diuji sekarang = KONTRAK YANG SAMA yang diandalkan seluruh jalur naskah:
            # `as_json=True` + jatah token sebesar jatah TERBESAR produksi + hasilnya wajib bisa
            # diurai oleh parser yang SAMA dengan produksi (`parse_json_lenient`). Jatah token
            # bawaannya 2000 = jatah terbesar `script_engine`; ia kenop admin (bukan angka mati),
            # dan penjaga uji menolak bila bawaan ini turun di bawah jatah produksi.
            # Biaya: satu panggilan berjatah 2000 token keluaran — masih receh untuk model naskah,
            # tapi memang lebih mahal dari uji lama; itu harga dari lencana yang tidak berbohong.
            jatah = ambang.angka("uji_model_max_tokens", 2000)
            out = p.complete(
                system="You are a professional viral video scriptwriter. Reply with JSON only.",
                user=('Tulis satu paragraf naskah video pendek berbahasa Indonesia, sekitar 90 kata, '
                      'bertema "pagi di pasar tradisional". Balas HANYA JSON: {"text": "..."}'),
                model=model_id, max_tokens=jatah, temperature=1.0, as_json=True)
            try:
                teks = str((parse_json_lenient(out) or {}).get("text") or "").strip()
            except Exception as pe:
                teks = ""
                logger.info(f"[model_tester] {model_key}: balasan tak bisa diurai jadi JSON: {pe}")
            ok = bool(teks)
            if ok:
                result = (f"LULUS — menjawab JSON yang bisa dipakai produksi "
                          f"({len(teks.split())} kata): {teks[:60]}…")
            else:
                # Sebab dipisah supaya admin tahu tindakannya: balasan KOSONG ≠ balasan yang ADA
                # tapi tak bisa dipakai (batas keluaran model terlalu rendah untuk naskah kita).
                result = ("GAGAL — balasan kosong (jatah token habis untuk nalar internal model)"
                          if not (out or "").strip() else
                          f"GAGAL — model menjawab tapi hasilnya TAK BISA DIPAKAI produksi: bukan "
                          f"JSON utuh (kemungkinan batas keluaran model lebih kecil dari jatah "
                          f"naskah {jatah} token). Cuplikan: {str(out)[:80]}…")

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
            # [B6] F4 (2026-07-15, teguran owner): generator video kini AKTIF — uji nyata via adapter
            # produksi (model_row injection = model nonaktif pun bisa diuji, pola sama image).
            # ⚠ BERBAYAR ke vendor: klip durasi TERKECIL yang diizinkan model (clip_durations=[1.0]
            # → _choose_duration ambil opsi minimum; mis. Hailuo 6s≈$0.27 · Kling 5s≈$0.35 · Veo 8s≈$0.80).
            from src.providers.visual.ai_video import AIVideoProvider
            p = AIVideoProvider({"visual_provider": f"ai_video:{model_key}", "visual_api_key": key,
                                 "model_row": {"provider_key": pk, "model_id": model_id, "component": comp,
                                               "default_params": m.get("default_params") or {}}})
            with tempfile.TemporaryDirectory() as td:
                clips = asyncio.run(p.fetch_clips(
                    keywords=["A single red balloon drifting slowly over a calm sea at golden hour, "
                              "gentle cinematic camera drift, photorealistic, vertical 9:16, no text, no logos"],
                    count=1, output_dir=Path(td), clip_durations=[1.0]))
                ok = bool(clips) and clips[0].duration > 0
                _d = clips[0].duration if clips else 0.0
                _mb = clips[0].file_size_mb if clips else 0.0
            result = f"LULUS — klip {_d:.1f}s ({_mb}MB) dihasilkan (berbayar ke vendor)" if ok else "GAGAL — klip kosong"
        else:
            return {"ok": False, "error": f"Jenis komponen tak dikenal: {comp}"}
    except Exception as e:
        note = f"GAGAL uji manual admin {stamp_date}: {str(e)[:160]}"
        _stamp_audit(sb, model_key, note)
        logger.warning(f"[model_tester] {model_key} GAGAL: {e}")
        # ── [22-Agu] JALUR UJI DISAMBUNGKAN KE KARANTINA (perintah owner) ──────────────────────
        # Pemicu: `gemini-2.5-flash` diuji dan Google menjawab "no longer available to new users"
        # — frasa itu PERSIS kata-global B1 milik karantina. Tapi karantina tak menyala, karena ia
        # hanya tersambung ke jalur PRODUKSI. Jalur uji berhenti di `cost_hint.audit`, dan modelnya
        # tetap ditawarkan ke tenant sampai admin mematikannya sendiri.
        # ⇒ Dua pintu lagi untuk bukti yang SAMA — kelas cacat 17-Agu (AI_ERROR_MGMT §9b).
        #
        # Penilaiannya TIDAK diulang di sini: ambang A + (B1|B2|B3) sudah ada di `karantina_model`
        # dan sudah dijaga uji. Menyalinnya ke sini = dua sumber kebenaran untuk "apakah model mati".
        # `dasar` diambil dari galat yang SESUNGGUHNYA (adapter mengisinya), tidak dipatok — uji bisa
        # gagal karena kunci salah / kuota habis / jaringan, dan itu BUKAN bukti model mati.
        # Yang dinilai = galat vendor apa adanya (`str(e)`), bukan `note` yang KAMI rakit: kata
        # seperti "no longer available" hanya hidup di jawaban vendor.
        # FAIL-SOFT MUTLAK: karantina adalah pembelajaran katalog, bukan jalur kerja. Kegagalannya
        # haram membuat admin melihat "uji gagal" padahal ujinya sendiri sudah menjawab.
        try:
            from src.orchestrator.karantina_model import karantina
            karantina(sb, model_key, getattr(e, "dasar", "") or "", str(e))
        except Exception as ke:
            logger.warning(f"[model_tester] penilaian karantina gagal — non-fatal: {ke}")
        return {"ok": False, "error": str(e)[:220]}

    _stamp_audit(sb, model_key, f"{'LULUS' if ok else 'GAGAL'} uji manual admin {stamp_date}")
    if used_pool and ok:
        result += " (memakai kunci Test Lab)"
    return {"ok": ok, "result": result} if ok else {"ok": False, "error": result}
