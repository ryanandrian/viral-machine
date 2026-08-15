// NICHE DNA — skema + validasi BERSAMA (klien editor & server API, admin & tenant).
// Sumber kebenaran bentuk = konsumen mesin (audit NICHE_DNA_AUDIT_REMEDIATION.md §1.1):
// - narration_persona: dict string (5 key inti: tone/style/avoid/hook_style/emotion_arc; key ekstra boleh)
// - visual_style: dict string (3 key inti: base_style/color_palette/atmosphere; ekstra: camera/lighting/…)
// - music_config: {mode: auto|random|fixed, mood?, track_id?}
// - mood_priority: string[] (nilai = moods.mood_id)
// - section_timing: {} ATAU LENGKAP 8 key int>0 (validasi ketat script_engine — parsial diabaikan mesin)
// - keywords/default_hashtags/visual_fallbacks: string[]
// - image_quality_tags/image_negative_prompt/emotion_scoring_criteria/style/target_emotion: string
// PENTING: DB tetap JSONB apa adanya — lib ini murni memastikan bentuk yang ditulis SELALU bisa
// dicerna pipeline (kesepakatan owner 2026-07-04: FE bongkar-pasang JSON, mesin tak berubah).

export const PERSONA_KEYS = ["tone", "style", "avoid", "hook_style", "emotion_arc"] as const;
export const VISUAL_CORE_KEYS = ["base_style", "color_palette", "atmosphere"] as const;
export const SECTION_KEYS = ["hook", "mystery_drop", "build_up", "pattern_interrupt", "core_facts", "curiosity_bridge", "climax", "cta"] as const;
export const MUSIC_MODES = ["auto", "random", "fixed"] as const;
export const MOTION_INTENSITIES = ["halus", "normal", "dinamis", "cepat"] as const;  // Ken Burns per-niche (visual_style.camera_motion)

// Label & penjelasan awam per bagian naskah (dipakai editor; ID/EN)
export const SECTION_LABELS: Record<string, [string, string, string, string]> = {
  hook:              ["Hook pembuka", "Opening hook", "Detik pertama yang menahan jempol penonton", "The first seconds that stop the scroll"],
  mystery_drop:      ["Umpan misteri", "Mystery drop", "Janji jawaban yang bikin bertahan", "The promise that keeps them watching"],
  build_up:          ["Membangun cerita", "Build up", "Konteks & ketegangan menuju inti", "Context & tension toward the core"],
  pattern_interrupt: ["Kejutan pola", "Pattern interrupt", "Selingan singkat pengusir bosan", "A quick jolt against boredom"],
  core_facts:        ["Fakta inti", "Core facts", "Isi utama yang dijanjikan", "The main promised content"],
  curiosity_bridge:  ["Jembatan penasaran", "Curiosity bridge", "Transisi yang memancing ke klimaks", "Transition teasing the climax"],
  climax:            ["Klimaks", "Climax", "Momen emosi tertinggi", "The emotional peak"],
  cta:               ["Ajakan penutup", "Closing CTA", "Penutup + ajakan (ikut cta_mode channel)", "Closer + call-to-action"],
};

// ── DEKLARASI PROPERTI VISUAL — SATU-SATUNYA tempat properti gaya visual dijelaskan ───────────────
// Editor admin, editor tenant, dan panduan di layar semuanya LAHIR dari daftar ini. Menambah properti
// ke-17 = menambah SATU baris di sini; kotaknya, labelnya, penjelasannya, dan contohnya muncul sendiri
// di kedua layar. (Standar world-class, ketok owner 2026-08-15 — `SISA_KERJA [B32]` T3.)
//
// CACAT YANG DITUTUP: sebelum ini hanya 3 kunci punya label; 13 kunci lain — yang dipakai 47–48 dari 48
// niche — tampil sebagai NAMA KODE INGGRIS di kotak kosong. Melanggar `NICHE_DNA §2` butir 2 ("NOL JSON
// mentah … label bahasa awam + contoh nyata + penjelasan dampaknya ke video") dan `DESAIN §5b` Lapis-2
// (aniconism & gaya rupa = milik pemilik niche, "TERLIHAT & bisa diubah").
// Dijaga `tests/test_properti_visual_berlabel.py`: kunci baru muncul di DB tanpa baris di sini → MERAH.
//
// `camera_motion` sengaja TIDAK di sini — ia objek bersarang dan punya seksi sendiri ("Gerakan Kamera",
// 4 tombol berlabel awam), bukan kotak teks.
export type VisualProp = { label: string; labelEn: string; hint: string; hintEn: string; contoh: string; panjang?: boolean };
export const VISUAL_PROPS: Record<string, VisualProp> = {
  render_style: {
    label: "Gaya rupa", labelEn: "Render style",
    hint: "SATU–DUA KATA yang menentukan hasilnya foto, animasi 3D, atau ilustrasi. Jangan diisi kalimat panjang — kata ini disisipkan apa adanya ke perintah gambar.",
    hintEn: "ONE–TWO WORDS deciding whether output looks photographic, 3D-animated, or illustrated. Keep it short — it is injected verbatim into the image prompt.",
    contoh: "photorealistic · stylized 3D animated · hand-drawn illustration",
  },
  base_style: {
    label: "Gaya dasar", labelEn: "Base style",
    hint: "Fondasi tampilan SEMUA gambar niche ini — kalimat pembuka yang dibaca mesin gambar.",
    hintEn: "The foundation look of every image in this niche — the opening line the image engine reads.",
    contoh: "sinematik fotorealistis, detail tajam, kedalaman ruang terasa", panjang: true,
  },
  color_palette: {
    label: "Palet warna", labelEn: "Colour palette",
    hint: "Warna yang mendominasi tiap adegan. Sebut 3–5 warna, jangan satu warna saja (hasilnya jadi satu nada membosankan).",
    hintEn: "Colours that dominate each scene. Name 3–5; a single colour yields flat, monotone frames.",
    contoh: "biru laut dalam, pirus, hitam pekat, perak dingin",
  },
  atmosphere: {
    label: "Suasana", labelEn: "Atmosphere",
    hint: "Perasaan yang ditinggalkan gambar pada penonton — bukan isinya, melainkan rasanya.",
    hintEn: "The feeling the image leaves with the viewer — not what is in it, but how it feels.",
    contoh: "megah dan sunyi, membuat penonton merasa kecil",
  },
  lighting: {
    label: "Pencahayaan", labelEn: "Lighting",
    hint: "Arah dan sifat cahaya. Ini penentu terbesar apakah gambar terlihat mahal atau murah.",
    hintEn: "Direction and quality of light — the single biggest factor in whether frames look expensive.",
    contoh: "cahaya jendela pagi yang lembut, garis tipis di tepi wajah", panjang: true,
  },
  camera: {
    label: "Sudut & lensa kamera", labelEn: "Camera & lens",
    hint: "Dari mana gambar diambil dan seberapa dekat ke subjek.",
    hintEn: "Where the shot is taken from and how close it sits to the subject.",
    contoh: "setinggi mata, lensa 35mm, dorongan lambat ke wajah", panjang: true,
  },
  composition: {
    label: "Komposisi", labelEn: "Composition",
    hint: "Peletakan subjek dalam bingkai tegak 9:16. Sisakan ruang kosong di atas bila judul akan ditumpangkan.",
    hintEn: "How the subject sits in the vertical 9:16 frame. Leave headroom if a title overlays the top.",
    contoh: "satu subjek dominan, latar berlapis, ruang kosong di sepertiga atas", panjang: true,
  },
  realism: {
    label: "Tingkat realisme", labelEn: "Realism level",
    hint: "Kalimat TEKSTUR: seberapa mirip foto atau seberapa bergaya. Berbeda dari “Gaya rupa” yang cuma 1–2 kata.",
    hintEn: "A TEXTURE sentence: how photographic or how stylised. Different from “Render style”, which is 1–2 words.",
    contoh: "kulit berpori halus, serat kain terlihat, bayangan kontak akurat", panjang: true,
  },
  color_grading: {
    label: "Gradasi warna", labelEn: "Colour grading",
    hint: "Sentuhan akhir warna: kontras, kedalaman bayangan, kehangatan. Hindari “satu warna menyelimuti seluruh gambar”.",
    hintEn: "Final colour pass: contrast, shadow depth, warmth. Avoid one hue washing the whole frame.",
    contoh: "kontras kaya, bayangan pekat tapi tidak mati, sorotan bersih", panjang: true,
  },
  motion: {
    label: "Gerak di dalam adegan", labelEn: "In-scene motion",
    hint: "Gerak yang DIGAMBARKAN di dalam satu bidikan. Berbeda dari “Gerakan Kamera” (zoom/geser) yang diatur di bawah.",
    hintEn: "Movement DEPICTED inside a shot. Different from “Camera Motion” (zoom/pan) set below.",
    contoh: "gerak tenang, satu aksi jelas per adegan",
  },
  reference: {
    label: "Rujukan gaya", labelEn: "Style reference",
    hint: "Bahasa visual yang jadi acuan mutu — sebut jenis karyanya, bukan judul berhak cipta.",
    hintEn: "The visual language used as a quality bar — name the genre, not a copyrighted title.",
    contoh: "dokumenter alam kelas bioskop", panjang: true,
  },
  subject: {
    label: "Subjek utama", labelEn: "Main subject",
    hint: "Siapa atau apa yang paling sering jadi pusat gambar di niche ini.",
    hintEn: "Who or what most often sits at the centre of the frame in this niche.",
    contoh: "orang biasa masa kini yang sedang beraktivitas",
  },
  environment: {
    label: "Lingkungan", labelEn: "Environment",
    hint: "Tempat kejadian yang khas untuk niche ini.",
    hintEn: "The settings characteristic of this niche.",
    contoh: "rumah sederhana, jalan kampung, dapur pagi hari",
  },
  strict_prohibition: {
    label: "Larangan mutlak niche", labelEn: "Absolute bans for this niche",
    hint: "Hal yang TIDAK BOLEH muncul di gambar mana pun niche ini — misalnya tingkat aniconism atau adab berpakaian. Milik Anda, bukan mesin. (Larangan MesinViral sendiri tetap berlaku dan tak bisa dimatikan dari sini.)",
    hintEn: "What must NEVER appear in any image of this niche — e.g. level of aniconism or dress modesty. Yours to set. (MesinViral's own hard bans still apply and cannot be switched off here.)",
    contoh: "jangan gambarkan nabi, rasul, atau malaikat — wajah, tubuh, siluet, maupun bayangannya",
    panjang: true,
  },
  mandatory_motion: {
    label: "Gerak wajib (video-AI)", labelEn: "Mandatory motion (AI-video)",
    hint: "Hanya untuk niche berdurasi 8 detik yang memakai video-AI: gerak yang harus ada di setiap klip.",
    hintEn: "Only for 8-second AI-video niches: motion that must be present in every clip.",
    contoh: "kamera bergerak halus maju",
  },
};

export type DnaErrors = Record<string, string>;

const isStr = (v: unknown): v is string => typeof v === "string";
const isStrArr = (v: unknown): v is string[] => Array.isArray(v) && v.every(isStr);
const isStrDict = (v: unknown): v is Record<string, string> =>
  !!v && typeof v === "object" && !Array.isArray(v) && Object.values(v as object).every(isStr);

// Validasi patch DNA (subset field boleh). Return errors per-field (kosong = valid).
// Dipakai SERVER (tolak + pesan — pengganti silent-skip) dan KLIEN (disable Simpan + pesan inline).
// [2026-08-14] PATRI LARANGAN — lapis kedua, di titik SIMPAN.
// Lapis pertama (dan yang sesungguhnya mengunci) ada di mesin: setiap prompt gambar/video melewati
// satu corong yang menempelkan patri dan menahan prompt yang meminta hal terlarang. Lapis ini
// menolak lebih awal, di layar, dengan pesan yang bisa dibaca — supaya pemilik niche tahu sebabnya
// alih-alih menemukan produksinya berhenti belakangan.
// Yang ditolak BUKAN penyebutan biasa (banyak niche Islami sah menyebut nabi sebagai konteks),
// melainkan kalimat yang jelas-jelas MEMERINTAHKAN penggambaran atau membatalkan patri.
const PATRI_BYPASS: RegExp[] = [
  /\b(abaikan|hiraukan|lupakan)\s+(semua\s+)?(larangan|aturan|instruksi|batasan)/i,
  /\bignore\s+(all\s+)?(previous|prior|above|safety|restrictions?|rules?)/i,
  /\b(gambarkan|lukiskan|tampilkan|perlihatkan)\s+(wajah|sosok|rupa)\s+(nabi|rasul|allah)/i,
  /\b(depict|draw|render|show|portray)\s+(the\s+)?(face|figure|form|likeness)\s+of\s+(the\s+)?(prophet|allah|god)/i,
  /\ballah'?s\s+(face|form|figure)\b/i,
];

export function validateDnaPatch(patch: Record<string, unknown>): DnaErrors {
  const e: DnaErrors = {};
  const has = (k: string) => k in patch && patch[k] !== undefined;

  // Diperiksa pada SELURUH nilai teks DNA (persona, visual_style, penajam, larangan, contoh bidikan)
  // — bukan hanya satu kolom, sebab teks yang dikirim ke mesin gambar berasal dari banyak kolom.
  const _teks: string[] = [];
  const _kumpul = (v: unknown) => {
    if (typeof v === "string") _teks.push(v);
    else if (Array.isArray(v)) v.forEach(_kumpul);
    else if (v && typeof v === "object") Object.values(v as object).forEach(_kumpul);
  };
  Object.values(patch).forEach(_kumpul);
  const _langgar = _teks.find((t) => PATRI_BYPASS.some((rx) => rx.test(t)));
  if (_langgar) {
    e.patri = "Isi ini mencoba membatalkan larangan yang dipatri MesinViral (penggambaran Allah SWT / "
      + "Nabi Muhammad ﷺ). Larangan itu tidak bisa dimatikan lewat pengaturan niche.";
  }

  if (has("name") && (!isStr(patch.name) || !(patch.name as string).trim())) e.name = "Nama tidak boleh kosong.";
  for (const k of ["style", "target_emotion", "image_quality_tags", "image_negative_prompt", "emotion_scoring_criteria"]) {
    if (has(k) && patch[k] !== null && !isStr(patch[k])) e[k] = "Harus berupa teks.";
  }
  for (const k of ["keywords", "default_hashtags", "visual_fallbacks", "mood_priority"]) {
    if (has(k) && !isStrArr(patch[k])) e[k] = "Harus berupa daftar teks.";
  }
  if (has("narration_persona") && !isStrDict(patch.narration_persona)) e.narration_persona = "Setiap isian persona harus teks.";
  // [EKSPRESI VOKAL 2026-07-16] {style?, stability?} angka 0..1, atau null (= ikut bawaan suara).
  if (has("voice_expression") && patch.voice_expression !== null) {
    const ve = patch.voice_expression as Record<string, unknown>;
    if (!ve || typeof ve !== "object" || Array.isArray(ve)) e.voice_expression = "Ekspresi vokal tidak valid.";
    else {
      const keys = Object.keys(ve);
      const badKey = keys.some((k) => k !== "style" && k !== "stability");
      const badVal = keys.some((k) => !Number.isFinite(Number(ve[k])) || Number(ve[k]) < 0 || Number(ve[k]) > 1);
      if (badKey || badVal || keys.length === 0) e.voice_expression = "Ekspresi vokal harus angka 0–1 untuk kedramatisan/kestabilan.";
    }
  }
  if (has("visual_style")) {
    const vs = patch.visual_style as Record<string, unknown>;
    if (!vs || typeof vs !== "object" || Array.isArray(vs)) e.visual_style = "Gaya visual tidak valid.";
    else {
      // camera_motion = objek bersarang (Ken Burns); sisanya WAJIB teks.
      const { camera_motion: cm, ...flat } = vs;
      if (!isStrDict(flat)) e.visual_style = "Setiap isian gaya visual harus teks.";
      else if (cm !== undefined) {
        const inten = (cm as Record<string, unknown> | null)?.intensity;
        if (!cm || typeof cm !== "object" || Array.isArray(cm) || !MOTION_INTENSITIES.includes(inten as typeof MOTION_INTENSITIES[number]))
          e.visual_style = `Intensitas gerak kamera harus salah satu: ${MOTION_INTENSITIES.join("/")}.`;
      }
    }
  }

  if (has("music_config")) {
    const mc = patch.music_config as Record<string, unknown>;
    if (!mc || typeof mc !== "object" || Array.isArray(mc)) e.music_config = "Konfigurasi musik tidak valid.";
    else {
      const mode = String(mc.mode ?? "auto");
      if (!MUSIC_MODES.includes(mode as typeof MUSIC_MODES[number])) e.music_config = `Mode musik harus salah satu: ${MUSIC_MODES.join("/")}.`;
      else if (mode === "fixed" && !isStr(mc.track_id)) e.music_config = "Mode 'satu lagu tetap' butuh pilihan track.";
      else if (mode === "random" && mc.mood != null && !isStr(mc.mood)) e.music_config = "Mood harus teks.";
    }
  }

  if (has("section_timing")) {
    const st = patch.section_timing as Record<string, unknown>;
    if (!st || typeof st !== "object" || Array.isArray(st)) e.section_timing = "Struktur durasi tidak valid.";
    else if (Object.keys(st).length > 0) {
      const missing = SECTION_KEYS.filter((k) => !(k in st));
      const bad = SECTION_KEYS.filter((k) => k in st && (!Number.isFinite(Number(st[k])) || Number(st[k]) <= 0));
      if (missing.length) e.section_timing = `Harus LENGKAP 8 bagian (mesin mengabaikan yang parsial). Kurang: ${missing.join(", ")}.`;
      else if (bad.length) e.section_timing = `Durasi harus angka detik > 0: ${bad.join(", ")}.`;
    }
  }
  return e;
}

// ── PENERAPAN PRESET "PILIH SATU KARAKTER" ────────────────────────────────────────────────────────
// Dipakai untuk properti ber-`apply_mode='replace'` (visual_style, narration_persona, …).
//
// CACAT YANG DITUTUP 2026-08-15 (`SISA_KERJA [B32]` T1): editor dulu merakit ulang objeknya —
// `{...kunci-inti-dikosongkan, ...preset}` — sehingga SEMUA properti di luar preset LENYAP. Ke-6 preset
// `visual_style` hanya memuat 6 kunci sementara niche memakai sampai 16 ⇒ satu klik menghapus s/d 9
// properti, termasuk `strict_prohibition` (larangan agama niche) dan `render_style` (gaya rupa).
//
// Kontrak ini memenuhi DUA keputusan owner sekaligus, yang tak bisa dipenuhi salah satunya saja:
//   • 4-Jul "preset karakter = PILIH SATU" ⇒ kunci milik KELUARGA preset yang tak diisi preset baru
//     WAJIB dikosongkan; kalau tidak, sisa gaya lama bercampur dengan gaya baru.
//   • 14-Agu `DESAIN_PRODUK_SAAS §5b` Lapis-2 ⇒ aniconism & gaya rupa milik PEMILIK NICHE, "terlihat
//     & bisa diubah" — haram lenyap sebagai efek samping memilih gaya.
// Maka: preset berkuasa penuh atas keluarganya sendiri, dan TIDAK menyentuh apa pun di luar itu.
//
// `keluarga` = gabungan kunci SELURUH preset properti tsb, DITEMUKAN dari data (lihat pemanggil) —
// bukan daftar hafalan. Preset baru dengan kunci baru otomatis ikut terhitung, jadi kelas kesalahan
// "pemeriksa buta terhadap yang baru" (pelajaran `test_rute_api_terjaga.py`) tidak lahir lagi.
export function terapkanPreset(
  sekarang: Record<string, string>,
  preset: Record<string, string>,
  keluarga: readonly string[],
): { hasil: Record<string, string>; diisi: string[]; dipertahankan: string[]; dikosongkan: string[] } {
  const anggota = new Set(keluarga);
  const hasil: Record<string, string> = {};
  const diisi: string[] = [], dipertahankan: string[] = [], dikosongkan: string[] = [];

  for (const [k, v] of Object.entries(sekarang)) {
    if (anggota.has(k) || k in preset) continue;   // milik keluarga → ditangani di bawah
    hasil[k] = v;                                   // DI LUAR keluarga → milik pemilik niche, utuh
    if (String(v).trim() !== "") dipertahankan.push(k);
  }
  for (const k of anggota) {
    if (k in preset) continue;
    const lama = sekarang[k];
    hasil[k] = "";                                  // "pilih satu": sisa karakter lama dibersihkan
    if (lama !== undefined && String(lama).trim() !== "") dikosongkan.push(k);
  }
  for (const [k, v] of Object.entries(preset)) {
    hasil[k] = v;
    diisi.push(k);
  }
  return { hasil, diisi, dipertahankan, dikosongkan };
}

// Kolom DNA yang di-copy saat buat niche baru dari template (wizard — keputusan owner: copy-dari-base).
// keywords/hashtags/fallbacks TIDAK di-copy (spesifik topik niche — harus milik niche baru).
export const TEMPLATE_COPY_COLUMNS = [
  "style", "target_emotion", "narration_persona", "voice_expression", "visual_style", "mood_priority",
  "emotion_scoring_criteria", "section_timing", "image_quality_tags", "image_negative_prompt",
  "music_config", "youtube_category_id",
] as const;
