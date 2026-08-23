"""
AI Cost (B2 BYOK cost-tracking, owner 2026-07-04) — konversi KONSUMSI (cost_meter) → USD.

Harga satuan = katalog `ai_models.pricing` (jsonb):
  {in_per_1m, out_per_1m, per_image, per_1m_chars, per_request_usd, source, synced_at}
  video ([B6] F2): {per_second_usd} ATAU {per_video_base_usd, base_seconds, per_extra_second_usd}
Diisi otomatis oleh price_sync (feed komunitas LiteLLM, harian) — admin bisa OVERRIDE
(pricing_locked=true → sinkron tak menimpa; wajib utk provider di luar feed, mis. ElevenLabs).

Kejujuran: angka = "konsumsi terukur × harga katalog per synced_at" — BUKAN membaca invoice tenant
(tak ada API-nya). Model tanpa harga → komponen ditandai unpriced (FE tampil jujur, bukan Rp 0 palsu).
"""

import os
from dataclasses import dataclass
from loguru import logger


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  DAFTAR SATUAN HARGA — SUMBER TUNGGAL. SSOT: `ARSITEKTUR_AI_PROVIDER_MODEL.md` §7b.
#
#  KENAPA ADA (23-Agu-2026): 10 cacat ditemukan di rantai ini dalam satu sesi, akarnya SATU —
#  pengetahuan "satuan apa berlaku untuk jenis apa, dihitung sekali di mana" tersebar di 4 tempat
#  yang tak saling tahu (sinkron harga · penghitung ini · layar tenant · panel admin). Tiap tempat
#  lalu membusuk sendiri: layar tenant tak punya cabang video (model video tampil "/gambar"),
#  penghitung menagih model gambar DUA KALI (+7,6%), sinkron menerima harga TEKS sebagai harga SUARA
#  (4× terlalu murah). Menambal per-kasus = 100 kesempatan salah baru saat model bertambah ratusan.
#
#  DUA UKURAN YANG WAJIB DIPISAH (kosakata FinOps FOCUS, diperiksa 23-Agu):
#    • satuan TAGIH   = ukuran yang vendor pakai menagih  → harga disimpan dalam ukuran INI
#    • satuan TERUKUR = ukuran yang mesin kita ukur        → keranjang meter (cost_meter)
#  Seluruh keluarga cacat itu lahir dari mengalikan harga ber-satuan-A dengan jumlah ber-satuan-B.
#  Tak ada jembatan antar keduanya ⇒ satuan itu TAK BISA DIHITUNG, dan wajib dinyatakan begitu.
#
#  URUTAN = PRIORITAS. Satuan pertama yang harganya ADA **dan** pemakaiannya ADA yang dipakai;
#  sisanya dilewati ⇒ **satu model satu tagihan, mustahil ganda secara struktur** (bukan dijaga
#  cabang if). Menambah penyedia/model bertipe yang sudah ada = NOL kode. Cara tagih yang
#  benar-benar baru = SATU baris di daftar ini (dan G2 menolak baris yang tak utuh).
# ══════════════════════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Satuan:
    jenis: str                  # llm | tts | image | video  (jenis model yang memakainya)
    skema: str                  # NAMA CARA TAGIH. Satuan ber-skema sama ditagih BERSAMA (mis. token
                                # masuk + token keluar); skema berbeda saling MENGECUALIKAN.
    kunci: str                  # kunci harga di ai_models.pricing (satuan TAGIH)
    satuan_tagih: str           # ukuran yang vendor tagih — untuk manusia
    keranjang: str              # keranjang cost_meter tempat pemakaiannya tercatat (satuan TERUKUR)
    medan: tuple                # (field,) di dalam keranjang; () = keranjang berisi angka skalar
    umpan: tuple                # kolom umpan harga publik yang BOLEH jadi sumbernya
    kali: float                 # pembagi jumlah (1e6 = tarif per sejuta, 1 = tarif per unit)
    bentuk: str                 # "produk" (jumlah×tarif) | "video_bertingkat"
    label: str                  # label layar (dipakai panel & layar tenant — nol teks di kode layar)
    kunci_dukung: tuple = ()    # kunci harga pendamping (basis klip butuh base_seconds dst)
    wajib: bool = False         # harga ESENSIAL skema ini. Tanpa harga wajib, skema TAK BERLAKU —
                                # walau satuan lainnya punya harga. Sebab: harga masukan suara ±1%
                                # dari tagihan; menagih hanya itu = angka kecil yang MASUK AKAL tapi
                                # salah, dan baris jadi TAMPAK berharga di panel. Lebih baik jujur
                                # "belum terhitung" (kelas cacat 23-Agu).


SATUAN_HARGA = (
    # ── naskah: tarif per-panggilan MENGECUALIKAN per-token (fal any-llm: $0,001/panggil) ──
    Satuan("llm", "naskah_panggilan", "per_request_usd", "panggilan", "llm", ("calls",), (), 1, "produk", "/panggilan"),
    # ── suara: huruf → token audio → detik. `output_cost_per_token` HARAM di sini: di umpan ia
    #    bermakna DUA hal tanpa penanda (harga audio pd satu baris, harga TEKS pd baris lain) ──
    Satuan("tts", "suara_huruf", "per_1m_chars", "sejuta huruf", "tts", (), ("input_cost_per_character",), 1e6, "produk", "/1jt huruf"),
    Satuan("tts", "suara_token", "in_per_1m", "sejuta token masuk", "tts_tokens", ("tokens_in",), ("input_cost_per_token",), 1e6, "produk", "/1jt token masuk"),
    Satuan("tts", "suara_token", "out_per_1m", "sejuta token audio", "tts_tokens", ("tokens_out",), ("output_cost_per_audio_token",), 1e6, "produk", "/1jt token audio", (), True),
    Satuan("tts", "suara_detik", "per_second_usd", "detik audio", "tts_seconds", (), ("output_cost_per_second",), 1, "produk", "/detik audio"),
    # ── gambar: per-gambar MENGECUALIKAN token (model gambar ber-tagih token jatuh ke skema token naskah) ──
    Satuan("image", "gambar_satuan", "per_image", "gambar", "image", (), ("output_cost_per_image",), 1, "produk", "/gambar"),
    # ── gambar ber-tagih MEGAPIKSEL (fal): jumlahnya sudah DIBULATKAN KE ATAS per gambar di
    #    pencatat — pembulatan adalah bagian dari cara vendor menagih, bukan pembulatan tampilan ──
    Satuan("image", "gambar_megapiksel", "per_megapixel_usd", "megapiksel (dibulatkan ke atas)",
           "image_megapiksel", (), (), 1, "produk", "/megapiksel"),
    # ── gambar ber-tagih TOKEN (gpt-image-1 dst): kolom keluarannya `output_cost_per_image_token`,
    #    BUKAN `output_cost_per_token` (yang bermakna ganda). Pemakaiannya tercatat di keranjang
    #    naskah krn adapter gambar mencatat token di sana ⇒ tetap SEKALI tagih (skema ini hanya
    #    berlaku bila `per_image` tak ada). Harga token keluaran WAJIB: tanpa itu yang tersisa cuma
    #    harga masukan (±1% tagihan) = angka kecil yang masuk akal tapi salah. ──
    Satuan("image", "gambar_token", "in_per_1m", "sejuta token masuk", "llm", ("tokens_in",), ("input_cost_per_token",), 1e6, "produk", "/1jt token masuk"),
    Satuan("image", "gambar_token", "out_per_1m", "sejuta token gambar", "llm", ("tokens_out",), ("output_cost_per_image_token",), 1e6, "produk", "/1jt token gambar", (), True),
    # ── video: per-detik ATAU basis-per-klip + detik tambahan ──
    Satuan("video", "video_detik", "per_second_usd", "detik video", "video", ("seconds",), ("output_cost_per_second",), 1, "produk", "/detik"),
    Satuan("video", "video_klip", "per_video_base_usd", "klip + detik lebih", "video", ("clips", "seconds"), (), 1,
           "video_bertingkat", "/klip", ("base_seconds", "per_extra_second_usd")),
    # ── video ber-tagih TOKEN (fal seedance): jumlah token = (tinggi×lebar×fps×durasi)÷1024, dihitung
    #    di pencatat dari fakta yang DIUKUR pada berkas hasil (bukan dari setelan katalog) ──
    Satuan("video", "video_token", "per_1m_video_tokens_usd", "sejuta token video", "video_token",
           (), (), 1e6, "produk", "/1jt token video"),
    # ── token naskah = PALING AKHIR: model gambar/suara ber-tagih token jatuh ke sini HANYA bila
    #    satuan jenisnya sendiri tak ada ⇒ tak pernah tertagih dua kali ──
    Satuan("llm", "naskah_token", "in_per_1m", "sejuta token masuk", "llm", ("tokens_in",), ("input_cost_per_token",), 1e6, "produk", "/1jt token masuk"),
    Satuan("llm", "naskah_token", "out_per_1m", "sejuta token keluar", "llm", ("tokens_out",), ("output_cost_per_token",), 1e6, "produk", "/1jt token keluar"),
)

# ══════════════════════════════════════════════════════════════════════════════════════════════
#  KATALOG FORMULA HARGA — nama CARA TAGIH yang dikenal mesin. SSOT: `ARSITEKTUR_AI_PROVIDER_MODEL.md`
#  §7b/§7f. Ditetapkan owner 23-Agu-2026: *"sebaiknya kita memiliki kategorisasi pricing untuk
#  mengelompokkan beberapa model yang memiliki formulasi pricing yang sama."*
#
#  KENAPA nama formula, bukan cuma satuan: satuan hanya menyebut UKURAN ("per detik"), sedangkan
#  formula bisa memuat CARA HITUNGNYA — mis. gambar fal ditagih per megapiksel DIBULATKAN KE ATAS,
#  video seedance ditagih per token = (tinggi×lebar×fps×durasi)÷1024. Dengan satuan saja, angka itu
#  harus dihitung tangan lalu disimpan mati; dengan formula, MESIN yang menghitung — jadi bila
#  resolusi/durasi berubah, biayanya ikut benar sendiri.
#
#  Dua formula terbaik justru TIDAK menghitung apa pun: vendor melaporkan biayanya sendiri.
#  Terverifikasi 23-Agu: OpenRouter mengirim `usage.cost` di setiap balasan; APIMaster menyediakan
#  penghitung saldo (`/v1/dashboard/billing/usage`, satuan SEN) yang bisa diselisihkan.
#
#  jenis "*" = berlaku untuk semua jenis model.
# ══════════════════════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Formula:
    kunci: str          # nilai kolom `ai_models.pricing_model`
    jenis: str          # llm | tts | image | video | *  (jenis model yang boleh memakainya)
    nama: str           # label pendek untuk panel
    penjelasan: str     # kalimat untuk admin — apa yang mesin lakukan & tarif apa yang ia butuh


FORMULA = (
    # ── tanpa taksiran: vendor menyebut biayanya sendiri (paling tepat) ──
    Formula("biaya_dilaporkan", "*", "biaya dilaporkan vendor",
            "Mesin TIDAK menghitung — biaya diambil dari angka yang vendor kirim di balasan tiap "
            "panggilan (mis. OpenRouter). Tak perlu tarif apa pun di baris ini."),
    Formula("selisih_akun", "*", "selisih penghitung akun",
            "Mesin membaca penghitung pemakaian akun vendor sebelum & sesudah produksi, lalu "
            "memakai selisihnya (mis. APIMaster). Tak perlu tarif; tak akurat bila satu kunci "
            "dipakai beberapa produksi serentak."),
    # ── naskah ──
    Formula("naskah_panggilan", "llm", "per panggilan",
            "Tarif tetap per satu panggilan, berapa pun panjang naskahnya. Butuh: tarif per panggilan."),
    Formula("naskah_token", "llm", "token masuk + keluar",
            "Jumlah token masuk & keluar dikali tarifnya masing-masing. Butuh: tarif per 1 juta "
            "token masuk dan keluar."),
    # ── suara ──
    Formula("suara_huruf", "tts", "per huruf",
            "Jumlah huruf naskah dikali tarif. Butuh: tarif per 1 juta huruf."),
    Formula("suara_token", "tts", "token audio",
            "Token yang VENDOR laporkan (teks masuk + audio keluar) dikali tarifnya. Butuh: tarif "
            "per 1 juta token audio (wajib) dan token masuk."),
    Formula("suara_detik", "tts", "per detik audio",
            "Durasi audio yang mesin ukur dari berkasnya dikali tarif. Butuh: tarif per detik audio."),
    # ── gambar ──
    Formula("gambar_satuan", "image", "per gambar",
            "Jumlah gambar dikali tarif. Butuh: tarif per gambar."),
    Formula("gambar_token", "image", "token gambar",
            "Token yang vendor laporkan dikali tarif token-gambar. Butuh: tarif per 1 juta token "
            "gambar (wajib) dan token masuk."),
    Formula("gambar_megapiksel", "image", "per megapiksel (dibulatkan ke atas)",
            "Ukuran gambar diubah ke megapiksel, DIBULATKAN KE ATAS, lalu dikali tarif — cara fal "
            "menagih (1080×1920 = 2,07 MP ditagih 3 MP). Butuh: tarif per megapiksel."),
    # ── video ──
    Formula("video_detik", "video", "per detik video",
            "Detik video yang diminta ke vendor dikali tarif. Bila vendor menagih beda saat audio "
            "dinyalakan, isi tarif yang sesuai setelan kita. Butuh: tarif per detik."),
    Formula("video_klip", "video", "per klip + detik tambahan",
            "Tarif dasar per klip untuk jatah detik tertentu, lalu tarif tambahan untuk detik di "
            "atasnya. Butuh: tarif dasar per klip, jatah detik, tarif detik tambahan."),
    Formula("video_token", "video", "token video",
            "Token dihitung dari (tinggi × lebar × fps × durasi) ÷ 1024, lalu dikali tarif — cara "
            "fal menagih seedance. Butuh: tarif per 1 juta token video."),
    # ── lain ──
    Formula("kuota_gratis", "*", "kuota gratis harian, lalu berbayar",
            "Gratis selama pemakaian harian masih di bawah kuota vendor; di atas itu dihitung per "
            "satuan. Butuh: besar kuota dan tarif per satuan."),
    Formula("gratis", "*", "gratis",
            "Vendor tidak menagih apa pun. Biaya selalu nol."),
)

# Formula → satuan harga yang ia pakai (turunan daftar satuan; nol penulisan ganda).
def satuan_formula(kunci: str) -> tuple:
    return tuple(s for s in SATUAN_HARGA if s.skema == kunci)


def formula_untuk_jenis(jenis: str) -> tuple:
    """Formula yang SAH untuk satu jenis model (termasuk yang berlaku untuk semua jenis)."""
    return tuple(f for f in FORMULA if f.jenis in (jenis, "*"))


# Urutan skema = PRIORITAS (kemunculan pertama di daftar). Dihitung sekali, bukan ditulis dua kali.
SKEMA_URUT = tuple(dict.fromkeys(s.skema for s in SATUAN_HARGA))


def satuan_untuk(jenis: str) -> tuple:
    """Satuan yang SAH untuk satu jenis model — dipakai sinkron harga & (lewat cermin DB) layar,
    supaya kosakata satuan hanya hidup di berkas ini."""
    return tuple(s for s in SATUAN_HARGA if s.jenis == jenis)


def kunci_token_naskah() -> tuple:
    """(kunci token masuk, kunci token keluar) skema token naskah — DITURUNKAN dari daftar, bukan
    diketik ulang. Dipakai sumber harga cadangan (OpenRouter) yang hanya melayani model naskah."""
    tok = [s for s in SATUAN_HARGA if s.skema == "naskah_token"]
    masuk = next(s.kunci for s in tok if "tokens_in" in s.medan)
    keluar = next(s.kunci for s in tok if "tokens_out" in s.medan)
    return masuk, keluar


def kunci_tunggal_formula(kunci_formula: str) -> str | None:
    """Kunci tarif SATU-SATUNYA milik sebuah formula, atau None bila formula itu memakai lebih dari
    satu tarif (mis. token masuk + keluar). Dipakai sinkron harga supaya ia tak perlu MENGETIK nama
    satuan — kosakata satuan hanya hidup di berkas ini (dijaga G1)."""
    sat = [s for s in SATUAN_HARGA if s.skema == kunci_formula]
    return sat[0].kunci if len(sat) == 1 else None


def semua_kunci_harga() -> tuple:
    """Semua kunci harga yang dikenal mesin — dipakai penjaga lonjakan harga & validasi pintu admin."""
    return tuple(dict.fromkeys([s.kunci for s in SATUAN_HARGA]
                               + [k for s in SATUAN_HARGA for k in s.kunci_dukung]))


KERANJANG_BIAYA = {"llm": "llm", "image": "image", "tts": "tts", "tts_tokens": "tts",
                   "tts_seconds": "tts", "video": "video",
                   # [F5] Biaya yang VENDOR laporkan sendiri. Pencatatnya hari ini hanya adapter
                   # NASKAH (penyedia router), jadi rinciannya masuk baris naskah. Bila kelak router
                   # yang sama melayani gambar/video, pencatatnya ditambah di jalur itu — G3 menjaga
                   # jumlah pencatat supaya penambahan itu tak bisa menyelinap tanpa terlihat.
                   "biaya_vendor": "llm",
                   # [F4b] Satuan tagih fal: megapiksel (gambar) & token video. Keranjangnya sendiri
                   # supaya jumlah gambar/detik yang lama TETAP tercatat apa adanya — yang berubah
                   # hanya DASAR tagihnya, dan formula baris model yang memilih.
                   "image_megapiksel": "image", "video_token": "video"}

# Formula yang memang TIDAK BUTUH TARIF apa pun di baris modelnya. Tanpa daftar ini, baris yang
# benar (vendor menyebut biayanya / vendor tak menagih) akan dituduh "celah data" dan dilaporkan
# belum-terhitung setiap hari — alarm palsu yang mengajari admin mengabaikan alarm.
FORMULA_TANPA_TARIF = frozenset({"gratis", "biaya_dilaporkan"})


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _pricing_map(sb=None) -> dict:
    """model_key & model_id → pricing dict (dua kunci → cocok apa pun yang tercatat meter)."""
    sb = sb or _sb()
    rows = sb.table("ai_models").select("model_key, model_id, pricing").execute().data or []
    out = {}
    for r in rows:
        p = r.get("pricing")
        if isinstance(p, dict) and p:
            out[r["model_key"]] = p
            if r.get("model_id"):
                out[r["model_id"]] = p
    return out


def _jumlah(pemakaian, medan: tuple):
    """Ambil angka pemakaian: keranjang skalar (huruf/gambar/detik) atau ber-medan (token/klip)."""
    if not medan:
        try:
            return {None: float(pemakaian or 0)}
        except (TypeError, ValueError):
            return {}
    if not isinstance(pemakaian, dict):
        return {}
    return {m: float(pemakaian.get(m, 0) or 0) for m in medan}


def _biaya_skema(skema: str, harga: dict, pemakaian_per_keranjang: dict) -> float | None:
    """Biaya satu SKEMA tagih. None = skema ini tak berlaku (harga atau pemakaiannya tak ada).
    Seluruh satuan ber-skema sama dihitung BERSAMA (token masuk + token keluar = satu tagihan)."""
    satuan = [s for s in SATUAN_HARGA if s.skema == skema]
    if any(harga.get(s.kunci) is None for s in satuan if s.wajib):
        return None          # harga esensial skema ini tak ada → skema TAK BERLAKU (gagal jujur)
    if not any(harga.get(s.kunci) is not None for s in satuan):
        return None
    if not any(s.keranjang in pemakaian_per_keranjang for s in satuan):
        return None
    total = 0.0
    for s in satuan:
        tarif = harga.get(s.kunci)
        if tarif is None or s.keranjang not in pemakaian_per_keranjang:
            continue
        pakai = _jumlah(pemakaian_per_keranjang[s.keranjang], s.medan)
        if s.bentuk == "video_bertingkat":
            # Basis per klip + detik di atas jatah basis (mis. Kling $0,35/5s + $0,07/s).
            klip = pakai.get("clips", 0.0)
            detik = pakai.get("seconds", 0.0)
            basis_detik = float(harga.get("base_seconds") or 0)
            lebih = float(harga.get("per_extra_second_usd") or 0)
            total += klip * float(tarif) + max(0.0, detik - klip * basis_detik) * lebih
            continue
        for medan, jumlah in pakai.items():
            _ = medan
            total += (jumlah / s.kali) * float(tarif)
    return total


# Formula yang penghitung BELUM dukung — sengaja dilaporkan JUJUR sebagai "tak terhitung", bukan
# dihitung dengan cara lain. Masing-masing punya langkah pemasangannya sendiri (SSOT §7f):
#   selisih_akun                     → TIDAK AKAN dipasang per-produksi: produksi berjalan SERENTAK
#                                      (ThreadPool sejumlah core), jadi selisih penghitung akun
#                                      mustahil diatribusikan ke satu produksi. Tempatnya di
#                                      rekonsiliasi tingkat TENANT (F8), bukan di sini.
#   kuota_gratis                     → butuh penghitungan kuota harian per akun tenant (SSOT §7e)
# (gambar_megapiksel & video_token DIDUKUNG sejak F4b — pencatatnya mengukur berkas hasil.)
FORMULA_BELUM_DIDUKUNG = frozenset({"selisih_akun", "kuota_gratis"})


def _formula_map(sb=None) -> dict:
    """model_key & model_id → nama FORMULA harga (`ai_models.pricing_model`, migr 0210).

    TERPISAH dari `_pricing_map` dengan sengaja: uji lama mengganti peta harga dengan kamus polos
    {model: harga}; menggabungkan keduanya akan memecah kontrak itu tanpa alasan."""
    sb = sb or _sb()
    rows = sb.table("ai_models").select("model_key, model_id, pricing_model").execute().data or []
    out = {}
    for r in rows:
        f = r.get("pricing_model")
        if not f:
            continue
        out[r["model_key"]] = f
        if r.get("model_id"):
            out[r["model_id"]] = f
    return out


def compute_cost_usd(ai_usage: dict, sb=None) -> dict | None:
    """Hitung biaya USD dari ringkasan cost_meter — SATU putaran atas DAFTAR SATUAN, nol cabang
    per-kasus. Return {usd, breakdown, unpriced, priced_at}; None bila usage kosong.

    ATURAN INTI (SSOT §7b/§7f): tiap model ditagih memakai **formula yang baris modelnya nyatakan**
    (`ai_models.pricing_model`, migr 0210) — bukan ditebak dari jenisnya. Baris tanpa formula
    dilaporkan JUJUR sebagai tak-terhitung. Sebelum F2 skemanya dipilih dari urutan prioritas; Sisanya dilewati ⇒ hitung-ganda mustahil
    secara struktur. Sebelum 23-Agu, `gemini-2.5-flash-image` ditagih per-gambar DAN per-token
    (+7,6% pada run 503) karena keputusan ini dulu tersebar di cabang if per-jenis.
    """
    if not ai_usage:
        return None
    try:
        prices = _pricing_map(sb)
    except Exception as e:
        logger.warning(f"[ai_cost] baca pricing gagal: {e}")
        return None

    # Formula per model (migr 0210) = penentu CARA hitung. Gagal baca = gangguan KAMI → jatuh ke
    # perilaku pra-F2 supaya biaya tak mendadak nol, TAPI dicatat (haram senyap).
    formulas = None
    try:
        formulas = _formula_map(sb)
    except Exception as e:
        logger.warning(f"[ai_cost] peta formula gagal dibaca ({e}) — memakai urutan prioritas "
                       f"(perilaku pra-F2); biaya tetap dihitung, tapi ini WAJIB diselidiki")

    br = {"llm": 0.0, "image": 0.0, "tts": 0.0, "video": 0.0}
    unpriced, synced = [], None

    # Kumpulkan pemakaian PER MODEL lintas keranjang — keputusan tagih diambil per MODEL, bukan
    # per keranjang. Itu sebabnya satu model tak bisa lagi ditagih di dua tempat.
    per_model: dict = {}
    for keranjang, isi in (ai_usage or {}).items():
        if keranjang not in KERANJANG_BIAYA or not isinstance(isi, dict):
            continue
        for model, nilai in isi.items():
            per_model.setdefault(str(model), {})[keranjang] = nilai

    for model, pemakaian in per_model.items():
        formula = (formulas or {}).get(model)
        harga = prices.get(model)
        if not harga and formula not in FORMULA_TANPA_TARIF:
            unpriced.append(model)
            continue

        # Formula GRATIS: vendor tak menagih (mis. Edge). Biaya 0 dan BUKAN "tak terhitung".
        if formula == "gratis":
            synced = synced or (harga or {}).get("synced_at")
            continue

        # [F5] VENDOR MENYEBUT BIAYANYA SENDIRI → dipakai apa adanya, mesin tidak menghitung apa pun.
        # Sengaja TIDAK lewat daftar satuan: daftar itu mengalikan JUMLAH × TARIF, sedangkan ini
        # sudah berupa jawabannya. Menaruhnya di daftar satuan berarti ia punya "tarif" — dan itu
        # membuka sumber angka kedua untuk model yang sama (dijaga G9).
        # Token panggilan yang sama diabaikan di sini ⇒ mustahil tertagih dua kali secara struktur.
        if formula == "biaya_dilaporkan":
            usd = pemakaian.get("biaya_vendor")
            if usd is None:
                unpriced.append(model)      # vendor tak menyebut → JUJUR, haram ditaksir dari token
                continue
            br[KERANJANG_BIAYA["biaya_vendor"]] += float(usd)
            synced = synced or (harga or {}).get("synced_at")
            continue

        # Formula yang penghitung belum dukung → JUJUR dilaporkan, bukan dihitung dengan cara lain.
        if formula in FORMULA_BELUM_DIDUKUNG:
            unpriced.append(model)
            continue

        # Skema yang dipakai = yang DINYATAKAN baris model. Bila peta formula tak terbaca
        # (gangguan DB = kegagalan KAMI, bukan celah data), jatuh ke urutan prioritas = perilaku
        # sebelum F2 — dan itu DICATAT, tidak senyap.
        if formula:
            urut = (formula,)
        else:
            if formulas is not None:
                unpriced.append(model)      # celah DATA: baris tanpa formula → jujur, berisik
                continue
            urut = SKEMA_URUT
        tertagih = False
        for skema in urut:
            nilai = _biaya_skema(skema, harga, pemakaian)
            if nilai is None:
                continue
            keranjang_skema = next(s.keranjang for s in SATUAN_HARGA
                                   if s.skema == skema and s.keranjang in pemakaian)
            br[KERANJANG_BIAYA[keranjang_skema]] += nilai
            synced = synced or harga.get("synced_at")
            tertagih = True
            break            # ← satu model satu tagihan
        if not tertagih:
            unpriced.append(model)

    total = br["llm"] + br["image"] + br["tts"] + br["video"]
    return {
        "usd": round(total, 6),
        "breakdown": {k: round(v, 6) for k, v in br.items()},
        "unpriced": sorted(set(unpriced)),
        "priced_at": synced,
    }
