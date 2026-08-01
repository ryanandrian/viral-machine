"""
[DURASI] ALAT UKUR biaya jeda per tanda baca — mengukur, bukan menyimpulkan.

═══ KENAPA MODUL INI ADA ═══

Biaya jeda (koma · em-dash · elipsis · akhir-kalimat) sebelumnya diturunkan lewat REGRESI dari naskah
produksi. Regresi dipaksa memisahkan enam pengaruh sekaligus dari data yang tidak dirancang untuk itu,
dan keempat tanda jeda bergerak bersama panjang naskah. Hasilnya angka yang tampak masuk akal tapi
salah — terukur 2026-08-01:

    id-ID-ArdiNeural   em-dash   regresi 1,137 dtk  ·  TERUKUR 0,424 dtk
    id-ID-GadisNeural  em-dash   regresi 1,262 dtk  ·  TERUKUR 0,400 dtk
    angka bawaan       elipsis           1,376 dtk  ·  TERUKUR 0,156 / 0,288 dtk
    angka bawaan       koma              0,221 dtk  ·  TERUKUR 0,396 / 0,388 dtk

Angka koma bawaan itu dipakai setiap suara yang belum terkalibrasi. Pada naskah 90 detik dengan 25
koma, selisih 0,17 dtk/koma = 4,3 detik — cukup untuk melempar video keluar batas sah.

═══ CARA UKUR YANG TAK BISA TERCAMPUR ═══

Untuk satu teks dasar berisi 4 klausa, dibuat lima versi yang HURUFNYA IDENTIK — hanya tanda di antara
klausanya berbeda:

    v0        A B C D.            (3 sambungan tanpa tanda)
    koma      A, B, C, D.
    em_dash   A — B — C — D.
    ellipsis  A... B... C... D.
    sentence  A. B. C. D.

Biaya satu tanda = (durasi versi bertanda − durasi v0) ÷ jumlah tanda yang ditambahkan. Karena
hurufnya identik, apa pun yang tersisa dari selisih itu HANYA milik tandanya. Terbukti sangat rapat:
rentang antar-6-teks hanya ±0,05 dtk.

Teks dasarnya ada di DB (`duration_probe_texts`), BUKAN di kode: mengganti teks = mengganti alat ukur,
jadi ia harus terlihat dan bisa ditambah (bahasa baru) tanpa developer.

═══ PAGAR ═══
  • Versi yang jumlah HURUFnya tidak identik → teks itu DIBUANG (selisihnya tak lagi murni milik tanda).
  • Biaya negatif atau di luar `duration_model.PAGAR` → DIBUANG (render cacat/vendor mengabaikan tanda).
  • Butuh minimal PROBE_MIN_TEKS teks yang lulus; kurang dari itu → tidak menghasilkan angka apa pun.
  • Memakai MEDIAN antar-teks (bukan rata-rata) supaya satu render aneh tak menggeser hasil.
  • Render memakai adaptor produksi yang sama → penjaga audio-terpotong ikut berlaku di sini.

BIAYA: modul ini MEMANGGIL penyedia suara (berbayar untuk ElevenLabs/fal). Karena itu ia TIDAK pernah
dipanggil otomatis dari pemeliharaan berkala — hanya saat seseorang memintanya untuk satu suara.
"""

from __future__ import annotations

import asyncio
import os
import statistics
import subprocess
from pathlib import Path

from loguru import logger

from src.config import ambang as _ambang
from src.production.duration_model import PAGAR, ciri_teks

# Tanda yang diukur → nama kolom ciri di `duration_model.ciri_teks` → kolom DB
TANDA = {
    "koma":     ("comma",    "sec_per_comma"),
    "em":       ("em_dash",  "sec_per_em_dash"),
    "elipsis":  ("ellipsis", "sec_per_ellipsis"),
    "titik":    ("sentence", "sec_per_sentence"),
}
# Penyusun versi. `v0` WAJIB ada — ia patokan yang lain.
VERSI = {
    "v0":      lambda k: " ".join(k) + ".",
    "koma":    lambda k: ", ".join(k) + ".",
    "em":      lambda k: " — ".join(k) + ".",
    "elipsis": lambda k: "... ".join(k) + ".",
    "titik":   lambda k: ". ".join(k) + ".",
}


def durasi_audio(path: str | Path) -> float:
    """Durasi berkas audio menurut ffprobe. Gagal → 0.0 (pemanggil membuang teks itu)."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, timeout=30).stdout.decode().strip()
        return float(out) if out else 0.0
    except Exception as e:
        logger.warning(f"[PauseProbe] ffprobe gagal {path}: {e}")
        return 0.0


def teks_probe(sb, lang: str) -> list[list[str]]:
    """Klausa alat ukur untuk satu bahasa, dari DB. Kosong → pemanggil berhenti jujur.
    Pencocokan bahasa memakai AWALAN (`en-US` → `en`): laju bicara milik bahasanya, bukan negaranya."""
    pre = (lang or "").split("-")[0].lower()
    rows = (sb.table("duration_probe_texts").select("idx,clauses,is_active,lang")
              .eq("lang", pre).eq("is_active", True).order("idx").execute().data or [])
    out = []
    for r in rows:
        c = r.get("clauses")
        if isinstance(c, list) and len(c) >= 2 and all(isinstance(x, str) and x.strip() for x in c):
            out.append([x.strip() for x in c])
    return out


def _biaya_dari_durasi(durasi: dict, ciri: dict) -> dict | None:
    """Biaya per tanda dari satu teks. None bila hurufnya tidak identik antar versi."""
    if "v0" not in durasi or durasi["v0"] <= 0:
        return None
    huruf = {v: c["chars"] for v, c in ciri.items()}
    if len(set(huruf.values())) != 1:
        logger.warning(f"[PauseProbe] teks dilewati — huruf tak identik antar versi: {huruf}")
        return None
    hasil = {}
    for vname, (kol, _db) in TANDA.items():
        if vname not in durasi or durasi[vname] <= 0:
            continue
        n = ciri[vname][kol] - ciri["v0"][kol]
        if n <= 0:
            continue
        hasil[vname] = (durasi[vname] - durasi["v0"]) / n
    return hasil or None


def ukur_jeda(voice_key: str, provider_key: str, config: dict, sb=None,
              lang: str | None = None, workdir: str | None = None) -> dict:
    """Ukur biaya tiap tanda jeda untuk SATU suara, lewat render nyata.

    `config` = konfigurasi adaptor apa adanya (kunci API, model, setelan suara) — dipakai persis
    seperti produksi supaya angkanya berlaku untuk produksi. Return:
        {"ok": bool, "voice_key", "nilai": {kolom_db: detik}, "n_teks": int, "rincian": [...], "error"}
    Fail-soft: exception apa pun → {"ok": False, "error": ...} tanpa melempar.
    """
    try:
        from src.providers.tts import build_tts_provider
        if sb is None:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        min_teks = _ambang.angka("probe_min_teks", 4)
        dasar = teks_probe(sb, lang or config.get("content_language") or "id")
        if len(dasar) < min_teks:
            return {"ok": False, "error": f"teks alat ukur bahasa '{lang}' hanya {len(dasar)} "
                                          f"(butuh {min_teks}) — isi tabel duration_probe_texts"}

        d = Path(workdir or f"/tmp/pause_probe/{voice_key[:24]}")
        d.mkdir(parents=True, exist_ok=True)

        per_tanda: dict[str, list[float]] = {k: [] for k in TANDA}
        rincian, lulus = [], 0
        for i, klausa in enumerate(dasar, 1):
            durasi, ciri = {}, {}
            for vname, fn in VERSI.items():
                teks = fn(klausa)
                f = d / f"{i:02d}_{vname}.mp3"
                if not f.exists() or f.stat().st_size < 2000:
                    prov = build_tts_provider(provider_key, config)
                    try:
                        asyncio.run(prov.generate(teks, f))
                    except Exception as e:
                        logger.warning(f"[PauseProbe] {voice_key} teks{i}/{vname} render gagal: {e}")
                        continue
                durasi[vname] = durasi_audio(f)
                ciri[vname] = ciri_teks(teks)
            biaya = _biaya_dari_durasi(durasi, ciri)
            if not biaya:
                continue
            lulus += 1
            rincian.append({"teks": i, "v0_detik": round(durasi["v0"], 2),
                            **{k: round(v, 3) for k, v in biaya.items()}})
            for k, v in biaya.items():
                per_tanda[k].append(v)

        if lulus < min_teks:
            return {"ok": False, "error": f"hanya {lulus} teks lulus (butuh {min_teks})",
                    "rincian": rincian}

        # ── SATU ANGKA HANYA SAH BILA PENGUKURANNYA SALING SETUJU ────────────────────────────────
        # Ditemukan 2026-08-01 pada percobaan pertama dengan ElevenLabs: nilai koma per-teks keluar
        # −0,244 · 0,122 · 0,244 · 0,505 · −0,226 · −0,104 → mediannya 0,009 dtk. Angka itu LOLOS
        # pemeriksaan "positif dan dalam pagar", lalu tersimpan sebagai "TERUKUR" — padahal artinya
        # "koma itu gratis", ranjau yang sama persis dengan yang modul ini dibuat untuk mencabut.
        #
        # Sebabnya bukan alat ukurnya: ElevenLabs bersifat tak-deterministik (setelan `stability` 0,3
        # membuat prosodinya diambil sampel tiap render), jadi dua render teks yang sama pun berbeda
        # durasinya. Selisih yang kita cari (0,2–0,4 dtk) tenggelam di dalam derau itu. Suara Edge
        # sebaliknya sangat rapat: sebaran antar-teks hanya ±0,05 dtk.
        #
        # Maka syaratnya bukan "hasilnya masuk akal", tapi "pengukurannya konsisten":
        #   (a) tandanya harus MENAMBAH waktu di hampir semua teks (bukan setengahnya negatif), dan
        #   (b) sebaran antar-teks (MAD) harus kecil secara MUTLAK — bukan relatif, karena tanda yang
        #       biayanya memang kecil (elipsis 0,156 dtk) akan selalu punya sebaran relatif besar.
        # Gagal → tandanya TIDAK dianggap terukur → angka BAWAAN yang dipakai. Menolak lebih baik
        # daripada menyimpan derau yang menyamar jadi pengukuran.
        min_positif = _ambang.pct("probe_min_positif_pct", 75)
        maks_mad    = _ambang.milidetik("probe_maks_mad_ms", 100)
        min_detik   = _ambang.milidetik("probe_min_detik_ms", 50)

        nilai, dibuang = {}, []
        for vname, (_kol, dbkol) in TANDA.items():
            v = per_tanda[vname]
            if len(v) < min_teks:
                dibuang.append(f"{dbkol}: hanya {len(v)} teks"); continue
            med = statistics.median(v)
            lo, hi = PAGAR[dbkol]
            if med <= 0 or not (lo <= med <= hi):
                dibuang.append(f"{dbkol}={med:.3f} di luar kewajaran {lo}..{hi}"); continue
            if med < min_detik:
                dibuang.append(f"{dbkol}={med:.3f} di bawah {min_detik} dtk — tak terbedakan dari derau")
                continue
            positif = sum(1 for q in v if q > 0) / len(v)
            if positif < min_positif:
                dibuang.append(f"{dbkol}: hanya {positif:.0%} teks menunjukkan tambahan waktu "
                               f"(butuh {min_positif:.0%}) — arahnya sendiri tidak konsisten")
                continue
            mad = statistics.median([abs(q - med) for q in v])
            if mad > maks_mad:
                dibuang.append(f"{dbkol}: sebaran antar-teks ±{mad:.3f} dtk > {maks_mad} — "
                               f"penyedia tidak konsisten, angkanya tak bisa dipercaya")
                continue
            nilai[dbkol] = round(med, 5)
        if dibuang:
            logger.warning(f"[PauseProbe] {voice_key} tanda dibuang: {dibuang}")
        if not nilai:
            return {"ok": False, "error": f"tak satu pun tanda menghasilkan angka wajar ({dibuang})",
                    "rincian": rincian}

        logger.info(f"[PauseProbe] {voice_key}: {lulus} teks · " +
                    " · ".join(f"{k}={v}" for k, v in nilai.items()))
        return {"ok": True, "voice_key": voice_key, "nilai": nilai, "n_teks": lulus,
                "dibuang": dibuang, "rincian": rincian}
    except Exception as e:
        logger.error(f"[PauseProbe] {voice_key} gagal (fail-soft): {e}")
        return {"ok": False, "error": str(e)}


def jeda_dari_timestamp(teks: str, kata_ts: list[dict]) -> dict:
    """Ukur biaya tiap tanda DARI DALAM SATU RENDER, memakai penanda waktu per kata.

    ═══ KENAPA CARA KEDUA INI ADA ═══
    Cara pasangan-terkontrol (`ukur_jeda`) mengandaikan penyedia menghasilkan audio yang SAMA untuk
    teks yang sama. Itu benar untuk Edge (sebaran antar-teks ±0,05 dtk) tapi TIDAK untuk ElevenLabs:
    setelan `stability` 0,3 membuat prosodinya diambil sampel tiap render. Terukur 2026-08-01, biaya
    koma versi ElevenLabs keluar −0,244 · 0,122 · 0,244 · 0,505 · −0,226 · −0,104 dtk — separuhnya
    negatif. Selisih yang dicari (0,2–0,4 dtk) tenggelam di dalam deraunya.

    Cara ini kebal terhadap derau itu, karena pembandingnya ADA DI DALAM RENDER YANG SAMA: jarak antar
    kata yang dipisahkan tanda, dibandingkan dengan jarak antar kata yang TIDAK dipisahkan tanda apa pun.
    Derau prosodi menggeser keduanya bersama-sama, jadi selisihnya bersih.

    Gratis: memakai penanda waktu yang memang sudah dikembalikan penyedia pada render biasa.

    Return {"comma": dtk, "em_dash": ..., "ellipsis": ..., "sentence": ..., "_n": {...}} — hanya berisi
    tanda yang datanya cukup. Teks & penanda tak sinkron → {} (menolak, bukan menebak).
    """
    if not teks or not kata_ts:
        return {}
    letak, pos = [], 0
    for w in kata_ts:
        kata = str(w.get("word") or "").strip()
        if not kata:
            continue
        i = teks.find(kata, pos)
        if i < 0:
            # Penanda tak bisa dipetakan ke teks (penyedia menormalkan angka jadi kata, dsb.) → berhenti
            # jujur. Menebak pemetaan berarti mengukur jarak antara dua kata yang salah.
            return {}
        pos = i + len(kata)
        try:
            letak.append((float(w.get("start")), float(w.get("end")), i, pos))
        except (TypeError, ValueError):
            return {}

    per: dict[str, list[float]] = {"none": [], "comma": [], "em_dash": [], "ellipsis": [], "sentence": []}
    for (_s1, e1, i1, akhir1), (s2, _e2, awal2, _p2) in zip(letak, letak[1:]):
        jarak = s2 - e1
        if jarak < 0 or jarak > 5:          # penanda cacat — jangan dipakai
            continue
        # Tanda baca sering MENEMPEL di dalam token kata ("storm," / "end."), sehingga teks di antara
        # dua token hanya berisi spasi. Percobaan pertama 2026-08-01 karena itu menemukan 1.823 jarak
        # antar-kata dan NOL tanda baca — alat ukurnya diam-diam tidak mengukur apa pun. Maka batasnya
        # diambil dari HURUF TERAKHIR kata ini sampai HURUF PERTAMA kata berikutnya, apa pun cara
        # penyedia memotong tokennya.
        p = akhir1
        while p > i1 and not teks[p - 1].isalnum():
            p -= 1
        q = awal2
        while q < len(teks) and not teks[q].isalnum():
            q += 1
        antara = teks[p:q]
        if "…" in antara or "..." in antara:
            per["ellipsis"].append(jarak)
        elif "—" in antara:
            per["em_dash"].append(jarak)
        elif any(ch in antara for ch in ".!?"):
            per["sentence"].append(jarak)
        elif any(ch in antara for ch in ",;:"):
            per["comma"].append(jarak)
        elif antara.strip() == "":
            per["none"].append(jarak)
    return {"_jarak": per}


def gabung_jeda_timestamp(semua: list[dict]) -> dict:
    """Gabungkan hasil `jeda_dari_timestamp` dari BANYAK render jadi satu biaya per tanda.

    Biaya tanda = median(jarak saat ada tanda) − median(jarak saat TIDAK ada tanda apa pun). Yang kedua
    adalah jeda alami antar kata; tanpa menguranginya, setiap tanda tampak lebih mahal dari semestinya.
    """
    per: dict[str, list[float]] = {"none": [], "comma": [], "em_dash": [], "ellipsis": [], "sentence": []}
    for h in semua:
        for k, v in (h.get("_jarak") or {}).items():
            per[k].extend(v)
    if len(per["none"]) < _ambang.angka("probe_ts_min_dasar", 30):
        return {"ok": False, "error": f"hanya {len(per['none'])} jarak antar-kata tanpa tanda "
                                      f"(butuh {_ambang.angka('probe_ts_min_dasar', 30)}) — tak ada pembanding"}
    dasar = statistics.median(per["none"])
    min_n = _ambang.angka("probe_ts_min_tanda", 12)
    nilai, dibuang, rincian = {}, [], {"jarak_dasar": round(dasar, 4), "n_dasar": len(per["none"])}
    for kol_ciri, dbkol in (("comma", "sec_per_comma"), ("em_dash", "sec_per_em_dash"),
                            ("ellipsis", "sec_per_ellipsis"), ("sentence", "sec_per_sentence")):
        v = per[kol_ciri]
        rincian[kol_ciri] = {"n": len(v), "median": round(statistics.median(v), 4) if v else None}
        if len(v) < min_n:
            dibuang.append(f"{dbkol}: hanya {len(v)} kemunculan (butuh {min_n})"); continue
        biaya = statistics.median(v) - dasar
        lo, hi = PAGAR[dbkol]
        if biaya <= 0.02 or not (lo <= biaya <= hi):
            dibuang.append(f"{dbkol}={biaya:.3f} tak wajar/tak terbedakan dari jeda alami"); continue
        nilai[dbkol] = round(biaya, 5)
    return {"ok": bool(nilai), "nilai": nilai, "dibuang": dibuang, "rincian": rincian,
            "error": None if nilai else f"tak satu pun tanda menghasilkan angka wajar ({dibuang})"}


def simpan_jeda(sb, voice_key: str, nilai: dict, n_teks: int) -> dict:
    """Tulis biaya jeda terukur + tandai `pause_source='measured'` supaya kalibrasi berkala
    MEMATOKNYA (kalau tidak, siklus berikutnya menimpanya dengan angka regresi lagi).

    MENAMBAL, TIDAK MENIMPA. `upsert` di postgrest MENGGANTI seluruh baris: percobaan pertama
    2026-08-01 nyaris menghapus `sec_per_char`, `chars_per_word`, dan `delivery_wps` milik suara yang
    sudah terkalibrasi — hanya diselamatkan oleh batasan NOT NULL. Modul ini hanya berhak atas kolom
    jeda; kolom lain milik `pace_calibration`."""
    from datetime import datetime, timezone
    kolom = {**nilai, "pause_source": "measured",
             "pause_measured_at": datetime.now(timezone.utc).isoformat(),
             # konvensi kode: penulis menyetel updated_at sendiri
             "updated_at": datetime.now(timezone.utc).isoformat()}
    ada = (sb.table("tts_pace_calibration").select("voice_key")
             .eq("voice_key", voice_key).eq("niche", "*").limit(1).execute().data or [])
    if ada:
        sb.table("tts_pace_calibration").update(kolom).eq("voice_key", voice_key).eq("niche", "*").execute()
    else:
        # `sample_n` = jumlah sampel PRODUKSI yang mem-fit huruf/angka — belum ada satu pun untuk suara
        # baru, jadi 0 (bukan `n_teks`: teks alat ukur bukan sampel produksi; menyamakan keduanya akan
        # membuat baris ini tampak lebih terkalibrasi daripada kenyataannya).
        sb.table("tts_pace_calibration").insert(
            {"voice_key": voice_key, "niche": "*", "sample_n": 0, **kolom}).execute()
    logger.info(f"[PauseProbe] {voice_key} biaya jeda TERUKUR tersimpan (n_teks={n_teks}, "
                f"{'perbarui' if ada else 'baris baru'})")
    return {"ok": True, "voice_key": voice_key, "nilai": nilai, "baris_baru": not ada}
