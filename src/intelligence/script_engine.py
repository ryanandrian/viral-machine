"""
Script Engine v0.3.2 — Fase 6C
Fixes:
  - Pattern interrupt: tidak ada contoh verbatim yang bisa di-copy
  - Retry prompt: menyertakan weak areas dari analyzer sebagai feedback
  - Threshold: dibaca dari Supabase (sekarang 82 untuk ryan_andrian)
  - CLIMAX: instruksi emosi eksplisit — cause, don't describe
  - CTA: chemistry-first, zero explicit CTA verbs
  - Retry feedback: skor per dimensi + teknik konkret per area lemah
"""

import os, json, re, time
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, get_niches, system_config
from src.content import beats as _beats   # SATU SUMBER kosakata beat (0128)

# Teknik perbaikan konkret per dimensi — dikirim ke LLM saat retry.
# Harus actionable dan spesifik, bukan saran generik.
DIMENSION_RETRY_GUIDANCE = {
    "emotional_peak": (
        # Generic fallback — dipakai hanya jika niche_profile tidak tersedia.
        # Normalnya diganti oleh _build_emotional_peak_guidance(niche_profile).
        "Do NOT describe the emotion — CAUSE it. Rewrite the CLIMAX so the viewer "
        "feels the final stage of this niche's emotion arc physically. "
        "Choose the technique that serves THIS specific topic: scale contrast, reversal, "
        "or infinite implication. Test: read aloud alone. If you don't feel it — rewrite."
    ),
    "cta_strength": (
        "Delete everything. Rewrite the CTA as a thought, not a request. "
        "NEVER use: follow, subscribe, like, hit, smash, or any imperative verb. "
        "Choose one: (1) A question so specific to this topic they cannot answer it alone. "
        "(2) A statement that implies something is coming that changes what they just learned. "
        "(3) A perspective shift that makes the viewer feel they now belong to a group that "
        "sees the world differently. Following should feel like THEIR idea."
    ),
    "hook_power": (
        "Rewrite the hook so it cannot belong to any other video. Use a specific number, "
        "name, or date from THIS topic. The information gap must be so precise that the "
        "viewer's only path forward is to keep watching. "
        "Test: could this hook appear on a different channel's video? If yes — rewrite."
    ),
    "curiosity_gap": (
        "Every section must end mid-thought — with something unresolved that only the next "
        "section answers. Each answer must reveal a deeper question. Cut any sentence that "
        "summarizes, explains, or closes a loop prematurely. "
        "The viewer stopping should feel like leaving a sentence unfinished."
    ),
    "retention_arc": (
        "Cover each sentence. Ask: does the video lose anything without it? "
        "If no — cut it. Every 5 seconds must deliver something new: a fact, a reframe, "
        "or a raised stake. Cut all filler words, all transitions that don't carry new information, "
        "all sentences that repeat what was already said in different words."
    ),
    "information_density": (
        "Replace every vague claim with its specific measurement. "
        "'Very large' → the actual size. 'Long ago' → the exact year. "
        "'Many scientists' → the specific institution or person. "
        "A fact without specificity is an opinion. Specificity is what makes content shareable — "
        "viewers share facts they can quote precisely, not impressions."
    ),
}

def _build_emotional_peak_guidance(niche_profile: dict) -> str:
    """
    Bangun retry guidance emotional_peak dari niche profile Supabase.
    Config-driven — tidak hardcode per niche.
    """
    vp          = niche_profile.get("narration_persona") or niche_profile.get("voice_profile") or {}
    emotion_arc = vp.get("emotion_arc", "").strip()
    target      = niche_profile.get("target_emotion", "").strip()
    style       = vp.get("style", "").strip()

    base = "Do NOT describe the emotion — CAUSE it. Rewrite the CLIMAX to deliver "
    if emotion_arc:
        base += f"the final stage of this arc: '{emotion_arc}'. "
    if target:
        base += f"The viewer must feel: {target}. "
    if style:
        base += f"Technique guidance: {style}. "
    base += (
        "Choose what serves THIS specific topic best: scale contrast, reversal, "
        "or infinite implication. Test: read aloud alone. If you don't feel it — rewrite completely."
    )
    return base


load_dotenv()

_DEFAULT_SECTION_TIMING = _beats.timing_defaults()   # SATU SUMBER (0128) — identik nilai lama

def _get_section_timing(niche: str) -> dict:
    """Load section timing dari tabel niches (Supabase). Fallback ke default jika tidak ada."""
    try:
        niches = get_niches()
        timing = (niches.get(niche) or {}).get("section_timing") or {}
        if timing and all(k in timing for k in _DEFAULT_SECTION_TIMING):
            return timing
    except Exception:
        pass
    return _DEFAULT_SECTION_TIMING.copy()


def _scale_section_timing(section_timing: dict, target_seconds: float) -> dict:
    """Skala proporsional section_timing agar total ≈ target_seconds (Duration Preset).
    Pertahankan rasio antar-section; min 1 dtk/section. Sesuai compression-mapping
    MULTI_FORMAT_STUDIO §3 (skema 8-section TETAP, durasi diskalakan ke preset;
    pengelompokan ke N visual-beat = urusan sisi visual, bukan struktur script)."""
    total = sum(section_timing.values()) or 1
    factor = target_seconds / total
    return {k: max(1, round(v * factor)) for k, v in section_timing.items()}


def _get_profile(niche: str) -> dict:
    """
    Load narration_persona dari niche registry (Supabase-driven, no hardcode).
    Jika narration_persona belum diisi admin, derive dari base fields niche.
    """
    niches     = get_niches()
    niche_data = niches.get(niche)
    if not niche_data:
        # F-2 audit atribusi (§3.3, owner 2026-07-15): dulu SUBSTITUSI SENYAP ke niche aktif pertama
        # → konten niche LAIN diproduksi diam-diam. Kini gagal jujur (run stop + Telegram).
        from src.exceptions import LLMError
        raise LLMError(f"Niche '{niche}' tidak ditemukan di registry — run dihentikan (no-fallback §3.3).",
                       step="script")

    vp = niche_data.get("narration_persona") or niche_data.get("voice_profile") or {}

    # Jika admin belum isi narration_persona, derive dari base fields
    if not vp.get("tone"):
        style          = niche_data.get("style", "engaging and informative")
        target_emotion = niche_data.get("target_emotion", "curiosity and wonder")
        vp = {
            "tone":        f"engaging narrator with {style} delivery",
            "style":       f"builds toward {target_emotion}, specific and concrete",
            "avoid":       "generic phrases, weak openers, filler words, vague claims",
            "hook_style":  "impossible_claim or question",
            "emotion_arc": f"curiosity → interest → {target_emotion}",
        }
        logger.debug(f"[ScriptEngine] narration_persona '{niche}' derived dari base fields")

    return vp


def _build_system_prompt():
    return (
        "You are a world-class short-form video scriptwriter. "
        "Your scripts go viral because every second stops the scroll, triggers curiosity, "
        "and makes viewers feel something real. "
        "You follow structural instructions precisely while sounding completely natural and original. "
        "Every line you write is specific to the topic — never generic, never templated. "
        "You ONLY respond with valid JSON. No markdown, no explanation, no text outside the JSON."
    )


def _build_insights_block(insights: dict) -> str:
    """
    Format channel_insights menjadi blok instruksi untuk prompt ScriptEngine.
    Hanya dipanggil jika grade != insufficient_data.
    """
    lines = ["CHANNEL PERFORMANCE INSIGHTS — This channel's real data. Apply these learnings:"]

    top_hooks = insights.get("top_hooks", [])
    if top_hooks:
        lines.append("TOP PERFORMING HOOKS from this channel (highest engagement — study these patterns):")
        for i, h in enumerate(top_hooks[:3], 1):
            # Kunci sesuai yang DISIMPAN PerformanceAnalyzer._compute_top_hooks: pattern/avg_view_pct/views.
            # CTR per-video tak tersedia YouTube API (selalu 0) → pakai retensi+views (sinyal nyata).
            pattern = h.get("pattern", "")
            ret     = h.get("avg_view_pct", 0) or 0
            views   = h.get("views", 0) or 0
            text    = h.get("hook", "")[:80]
            lines.append(f"  {i}. \"{text}\" | Pattern: {pattern} | Retention: {ret:.0f}% | Views: {views:,}")

    ct_perf_raw = insights.get("content_type_perf", {})
    # content_type_perf dari PerformanceAnalyzer adalah dict {ct_name: {...}}
    if isinstance(ct_perf_raw, dict):
        ct_perf = sorted(
            [{"content_type": k, **v} for k, v in ct_perf_raw.items()],
            key=lambda x: x.get("avg_view_pct", 0),
            reverse=True,
        )
    else:
        ct_perf = ct_perf_raw
    if ct_perf:
        lines.append("CONTENT TYPES ranked by audience retention:")
        for ct in ct_perf[:3]:
            lines.append(
                f"  - {ct.get('content_type','?')}: "
                f"retention {ct.get('avg_view_pct',0):.0f}% | "
                f"avg views {ct.get('avg_views',0):,.0f}"
            )

    # avoid_patterns adalah list[str] dari PerformanceAnalyzer
    avoid_patterns = insights.get("avoid_patterns", [])
    if isinstance(avoid_patterns, list) and avoid_patterns:
        lines.append("AVOID — these content types underperform on this channel:")
        for p in avoid_patterns[:3]:
            lines.append(f"  - {p}")

    return "\n".join(lines)


# ── Compression-mapping (MULTI_FORMAT §3): N beat per preset = visual_beats = jumlah scene = QC clip.
# 8s=1 (ai_video, di luar image-sequence). Image-sequence: 3..9 beat. Tiap beat = 1 seksi narasi + 1 scene.
# SATU SUMBER (0128): kosakata beat dari src.content.beats (DB content_beats + fallback konstanta identik).
# Dulu 5 dict tersebar di sini + core_facts_2 mati. Nilai turunan IDENTIK (bukti derive==current).
_BEAT_WEIGHT   = _beats.weights()
_ROLE_LABEL    = _beats.labels_upper()
# kata per kalimat alami (median naskah nyata) — satu sumber: duration_model.BAWAAN
from src.production.duration_model import BAWAAN as _DUR_BAWAAN
_WPS_KAL_BAWAAN = _DUR_BAWAAN["words_per_sentence"]
_ALL_SECTIONS  = _beats.all_beats()


def _active_beats(n_beats: int) -> list:
    return _beats.beats_for_n(n_beats)


def _beats_for_preset(preset_seconds) -> list:
    """Beat aktif (SEGMENTASI) preset = SINGLE-SOURCE dari DB `duration_presets.beats`
    (konsisten dgn panel tenant/admin); fallback `_BEATS_FOR_N` bila DB kosong (pra-migrasi/legacy).
    Validasi: hanya key beat dikenal (_BEAT_WEIGHT)."""
    from src.config.format_catalog import preset_beats, preset_visual_beats
    db = preset_beats(preset_seconds)
    if db:
        known = [b for b in db if b in _BEAT_WEIGHT]
        if known:
            return known
    return _active_beats(int(preset_visual_beats(preset_seconds)))


def _distribute_words(active: list, total_words: int) -> dict:
    tot = sum(_BEAT_WEIGHT.get(b, 5) for b in active) or 1
    return {b: max(5, round(total_words * _BEAT_WEIGHT.get(b, 5) / tot)) for b in active}


def _script_len_tol() -> float:
    """[DURASI-F3] Toleransi panjang naskah SATU-SUMBER — menggantikan 6 angka terpatri yang saling
    bertentangan (prompt ±10%, rentang legacy −8/+12%, plafon beat +15%, gerbang length_ok ±10%).
    Sumber: env `SCRIPT_LENGTH_TOLERANCE` (dihidupkan dari config-mati; default 0.12) DIPAGARI
    `min(·, QC_DURATION_TOLERANCE)` — target internal TIDAK PERNAH lebih longgar dari penggaris QC
    produksi (satu knob, satu kebenaran; akar insiden 'tiga penggaris beda' 2026-07-15)."""
    try:
        s = float(os.getenv("SCRIPT_LENGTH_TOLERANCE", "0.12"))
    except Exception:
        s = 0.12
    try:
        q = float(os.getenv("QC_DURATION_TOLERANCE", "0.15"))
    except Exception:
        q = 0.15
    return max(0.02, min(s, q))


# ── Rincian tanda-jeda dari TEKS (satu sumber: duration_model) ────────────────────────────────────
# Estimator lama beserta benih jedanya DIBUANG 2026-07-31. Isinya: `kata ÷ (delivery_wps × 1,10) +
# Σ jeda_benih` dengan benih em_dash 0,55 · ellipsis 0,75 · sentence 0,35 · comma 0,12 — angka yang
# komentar aslinya sendiri tandai "SEED ... kalibrasi per provider → DB", dan kalibrasi itu hanya
# pernah dikerjakan untuk `delivery_wps`, TIDAK untuk angka jedanya. Diuji pada 60 render naskah
# produksi: salah rata-rata 7,01 dtk (10% akurat ±2 dtk). Terukur, jeda akhir-kalimat yang benar
# 0,60–1,31 dtk dan elipsis 0,80–1,38 dtk — benihnya ~3x terlalu kecil, dan selisih itu ditambal
# dengan MEMPERLAMBAT SUARA (41% render mentok di batas 0,70). Penggantinya `duration_model`.
#
# `solve_speed_for_duration` juga dibuang bersamanya: fungsinya menghitung pengali kecepatan suara
# agar taksiran mendarat — tuas yang dilarang owner 2026-07-29.


def _count_pauses(text: str) -> dict:
    """Hitung token-jeda dari TEKS. Delegasi ke `duration_model.ciri_teks` agar angka di sini IDENTIK
    dengan yang dipakai meramal durasi (dulu dua implementasi terpisah = risiko drift senyap).
    Bentuk keluarannya dipertahankan (dipakai kolom `tts_delivery_samples.pause_counts`)."""
    from src.production.duration_model import ciri_teks
    f = ciri_teks(text)
    return {"em_dash": f["em_dash"], "ellipsis": f["ellipsis"], "sentence": f["sentence"],
            "comma": f["comma"], "digits": f["digits"], "linebreak": (text or "").count("\n")}


# ── PUTARAN PERBAIKAN NASKAH ("refit") ────────────────────────────────────────────────────────────
# Kenapa ini ada: terukur, LLM hanya memenuhi 63–75% anggaran kata (preset 60s: diminta 149, ditulis
# 111 · preset 90s: diminta 228, ditulis 144), dan mengulang generate dari nol tidak memperbaikinya —
# goyangan antar-produksi ±12–39%. Yang berhasil: menyuruh model MEMPERBAIKI naskahnya sendiri dengan
# selisih yang PERSIS, sambil KODE memverifikasi tak ada fakta yang hilang.
#
# Terbukti (14 naskah, 7 preset × 2 niche): tanpa langkah ini 5/6 mendarat; dengan langkah ini 14/14
# mendarat, fakta utuh 14/14, rata-rata 1,0 putaran. Bukti: QC_CONTENT_ARCHITECTURE.md §2c.
#
# Kenapa MODEL yang memangkas, bukan kode: diuji dan GAGAL — aturan buatan-tangan tidak bisa
# membedakan fakta terkuat dari kalimat hiasan (kalimat terkuat sebuah naskah bernilai 0 di semua
# penanda permukaan, sama dengan kalimat berbunga). Kode yang memangkas pernah membuang fakta paling
# mengejutkan sebuah naskah. Jadi: model memilih kata, KODE memverifikasi fakta & durasi.

# Angka TANPA tanda baca yang menempel: pola lama `\d[\d.,]*` menangkap "747," sehingga
# "747" di hasil perbaikan dianggap HILANG → perbaikan sah ditolak (terukur 2026-07-31).
_RX_ANGKA_FAKTA = re.compile(r"\d+(?:[.,]\d+)*")


def _nama_diri(teks: str) -> set:
    """Nama diri = kata berhuruf-besar yang BUKAN kata pertama kalimat (kata pertama selalu besar)."""
    out = set()
    for kal in re.split(r"(?<=[.!?…])\s+", teks or ""):
        for i, w in enumerate(kal.split()):
            b = w.strip("\"'“”‘’()[].,;:!?…—–-")
            if i and len(b) >= 3 and b[0].isupper() and any(ch.islower() for ch in b[1:]):
                out.add(b)
    return out


# Panjang minimum sebuah kata berhuruf-besar untuk dianggap NAMA DIRI. Ada karena terukur: kata biasa
# yang kebetulan berhuruf besar ("Tires") memblokir perbaikan yang sebenarnya sah — satu putaran refit
# terbuang. Nama diri sungguhan cenderung lebih panjang (Neuschwanstein, Mariana, Pajajaran).
_MIN_HURUF_NAMA = 6


def _fakta_hilang(asal: str, baru: str) -> list:
    """Angka/tahun & nama diri yang ADA di naskah asal tapi HILANG di hasil perbaikan.
    Non-kosong = perbaikan DITOLAK: durasi tidak pernah dibeli dengan membuang fakta.

    ANGKA dijaga ketat (satu pun hilang = tolak) — tahun & jumlah adalah fakta yang paling mudah
    diverifikasi dan paling sering menjadi inti naskah. NAMA hanya dijaga bila cukup panjang untuk
    memang berupa nama (lihat `_MIN_HURUF_NAMA`)."""
    hilang = sorted(set(_RX_ANGKA_FAKTA.findall(asal)) - set(_RX_ANGKA_FAKTA.findall(baru)))
    hilang += sorted(n for n in (_nama_diri(asal) - _nama_diri(baru)) if len(n) >= _MIN_HURUF_NAMA)
    return hilang


def _refit_naskah(provider, model, script: dict, beats: list, resep: dict, vonis_awal: dict,
                  maks_putaran: int = 2) -> tuple[dict, list]:
    """Suruh MODEL merapatkan/melengkapi naskahnya sendiri sampai vonis durasi OK.

    Mengembalikan (script, jejak). Script hanya diganti bila perbaikan LULUS verifikasi:
      • semua beat aktif terisi (struktur utuh → prompt gambar & durasi per-beat tetap konsisten)
      • NOL fakta hilang (angka/tahun/nama diri)
      • vonis durasi membaik
    Gagal verifikasi / gagal teknis → naskah ASAL dikembalikan apa adanya (gerbang pipeline yang
    melaporkan jujur). Tidak pernah memaksa.
    """
    from src.production.duration_model import vonis as _vonis_fn
    jejak = []
    kini = dict(script)
    v = vonis_awal
    for putaran in range(1, max(1, int(maks_putaran)) + 1):
        if v["status"] == "ok":
            break
        kurang = v["status"] == "terlalu_pendek"
        cara = ("EXPAND the facts already present — more concrete detail, more specifics. Do NOT add new "
                f"facts you have not already stated, do NOT repeat, do NOT pad with filler. KEEP AT LEAST "
                f"{resep['kalimat']} separate sentences — do NOT merge sentences while lengthening "
                "(merging removes the natural pauses and the video stays too short)."
                if kurang else
                "TIGHTEN: cut redundant words, MERGE sentences that say the same thing (fewer sentence "
                "ends = less silence), delete decoration that adds no information. Never delete a "
                "sentence that carries a fact.")
        isi = {b: (kini.get(b) or "").strip() for b in beats if (kini.get(b) or "").strip()}
        user = (
            f"This video narration must be EXACTLY the right length. It is now "
            f"{len((kini.get('full_script') or '').split())} words in "
            f"{_count_pauses(kini.get('full_script') or '')['sentence']} sentences; it must be "
            f"{resep['kata_min']}–{resep['kata_maks']} words in about {resep['kalimat']} sentences → "
            f"{'ADD' if kurang else 'REMOVE'} about {v['kata_selisih']} words.\n"
            "ABSOLUTE RULES:\n"
            "1. Do NOT lose any FACT: every number, year, person/place name and every event stated must "
            "still be there.\n"
            f"2. How: {cara}\n"
            "3. Do NOT change the first sentence.\n"
            "4. Keep the same language, tone and style. Whole sentences only. NEVER use '...'. "
            "Commas sparingly.\n"
            "5. Return the SAME section keys, nothing else.\n\n"
            f"SCRIPT (JSON):\n{json.dumps(isi, ensure_ascii=False, indent=1)}\n\n"
            "Reply with JSON only, exactly these keys: " + ", ".join(isi)
        )
        # Balasan JSON rusak = coba lagi, JANGAN menghabiskan putaran (terukur: satu "Unterminated
        # string" menghabiskan putaran satu-satunya dan naskah preset 15 dtk tetap kepanjangan).
        hasil = None
        for _c in range(1, int(os.getenv("SCRIPT_REFIT_PARSE_RETRY", "2")) + 1):
            try:
                raw = provider.complete(system="You are a professional video-script editor. Reply with JSON only.",
                                        user=user, model=model, temperature=0.4, max_tokens=2000, as_json=True)
                hasil = json.loads(ScriptEngine._clean_json(ScriptEngine.__new__(ScriptEngine), raw))
                break
            except Exception as e:
                jejak.append(f"putaran {putaran} coba {_c}: balasan rusak ({str(e)[:45]})")
                time.sleep(1)
        if hasil is None:
            break
        baru = {b: (hasil.get(b) or "").strip() for b in isi}
        if any(not baru[b] for b in baru):
            jejak.append(f"putaran {putaran}: DITOLAK — ada bagian yang dikosongkan")
            break
        teks_baru = " ".join(baru[b] for b in beats if b in baru)
        hilang = _fakta_hilang(kini.get("full_script") or "", teks_baru)
        if hilang:
            jejak.append(f"putaran {putaran}: DITOLAK — fakta hilang: {', '.join(hilang[:5])}")
            break
        v_baru = _vonis_fn(teks_baru, resep["_preset"], resep["_tangga"], resep["_overhead"],
                           resep.get("_kalibrasi"))
        jejak.append(f"putaran {putaran}: {v['video_prediksi']:.0f}s → {v_baru['video_prediksi']:.0f}s "
                     f"({v_baru['status']})")
        kini = {**kini, **baru, "full_script": teks_baru}
        v = v_baru
    return kini, jejak


# ── TULIS PER-BAGIAN ("per-beat") ─────────────────────────────────────────────────────────────────
# Kenapa ini ada: terukur, satu panggilan TIDAK sanggup menulis naskah panjang. Plafon satu panggilan
# 372–832 kata di 5 model — tapi yang jauh lebih menentukan: model yang dipakai channel tenant nyata
# menulis JAUH di bawah pesanan (uji rantai penuh 2026-07-31: llama-3.1-8b menulis 37 kata untuk
# preset 90 dtk yang butuh ±206; llama-3.3-70b menulis 62–91 kata untuk preset 60 dtk yang butuh
# 128–166). Meminta ulang dari nol tidak menutupnya — goyangan antar-produksi ±12–39%.
#
# Yang menutupnya: memecah pekerjaan jadi sepotong-sepotong yang setiap model SANGGUP. Satu bagian
# preset 90 dtk hanya ±30 kata — di bawah kemampuan model mana pun. Terbukti di preset 75 & 90:
# naskah per-bagian mendarat di band pada uji 14/14 (QC_CONTENT_ARCHITECTURE.md §2c).
#
# Bagian ditulis BERURUTAN dan tiap bagian melihat bagian sebelumnya, supaya tidak mengulang fakta dan
# alurnya menyambung — dua cacat yang muncul saat bagian ditulis buta satu sama lain.

def _generate_per_beat(provider, model, topic, niche, beats: list, resep: dict,
                       niche_profile: dict | None, content_language: str | None,
                       insights_block: str | None = None) -> dict:
    """Tulis naskah BAGIAN PER BAGIAN. Mengembalikan dict beat→teks + full_script, atau {} bila gagal.

    Dipakai saat satu panggilan terbukti tak sanggup memenuhi panjang (lihat catatan di atas).
    Tiap bagian: target kata & kalimat sendiri (dari BEAT PLAN yang sama), peran yang jelas, DNA niche,
    dan larangan yang sudah terukur mahal (elipsis, mengulang, menyimpulkan sebelum waktunya).
    """
    # Kuota per-bagian membidik TARGET SEBENARNYA (tengah band), TANPA markup.
    # Kenapa tanpa markup: markup pernah dipasang ×1,45 karena tiap bagian under-write ±65%. Begitu
    # tiap bagian MENGOREKSI DIRI ke kuotanya (lihat di bawah), markup jadi DOBEL — terukur: naskah
    # 295 kata untuk preset 75 dtk yang butuh ±180, lalu putaran perbaikan mentok (114→94→92→91 dtk,
    # band 68–82). Memanjangkan itu yang sulit bagi model, dan itu sudah ditangani per-bagian; jadi
    # tak ada lagi alasan meminta lebih dari yang dibutuhkan. Batas atas band tetap jadi plafon keras.
    _mk = float(os.getenv("SCRIPT_PERBEAT_MARKUP", "1.0"))
    _total = min(resep["kata_maks"], max(1, round(resep["kata_bidik"] * _mk)))
    kuota = _distribute_words(beats, _total)
    wpk = max(6.0, float((resep.get("_kalibrasi") or {}).get("words_per_sentence")
                         or _WPS_KAL_BAWAAN))
    dna = ""
    if niche_profile:
        _np = niche_profile.get("narration_persona") or {}
        dna = (f"TONE: {_np.get('tone','')} | STYLE: {_np.get('style','')} | "
               f"AVOID (never use these): {_np.get('avoid','')}")
    lokal = (_content_language_block(content_language) if content_language
             and not str(content_language).lower().startswith("en") else "")
    # blok bahasa produksi menyebut nama-nama kunci JSON naskah utuh → baris itu dibuang di sini,
    # sebab bagian ini membalas kunci lain ({"text": ...}). (Cacat terukur: 3 niche gagal parse.)
    if lokal:
        lokal = "\n".join(l for l in lokal.split("\n")
                          if "JSON KEYS" not in l and "hashtags" not in l and "full_script" not in l
                          and "background_music_mood" not in l and '"title"' not in l)

    hasil, terpakai = {}, []
    for i, b in enumerate(beats):
        w = max(8, int(kuota.get(b, 0)))
        s_t = max(1, round(w / wpk))
        peran = _ROLE_LABEL.get(b, b)
        konteks = ""
        if terpakai:
            konteks = ("ALREADY WRITTEN (do NOT repeat these facts; continue naturally from here):\n"
                       + "\n".join(f"- [{_ROLE_LABEL.get(k, k)}] {v}" for k, v in terpakai) + "\n\n")
        terakhir = (i == len(beats) - 1)
        user = (
            f"NICHE: {niche}\nTOPIC: {topic.get('topic','')}\n"
            + (f"ANGLE: {topic.get('angle','')}\n" if topic.get("angle") else "")
            + (f"{dna}\n" if dna else "")
            + (f"{lokal}\n" if lokal else "")
            + f"\n{konteks}"
            f"Write ONLY the [{peran}] part of this video narration ({i+1} of {len(beats)}).\n"
            f"Length: about {w} words in about {s_t} sentence(s). Count before answering.\n"
            "RULES: whole sentences only · NEVER use '...' (it burns over a second of silence) · "
            "commas sparingly · do not name or number the section · "
            + ("this is the FINAL part: close it in a way that leaves curiosity, no new facts.\n"
               if terakhir else "do NOT conclude or summarise — that belongs to a later part.\n")
            + (f"\n{insights_block}\n" if insights_block else "")
            + '\nReply with JSON only: {"text": "..."}'
        )
        # Jalur ini memakai BANYAK panggilan kecil (satu per bagian) alih-alih satu panggilan besar —
        # dan itu membuatnya rentan THROTTLE penyedia. Terukur pada uji rantai penuh: satu 429/503 dari
        # Groq membatalkan SELURUH naskah. Karena itu throttle & gangguan sesaat DITUNGGU lalu diulang;
        # error non-retryable (kredit habis, kunci ditolak, model dipensiunkan) langsung berhenti —
        # menunggu tak akan menolongnya.
        from src.exceptions import ErrorClass as _EC
        _RETRYABLE = {_EC.RATE_LIMIT, _EC.TRANSIENT, _EC.UNKNOWN}
        teks = ""
        for _coba in range(1, int(os.getenv("SCRIPT_PERBEAT_RETRY", "3")) + 1):
            try:
                raw = provider.complete(system="You are a professional viral video scriptwriter. Reply with JSON only.",
                                        user=user, model=model, temperature=1.0, max_tokens=1200, as_json=True)
                teks = (json.loads(ScriptEngine._clean_json(ScriptEngine.__new__(ScriptEngine), raw)).get("text")
                        or "").strip()
                if teks:
                    break
            except Exception as e:
                _kelas = getattr(e, "error_class", _EC.UNKNOWN)
                if _kelas not in _RETRYABLE:
                    logger.warning(f"[ScriptEngine] per-bagian '{b}' berhenti ({_kelas}): {str(e)[:90]}")
                    return {}
                _jeda = 2 ** _coba
                logger.warning(f"[ScriptEngine] per-bagian '{b}' {_kelas} (coba {_coba}) — tunggu {_jeda}s: "
                               f"{str(e)[:70]}")
                time.sleep(_jeda)
        if not teks:
            logger.warning(f"[ScriptEngine] per-bagian '{b}' balasan kosong")
            return {}
        # ── BETULKAN BAGIAN ITU SEKETIKA, bukan menunggu seluruh naskah selesai ───────────────────
        # Kenapa: terukur, model mengirim ±65% dari pesanan TIAP BAGIAN (8w dari 11 · 24w dari 37 ·
        # 29w dari 40 · 19w dari 37). Memperbaiki setelah semua bagian jadi berarti meminta model
        # menutup selisih BESAR pada naskah panjang — hal yang justru tidak ia sanggupi. Sebaliknya
        # menyuruhnya menambah 15 kata menjadi 30 pada SATU bagian adalah pekerjaan kecil yang pasti
        # bisa. Jadi kekurangan ditutup di tempat ia lahir, sementara masih murah.
        _amb_bagian = float(os.getenv("SCRIPT_PERBEAT_MIN_RASIO", "0.85"))
        if len(teks.split()) < _amb_bagian * w:
            _kurang = w - len(teks.split())
            _up2 = (
                f"{(dna + chr(10)) if dna else ''}"
                f"Perluas naskah bagian [{peran}] berikut menjadi sekitar {w} kata "
                f"(sekarang {len(teks.split())} — tambah ±{_kurang} kata).\n"
                "ATURAN MUTLAK: jangan hilangkan satu fakta pun (angka, tahun, nama, peristiwa) · "
                "perinci fakta yang SUDAH ada, jangan menambah fakta baru · jangan mengulang · "
                f"bahasa & nada persis sama · sekitar {s_t} kalimat · kalimat utuh · TANPA tanda '...'.\n\n"
                f"NASKAH:\n{teks}\n\nBalas JSON saja: {{\"text\": \"...\"}}"
            )
            try:
                _raw2 = provider.complete(system="Kamu editor naskah video profesional. Balas JSON saja.",
                                          user=_up2, model=model, temperature=0.4, max_tokens=1200,
                                          as_json=True)
                _t2 = (json.loads(ScriptEngine._clean_json(ScriptEngine.__new__(ScriptEngine),
                                                           _raw2)).get("text") or "").strip()
                # terima HANYA bila lebih panjang DAN nol fakta hilang — perbaikan tak boleh
                # dibayar dengan isi (pelajaran: kode yang memangkas pernah membuang fakta terkuat)
                if _t2 and len(_t2.split()) > len(teks.split()) and not _fakta_hilang(teks, _t2):
                    logger.info(f"[ScriptEngine] bagian '{b}' dilengkapi {len(teks.split())}→"
                                f"{len(_t2.split())}w (target {w}w)")
                    teks = _t2
                else:
                    logger.info(f"[ScriptEngine] pelengkapan bagian '{b}' DITOLAK "
                                f"(tak lebih panjang / ada fakta hilang) — pakai versi asal")
            except Exception as _e2:
                logger.warning(f"[ScriptEngine] pelengkapan bagian '{b}' gagal: {str(_e2)[:70]}")

        hasil[b] = teks
        terpakai.append((b, teks))
        logger.info(f"[ScriptEngine] per-bagian {i+1}/{len(beats)} [{peran}]: {len(teks.split())}w "
                    f"(target {w}w)")
    hasil["full_script"] = " ".join(hasil[b] for b in beats if hasil.get(b))
    return hasil


def _narrative_intent(target_duration, n_beats) -> str:
    if n_beats <= 3:
        return (f"ULTRA-SHORT {target_duration}s: ONE razor-sharp idea. No setup, no padding — "
                f"hook straight into the single most striking fact, then a resonant close. Every word fights to stay.")
    if n_beats <= 5:
        return (f"SHORT {target_duration}s: a tight arc — hook, the core revelation with hard specifics, a landing. Dense, zero filler.")
    if n_beats <= 7:
        return (f"{target_duration}s: a full short-form arc — build-up, surprising facts, emotional climax. Develop but stay tight.")
    return (f"LONG {target_duration}s: the complete arc — layered mystery, multiple distinct facts, build and release with depth. Zero filler.")


def compute_beat_durations(script: dict, word_timestamps: list | None, audio_duration: float) -> list:
    """Durasi per-beat untuk image-gen + render (1 image per beat). SUMBER TUNGGAL (dipanggil SEKALI di
    pipeline) → dikonsumsi visual_assembler (bake Ken-Burns) DAN renderer (concat) = bake==display=exact
    → sinkron TTS, nol glitch. Dari word_timestamps NYATA (presisi per-beat) bila ada+andal; else proporsi
    jumlah-kata. Total dinormalisasi = audio_duration."""
    beats  = script.get("beats") or _ALL_SECTIONS
    counts = [max(1, len((script.get(b) or "").split())) for b in beats]
    total_w = sum(counts) or 1
    wt = word_timestamps or []
    durs = None
    if wt and len(wt) >= total_w * 0.6:          # cukup andal (ElevenLabs ~98%, edge ~80%)
        durs, idx = [], 0
        for c in counts:
            s_i = min(idx, len(wt) - 1)
            e_i = min(idx + c - 1, len(wt) - 1)
            d = float(wt[e_i].get("end", 0)) - float(wt[s_i].get("start", 0))
            durs.append(max(0.6, d))
            idx += c
    if not durs:                                  # fallback: proporsi jumlah-kata
        durs = [max(0.6, audio_duration * c / total_w) for c in counts]
    tot = sum(durs) or 1
    if audio_duration > 0:                         # normalisasi total = audio_duration (presisi)
        durs = [round(d * audio_duration / tot, 4) for d in durs]
    return durs


def _content_language_block(locale: str | None) -> str:
    """Mandat bahasa KONTEN utk prompt LLM. English/locale kosong → '' (prompt byte-identik dgn
    perilaku lama = NOL regresi channel live). Non-English → blok wajib di posisi atas prompt."""
    from src.intelligence.config import is_english_locale, content_language_name
    if is_english_locale(locale):
        return ""
    name = content_language_name(locale)
    return f"""
🌐 CONTENT LANGUAGE — ABSOLUTE, NON-NEGOTIABLE:
Write EVERY output value in {name} ({locale}): all narration beats, "title", "full_script", and "hashtags".
- Native, idiomatic {name} as written by a top local storyteller — NOT a translation from English.
  No English words except unavoidable proper nouns, brand names, or terms with no natural equivalent.
- Address the viewer directly in natural second person for {name} (the spirit of the "you" rules below).
- Numbers, analogies, and cultural references must feel natural to a {name}-speaking audience.
- JSON KEYS stay in English exactly as specified — only the VALUES are in {name}.
- EXCEPTION: "background_music_mood" stays in English (internal production metadata, never shown to viewers).
"""


def _build_user_prompt(topic, niche, niche_visual_style=None, feedback=None, insights_block=None,
                       preset_seconds=None, format_wps=None, render_overhead_sec=0.0,
                       cta_mode="implicit", brand_name=None, brand_cta_text=None,
                       delivery_p=None, voice_name=None, tts_provider=None,
                       content_language=None, resep_durasi=None):
    """
    Build prompt. Jika feedback ada (dari retry), sisipkan sebagai instruksi perbaikan.
    niche_visual_style: dict dari tabel niches (base_style, color_palette, atmosphere).
    preset_seconds/format_wps: Duration Preset per-channel (MULTI_FORMAT §3). None → perilaku lama.
    cta_mode/brand_name: Branded Content (§6) — 'soft_sell' izinkan SATU sebutan brand halus.
    """
    profile        = _get_profile(niche)   # niche tak dikenal → raise di _get_profile (F-2, no-fallback)
    niches         = get_niches()
    niche_data     = niches.get(niche) or {}   # F-2: {} mustahil pasca guard _get_profile; substitusi dibuang
    section_timing = _get_section_timing(niche)
    # Duration Preset (per-channel, opsional): skalakan timing ke target + WPS per-format (§3).
    # preset_seconds/format_wps None → perilaku lama (timing niche, WPS 2.4). Non-breaking.
    if preset_seconds:
        section_timing = _scale_section_timing(section_timing, preset_seconds)
    WPS             = float(format_wps) if format_wps else 2.4
    target_duration = int(preset_seconds) if preset_seconds else sum(section_timing.values())
    words           = {k: max(4, round(v * WPS)) for k, v in section_timing.items()}
    total_words     = sum(words.values())          # total kata = target_duration × WPS provider terdaftar
    _tol            = _script_len_tol()            # [DURASI-F3] satu-sumber (ganti 0.92/1.12 terpatri)
    _lo, _hi        = round(total_words * (1 - _tol)), round(total_words * (1 + _tol))

    # ── Compression-mapping per-preset (MULTI_FORMAT §3): N beat = visual_beats → narasi + scene + QC.
    from src.config.format_catalog import preset_visual_beats as _pvb
    if preset_seconds:
        # Budget = (detik − overhead render) × WPS. QC mengukur VIDEO FINAL = audio + trailing_silence
        # (+ loop net), jadi target AUDIO = preset − overhead agar video JADI ≈ preset. Tanpa ini, kata
        # in-range pun bisa overshoot di preset pendek (terbukti: 15s 27 kata → 18.2s > window 17.2).
        # ── SATU PENGGARIS (2026-07-31) ────────────────────────────────────────────────────────────
        # Bila resep terkalibrasi ada, ANGKA RENCANA ADEGAN diambil DARI RESEP ITU — bukan dihitung
        # ulang dengan rumus lama `(detik − overhead) × wps` yang BUTA JEDA. Tanpa ini prompt membawa
        # DUA total kata yang bertentangan: rencana adegan bilang satu angka ("MIN dan MAX keduanya
        # batas keras"), blok bentuk bilang angka lain — persis cacat "tiga penggaris" yang pernah
        # melahirkan insiden 2026-07-15. Batas per-adegan pun diturunkan dari BAND SAH (titik-tengah
        # owner), bukan dari toleransi persen.
        # Bobot antar-adegan (`content_beats.weight`) tetap yang membagi total ini ke tiap adegan —
        # jadi kenop admin di Catalog > Durasi tetap berlaku, dan kini justru lebih menentukan karena
        # ia juga menetapkan ukuran tiap panggilan pada jalur tulis-per-bagian.
        if resep_durasi:
            total_words = int(resep_durasi["kata_bidik"])
            _lo, _hi    = int(resep_durasi["kata_min"]), int(resep_durasi["kata_maks"])
        else:
            _spoken = max(1.0, float(preset_seconds) - float(render_overhead_sec or 0))
            total_words = round(_spoken * WPS)
            _lo, _hi    = round(total_words * (1 - _tol)), round(total_words * (1 + _tol))
        active  = _beats_for_preset(preset_seconds)  # SEGMENTASI dari DB (single-source) / fallback _BEATS_FOR_N
        n_beats = len(active)
        words   = _distribute_words(active, total_words)   # konsentrasi budget ke beat aktif (bukan sebar 8)
        n_scenes = len(active)
        inactive = [s for s in _ALL_SECTIONS if s not in active]
        _wsum = sum(words.get(b, 0) for b in active) or 1
        # [DURASI-F3] BEAT PLAN = SATU-SATUNYA otoritas angka (dulu 3 tempat beda nilai → LLM disodori
        # mistar bertentangan). Tiap beat: target + MIN + MAX dari toleransi TUNGGAL (_script_len_tol).
        # MIN per-beat = lantai anti-KEPENDEKAN (akar 85% video pendek — dulu hanya ada plafon +15%).
        # Plafon konkret per-beat jauh lebih dipatuhi LLM daripada total agregat (terbukti preset pendek).
        # + Protokol swa-verifikasi: draft → hitung per-beat → revisi yang meleset → output `_beat_words`.
        # MIN/MAX per-adegan = proporsi BAND SAH (bukan ±persen): rasio band ke total, supaya bila tiap
        # adegan mendarat di rentangnya, TOTALNYA otomatis mendarat di band. Satu penggaris, bukan dua.
        _r_lo = (_lo / total_words) if total_words else (1 - _tol)
        _r_hi = (_hi / total_words) if total_words else (1 + _tol)
        _bmin = lambda w: max(3, round(w * _r_lo))
        _bmax = lambda w: max(_bmin(w) + 1, round(w * _r_hi))
        _plan_lines = "\n".join(
            f"   beat {i+1} — {_ROLE_LABEL.get(b, b)}: target {words.get(b,0)} words (MIN {_bmin(words.get(b,0))} / MAX {_bmax(words.get(b,0))}) — {round(100*words.get(b,0)/_wsum)}%"
            for i, b in enumerate(active))
        beat_plan = (
            f"\n📐 BEAT PLAN — {target_duration}s video = {len(active)} BEATS (compression-mapping, non-negotiable):\n"
            f"{_narrative_intent(target_duration, len(active))}\n"
            f"Write EXACTLY these {len(active)} beats IN ORDER. These are the ONLY word numbers that matter — "
            f"each beat has a BINDING budget (MIN and MAX are both hard limits):\n{_plan_lines}\n"
            f"⚠️ A beat UNDER its MIN makes the video too short and unusable — this is the #1 failure. "
            f"A beat OVER its MAX makes the video overrun. Fill thin beats with CONCRETE substance "
            f"(facts, numbers, names, vivid imagery) — never filler or repetition.\n"
            f"✅ SELF-CHECK before answering (mandatory): draft all beats → COUNT the words of each beat → "
            f"REVISE any beat outside its MIN–MAX → only then output. Report the final per-beat counts in "
            f"`_beat_words` (they must be your real counts, not the targets).\n"
            + (f"Leave these JSON fields as EMPTY string \"\": {', '.join(inactive)}.\n" if inactive else "")
            + (f"Also output field \"core_facts_2\" (a SECOND distinct fact).\n" if "core_facts_2" in active else "")
            + f"The numbered section guide below is your CRAFT TOOLBOX — apply only the active beats' techniques.\n"
        )
        words = {s: words.get(s, 0) for s in _ALL_SECTIONS}   # panduan ber-nomor (1-8) refs semua 8; inactive→0
    else:
        active, n_scenes, beat_plan = list(words.keys()), 6, ""

    feedback_block = ""
    if feedback:
        feedback_block = f"""
QUALITY GATE FAILED — The previous attempt did not reach the threshold.
Rewrite completely from scratch. Do not rephrase — fundamentally rethink each weak dimension.
The previous attempt's structure, phrasing, and approach are now off-limits.

Dimensions that need improvement (with specific techniques to apply):
{chr(10).join(f"  • {w}" for w in feedback)}

Apply each technique above precisely. Fresh thinking only — not a revision of what came before.
"""


    insights_section = ""
    if insights_block:
        insights_section = f"\n{insights_block}\n"

    # Branded Content §6 — soft-sell: izinkan SATU sebutan brand halus di CTA (anti-hard-sell TETAP).
    soft_sell_block = ""
    if cta_mode == "soft_sell" and brand_name:
        soft_sell_block = f"""
SOFT-SELL MODE (anti-hard-sell TETAP berlaku): KHUSUS di bagian CTA, kamu BOLEH menyisipkan
SATU sebutan brand yang HALUS & natural untuk "{brand_name}" — terasa seperti pemikiran tulus,
bukan iklan. Pola contoh (jangan salin mentah, adaptasi ke topik): "… bersama {brand_name}."
DILARANG hard-sell: tanpa "beli", "diskon", "promo", "klik link sekarang", tanpa imperative jualan.
Maksimal SATU sebutan brand di seluruh script.{(' Arahan brand: ' + brand_cta_text) if brand_cta_text else ''}
"""

    # ── Length directive — DUA-SISI + sadar-preset (B2). Ganti blok satu-sisi lama yang seragam
    # ("FEWER=fail / Do NOT be terse / at least lo") — penyebab 15s OVERSHOOT (lawan sinyal ringkas)
    # & 60s UNDERSHOOT (dorongan floor kurang). Preset PENDEK: density=quality, batas-ATAS galak,
    # "bukan asal-pendek". Preset PANJANG/legacy: capai budget dgn fakta spesifik (bukan filler) +
    # batas-atas tetap ada. Terukur: 15s 30w(budget24), 60s 70w(budget97), skor <80 (lihat journal 2026-06-18).
    if preset_seconds and resep_durasi:
        # ── PERINTAH PANJANG BERBASIS ALAT UKUR TERKALIBRASI (2026-07-31) ──────────────────────────
        # Menggantikan blok §10.A "durasi-via-speed". Yang dicabut & sebabnya (terukur, 294 produksi):
        #   • Instruksi `speed` untuk mood → dipakai sistem sebagai TUAS DURASI: 41% render mentok di
        #     batas paling lambat (0,70), NOL render berjalan normal, median 0,81. Mood narasi rusak
        #     DAN durasi tetap meleset (median −4,7 dtk). Owner melarang tuas ini.
        #   • "≈P kata/detik" → angka itu buta-jeda; jeda per kalimat terukur 0,6–1,3 dtk, bukan 0,35.
        # Yang menggantikan: DUA angka dari `duration_model.resep` — jumlah kata DAN jumlah kalimat.
        # Jumlah kalimat wajib ikut diperintahkan karena (a) tiap kalimat memakan jeda nyata, dan
        # (b) terukur model MENAATI perintah jumlah kalimat jauh lebih baik daripada jumlah kata
        # (kalimat bisa dihitung sendiri oleh model; kata tidak).
        # Terbukti: 14/14 naskah lintas 7 preset × 2 niche mendarat di band, fakta utuh 14/14,
        # kecepatan suara 1,0 sepanjang uji (bukti: QC_CONTENT_ARCHITECTURE.md §2c).
        _r = resep_durasi
        if len(active) <= 2:
            _emph = ("⚠️ ULTRA-SHORT: every word must earn its place. ONE razor-sharp idea, densely. "
                     "Going over the word range makes the video overrun and be rejected.")
        else:
            _emph = ("⚠️ UNDER-writing is the #1 cause of failure here: when a beat feels thin, ADD concrete "
                     "substance (a fact, a number, a name) — never stop early, never pad with filler.")
        length_block = (
            "🎙️ THIS SCRIPT WILL BE SPOKEN ALOUD — its LENGTH IS the video's duration.\n"
            f"HARD SHAPE (overrides any other length hint above):\n"
            f"  1. TOTAL {_r['kata_min']}–{_r['kata_maks']} words (aim {_r['kata_bidik']}). Count them yourself "
            f"before answering.\n"
            f"  2. About {_r['kalimat']} sentences — do NOT exceed. Every sentence end adds real SILENCE to the "
            f"video; flowing sentences beat many short ones.\n"
            f"  3. NEVER use '...' (ellipsis): one ellipsis burns >1 second of silence.\n"
            f"  4. Commas sparingly — each one adds a short pause.\n"
            f"{_emph}\n"
            "The BEAT PLAN above splits these words across beats; the two numbers here are the authority "
            "for the TOTAL. Report word_count in `_duration_check` and real per-beat counts in `_beat_words`."
        )
    elif preset_seconds and len(active) <= 5:
        length_block = (
            f"🎯 LENGTH — WAJIB (video {target_duration} detik = SANGAT PENDEK):\n"
            f"Total narasi HARUS {total_words} kata — rentang KETAT {_lo}–{_hi}. "
            f"LEBIH dari {_hi} kata = audio kepanjangan = video DITOLAK. KURANG dari {_lo} = DITOLAK.\n"
            f"Di durasi sependek ini setiap kata WAJIB berbobot: padat, tajam, NOL filler, NOL pengulangan. "
            f"Ini BUKAN 'asal pendek' — justru tiap kata harus memukul & spesifik (angka/nama/fakta nyata). "
            f"JANGAN memanjang atau menjelaskan berlebih. Hitung jumlah katamu sebelum selesai — pastikan ≤ {_hi}."
        )
    else:
        length_block = (
            f"🎯 CRITICAL LENGTH REQUIREMENT — NON-NEGOTIABLE:\n"
            f"The COMPLETE narration (all sections combined) MUST total {total_words} words (range {_lo}–{_hi} words).\n"
            f"This word count makes the spoken audio last {target_duration}s — FEWER than {_lo} = audio too short = video FAILS; "
            f"MORE than {_hi} = audio too long = video FAILS.\n"
            f"Reach {total_words} words by adding SPECIFIC facts, numbers, names, concrete detail — NOT filler or repetition. "
            f"The per-section counts below add up to {total_words} — hit every one. Verify the total is between {_lo} and {_hi} before finishing."
        )

    return f"""Write a viral short-form video script.

TOPIC: {topic.get('topic', '')}
ANGLE: {topic.get('angle', topic.get('topic', ''))}
NICHE: {niche_data.get('name', niche)}
TARGET DURATION: {target_duration} seconds of spoken narration.
{_content_language_block(content_language)}
{length_block}

TONE: {profile['tone']}
STYLE: {profile['style']}
AVOID: {profile['avoid']}
EMOTION ARC: {profile['emotion_arc']}
HOOK FORMULA: {profile['hook_style']}
{("🎯 NICHE EMOTIONAL QUALITY BAR (aim for this from the first draft — it is how this script is scored): " + niche_data.get('emotion_scoring_criteria','')) if niche_data.get('emotion_scoring_criteria') else ""}
{insights_section}{soft_sell_block}{feedback_block}{beat_plan}
Follow the BEAT PLAN above — write ONLY the active beats (others = empty ""). The numbered guide below is craft reference per section:

1. HOOK ({section_timing['hook']}s ~{words['hook']} words)
   JOB: Stop scroll in the first second. Create an information gap that demands resolution.
   MUST: Use {profile['hook_style']}. The most counterintuitive angle of THIS specific topic.
   FORBIDDEN: "Did you know", "In this video", "Today we", any opener that could apply to any topic.
   QUALITY BAR: If this hook could belong to a different video, rewrite it.

2. MYSTERY DROP ({section_timing['mystery_drop']}s ~{words['mystery_drop']} words)
   JOB: Before answering hook, introduce a NEW layer of mystery specific to this topic.
   MUST: A detail that makes THIS topic even stranger than the hook implied.
   FORBIDDEN: Generic transitions. Every word must be about THIS specific topic.

3. BUILD UP ({section_timing['build_up']}s ~{words['build_up']} words)
   JOB: Deliver surprising fact 1 with context. Make the viewer feel the weight and scale.
   MUST: At least one specific number, name, or date anchored to this topic.
   TECHNIQUE: Human-scale analogy — translate abstract scale into something felt viscerally.

4. PATTERN INTERRUPT ({section_timing['pattern_interrupt']}s ~{words['pattern_interrupt']} words)
   JOB: Shatter the rhythm before they grow comfortable. Reframe everything said so far.
   MUST: Write something SPECIFIC to this topic that reframes the previous section unexpectedly.
   FORBIDDEN: "Wait. It gets worse." or any phrase that could appear in any video on any topic.
   QUALITY BAR: If this line could be copy-pasted into a different video, rewrite it.

5. CORE FACTS ({section_timing['core_facts']}s ~{words['core_facts']} words)
   JOB: Facts 2 and 3 — each more surprising than the last. Maximum information density.
   MUST: At least 2 distinct, specific, verifiable facts. Each sentence adds new information.
   FORBIDDEN: Repeating anything said before. Vague claims without specifics.

6. CURIOSITY BRIDGE ({section_timing['curiosity_bridge']}s ~{words['curiosity_bridge']} words)
   JOB: Create maximum anticipation for the climax. They must feel they cannot stop now.
   MUST: Point toward something not yet revealed — a specific unanswered question from THIS topic.
   FORBIDDEN: Summarizing. Generic "but it gets even more interesting" without specifics.

7. CLIMAX ({section_timing['climax']}s ~{words['climax']} words)
   JOB: The moment they feel something they cannot name but must share.
   MUST: The most unexpected, most impactful truth about this topic. Let it land in silence.
   TECHNIQUE: Write the climax first, then build everything before toward it.
   EMOTIONAL TECHNIQUE — do NOT describe the emotion. CAUSE it through one of these:
     • Scale contrast: reduce something infinite to a single human moment — or expand
       a human to cosmic/historical scale until the viewer feels the weight physically.
     • Reversal: the truth about this topic is the precise opposite of what seemed obvious.
       The setup leads one direction; the climax breaks it completely.
     • Infinite implication: one fact that permanently changes how the viewer sees
       something they encounter every day — their life, their place in the world, time itself.
   QUALITY BAR: Read the climax aloud alone. If you don't feel something — rewrite it.
   The viewer's next instinct should be to sit in silence, screenshot it, or tell someone immediately.

8. CTA ({section_timing['cta']}s ~{words['cta']} words)
   JOB: Create a chemical reaction — leave something unresolved that only this channel completes.
   PHILOSOPHY: Never ask. Never instruct. Chemistry is built through resonance, not solicitation.
   The viewer must feel that following is THEIR decision — the only logical response to what
   they just experienced. The channel sees something about the world that most people miss.
   MUST: Choose ONE — a question so specific to this topic they cannot answer it alone,
         a revelation that implies something larger is coming, or a reframe that makes
         the viewer feel they now see the world differently than they did 90 seconds ago.
   EXAMPLE PATTERNS (absorb the principle — never copy the words, adapt deeply to topic):
     - Open question: 'What does it mean that you now know this — and most people never will?'
     - Implication drop: 'The next discovery in this field makes this one look like a footnote.'
     - Identity shift: 'You just understood something that took scientists decades to accept.'
   FORBIDDEN: 'Follow', 'Subscribe', 'Like', 'Hit the bell', 'Smash the like button',
              any sentence beginning with an imperative verb directed at the viewer,
              any phrase that sounds like a creator asking for something from the audience.
   QUALITY BAR: Read it aloud as if speaking to one person you respect.
   If it sounds like a pitch — delete it and rewrite. If it sounds like a genuine thought — keep it.

WRITING RULES — every single one non-negotiable:
- Second person "you" throughout — intimacy is everything
- Maximum 15 words per sentence — punchy, direct, no run-ons
- Specific numbers always beat vague words: "13.8 billion years" not "billions of years ago"
- Every section transition must feel inevitable — not a gear shift, a deepening
- Zero filler: "basically", "literally", "you know", "kind of", "amazing", "incredible"
TTS DELIVERY RULES — write for the human ear, not the eye:
- ⏱ DURATION-CRITICAL: each em-dash (—) and ellipsis (…) becomes ≈0.6–1.0s of SILENCE when spoken — they EAT runtime. Over-using pauses is the #1 reason a video runs too long. Use them DELIBERATELY: at most ~1 per beat, only where the drama truly earns it.
- Em-dash (—) for ONE key mid-sentence pause per beat: "It survived — against all odds."
- Ellipsis (…) sparingly for suspense: "No one knew what was coming…"
- Short standalone sentences for emphasis (these read FAST — safe for runtime): "It was real. Completely real."
- ALWAYS "heard of" not "heard about": "You've never heard of this discovery."
- Sentence fragments for impact, used sparingly: "Thirteen billion years. Vanished."
- KEEP PACING TIGHT: every line moves the story forward — no dwelling, no padding. When in doubt, fewer pauses = more reliable runtime + punchier delivery.

Return ONLY valid JSON — no markdown, no preamble, no explanation:
{{
  "title": "SEO-optimized title under 60 characters — specific, not generic",
  "hook": "exact hook text",
  "mystery_drop": "exact mystery drop text",
  "build_up": "exact build up text",
  "pattern_interrupt": "exact pattern interrupt text — must be topic-specific",
  "core_facts": "exact core facts text",
  "core_facts_2": "exact SECOND distinct fact text — ONLY if CORE FACT 2 is listed in the BEAT PLAN above; otherwise an empty string",
  "curiosity_bridge": "exact curiosity bridge text",
  "climax": "exact climax text",
  "cta": "exact cta text — must sound human, not scripted",
  "full_script": "ONLY the active beats joined as one naturally flowing paragraph — no section labels, no empty gaps",
  "word_count": 140,
  "estimated_duration_seconds": {target_duration},
  "section_durations": {json.dumps(section_timing)},
  "tts_params": {{"stability": 0.5, "style": 0.3}},
  "_duration_check": {{"word_count": 95, "est_seconds": 56.5}},
  "_beat_words": {{"hook": 12, "core_facts": 45}},
  "background_music_mood": "specific mood, instrumentation, and emotional arc — not just one word",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#shorts"]
}}

NOTE: This call writes the NARRATION ONLY. Do NOT output image prompts/visual_suggestions/thumbnail — those are generated in a separate dedicated step."""


class ScriptEngine:

    def __init__(self):
        pass

    def _get_run_config(self, tenant_config):
        try:
            from src.config.tenant_config import load_tenant_config
            return load_tenant_config(tenant_config.tenant_id, getattr(tenant_config, "channel_id", None), getattr(tenant_config, "niche", None))
        except Exception as e:
            logger.warning(f"[ScriptEngine] RunConfig failed ({e}) — defaults")
            return None

    def _clean_json(self, raw):
        raw   = raw.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        raw = re.sub(r',\s*([}\]])', r'\1', raw)
        raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)
        return raw.strip()

    def _validate_and_fix(self, script, topic, section_timing: dict | None = None, active_beats: list | None = None):
        """Validasi TAHAP-1 (narasi saja). visual_suggestions TIDAK dibuat di sini lagi —
        dipindah ke Tahap-2 terdedikasi (Opsi A) pasca hook-optimize."""
        if not isinstance(script, dict):
            return None
        # required = beat inti yg BENAR-BENAR aktif di preset ini (segmentasi DB bisa <hook+core+cta,
        # mis. 15s=hook-core tanpa cta, 8s=core saja). Intersection {hook,core,cta} ∩ active + full_script.
        _core_req = [b for b in ("hook", "core_facts", "cta") if (not active_beats or b in active_beats)]
        required = _core_req + ["full_script"]
        if any(not script.get(f) for f in required):
            logger.warning(f"[ScriptEngine] Missing required fields")
            return None
        for f in ["mystery_drop", "build_up", "pattern_interrupt", "curiosity_bridge", "climax", "core_facts_2"]:
            script.setdefault(f, "")
        # A2 (Opsi A): SETIAP beat aktif preset WAJIB punya teks — compute_beat_durations + image-gen
        # baca per-beat; beat aktif kosong → durasi & scene meleset. Kosong → tolak (retry attempt).
        if active_beats:
            empty = [b for b in active_beats if not (script.get(b) or "").strip()]
            if empty:
                logger.warning(f"[ScriptEngine] Beat aktif kosong (tolak→retry): {empty}")
                return None
        script.setdefault("section_durations", section_timing or _DEFAULT_SECTION_TIMING)
        if not script.get("full_script"):
            parts = [script.get(s, "") for s in _beats.all_beats()]
            script["full_script"] = " ".join(p for p in parts if p)
        return script

    def _generate_one(self, provider, model, topic, niche, attempt,
                      niche_visual_style=None, feedback=None, insights_block=None,
                      preset_seconds=None, format_wps=None, render_overhead_sec=0.0,
                      cta_mode="implicit", brand_name=None, brand_cta_text=None,
                      delivery_p=None, voice_name=None, tts_provider=None,
                      content_language=None, resep_durasi=None):
        """Satu attempt generate script via LLMProvider (config-driven).

        Provider memegang SDK client + format API spesifik vendor — di sini tak
        ada nama SDK/provider. Gagal LLM (LLMError) = stop attempt ini (loop akan
        retry provider yang SAMA); TIDAK ada silent fallback ke provider lain.
        """
        from src.providers.llm import LLMError

        section_timing = _get_section_timing(niche)
        active_beats = None
        if preset_seconds:   # selaras dgn prompt (validate pakai timing + beat aktif yg sama)
            section_timing = _scale_section_timing(section_timing, preset_seconds)
            from src.config.format_catalog import preset_visual_beats as _pvb
            active_beats = _beats_for_preset(preset_seconds)   # segmentasi DB (single-source) — WAJIB non-kosong (A2)
        try:
            raw = provider.complete(
                system=_build_system_prompt(),
                user=_build_user_prompt(
                    topic, niche, niche_visual_style, feedback, insights_block,
                    preset_seconds=preset_seconds, format_wps=format_wps,
                    render_overhead_sec=render_overhead_sec,
                    cta_mode=cta_mode, brand_name=brand_name, brand_cta_text=brand_cta_text,
                    delivery_p=delivery_p, voice_name=voice_name, tts_provider=tts_provider,
                    content_language=content_language, resep_durasi=resep_durasi,
                ),
                model=model,
                temperature=1.0,
                max_tokens=2000,
                as_json=True,
            )
            script = json.loads(self._clean_json(raw))
            script = self._validate_and_fix(script, topic, section_timing, active_beats=active_beats)
            if script:
                logger.info(
                    f"[ScriptEngine] {provider.provider_name} attempt {attempt} "
                    f"OK (model={model})"
                )
            return script
        except LLMError as e:
            # Kegagalan provider tenant — JANGAN pindah ke provider lain.
            logger.warning(
                f"[ScriptEngine] {provider.provider_name} attempt {attempt} "
                f"gagal: {e}"
            )
            self.last_error = str(e)[:220]   # alasan vendor → error pipeline/Telegram (no-silent)
            return None
        except Exception as e:
            logger.warning(
                f"[ScriptEngine] attempt {attempt} parse/validate gagal: {e}"
            )
            self.last_error = str(e)[:220]
            return None

    def _load_insights(self, tenant_id: str, channel_id: str | None = None) -> dict | None:
        """Load channel_insights terbaru CHANNEL INI (isolasi per-channel). Fire-and-forget."""
        try:
            from src.analytics.performance_analyzer import PerformanceAnalyzer
            return PerformanceAnalyzer().load_latest_insights(tenant_id, channel_id)
        except Exception as e:
            logger.warning(f"[ScriptEngine] Load insights gagal (non-fatal): {e}")
            return None

    def generate_visual_prompts(self, script: dict, tenant_config) -> dict:
        """TAHAP-2 (Opsi A): LLM TERDEDIKASI membuat prompt image per-beat dari narasi FINAL.
        Dipanggil SETELAH hook-optimize (hook sudah final). Clue = teks beat + niche_visual_style +
        peran arc. 1 LLM call melihat SEMUA beat → koheren + bervariasi (through-line + varied composition).
        Set script['thumbnail_concept'] + script['visual_suggestions'] (index0 = thumbnail = scene hook).
        Sanitize tiap prompt + fallback EKSTRAKTIF (robust): tak pernah "N/A"/instruksi/kosong → tahan
        model image murah (flux/SD). visual_suggestions panjang = jumlah beat (= visual_beats preset)."""
        beats      = script.get("beats") or list(_ALL_SECTIONS)
        run_config = self._get_run_config(tenant_config)
        # VISUAL DNA niche (owner: SELURUH property niche = sumber prompting; NO-HARDCODE).
        # Inject SELURUH key visual_style apa adanya → admin tambah key (lighting/camera/composition/
        # realism/reference/color_grading/motion/…) langsung berpengaruh TANPA ubah kode. Kosong → fallback minimal.
        nvs        = (getattr(run_config, "niche_visual_style", {}) or {}) if run_config else {}
        dna_lines  = "\n".join(f"- {k.replace('_',' ')}: {v}" for k, v in nvs.items() if v) \
                     or "- style: cinematic, photorealistic, dramatic lighting"
        dna_inline = "; ".join(str(v) for v in nvs.values() if v) or "cinematic, photorealistic, dramatic lighting"
        # style_exemplars = eks-`visual_fallbacks` (di-repurpose): contoh shot terbaik niche → few-shot
        # acuan kualitas (bukan lagi padding stock-lib v1). Admin kurasi di niche.
        exemplars  = (getattr(run_config, "niche_visual_fallbacks", []) or []) if run_config else []
        exemplar_block = ("\nEXEMPLAR SHOTS (this niche's signature look — MATCH this quality bar, don't copy verbatim):\n"
                          + "\n".join(f"  • {e}" for e in exemplars[:6])) if exemplars else ""
        topic_text = script.get("topic", "") or script.get("title", "")
        niche_key  = getattr(tenant_config, "niche", "") or script.get("niche", "")
        niche_name = (get_niches().get(niche_key) or {}).get("name", niche_key)

        def _extractive(beat: str) -> str:
            txt   = (script.get(beat) or "").strip()
            first = (txt.split(".")[0].strip() if txt else topic_text) or topic_text
            return (f"{first}. {dna_inline}. Single commanding focal point, vertical 9:16, "
                    f"photorealistic, no text no words no letters no numbers no logos no watermarks.")

        def _bad(p) -> bool:
            if not p or not isinstance(p, str):
                return True
            s = p.strip().lower()
            if len(s) < 15:
                return True
            return any(m in s for m in ["n/a", "look at", "you just wrote", "[", "visual direction", "scene 1", "scene 2"])

        non_hook  = beats[1:]                 # beat[0]=hook → jadi thumbnail/hook-frame
        thumbnail = ""
        scenes    = []
        llm       = run_config.get_llm_provider()      if run_config else None
        model     = run_config.llm_model_for("utility") if run_config else ""
        if llm:
            try:
                beat_lines = "\n".join(
                    f"- BEAT {i+2} [{_ROLE_LABEL.get(b, b)}]: {(script.get(b) or '').strip()[:400]}"
                    for i, b in enumerate(non_hook)
                )
                system = (
                    "You are an elite cinematic visual director for viral short-form vertical video. "
                    "You convert each narration beat into ONE photorealistic image prompt grounded in what "
                    "the beat actually says. Output ONLY valid JSON — no markdown, no preamble."
                )
                user = f"""TOPIC: {topic_text}
NICHE: {niche_name}

VISUAL DNA — the signature cinematic identity of this niche. Apply ALL of it to EVERY image:
{dna_lines}
{exemplar_block}

Below is the FINAL narration, beat by beat. Make each image match what is actually SAID in that beat.

RULES (every prompt — non-negotiable for a VIRAL, breathtaking result):
- Build the image around the single most CONCRETE visual element named/implied in that beat's text — not the topic in general.
- BEAUTY FIRST: every frame must be gallery-grade cinematic. EXPLICITLY apply the VISUAL DNA's lighting, camera/lens, composition, color, and realism in your description. Not "good enough" — stunning, scroll-stopping, emotionally striking.
- Photorealistic, vertical 9:16, ONE commanding focal point with depth.
- Keep ONE consistent visual through-line across all scenes (a recurring subject/setting/palette that evolves), but VARY composition, scale, and camera angle so no two scenes look alike.
- Write a concrete, richly cinematic DESCRIPTION (2-3 sentences) that explicitly names the lighting + camera + mood. NEVER write instructions. NEVER output "N/A".
- The narration may be in a non-English language — but write EVERY image prompt in ENGLISH (image models follow English best). Translate the beat's concrete visual element into English for the prompt.
- ABSOLUTELY NO text, words, letters, numbers, signs, logos, or watermarks inside the image.

THUMBNAIL = the opening HOOK frame. HOOK text: "{(script.get(beats[0]) or '').strip()[:300]}"
Make it the most scroll-stopping, beautiful frame of all — one striking focal point, FULL VISUAL DNA applied, clear NEGATIVE SPACE in the upper third for a title overlay.

BEATS to illustrate (one prompt each, IN ORDER):
{beat_lines}

Return ONLY valid JSON:
{{
  "thumbnail_concept": "concrete description of the opening hook image (negative space at top)",
  "scenes": ["concrete prompt for BEAT 2", "concrete prompt for BEAT 3", "... EXACTLY {len(non_hook)} items, in order"]
}}"""
                raw  = llm.complete(system=system, user=user, model=model,
                                    temperature=0.8, max_tokens=1400, as_json=True)
                data = json.loads(self._clean_json(raw))
                thumbnail = (data.get("thumbnail_concept") or "").strip()
                scenes    = data.get("scenes") if isinstance(data.get("scenes"), list) else []
            except Exception as e:
                logger.warning(f"[ScriptEngine] Tahap-2 image-prompt gagal ({e}) → fallback ekstraktif")

        # Sanitize + pad/trim tepat len(non_hook); cacat → fallback ekstraktif per-beat
        clean_scenes = []
        for i, b in enumerate(non_hook):
            p = scenes[i] if i < len(scenes) else ""
            clean_scenes.append(_extractive(b) if _bad(p) else p.strip())
        if _bad(thumbnail):
            thumbnail = _extractive(beats[0]) if beats else _extractive("hook")

        script["thumbnail_concept"]  = thumbnail
        script["visual_suggestions"] = [thumbnail] + clean_scenes   # index0 = scene hook = thumbnail
        logger.info(
            f"[ScriptEngine] Tahap-2 prompt-image: {len(script['visual_suggestions'])} "
            f"(1 thumbnail + {len(clean_scenes)} scene) via {'LLM' if llm and scenes else 'fallback-ekstraktif'}"
        )
        return script

    def generate_video_prompt(self, script: dict, tenant_config) -> dict:
        """[B6] F2 — TAHAP-2 varian VIDEO (render_mode ai_video, preset 8s): 1 LLM call membuat SATU
        prompt text-to-video (subjek + GERAK + kamera + mood) dari narasi final + SELURUH VISUAL DNA
        niche (termasuk key subject/strict_prohibition/motion — admin-editable, no-hardcode).
        Set script['video_prompt'].
        ⛔ NO-FALLBACK (§3.3, teguran owner 2026-07-14): prompt = SELURUH video berbayar — LLM gagal /
        output cacat → LLMError (run STOP + Telegram), BUKAN prompt rakitan mekanis diam-diam."""
        from src.exceptions import LLMError
        run_config = self._get_run_config(tenant_config)
        nvs        = (getattr(run_config, "niche_visual_style", {}) or {}) if run_config else {}
        dna_lines  = "\n".join(f"- {k.replace('_',' ')}: {v}" for k, v in nvs.items() if v) \
                     or "- style: cinematic, photorealistic, dramatic lighting"
        exemplars  = (getattr(run_config, "niche_visual_fallbacks", []) or []) if run_config else []
        exemplar_block = ("\nEXEMPLAR SHOTS (signature look — MATCH this bar, don't copy verbatim):\n"
                          + "\n".join(f"  • {e}" for e in exemplars[:4])) if exemplars else ""
        beats     = script.get("beats") or []
        narration = " ".join((script.get(b) or "").strip() for b in beats).strip() \
                    or (script.get("full_script") or "").strip()

        try:
            llm    = run_config.get_llm_provider()       if run_config else None
            model  = run_config.llm_model_for("utility") if run_config else ""
        except Exception as _le:
            raise LLMError(f"Prompt-video butuh LLM channel — tidak tersedia: {_le}", step="visual_prompt")
        if not llm:
            raise LLMError("Prompt-video butuh LLM channel — belum terkonfigurasi.", step="visual_prompt")
        prompt = ""
        if llm:
            try:
                system = (
                    "You are an elite cinematic director writing ONE text-to-video prompt for a short "
                    "vertical clip. Output ONLY the prompt text — no JSON, no markdown, no preamble."
                )
                user = f"""NARRATION (final, may be non-English — the visual must match its feeling):
"{narration[:500]}"

VISUAL DNA — the niche's signature identity. Apply ALL of it, including any restrictions verbatim:
{dna_lines}
{exemplar_block}

Write ONE text-to-video prompt (3-4 sentences, ENGLISH) for a single continuous shot:
- Describe the SUBJECT concretely (who/what fills the frame) per the VISUAL DNA.
- Describe the MOTION: what moves inside the frame (hair, fabric, light) AND the camera movement (slow push-in / gentle orbit) — this is video, not a still.
- Name the lighting, lens/depth-of-field, mood and color grade explicitly.
- Vertical 9:16. Photorealistic. ABSOLUTELY NO text, words, letters, logos, or watermarks in frame.
- Obey every restriction in the VISUAL DNA strictly (they are non-negotiable)."""
                raw = (llm.complete(system=system, user=user, model=model,
                                    temperature=0.7, max_tokens=350) or "").strip().strip('"')
                low = raw.lower()
                if len(raw) >= 40 and not any(m in low for m in ("n/a", "```", "{", "here is", "here's")):
                    prompt = raw
            except LLMError:
                raise
            except Exception as e:
                raise LLMError(f"Tahap-2 prompt-video gagal: {e}", step="visual_prompt") from e

        if not prompt:
            # Output LLM cacat/kosong = kegagalan komponen → STOP jujur (§3.3) — video 8s berbayar
            # tidak boleh diproduksi dari prompt rakitan mekanis diam-diam (teguran owner 2026-07-14).
            raise LLMError("Tahap-2 prompt-video: output LLM cacat/kosong — run dihentikan (no-fallback §3.3).",
                           step="visual_prompt")
        script["video_prompt"] = prompt
        logger.info(f"[ScriptEngine] Tahap-2 prompt-video (LLM): {prompt[:120]}...")
        return script

    def generate(self, topic, tenant_config):
        logger.info(f"[ScriptEngine] Generating: {topic.get('topic','')[:50]}...")

        run_config         = self._get_run_config(tenant_config)
        self.last_error    = ""   # reset per-run (dibaca pipeline saat naskah gagal total)
        # Label provider = library NYATA channel (groq/gemini/openai/anthropic). Dulu
        # effective_llm_provider() (peta legacy claude|openai saja) → log/Runs menulis "openai"
        # padahal panggilan sesungguhnya ke Groq (menyesatkan diagnosa, insiden 2026-07-08).
        llm_provider       = ((getattr(run_config, "llm_library", None) or run_config.effective_llm_provider()) if run_config else "")
        min_score          = run_config.script_min_viral_score  if run_config else 82
        max_retry          = run_config.script_max_retry        if run_config else 3
        niche_visual_style = getattr(run_config, "niche_visual_style", {}) or {}
        # LLM via provider abstraction (config-driven, BYOK). Provider memegang
        # API key + SDK client — di sini tak ada nama SDK/provider/model.
        llm          = run_config.get_llm_provider()      if run_config else None
        script_model = run_config.llm_model_for("script") if run_config else ""
        # Duration Preset per-channel (MULTI_FORMAT §3) — dari tenant_config (konteks channel).
        # null → legacy (timing niche, WPS 2.4) = non-breaking. WPS EFEKTIF = delivery TTS provider
        # (solusi 2-kelas: ElevenLabs-class ~1.8 vs edge ~2.6) → word-budget pas per kelas.
        from src.config.format_catalog import effective_wps as _eff_wps
        preset_seconds = getattr(tenant_config, "duration_preset", None)
        # Beat-aktif preset (segmentasi DB single-source) — dipakai analyzer utk renormalisasi bobot
        # (preset pendek tak dihukum climax/cta absen). None (legacy tanpa preset) → analyzer pakai 6 dim.
        active_beats   = _beats_for_preset(preset_seconds) if preset_seconds else None
        # Word-budget pakai delivery_wps provider TERDAFTAR tenant (mis. elevenlabs 1.8 → 60s=108 kata).
        # TTS apa-adanya: premium dulu → bila kredit kurang fallback edge (produk jadi, durasi bisa
        # tak lolos QC → Opsi C: flagged + tenant putuskan). Akar akurasi durasi = LLM hit word-budget.
        _tts_provider  = getattr(run_config, "tts_provider", None) if run_config else None
        format_wps     = _eff_wps(getattr(tenant_config, "format_profile", None), _tts_provider) if preset_seconds else None
        # F5-01: pace VOICE-FIRST (no-hardcode voice) — voice_catalog.delivery_wps menimpa pace provider
        # HANYA untuk voice ini (mis. Arnold lebih cepat = DATA di baris voice, bukan if-else di kode).
        # NULL/di-luar-guard [1.0,4.0] → tetap pakai pace provider (fallback) = perilaku sekarang.
        if preset_seconds and run_config:
            _vw = getattr(run_config, "voice_delivery_wps", None)
            try:
                if _vw is not None and 1.0 <= float(_vw) <= 4.0:
                    format_wps = float(_vw)
                    logger.info(f"[ScriptEngine] F5-01 pace voice-first: {format_wps} wps "
                                f"(voice={getattr(run_config,'tts_voice',None)}) — override pace provider")
            except Exception:
                pass
            # [DURASI-F2] lapis TERTINGGI: pace TERKALIBRASI (voice×niche) dari render nyata
            # (tts_pace_calibration via tenant_config; bukti replay: error taksiran 9.3%→4.7%).
            # None (belum ada data/di luar guard) → lapis di atas tetap berlaku = perilaku lama persis.
            _pcal = getattr(run_config, "pace_calibrated", None)
            try:
                if _pcal is not None and 1.0 <= float(_pcal) <= 4.0:
                    format_wps = float(_pcal)
                    logger.info(f"[ScriptEngine] F2 pace TERKALIBRASI: {format_wps} wps "
                                f"(voice={getattr(run_config,'tts_voice',None)}×niche) — override lapis lama")
            except Exception:
                pass
        # `_base_p` = pace kata/detik lapis-lama. Sejak 2026-07-31 hanya dipakai jalur CADANGAN
        # (preset di luar tangga aktif → resep tak bisa dihitung); jalur utama memakai `duration_model`.
        _base_p = float(format_wps) if format_wps else None
        _voice_name = (getattr(run_config, "tts_voice", None) if run_config else None) or None
        # Cacat B (#3) — BUDGET SADAR-OVERHEAD RENDER: QC mengukur VIDEO FINAL = audio + trailing_silence
        # (+ loop net = loop_dur−0.5 xfade). Target AUDIO = preset − overhead agar video JADI ≈ preset.
        # Tanpa ini kata in-range pun overshoot di preset pendek (terbukti: 15s 27 kata → video 18.2s > 17.2).
        # No-hardcode: trailing_silence + loop dari tenant_configs (sama dgn yang dipakai video_renderer).
        render_overhead_sec = 0.0
        if preset_seconds and run_config:
            # [DURASI-F4] overhead PENUH (trailing efektif + loop bersih) via SATU helper
            # format_catalog.effective_overhead — nilai identik rumus inline lama (trail + loopn),
            # kini satu sumber dgn resep durasi + gerbang pra-visual + QC pasca-render.
            from src.config.format_catalog import effective_overhead as _eff_ovh
            render_overhead_sec = _eff_ovh(preset_seconds, run_config)
            logger.info(f"[ScriptEngine] #3 budget overhead-aware: preset {preset_seconds}s − overhead {render_overhead_sec}s "
                        f"= audio-target {max(1.0, preset_seconds-render_overhead_sec)}s")
        # ── RESEP DURASI (2026-07-31): dua angka — KATA & KALIMAT — dari alat ukur terkalibrasi ────
        # `_kalib` = koefisien per-suara dari `tts_pace_calibration` (ditulis pace_calibration.py dari
        # render nyata). None/kosong → duration_model memakai angka BAWAAN terukur, jadi jalur ini
        # tetap hidup pada tenant/suara yang belum punya sampel.
        # `_tangga` = preset AKTIF dari DB → menentukan batas titik-tengah. Kosong → resep None →
        # gerbang durasi TIDAK menilai apa pun (gagal-aman: tak mengarang batas).
        _kalib, _resep, _tangga = None, None, []
        if preset_seconds:
            from src.config.format_catalog import active_presets as _act_presets
            from src.production.duration_model import resep as _resep_durasi
            _kalib = (getattr(run_config, "duration_calibration", None) or None) if run_config else None
            _tangga = _act_presets()
            if _tangga and int(preset_seconds) in _tangga:
                try:
                    _resep = _resep_durasi(preset_seconds, _tangga, render_overhead_sec, _kalib)
                    _resep.update({"_preset": preset_seconds, "_tangga": _tangga,
                                   "_overhead": render_overhead_sec, "_kalibrasi": _kalib})
                    logger.info(f"[ScriptEngine] resep durasi preset {preset_seconds}s: "
                                f"{_resep['kata_min']}-{_resep['kata_maks']} kata (bidik {_resep['kata_bidik']}) / "
                                f"{_resep['kalimat']} kalimat · band video "
                                f"{_resep['band_video'][0]:.0f}-{_resep['band_video'][1]:.0f}s"
                                f"{' · kalibrasi suara AKTIF' if _kalib else ' · angka bawaan (suara belum dikalibrasi)'}")
                except ValueError as _pe:
                    logger.warning(f"[ScriptEngine] resep durasi tak bisa dihitung ({_pe}) — gerbang durasi PASIF")
            else:
                logger.warning(f"[ScriptEngine] preset {preset_seconds}s tak ada di tangga aktif {_tangga} — "
                               f"gerbang durasi PASIF (tak mengarang batas)")

        # Branded Content §6 — soft-sell (opsional; implicit → tanpa brand)
        _cta_mode  = getattr(tenant_config, "cta_mode", "implicit") or "implicit"
        _brand     = getattr(tenant_config, "brand_name", None)
        _brand_cta = getattr(tenant_config, "brand_cta_text", None)
        # Bahasa KONTEN per-channel (channels.content_language via tenant_config.language).
        # en* → blok bahasa TIDAK di-inject (prompt identik perilaku lama); non-en → mandat bahasa.
        _clang = getattr(tenant_config, "language", None) or "en-US"

        # S1-B: load channel insights — inject ke semua attempt jika grade cukup
        insights       = self._load_insights(tenant_config.tenant_id, getattr(tenant_config, "channel_id", None))
        insights_block = None
        insights_grade = ""
        if insights:
            grade          = insights.get("performance_grade", "insufficient_data")
            insights_grade = grade
            if grade != "insufficient_data":
                insights_block = _build_insights_block(insights)
                logger.info(
                    f"[ScriptEngine] Insights injected | grade={grade} | "
                    f"top_hooks={len(insights.get('top_hooks', []))} | "
                    f"content_types={len(insights.get('content_type_perf', []))}"
                )

        logger.info(
            f"[ScriptEngine] provider={llm_provider} "
            f"min_score={min_score} max_retry={max_retry}"
        )

        try:
            from src.intelligence.script_analyzer import ScriptAnalyzer
            # Analyzer pakai provider LLM tenant yang sama (model task 'analyzer').
            analyzer = ScriptAnalyzer(
                provider=llm,
                model=(run_config.llm_model_for("analyzer") if run_config else ""),
            )
        except Exception as e:
            logger.warning(f"[ScriptEngine] Analyzer failed ({e}) — no gate")
            analyzer = None

        # Niche profile untuk emotional_peak scoring yang niche-aware.
        # Config-driven dari Supabase — tidak hardcode per niche.
        niches_data   = get_niches()
        niche_profile = niches_data.get(tenant_config.niche) or {}

        best_script     = None
        best_score      = 0
        best_len_ok_script = None   # #2 — best yang LULUS length-gate (panjang PAS → lolos QC durasi)
        best_len_ok_score  = 0
        actual_provider = llm_provider
        feedback        = None  # Feedback dari attempt sebelumnya
        # F2d — target word-budget (LLM-QC length gate). Aktif hanya bila preset di-set.
        # Anggaran kata = dari RESEP terkalibrasi bila ada (sadar-jeda); jatuh ke rumus lama hanya bila
        # resep tak bisa dihitung (preset tak di tangga aktif) — supaya jalur lama tak mati mendadak.
        word_budget = (_resep["kata_bidik"] if _resep else
                       (round(max(1.0, preset_seconds - render_overhead_sec) * float(format_wps))
                        if (preset_seconds and format_wps) else None))
        # [DURASI-F3] toleransi SATU-SUMBER utk gerbang durasi internal (dulu: _LEN_TOL dibaca tapi TAK
        # PERNAH dipakai = config-mati, gerbang malah hardcode ±10% — insiden 'tiga penggaris' 2026-07-15).
        _len_tol = _script_len_tol()

        for attempt in range(1, max_retry + 1):
            logger.info(f"[ScriptEngine] Attempt {attempt}/{max_retry} via {llm_provider}")

            script = self._generate_one(
                llm, script_model, topic, tenant_config.niche, attempt,
                niche_visual_style, feedback, insights_block,
                preset_seconds=preset_seconds, format_wps=format_wps,
                render_overhead_sec=render_overhead_sec,
                cta_mode=_cta_mode, brand_name=_brand, brand_cta_text=_brand_cta,
                delivery_p=_base_p, voice_name=_voice_name, tts_provider=_tts_provider,
                content_language=_clang, resep_durasi=_resep,
            )

            if not script:
                if attempt < max_retry:
                    time.sleep(2 ** attempt)
                continue

            if analyzer:
                # active_beats (segmentasi DB preset) → analyzer renormalisasi bobot atas dimensi
                # relevan; preset pendek (tanpa climax/cta) tak dihukum bagian absen.
                analysis = analyzer.analyze(script, tenant_config.niche,
                                            niche_profile=niche_profile, active_beats=active_beats,
                                            content_language=_clang)
                score    = analysis.get("viral_score", 0)
                script["viral_analysis"] = analysis
                # ⚠️ SKOR BERTANDA = BUKAN PENILAIAN MUTU (2026-07-31). Bila penilai LLM gagal,
                # analyzer mengembalikan taksiran lokal yang terukur ±20 poin lebih rendah. Dulu skor
                # itu dipakai apa adanya sebagai gerbang `script_min_viral_score` → naskah bagus
                # ditolak & data mesin belajar keracunan, tanpa jejak. Sekarang: skor bertanda tidak
                # boleh menjatuhkan naskah — dianggap "lulus mutu" agar gerbang DURASI tetap yang
                # memutuskan, dan kegagalan penilai dicatat keras di log + menempel di naskah.
                if analysis.get("estimated"):
                    logger.error(f"[ScriptEngine] penilai mutu TIDAK BEKERJA ({analysis.get('estimate_reason')}) — "
                                 f"skor {score} DIABAIKAN sebagai gerbang mutu (bukan penilaian sah)")
                    score = max(int(min_score or 0), int(score or 0))
                    script["quality_gate_skipped"] = analysis.get("estimate_reason") or "penilai mutu gagal"

                # Siapkan feedback untuk retry berikutnya.
                # Sertakan skor aktual + teknik konkret per dimensi lemah
                # agar model tahu ANGKA yang harus dicapai dan CARA spesifiknya.
                weak_areas   = analysis.get("weak_areas", [])
                dim_scores   = analysis.get("dimension_scores", {})
                retry_note   = analysis.get("retry_suggestion", "")
                feedback = []
                for area in weak_areas:
                    area_score = dim_scores.get(area, "?")
                    # emotional_peak: gunakan guidance niche-aware dari Supabase
                    # dimensi lain: guidance universal dari DIMENSION_RETRY_GUIDANCE
                    if area == "emotional_peak" and niche_profile:
                        guidance = _build_emotional_peak_guidance(niche_profile)
                    else:
                        guidance = DIMENSION_RETRY_GUIDANCE.get(
                            area, "improve this dimension — be more specific and impactful"
                        )
                    feedback.append(
                        f"{area} scored {area_score}/100 (need {min_score}+): {guidance}"
                    )
                if retry_note:
                    feedback.append(f"Analyzer note: {retry_note}")

                logger.info(
                    f"[ScriptEngine] Score: {score}/100 "
                    f"(threshold: {min_score}) | {analysis.get('summary','')}"
                )
                if weak_areas:
                    logger.info(f"[ScriptEngine] Weak areas: {weak_areas}")
            else:
                score = 82
                script["viral_analysis"] = {}
                feedback = None

            # ── GERBANG DURASI = VONIS ALAT UKUR TERKALIBRASI (2026-07-31) ────────────────────────
            # Menggantikan jaring §10.A yang MENYOLVE KECEPATAN SUARA agar taksiran mendarat. Yang
            # dicabut & sebabnya (terukur dari 294 produksi): solver itu memperlambat suara sampai
            # batas bawah pada 41% render (NOL render normal, median 0,81) — mood narasi rusak DAN
            # durasi tetap meleset median −4,7 dtk. Kecepatan suara bukan tuas (owner 2026-07-29).
            #
            # SEKARANG: durasi diputuskan dari TEKS saja, oleh alat ukur yang dikalibrasi dari render
            # nyata (duration_model; salah luar-sampel 0,96–1,09 dtk vs 2,76–7,01 dtk estimator lama).
            # Di luar band titik-tengah → naskah diperbaiki PENULISNYA (retry ber-umpan-balik angka
            # persis), bukan ditambal di sisi suara.
            length_ok = True
            if preset_seconds and _resep:
                from src.production.duration_model import (ciri_teks as _ciri, rincian_audio as _rincian,
                                                          vonis as _vonis)
                _txt = script.get("full_script") or ""
                _v   = _vonis(_txt, preset_seconds, _tangga, render_overhead_sec, _kalib)
                _f   = _ciri(_txt)
                _rinci = _rincian(_txt, _kalib)
                script["_duration_est"] = {                      # observability → tts_delivery_samples
                    "est_seconds": _v["audio_prediksi"], "video_seconds": _v["video_prediksi"],
                    "pause_seconds": _rinci["jeda"], "speech_seconds": _rinci["bicara"],
                    "words": _f["words"], "chars": _f["chars"], "sentences": _f["sentence"],
                    "band_video": list(_v["band_video"]), "status": _v["status"],
                }
                if _v["status"] != "ok":
                    length_ok = False
                    _lo, _hi = _v["band_video"]
                    _arah = ("SHORTEN" if _v["status"] == "terlalu_panjang" else "LENGTHEN with concrete substance")
                    # ground-truth PER-BEAT: sistem hitung kata NYATA tiap beat (bukan laporan model)
                    _beats_now = _beats_for_preset(preset_seconds)
                    _quota     = _distribute_words(_beats_now, _resep["kata_bidik"]) if _beats_now else {}
                    _actual    = {b: len((script.get(b) or "").split()) for b in _beats_now}
                    _offb      = [f"{b}: {_actual[b]}w vs target {_quota.get(b,0)}w" for b in _beats_now
                                  if _quota.get(b) and abs(_actual[b] - _quota[b]) / _quota[b] > _len_tol]
                    feedback = (feedback or []) + [
                        f"DURATION FAIL: {_f['words']} words in {_f['sentence']} sentences "
                        f"({_f['ellipsis']} ellipses, {_f['comma']} commas) → video would be "
                        f"{_v['video_prediksi']:.1f}s, outside the valid {_lo:.0f}–{_hi:.0f}s. "
                        f"{_arah} by ≈{_v['kata_selisih']} words. Target: {_resep['kata_min']}–"
                        f"{_resep['kata_maks']} words in ≈{_resep['kalimat']} sentences. "
                        f"Every sentence end and every ellipsis costs real silence — merge sentences "
                        f"instead of adding them, and never use '...'."
                        + (f" OFF-BUDGET BEATS (fix exactly these): {'; '.join(_offb)}." if _offb else "")]
                    logger.info(f"[ScriptEngine] durasi: {_f['words']}w/{_f['sentence']}kal → "
                                f"{_v['video_prediksi']:.1f}s di luar {_lo:.0f}-{_hi:.0f}s → retry")
                else:
                    logger.info(f"[ScriptEngine] durasi: {_f['words']}w/{_f['sentence']}kal → "
                                f"{_v['video_prediksi']:.1f}s ∈ band ✓")

            # ── PEMERIKSA CACAT MEKANIS (2026-07-31) ──────────────────────────────────────────
            # Terukur: KODE menangkap lebih banyak cacat daripada penilai AI (kalimat menggantung,
            # kata bahasa asing menyelinap, kata yang DILARANG niche, frasa berulang, artefak
            # sambungan), dan AI justru MELEWATKAN pelanggaran register walau DNA niche diberikan.
            # Aturannya datang dari baris NICHE di DB — nol daftar per-niche di kode (ratusan niche
            # akan datang). Cacat PARAH → naskah ditolak & sebabnya jadi umpan-balik retry yang persis.
            _cacat = []
            try:
                from src.intelligence.script_checker import (ada_cacat_parah as _parah,
                                                             periksa_naskah as _periksa,
                                                             ringkas_temuan as _ringkas)
                _cacat = _periksa(script.get("full_script") or "", niche_profile=niche_profile,
                                  content_language=_clang, beat_keys=active_beats)
                script["mechanical_issues"] = _cacat
                if _cacat:
                    logger.info(f"[ScriptEngine] pemeriksa mekanis: {_ringkas(_cacat)}")
                if _parah(_cacat):
                    length_ok = False       # pakai jalur retry yang sama dgn gerbang durasi
                    feedback = (feedback or []) + [
                        "MECHANICAL DEFECTS (must fix, these are certain — not opinions): "
                        + "; ".join(f"{c['jenis']}: {c['pesan']}"
                                    + (f" [{c['bukti']}]" if c["bukti"] else "")
                                    for c in _cacat if c["parah"])]
            except Exception as _ce:
                logger.warning(f"[ScriptEngine] pemeriksa mekanis gagal (naskah tak dihukum): {_ce}")

            if score > best_score:
                best_score  = score
                best_script = script
            # #2 — lacak best LENGTH-COMPLIANT terpisah. Naskah salah-durasi GAGAL QC (→ ready_with_issues,
            # tak auto-publish); lebih baik kirim yang panjangnya PAS + skor tertinggi DI ANTARA yang pas.
            if length_ok and score > best_len_ok_score:
                best_len_ok_score  = score
                best_len_ok_script = script

            if score >= min_score and length_ok:
                logger.info(
                    f"[ScriptEngine] ✅ Quality gate passed: "
                    f"{score}/100 (attempt {attempt}) | length_ok={length_ok}"
                )
                break

            if attempt < max_retry:
                logger.info(
                    f"[ScriptEngine] Score {score} < {min_score} — "
                    f"retry dengan feedback: {feedback}"
                )
                time.sleep(1)

        if best_script is None:
            logger.error("[ScriptEngine] All attempts failed")
            return {}

        # #2 — FINAL: utamakan naskah length-compliant (lolos QC durasi) + skor tertinggi di antaranya;
        # bila tak ada yang pas → fallback skor-tertinggi (perilaku lama). Jaga kualitas DALAM batas panjang.
        if best_len_ok_script is not None and best_len_ok_script is not best_script:
            logger.info(f"[ScriptEngine] #2 pilih naskah length-compliant (skor {best_len_ok_score}) alih-alih "
                        f"skor-tertinggi {best_score} (salah-durasi) — agar lolos QC durasi")
            best_script = best_len_ok_script
            best_score  = best_len_ok_score

        # ── JALUR PER-BAGIAN: dipakai bila satu panggilan terbukti tak sanggup memenuhi panjang ────
        # Pemicunya BUKTI, bukan tebakan: naskah terbaik dari seluruh attempt masih di bawah
        # SCRIPT_PERBEAT_TRIGGER × batas bawah resep. Terukur pada channel nyata (2026-07-31):
        # llama-3.1-8b menulis 37 kata untuk preset 90 dtk (butuh ±206), llama-3.3-70b 62–91 kata
        # untuk preset 60 dtk (butuh 128–166) — selisih sebesar itu tak bisa ditutup dengan meminta
        # ulang. Memecah jadi bagian ±30 kata membuatnya berada di dalam kemampuan model mana pun.
        if preset_seconds and _resep and best_script:
            _amb = float(os.getenv("SCRIPT_PERBEAT_TRIGGER", "0.80"))
            _w_now = len((best_script.get("full_script") or "").split())
            if _w_now < _amb * _resep["kata_min"]:
                logger.warning(f"[ScriptEngine] naskah {_w_now} kata << batas bawah {_resep['kata_min']} "
                               f"— satu panggilan tak sanggup; beralih ke TULIS PER-BAGIAN")
                _pb = _generate_per_beat(llm, script_model, topic, tenant_config.niche,
                                         _beats_for_preset(preset_seconds), _resep, niche_profile,
                                         _clang, insights_block)
                if _pb.get("full_script"):
                    _w_pb = len(_pb["full_script"].split())
                    if _w_pb > _w_now:
                        best_script = {**best_script, **_pb}
                        best_script["_written_per_beat"] = True
                        logger.info(f"[ScriptEngine] per-bagian menghasilkan {_w_pb} kata "
                                    f"(sebelumnya {_w_now}) — dipakai")
                    else:
                        logger.warning(f"[ScriptEngine] per-bagian {_w_pb} kata tidak lebih baik dari "
                                       f"{_w_now} — naskah asal dipertahankan")

        # ── PERBAIKAN AKHIR: suruh MODEL merapatkan/melengkapi bila durasi masih di luar band ──────
        # Retry biasa mengulang dari nol dan itu TIDAK menutup selisih (goyangan antar-produksi
        # ±12–39%). Yang menutup: memberi model selisih yang PERSIS atas naskahnya sendiri.
        # Terukur: tanpa langkah ini 5/6 mendarat; dengan langkah ini 14/14 (7 preset × 2 niche),
        # fakta utuh 14/14, rata-rata 1,0 putaran. Kode memverifikasi fakta & durasi; model memilih kata.
        if preset_seconds and _resep and best_script:
            from src.production.duration_model import vonis as _vonis_akhir
            _v_akhir = _vonis_akhir(best_script.get("full_script") or "", preset_seconds, _tangga,
                                    render_overhead_sec, _kalib)
            if _v_akhir["status"] != "ok":
                _maks = int(os.getenv("SCRIPT_REFIT_ROUNDS", "3"))
                best_script, _jejak = _refit_naskah(
                    llm, script_model, best_script, _beats_for_preset(preset_seconds), _resep,
                    _v_akhir, maks_putaran=_maks)
                _v2 = _vonis_akhir(best_script.get("full_script") or "", preset_seconds, _tangga,
                                   render_overhead_sec, _kalib)
                best_script["_duration_est"] = {**(best_script.get("_duration_est") or {}),
                                                "est_seconds": _v2["audio_prediksi"],
                                                "video_seconds": _v2["video_prediksi"],
                                                "status": _v2["status"], "refit": _jejak}
                if _v2["status"] == "ok":
                    logger.info(f"[ScriptEngine] refit BERHASIL: {_jejak} → video {_v2['video_prediksi']:.1f}s "
                                f"∈ band {_v2['band_video'][0]:.0f}-{_v2['band_video'][1]:.0f}s")
                else:
                    logger.warning(f"[ScriptEngine] refit belum cukup: {_jejak} → video "
                                   f"{_v2['video_prediksi']:.1f}s masih di luar band "
                                   f"{_v2['band_video'][0]:.0f}-{_v2['band_video'][1]:.0f}s — "
                                   f"gerbang pipeline yang memutuskan (gagal JUJUR, tidak diakali)")

        # ── PERIKSA ULANG setelah teks berubah (per-bagian / perbaikan) ────────────────────────────
        # Lubang yang sempat ada: pemeriksa cacat mekanis & rincian durasi dijalankan DI DALAM loop
        # attempt, sehingga hasilnya menempel pada teks LAMA — padahal jalur per-bagian & perbaikan
        # mengganti naskah SEPENUHNYA. Tanpa ini, `mechanical_issues` di naskah akhir menyesatkan
        # (melaporkan teks yang sudah tidak dipakai) dan cacat baru dari penggabungan per-bagian
        # (artefak sambungan, frasa berulang) lolos tanpa terlihat.
        if best_script and (best_script.get("_written_per_beat")
                            or (best_script.get("_duration_est") or {}).get("refit")):
            try:
                from src.intelligence.script_checker import periksa_naskah as _periksa2
                from src.intelligence.script_checker import ringkas_temuan as _ringkas2
                _c2 = _periksa2(best_script.get("full_script") or "", niche_profile=niche_profile,
                                content_language=_clang, beat_keys=active_beats)
                best_script["mechanical_issues"] = _c2
                logger.info(f"[ScriptEngine] periksa ulang naskah akhir: {_ringkas2(_c2)}")
            except Exception as _ce2:
                logger.warning(f"[ScriptEngine] periksa ulang gagal (naskah tetap dipakai): {_ce2}")
            # angka pelaporan diselaraskan ke teks AKHIR (dulu tertinggal di teks lama → sampel
            # kalibrasi & log menyebut jeda/kata yang tidak sesuai naskah yang benar-benar dirender)
            try:
                from src.production.duration_model import rincian_audio as _rinci2
                _r2 = _rinci2(best_script.get("full_script") or "", _kalib)
                best_script["_duration_est"] = {**(best_script.get("_duration_est") or {}),
                                                "pause_seconds": _r2["jeda"], "speech_seconds": _r2["bicara"],
                                                "words": _r2["words"], "chars": _r2["chars"],
                                                "sentences": _r2["sentence"]}
                best_script["word_count"] = _r2["words"]      # laporan LLM bisa basi; ini hitungan sistem
            except Exception:
                pass

        if best_score < min_score:
            logger.warning(
                f"[ScriptEngine] Best score {best_score}/100 below "
                f"threshold {min_score} — using best available"
            )

        from src.config.format_catalog import preset_visual_beats as _pvb_g
        _beats = _beats_for_preset(preset_seconds) if preset_seconds else list(_ALL_SECTIONS)
        best_script.update({
            "topic":                   topic.get("topic", ""),
            "viral_score":             topic.get("viral_score", 0),
            "script_viral_score":      best_score,
            "tenant_id":               tenant_config.tenant_id,
            "niche":                   tenant_config.niche,
            "beats":                   _beats,   # urutan beat aktif (compression-mapping) → image-gen + render per-preset

            "generated_at":            datetime.now().isoformat(),
            "llm_provider_used":       actual_provider,
            "llm_provider_requested":  llm_provider,
            # S3-A: simpan 5 skor dimensi untuk adaptive weight computation
            "topic_scores": {
                "search_volume":       topic.get("search_volume", 0),
                "trend_momentum":      topic.get("trend_momentum", 0),
                "emotional_trigger":   topic.get("emotional_trigger", 0),
                "competition_gap":     topic.get("competition_gap", 0),
                "evergreen_potential": topic.get("evergreen_potential", 0),
            },
            # S3-B: tag grade saat produksi untuk attribution
            "insights_grade": insights_grade,
        })

        logger.info(
            f"[ScriptEngine] Done: "
            f"{len(best_script.get('full_script','').split())} words | "
            f"score={best_score}/100 | used={actual_provider}"
        )
        return best_script

    def generate_batch(self, topics, tenant_config, count=1):
        scripts = []
        for topic in topics[:count]:
            script = self.generate(topic, tenant_config)
            if script:
                scripts.append(script)
        os.makedirs("logs", exist_ok=True)
        with open(f"logs/scripts_{tenant_config.tenant_id}.json", "w") as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)
        logger.info(f"[ScriptEngine] Batch: {len(scripts)}/{count} generated")
        return scripts


if __name__ == "__main__":
    tenant     = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")
    test_topic = {
        "topic":       "The Fermi Paradox — Why the Universe is Silent",
        "angle":       "The universe is 13.8 billion years old — where is everyone?",
        "hook":        "The universe should be full of alien civilizations. So where are they?",
        "viral_score": 88,
    }
    logger.info("Testing Script Engine v0.3.1...")
    engine  = ScriptEngine()
    scripts = engine.generate_batch([test_topic], tenant, count=1)
    if scripts:
        s = scripts[0]
        print(f"\n{'='*60}")
        print(f"SCRIPT   : {s.get('title','')}")
        print(f"PROVIDER : {s.get('llm_provider_used','')} (requested: {s.get('llm_provider_requested','')}) ")
        print(f"SCORE    : {s.get('script_viral_score',0)}/100")
        print(f"WORDS    : {s.get('word_count', len(s.get('full_script','').split()))}")
        print(f"DURATION : ~{s.get('estimated_duration_seconds',51)}s")
        print(f"{'='*60}")
        for sec in ["hook","mystery_drop","build_up","pattern_interrupt",
                    "core_facts","curiosity_bridge","climax","cta"]:
            val = s.get(sec,"")
            if val:
                print(f"\n[{sec.upper().replace('_',' ')}]\n{val}")
        print(f"\n{'─'*40}")
        print("VISUAL SUGGESTIONS:")
        for i, vs in enumerate(s.get("visual_suggestions",[]),1):
            print(f"  {i}. {vs}")
        print(f"\nMUSIC MOOD: {s.get('background_music_mood','')}")
        print(f"\nTHUMBNAIL: {s.get('thumbnail_concept','')}")
        analysis = s.get("viral_analysis",{})
        if analysis.get("dimension_scores"):
            print("\nDIMENSION SCORES:")
            for k,v in analysis["dimension_scores"].items():
                bar = "█"*(v//10) + "░"*(10-v//10)
                print(f"  {k:<22} {bar} {v}/100")
    else:
        print("FAILED")
