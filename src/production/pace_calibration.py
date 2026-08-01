"""
[DURASI] Kalibrasi durasi dari render NYATA — mesin mengukur dirinya sendiri.

APA YANG DIHITUNG (satu sumber data: `tts_delivery_samples`)
  Koefisien model durasi per SUARA → `tts_pace_calibration`:
      detik_audio = a·huruf + b·ANGKA + c·kalimat + d·elipsis + e·koma + f·em_dash
  plus dua angka bentuk naskah (`chars_per_word`, `words_per_sentence`) yang dipakai menerjemahkan
  target detik menjadi perintah JUMLAH KATA & JUMLAH KALIMAT ke penulis, dan `calib_error_secs` =
  kesalahan LUAR-SAMPEL angka itu sendiri.

AKAR (diukur 2026-07-31 dari 294 produksi nyata; rincian: QC_CONTENT_ARCHITECTURE.md §2c)
  Hanya 22% video mendarat di batas titik-tengah owner. Estimator lama meramal `kata ÷ (wps × 1,10)
  + Σ jeda_BENIH`; angka jedanya tak pernah dikalibrasi (benih akhir-kalimat 0,35 dtk vs terukur
  0,60–1,31). Salah rata-rata 7,01 dtk pada 60 render naskah produksi — dan selisihnya ditambal
  dengan MEMPERLAMBAT SUARA (41% render mentok di batas 0,70; NOL render normal). Owner melarang
  tuas kecepatan; maka alat ukurnya yang harus benar.

  Modul ini juga TIDAK LAGI menginversi pace lewat model jeda (cara lama), yang berputar di dalam
  kesalahannya sendiri: `wps = kata ÷ ((audio − jeda_benih) × speed^α × 1,10)` — jeda yang salah
  berpindah jadi pace yang salah, lalu pace itu dipakai lagi menghitung anggaran kata. Sekarang
  seluruh koefisien di-fit SEKALIGUS dari (huruf, angka, tanda baca) → audio, tanpa asumsi apa pun.
  Suku ANGKA ada karena terukur: satu tahun empat-angka menambah 1,70 dtk padahal hanya 4 huruf
  ("1348" dibacakan "seribu tiga ratus empat puluh delapan"). Menambahnya menurunkan kesalahan
  luar-sampel di 4 dari 5 suara produksi.

KEJUJURAN ANGKA
  `calib_error_secs` dihitung LEAVE-ONE-OUT: tiap sampel diramal oleh koefisien yang di-fit TANPA
  sampel itu. Jadi angka yang dilaporkan adalah kesalahan pada data yang BELUM pernah dilihat —
  bukan angka yang dipoles oleh datanya sendiri. Terbukti membedakan: model per-KATA 1,55 dtk vs
  per-HURUF 0,96 dtk (n=60); tanpa leave-one-out keduanya tampak jauh lebih bagus.

PAGAR ANTI-RANJAU
  • HANYA menulis kolom yang ditambahkan migrasi 0182 (+ `delivery_wps` lapis lama, tetap diisi
    supaya jalur cadangan tidak mati). Tabel kosong = perilaku bawaan `duration_model` (terukur).
  • Sampel dipakai HANYA bila kecepatan suara ≈1,0 — sejak tuas kecepatan dicabut itulah satu-satunya
    keadaan yang sah. Sampel lama ber-speed 0,7–1,3 DIBUANG eksplisit (dilaporkan jumlahnya), sebab
    memasukkannya berarti mengkalibrasi dunia yang sudah tidak ada.
  • `voice_catalog.pace_locked=true` → suara TIDAK ditulis + baris kalibrasi lamanya DIHAPUS (admin berdaulat).
  • Sel < PACE_CALIB_MIN_N sampel tidak ditulis (kurang bukti ≠ menebak).
  • Per KOLOM juga: tanda yang muncul di < PACE_CALIB_MIN_FITUR_N naskah TIDAK dapat koefisien —
    dikosongkan agar `duration_model.BAWAAN` yang terukur dipakai. Kolom "ada tapi jarang" lebih
    berbahaya daripada kolom kosong: hasilnya angka yang tampak masuk akal (terukur: em-dash 1,137
    dtk dari 6 naskah, sementara suara ber-data-tebal 0,16–0,25).
  • Koefisien di luar pagar `duration_model.PAGAR` → seluruh sel DILEWATI + warning. Tidak di-clamp
    diam-diam: data rusak tidak boleh menyelinap jadi angka yang tampak masuk akal.
  • Kesalahan luar-sampel di atas PACE_CALIB_MAX_ERR → sel DILEWATI (angka yang tak lebih baik dari
    bawaan tidak dipasang).

Penjadwalan berkala + alarm drift = `run_maintenance` (dipanggil self_learning tiap cadence).
"""

import json
import os
import statistics
from loguru import logger

from src.config import ambang as _ambang

# Kolom fit: satuan bicara + empat tanda jeda. Urutan ini mengikat nama kolom DB di bawah.
_FIT_KOL = ["chars", "digits", "sentence", "ellipsis", "comma", "em_dash"]
_KOL_DB = {"chars": "sec_per_char", "digits": "sec_per_digit", "sentence": "sec_per_sentence",
           "ellipsis": "sec_per_ellipsis", "comma": "sec_per_comma", "em_dash": "sec_per_em_dash"}
# Rentang kecepatan yang dianggap "normal" (tuas kecepatan sudah dicabut → produksi selalu di sini).
_SPEED_LO, _SPEED_HI = 0.98, 1.02


def _fit(rows: list) -> list | None:
    """Kuadrat terkecil untuk detik = Σ x_j · ciri_j.

    ═══ SATU KOLOM HANYA BOLEH PUNYA KOEFISIEN BILA ADA CUKUP BUKTI UNTUKNYA ═══

    Kembaliannya `None` untuk kolom yang buktinya kurang — BUKAN 0. Bedanya menentukan: menulis 0
    berarti memberi tahu mesin "tanda ini GRATIS", dan itu salah. `None` membuat
    `duration_model.angka_efektif` memakai angka BAWAAN terukur untuk kunci itu.

    Dua kegagalan NYATA yang terhitung di DB 2026-08-01 — keduanya lahir dari aturan lama
    `any(r[k] for r in rows)` ("ada satu saja, fit-lah"):

      1. `sec_per_ellipsis = 0,000` untuk kedua suara Indonesia. Sebabnya: 36 naskah kalibrasi memuat
         NOL elipsis, jadi kolomnya seluruh-nol dan ter-fit 0. Biaya nyatanya >1 detik per tanda.
         Setiap naskah produksi yang memakai "..." diramal terlalu pendek, tanpa jejak apa pun.
      2. `sec_per_em_dash = 1,137` (Ardi) dan `1,262` (Gadis) — di-fit dari hanya 6 naskah / 20
         kemunculan. Bandingkan tiga suara Inggris yang datanya tebal: 0,164–0,247. Jadi angka ID-nya
         5–7× lipat: itu bukan pengukuran, itu derau yang menyamar jadi pengukuran. Naskah dengan 4
         em-dash akan salah ramal ~4 detik ke arah yang salah.

    Kolom "ada tapi jarang" justru LEBIH berbahaya daripada kolom yang kosong: kolom kosong menghasilkan
    0 yang mencurigakan, sedangkan kolom jarang menghasilkan angka yang tampak masuk akal. Karena itu
    ambangnya BUKAN "ada/tidak ada", tapi "muncul di cukup banyak naskah".
    """
    min_bukti = _ambang.angka("pace_calib_min_fitur_n", 10)
    # Ambang tak boleh melebihi ukuran selnya sendiri — kalau tidak, kolom yang HADIR DI SEMUA sampel
    # (huruf, kalimat) ikut tertolak dan seluruh fit mati. Batas bawah 3: di bawah itu satu naskah
    # aneh sudah cukup menentukan koefisien.
    min_bukti = max(3, min(min_bukti, len(rows)))
    aktif = [j for j, k in enumerate(_FIT_KOL)
             if sum(1 for r in rows if r[k]) >= min_bukti]
    if not aktif:
        return None
    n = len(aktif)
    N = [[sum(r[_FIT_KOL[a]] * r[_FIT_KOL[b]] for r in rows) for b in aktif]
         + [sum(r[_FIT_KOL[a]] * r["audio"] for r in rows)] for a in aktif]
    for i in range(n):
        pv = max(range(i, n), key=lambda x: abs(N[x][i]))
        if abs(N[pv][i]) < 1e-12:
            return None
        N[i], N[pv] = N[pv], N[i]
        for r in range(n):
            if r != i:
                f = N[r][i] / N[i][i]
                for cc in range(i, n + 1):
                    N[r][cc] -= f * N[i][cc]
    x = [None] * len(_FIT_KOL)          # None = tak teridentifikasi (bukan "gratis")
    for i, j in enumerate(aktif):
        x[j] = N[i][n] / N[i][i]
    return x


def _fit_jeda_dipatok(rows: list, jeda: dict) -> list | None:
    """Fit HANYA huruf + angka, dengan biaya jeda DIPATOK pada angka yang sudah diukur langsung.

    Kenapa ini lebih akurat: regresi 6-koefisien dipaksa memisahkan empat jenis jeda yang semuanya
    bergerak bersama panjang naskah, dari data yang tidak dirancang untuk itu. Bila biaya jeda sudah
    diketahui dari pengukuran terkontrol (`pause_probe`), biaya itu cukup DIKURANGKAN dari audio dan
    sisanya hanya menyisakan dua parameter untuk di-fit — jauh lebih stabil.

    Terbukti pada 36 render yang sama (leave-one-out, rentang preset produksi ≤100 dtk):
        id-ID-ArdiNeural   salah rata 1,47 → 1,18 dtk · terburuk 5,33 → 3,76 dtk
        id-ID-GadisNeural  salah rata 1,82 → 1,58 dtk · terburuk 5,89 → 4,61 dtk

    `jeda` = {nama_kolom_ciri: detik} untuk tanda yang dipatok. Kembalian bentuknya sama dengan `_fit`
    (sejajar `_FIT_KOL`): kolom yang dipatok berisi angka patokan, huruf/angka hasil fit.
    """
    kol = [k for k in ("chars", "digits") if sum(1 for r in rows if r[k]) >= 3]
    if "chars" not in kol:
        return None
    n = len(kol)
    sisa = [r["audio"] - sum(v * r[k] for k, v in jeda.items()) for r in rows]
    N = [[sum(r[kol[a]] * r[kol[b]] for r in rows) for b in range(n)]
         + [sum(r[kol[a]] * s for r, s in zip(rows, sisa))] for a in range(n)]
    for i in range(n):
        pv = max(range(i, n), key=lambda x: abs(N[x][i]))
        if abs(N[pv][i]) < 1e-12:
            return None
        N[i], N[pv] = N[pv], N[i]
        for r in range(n):
            if r != i:
                f = N[r][i] / N[i][i]
                for cc in range(i, n + 1):
                    N[r][cc] -= f * N[i][cc]
    x = [None] * len(_FIT_KOL)
    for i, k in enumerate(kol):
        x[_FIT_KOL.index(k)] = N[i][n] / N[i][i]
    for k, v in jeda.items():
        if k in _FIT_KOL:
            x[_FIT_KOL.index(k)] = v
    return x


def _ramal(x: list, r: dict) -> float:
    """Kolom tak teridentifikasi (None) memakai angka BAWAAN terukur, bukan dianggap nol."""
    from src.production.duration_model import BAWAAN
    tot = 0.0
    for j, k in enumerate(_FIT_KOL):
        koef = x[j] if x[j] is not None else BAWAAN[_KOL_DB[k]]
        tot += koef * r[k]
    return tot


def _error_luar_sampel(rows: list, jeda: dict | None = None) -> float | None:
    """Leave-one-out: tiap sampel diramal oleh fit TANPA sampel itu. Inilah satu-satunya angka
    kesalahan yang boleh dipercaya (fit pada datanya sendiri selalu tampak lebih bagus).
    `jeda` diisi → dinilai dengan cara yang SAMA seperti yang dipakai produksi (jeda dipatok)."""
    errs = []
    for i in range(len(rows)):
        sisa_rows = rows[:i] + rows[i + 1:]
        x = _fit_jeda_dipatok(sisa_rows, jeda) if jeda else _fit(sisa_rows)
        if x is None:
            return None
        errs.append(abs(_ramal(x, rows[i]) - rows[i]["audio"]))
    return statistics.mean(errs) if errs else None


def compute_pace_calibration(sb=None, dry_run: bool = False) -> dict:
    """Fit koefisien durasi per SUARA dari `tts_delivery_samples` → `tts_pace_calibration`.
    dry_run=True → hitung saja, NOL tulis. Fail-soft total: exception → log + {"error": ...};
    TIDAK pernah mengganggu produksi."""
    try:
        from src.production.duration_model import PAGAR
        if sb is None:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        min_n = _ambang.angka("pace_calib_min_n", 14)         # fit 6 koefisien butuh cukup titik
        min_chars = _ambang.angka("pace_calib_min_chars", 60)  # naskah super-pendek = rasio jeda liar
        max_err = _ambang.milidetik("pace_calib_max_err_ms", 2500)  # tak lebih baik dari bawaan: buang

        from src.production.voice_delivery import laju_sama, rasio_dari_teks, rasio_laju
        _vc = (sb.table("voice_catalog").select("voice_key,pace_locked,default_settings")
                 .execute().data or [])
        locked = {r["voice_key"] for r in _vc if r.get("pace_locked")}
        # [0184] Baseline laju suara SAAT INI. Sampel yang direkam pada baseline BERBEDA tidak boleh
        # ikut di-fit: kesalahan paling mahal 2026-07-31 adalah mengukur pada baseline lain dari
        # produksi (selisih 15% pada laju bicara) tanpa apa pun di sistem yang memberi tahu — dua hari
        # pengukuran terbuang, dan koefisiennya akan tampak "terkalibrasi" padahal salah.
        #
        # [0185] Dibandingkan sebagai RASIO, bukan sebagai teks. Versi teks punya cacat yang
        # mematikan tanpa suara: hanya adaptor Edge menuliskan `rate` bergaya persen, sehingga
        # perbandingan teks menolak SETIAP sampel ElevenLabs/fal/OpenAI (rekamannya kosong atau
        # bergaya `speed`). Akibatnya suara berbayar tak akan pernah terkalibrasi — selamanya, tanpa
        # satu pun pesan error. Rasio dihitung satu fungsi bersama (`voice_delivery`) yang juga dipakai
        # adaptor, jadi kedua sisi tak bisa berbeda diam-diam.
        BASELINE = {r["voice_key"]: rasio_laju(r.get("default_settings")) for r in _vc}
        # Baris kalibrasi yang biaya jedanya SUDAH DIUKUR LANGSUNG → dipatok, bukan di-fit ulang.
        # Tanpa ini, siklus berikutnya menimpa angka terukur dengan angka regresi dan ranjaunya kembali
        # sendiri (em-dash 1,137 dtk padahal terukur 0,424).
        _pc_lama = (sb.table("tts_pace_calibration")
                      .select("voice_key,niche,pause_source,sec_per_comma,sec_per_em_dash,"
                              "sec_per_ellipsis,sec_per_sentence")
                      .eq("niche", "*").execute().data or [])
        JEDA_TERUKUR = {}
        for r in _pc_lama:
            if (r.get("pause_source") or "") != "measured":
                continue
            j = {}
            for kol_ciri, kol_db in (("comma", "sec_per_comma"), ("em_dash", "sec_per_em_dash"),
                                     ("ellipsis", "sec_per_ellipsis"), ("sentence", "sec_per_sentence")):
                v = r.get(kol_db)
                if v is not None:
                    j[kol_ciri] = float(v)
            if j:
                JEDA_TERUKUR[r["voice_key"]] = j

        rows, off = [], 0
        while True:  # paginasi manual — jangan percaya cap default (pelajaran undercount 7.220-vs-1000)
            b = (sb.table("tts_delivery_samples")
                   .select("voice_key,niche,speed,words,chars,raw_audio_secs,audio_secs,"
                           "pause_counts,voice_rate")
                   .range(off, off + 999).execute().data or [])
            rows += b
            if len(b) < 1000:
                break
            off += 1000

        ok, buang = [], {"tanpa_huruf": 0, "speed_bukan_1": 0, "tak_lengkap": 0,
                         "terlalu_pendek": 0, "setelan_suara_beda": 0}
        for r in rows:
            try:
                vk, pc = r.get("voice_key"), r.get("pause_counts") or {}
                ch = r.get("chars")
                sp = float(r.get("speed") or 0)
                au = float(r.get("raw_audio_secs") or r.get("audio_secs") or 0)
                if not vk or not pc or au <= 0:
                    buang["tak_lengkap"] += 1; continue
                if ch is None:
                    buang["tanpa_huruf"] += 1; continue      # sampel pra-0182 → tak bisa dipakai model huruf
                if not (_SPEED_LO <= sp <= _SPEED_HI):
                    buang["speed_bukan_1"] += 1; continue    # dunia lama (suara dimodulasi) — tak sah lagi
                if int(ch) < min_chars:
                    buang["terlalu_pendek"] += 1; continue
                # [0184/0185] laju harus SAMA dengan baseline suara saat ini; kosong = tak bisa
                # diverifikasi asalnya → dibuang (lebih baik menolak daripada mengarang keyakinan).
                # Dibandingkan sebagai rasio → berlaku untuk SEMUA penyedia, bukan hanya Edge.
                if not laju_sama(rasio_dari_teks(r.get("voice_rate")), BASELINE.get(vk)):
                    buang["setelan_suara_beda"] += 1; continue
                ok.append({"vk": vk, "niche": r.get("niche") or "*", "audio": au, "chars": int(ch),
                           "digits": int(pc.get("digits") or 0), "words": int(r.get("words") or 0),
                           "sentence": int(pc.get("sentence") or 0), "ellipsis": int(pc.get("ellipsis") or 0),
                           "comma": int(pc.get("comma") or 0), "em_dash": int(pc.get("em_dash") or 0)})
            except Exception:
                buang["tak_lengkap"] += 1

        ditulis, dilewati = [], []
        per_suara = {}
        for s in ok:
            if s["vk"] in locked:
                continue
            per_suara.setdefault(s["vk"], []).append(s)

        for vk, g in sorted(per_suara.items()):
            if len(g) < min_n:
                dilewati.append((vk, f"sampel {len(g)} < {min_n}")); continue
            # Biaya jeda sudah diukur langsung? → DIPATOK, hanya huruf+angka yang di-fit (lebih akurat,
            # terbukti). Belum? → regresi biasa dengan aturan bukti-minimum per kolom.
            jeda_patok = JEDA_TERUKUR.get(vk)
            x = _fit_jeda_dipatok(g, jeda_patok) if jeda_patok else _fit(g)
            if x is None:
                dilewati.append((vk, "sistem tak terpecahkan")); continue
            # Kolom tak teridentifikasi TIDAK ditulis (None) → `angka_efektif` memakai bawaan terukur.
            nilai = {_KOL_DB[k]: (round(x[j], 5) if x[j] is not None else None)
                     for j, k in enumerate(_FIT_KOL)}
            luar = [f"{k}={v}" for k, v in nilai.items()
                    if v is not None and not (PAGAR[k][0] <= v <= PAGAR[k][1])]
            if luar:
                dilewati.append((vk, f"koefisien di luar pagar: {', '.join(luar)}"))
                logger.warning(f"[PaceCalib] {vk} DILEWATI — {luar} (tidak di-clamp; data dicurigai)")
                continue
            err = _error_luar_sampel(g, jeda_patok)
            if err is None or err > max_err:
                dilewati.append((vk, f"kesalahan luar-sampel {err} > {max_err}"))
                logger.warning(f"[PaceCalib] {vk} DILEWATI — kesalahan luar-sampel {err} dtk "
                               f"tidak lebih baik dari angka bawaan")
                continue
            hpk = statistics.median([r["chars"] / max(1, r["words"]) for r in g if r["words"]])
            wpk = statistics.median([r["words"] / max(1, r["sentence"]) for r in g if r["sentence"]])
            baris = {"voice_key": vk, "niche": "*", "sample_n": len(g),
                     **nilai,
                     # Ditulis eksplisit supaya keadaannya tak pernah ambigu di DB maupun di layar
                     # admin: 'measured' = biaya jeda dari pengukuran terkontrol dan DIPATOK di sini.
                     "pause_source": "measured" if jeda_patok else "fitted",
                     "chars_per_word": round(hpk, 3), "words_per_sentence": round(wpk, 3),
                     "calib_error_secs": round(err, 3),
                     # lapis lama tetap diisi supaya jalur cadangan (preset di luar tangga) tak mati
                     "delivery_wps": round(statistics.median([r["words"] / r["audio"] for r in g]), 3)}
            for k in ("chars_per_word", "words_per_sentence"):
                if not (PAGAR[k][0] <= baris[k] <= PAGAR[k][1]):
                    baris[k] = None                      # di luar pagar → biarkan bawaan yang dipakai
            ditulis.append(baris)
            logger.info(f"[PaceCalib] {vk}: n={len(g)} · {nilai['sec_per_char']:.5f}/huruf · "
                        f"jeda-kalimat {nilai['sec_per_sentence']:.2f}s · salah luar-sampel {err:.2f}s")

        # ── SAPU BARIS WARISAN yang tak bisa diverifikasi (§3.2 nol fosil) ────────────────────────
        # Terhitung di DB 2026-08-01: 11 dari 18 baris hanya berisi `delivery_wps` dari algoritma LAMA
        # (inversi lewat model jeda yang salah, disaring dari sampel ber-kecepatan 0,7–1,3 — dunia yang
        # sudah tidak ada). Baris seperti itu tidak bisa dipakai model baru DAN tidak bisa diverifikasi
        # asalnya. Membiarkannya = angka basi yang menunggu dipakai jalur cadangan, dan itu ranjau.
        # Dibuang HANYA setelah suara itu punya baris ber-koefisien yang sah — jadi tak pernah ada
        # keadaan "kalibrasi hilang". Suara yang dikunci admin tidak disentuh.
        sapu = [b["voice_key"] for b in ditulis]
        if not dry_run:
            if ditulis:
                sb.table("tts_pace_calibration").upsert(ditulis).execute()
            for vk in sapu:
                if vk in locked:
                    continue
                sb.table("tts_pace_calibration").delete().eq("voice_key", vk) \
                  .neq("niche", "*").is_("sec_per_char", "null").execute()
            for vk in locked:
                sb.table("tts_pace_calibration").delete().eq("voice_key", vk).execute()

        ringkas = {"sampel_total": len(rows), "sampel_dipakai": len(ok), "dibuang": buang,
                   "baris_warisan_disapu_utk": sapu,
                   "suara_ditulis": len(ditulis), "dilewati": dilewati,
                   "locked": sorted(locked), "min_n": min_n, "dry_run": dry_run, "rows": ditulis}
        logger.info(f"[PaceCalib] total={len(rows)} dipakai={len(ok)} dibuang={buang} "
                    f"ditulis={len(ditulis)} dilewati={len(dilewati)} dry_run={dry_run}")
        return ringkas
    except Exception as e:
        logger.error(f"[PaceCalib] gagal (fail-soft, produksi tak terganggu): {e}")
        return {"error": str(e)}


# ── [DURASI-F5] SWA-PEMELIHARAAN — dipanggil berkala dari self_learning (fail-soft total) ────────────


def align_beat_weights(sb=None, dry_run: bool = False) -> dict:
    """[F5] Selaraskan `content_beats.weight` ke KENYATAAN (porsi kata nyata per-beat dari
    `tts_delivery_samples.beat_words` — hitungan sistem, bukan laporan LLM).
    Keputusan owner (delegasi 2026-07-16): dinamis-SEDERHANA — bukan optimasi kreatif; hanya
    kalibrasi deskriptif (bobot mengikuti apa yang nyatanya ditulis, agar kuota jujur).
    PAGAR: `weight_locked=true` → beat TAK disentuh · min-sampel per-beat (BEAT_ALIGN_MIN_N) ·
    langkah DIBATASI ±BEAT_ALIGN_MAX_STEP_PCT per siklus (geser halus, tak pernah melompat) ·
    bobot integer ≥1 · pembulatan tanpa-perubahan = tanpa-tulis · semua perubahan di-log."""
    try:
        if sb is None:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        min_n    = _ambang.angka("beat_align_min_n", 10)
        step_pct = max(0.01, min(0.5, _ambang.pct("beat_align_max_step_pct", 20)))

        beats = {r["beat_key"]: r for r in
                 (sb.table("content_beats").select("beat_key,weight,weight_locked").execute().data or [])}
        rows, off = [], 0
        while True:
            b = (sb.table("tts_delivery_samples").select("beat_words")
                   .not_.is_("beat_words", "null").range(off, off + 999).execute().data or [])
            rows += b
            if len(b) < 1000:
                break
            off += 1000

        # Rasio per-beat per-sampel: porsi NYATA ÷ porsi KONFIGURASI (dihitung atas set beat sampel itu
        # sendiri — set aktif beda per preset, membandingkan share global = salah).
        ratios: dict[str, list] = {}
        for r in rows:
            bw = r.get("beat_words") or {}
            keys = [k for k in bw if k in beats and isinstance(bw[k], (int, float)) and bw[k] > 0]
            tot_w = sum(float(bw[k]) for k in keys)
            tot_cfg = sum(float(beats[k]["weight"]) for k in keys)
            if len(keys) < 1 or tot_w <= 0 or tot_cfg <= 0:
                continue
            for k in keys:
                share_real = float(bw[k]) / tot_w
                share_cfg  = float(beats[k]["weight"]) / tot_cfg
                if share_cfg > 0:
                    ratios.setdefault(k, []).append(share_real / share_cfg)

        changes, skipped_lock, below = [], [], 0
        for bk, rs in sorted(ratios.items()):
            if len(rs) < min_n:
                below += 1; continue
            row = beats[bk]
            if row.get("weight_locked"):
                skipped_lock.append(bk); continue
            old = int(row["weight"])
            med = statistics.median(rs)
            target = old * med
            # langkah dibatasi: bergerak menuju target, maksimal ±step_pct dari nilai lama
            bounded = max(old * (1 - step_pct), min(old * (1 + step_pct), target))
            new = max(1, round(bounded))
            if new != old:
                changes.append({"beat_key": bk, "old": old, "new": new,
                                "ratio_median": round(med, 3), "n": len(rs)})
                if not dry_run:
                    sb.table("content_beats").update({"weight": new}).eq("beat_key", bk).execute()
                logger.info(f"[BeatAlign] {bk}: weight {old} → {new} (rasio nyata/cfg {med:.3f}, n={len(rs)}, "
                            f"step≤±{int(step_pct*100)}%){' [DRY]' if dry_run else ''}")
        summary = {"samples": len(rows), "changes": changes, "locked_skipped": skipped_lock,
                   "beats_below_min_n": below, "min_n": min_n, "dry_run": dry_run}
        logger.info(f"[BeatAlign] samples={len(rows)} changes={len(changes)} locked={len(skipped_lock)} below_min={below}")
        return summary
    except Exception as e:
        logger.error(f"[BeatAlign] gagal (fail-soft): {e}")
        return {"error": str(e)}


# ── Teks alarm drift: fungsi MURNI supaya bisa diuji tanpa mengirim Telegram sungguhan ──────────
# Owner 2026-07-28: pesan lama menyebut angka TANPA arah, jadi angka yang sedang MEMBAIK
# (12,8→12,3→11,5→10,4%) terbaca seolah macet — owner 5 hari mengira sistem rusak padahal ia sedang
# menyembuhkan diri. Pesan lama juga menyuruh "panggil developer bila muncul lagi besok", padahal
# muncul-lagi itu WAJAR selama angkanya turun. Dan saat akhirnya normal, tak ada kabar apa pun.

def _baca_state(sb, key: str) -> dict:
    """Status alarm drift dari app_config (JSON di value_text). Fail-soft: gagal baca → anggap kosong,
    alarm tetap boleh berbunyi (lebih baik dering ganda daripada bisu senyap)."""
    try:
        row = (sb.table("app_config").select("value_text").eq("key", key).limit(1).execute().data or [])
        if row and row[0].get("value_text"):
            v = json.loads(row[0]["value_text"])
            if isinstance(v, dict):
                return v
    except Exception as e:
        logger.warning(f"[DriftAlarm] baca status gagal (dianggap kosong): {e}")
    return {}


def _simpan_state(sb, key: str, med: float, alarming: bool) -> None:
    """Rekam median + status alarm. `last_at` HANYA diperbarui saat benar-benar mengirim alarm,
    supaya rem 24 jam tidak ikut ter-reset oleh pemeriksaan yang diam."""
    try:
        from datetime import datetime, timezone
        lama = _baca_state(sb, key)
        state = {"median": round(float(med), 2), "alarming": bool(alarming),
                 "last_at": datetime.now(timezone.utc).isoformat() if alarming else lama.get("last_at")}
        sb.table("app_config").upsert({
            "key": key, "value": 0,   # kolom NOT NULL (int); isi sebenarnya di value_text
            "value_text": json.dumps(state),
            "description": "OPS (otomatis, jangan diubah manual): status alarm drift durasi — median terakhir, sedang-alarm?, waktu alarm terakhir",
        }).execute()
    except Exception as e:
        logger.warning(f"[DriftAlarm] tulis status gagal (non-fatal): {e}")


def _drift_alarm_text(med: float, thresh: float, n: int, prev: float | None) -> str:
    """Pesan saat akurasi masih di bawah standar — SELALU menyebut arah pergerakan."""
    if prev is None:
        arah = "Ini pemeriksaan pertama sejak mesin mulai mengoreksi."
        saran = "Bila besok angkanya TIDAK turun, minta developer memeriksa."
    elif med < prev - 0.05:
        arah = f"MEMBAIK dari {prev:.1f}% pada pemeriksaan sebelumnya — mesin sedang mengoreksi diri."
        saran = "Tidak perlu tindakan apa pun; cukup pantau sampai kembali normal."
    elif med > prev + 0.05:
        arah = f"MEMBURUK dari {prev:.1f}% pada pemeriksaan sebelumnya."
        saran = "Minta developer memeriksa — biasanya ada suara/model baru yang datanya belum terkumpul."
    else:
        arah = f"TIDAK BERUBAH dari {prev:.1f}% pada pemeriksaan sebelumnya."
        saran = "Bila besok masih sama, minta developer memeriksa — koreksi otomatis tampaknya mentok."
    return (f"⚠️ Pemeriksaan otomatis MesinViral — akurasi durasi video di bawah standar: "
            f"rata-rata meleset {med:.1f}% (batas wajar {thresh:.0f}%) pada {n} video terakhir.\n"
            f"📉 {arah}\n"
            f"👉 {saran}")


def _drift_recovery_text(med: float, thresh: float, n: int, prev: float | None) -> str:
    """Pesan SEKALI saat akurasi kembali normal — tanpa ini, diam bisa berarti 'beres' atau 'alarm rusak'."""
    dari = f" (sebelumnya {prev:.1f}%)" if prev is not None else ""
    return (f"✅ Akurasi durasi video sudah KEMBALI NORMAL: rata-rata meleset {med:.1f}%{dari} "
            f"— di bawah batas wajar {thresh:.0f}%, dari {n} video terakhir.\n"
            f"👍 Koreksi otomatis berhasil. Tidak ada tindakan yang perlu Anda lakukan.")


def check_drift_alarm(sb=None) -> dict:
    """[F5] ALARM drift estimator: median |error| taksiran-vs-nyata pada N sampel TERBARU ber-taksiran.
    Melewati ambang → Telegram ADMIN (bukan aksi otomatis apa pun — manusia yang menindak; §0.6).
    Ambang & jendela config-driven (DRIFT_ALARM_PCT / DRIFT_WINDOW_N)."""
    try:
        if sb is None:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        window = _ambang.angka("drift_window_n", 30)
        thresh = _ambang.angka("drift_alarm_pct", 10)
        rows = (sb.table("tts_delivery_samples")
                  .select("predicted_secs,raw_audio_secs,created_at")
                  .not_.is_("predicted_secs", "null").not_.is_("raw_audio_secs", "null")
                  .order("created_at", desc=True).limit(window).execute().data or [])
        errs = [abs(float(r["predicted_secs"]) - float(r["raw_audio_secs"])) / float(r["raw_audio_secs"]) * 100
                for r in rows if float(r["raw_audio_secs"] or 0) > 0]
        if len(errs) < max(5, window // 3):   # data terlalu tipis → jangan bunyi (anti-alarm-palsu)
            return {"status": "insufficient_data", "n": len(errs)}
        med = statistics.median(errs)
        alarmed = med > thresh
        suppressed = False
        _KEY = "ops_drift_alarm_state"   # JSON: {last_at, median, alarming}
        st = _baca_state(sb, _KEY)
        if alarmed:
            # REM JEDA-ULANG persisten (owner 2026-07-16: 6 dering sehari krn tiap deploy me-restart
            # worker → penjaga langsung periksa → alarm lagi; memori proses hilang saat restart —
            # itulah akarnya → waktu alarm terakhir disimpan di DB `app_config`, BUKAN di memori).
            # Maks 1 alarm per DRIFT_ALARM_COOLDOWN_H (default 24 jam). Fail-soft: gagal baca/tulis
            # jam-terakhir → alarm TETAP terkirim (lebih baik dering ganda daripada bisu senyap).
            cooldown_h = _ambang.angka("drift_alarm_cooldown_h", 24)
            try:
                from datetime import datetime, timezone
                last = st.get("last_at")
                if last:
                    dt_last = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
                    hours = (datetime.now(timezone.utc) - dt_last).total_seconds() / 3600.0
                    if 0 <= hours < cooldown_h:
                        suppressed = True
                        logger.info(f"[DriftAlarm] alarm DITAHAN (rem {cooldown_h:.0f}j; terakhir {hours:.1f}j lalu)")
            except Exception as ce:
                logger.warning(f"[DriftAlarm] baca jam-alarm-terakhir gagal (alarm tetap dikirim): {ce}")
            if not suppressed:
                try:
                    from src.utils.telegram_notifier import TelegramNotifier
                    # Bahasa dampak-bisnis, nol jargon (§4.1) + ARAH pergerakan (owner 2026-07-28).
                    TelegramNotifier().notify_admin(_drift_alarm_text(med, thresh, len(errs), st.get("median")))
                    _simpan_state(sb, _KEY, med, True)
                except Exception as te:
                    logger.warning(f"[DriftAlarm] kirim telegram gagal (non-fatal): {te}")
        elif st.get("alarming"):
            # PULIH: sempat alarm, kini kembali normal → kabari SEKALI. Tanpa ini, diam bisa berarti
            # "sudah beres" atau "alarmnya rusak", dan owner tak punya cara membedakannya.
            try:
                from src.utils.telegram_notifier import TelegramNotifier
                TelegramNotifier().notify_admin(_drift_recovery_text(med, thresh, len(errs), st.get("median")))
            except Exception as te:
                logger.warning(f"[DriftAlarm] kabar pulih gagal (non-fatal): {te}")
            _simpan_state(sb, _KEY, med, False)
        else:
            _simpan_state(sb, _KEY, med, False)   # rekam median agar pemeriksaan berikutnya punya pembanding
        logger.info(f"[DriftAlarm] median_err={med:.1f}% n={len(errs)} ambang={thresh}% alarm={alarmed} ditahan={suppressed}")
        return {"median_err_pct": round(med, 1), "n": len(errs), "threshold": thresh,
                "alarmed": alarmed, "suppressed": suppressed}
    except Exception as e:
        logger.error(f"[DriftAlarm] gagal (fail-soft): {e}")
        return {"error": str(e)}


def run_maintenance(sb=None) -> dict:
    """[F5] Satu pintu swa-pemeliharaan berkala (dipanggil self_learning tiap cadence):
    (1) kalibrasi koefisien durasi dari sampel baru → (2) selaraskan bobot-beat (dibatasi+terkunci-
    hormat) → (3) alarm drift ke admin. Semua fail-soft — kegagalan di sini TIDAK pernah mengganggu
    produksi."""
    out = {}
    out["pace"]  = compute_pace_calibration(sb=sb)
    out["beats"] = align_beat_weights(sb=sb)
    out["drift"] = check_drift_alarm(sb=sb)
    return out
