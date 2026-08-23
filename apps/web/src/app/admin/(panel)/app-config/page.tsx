"use client";

import { useState, useEffect, useCallback } from "react";
import { SlidersHorizontal } from "lucide-react";

// Application Config (admin) — parameter GLOBAL mesin & trial (app_config). Halaman khusus.
// Auto-save (PATCH /api/admin/app-config/[key]). Label ramah + keterangan bahasa admin (description DB).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type AppCfg = { key: string; value: number; value_text: string | null; description: string | null };

// Metadata tampilan (label ramah + unit + grup). Keterangan detail = description (DB, bahasa admin).
const G_BILLING = "Langganan, Trial & Penagihan";
const G_GERBANG = "Gerbang Uji Produksi (penjaga kebocoran konten)";   // [B24] §10d
const G_LIFECYCLE = "Pertumbuhan & Siklus-Hidup";
const G_TREND = "Bobot Sumber Tren";
const G_ENGINE = "Performa Mesin Tren";
const G_LEARNING = "Kurva Belajar (Self-Learning)";
const G_RETENTION = "Mata Mesin — Kurva Retensi Per-Momen (Lapis 1)";   // [B17 §6 M1] kebijakan kolektor
const G_ANALYST = "Otak Analis (Lapis 2)";   // [B17 §6 A1] analis LLM per-channel + buku keputusan
const G_PARTNER = "Program Agen (Partner)";
const G_HARGA = "Sumber Harga Model AI";   // [F3 2026-08-23] sumber tarif = data, bukan tertanam di kode
const G_DURASI = "Durasi Video & Mutu Naskah";        // [DURASI 2026-08-01] kenop yang owner bisa tindak
const G_DURASI_LANJUT = "Durasi — Ambang Teknis (lanjutan)";  // penjaga statistik: jarang disentuh, tapi HARUS terlihat
const G_OTHER = "Lainnya";
const G_INTERNAL = "Internal — ditulis mesin (jangan diubah)";
const CFG_GROUPS: [string, string][] = [
  [G_BILLING, "Subscription, Trial & Billing"],
  [G_GERBANG, "Production Test Gate (content leak guard)"],   // [B24] §10d
  [G_LIFECYCLE, "Growth & Lifecycle"],
  [G_TREND, "Trend Source Weights"],
  [G_ENGINE, "Trend Engine Performance"],
  [G_LEARNING, "Learning Curve (Self-Learning)"],
  [G_RETENTION, "Engine Eyes — Per-Moment Retention Curves (Layer 1)"],   // [B17 §6 M1]
  [G_ANALYST, "Analyst Brain (Layer 2)"],   // [B17 §6 A1]
  [G_PARTNER, "Partner Program"],   // [B21] kartu terpusat 9 kenop (teguran owner 2026-07-17: jangan berserakan di Lainnya)
  [G_DURASI, "Video Duration & Script Quality"],
  [G_DURASI_LANJUT, "Duration — Technical Thresholds (advanced)"],
  [G_OTHER, "Others"],   // ← catch-all: SETIAP key app_config tanpa metadata TETAP tampil (anti-hilang selamanya)
  [G_INTERNAL, "Internal — machine-written (do not edit)"],   // penanda mesin: tampil (transparansi) tapi READ-ONLY
];
// DWIBAHASA WAJIB ([[feedback_bilingual_mandatory]], owner 2026-07-05): label/desc/hint/unit = {id,en};
// desc FE ini = sumber tampilan (DB description = fallback teknis). Key baru TANPA meta = CACAT — lengkapi di sini.
type BiTxt = { id: string; en: string };
const U_HARI: BiTxt = { id: "hari", en: "days" }; const U_JAM: BiTxt = { id: "jam", en: "hours" };
const U_PCT: BiTxt = { id: "%", en: "%" }; const U_DETIK: BiTxt = { id: "detik", en: "sec" };
const U_MS: BiTxt = { id: "ms", en: "ms" }; const U_NONE: BiTxt = { id: "", en: "" };
const U_MB: BiTxt = { id: "MB", en: "MB" }; const U_KALI: BiTxt = { id: "kali", en: "times" };
const U_NASKAH: BiTxt = { id: "naskah", en: "scripts" }; const U_VIDEO: BiTxt = { id: "video", en: "videos" };
const U_RP: BiTxt = { id: "Rp", en: "IDR" }; const U_TGL: BiTxt = { id: "tgl/bln", en: "day/mo" };
// `optionLabels` = teks manusiawi untuk tiap pilihan dropdown (dwibahasa). Tanpa ini, kenop "1/0"
// tampil sebagai angka telanjang — pilihan terbatas yang tak terbaca sama saja dengan salah-ketik
// yang menunggu terjadi (§3.3: tipe input tepat + label yang bermakna).
const CFG_META: Record<string, { label: BiTxt; group: string; unit: BiTxt; desc?: BiTxt; hint?: BiTxt; options?: string[]; optionLabels?: Record<string, BiTxt>; readonly?: boolean }> = {
  // ── [B24 2026-08-02] GERBANG UJI PRODUKSI — penjaga kebocoran konten ────────────────────────────
  // Empat pintu (Uji produksi channel · Uji niche · Jalankan-ulang · unduh stok) menghasilkan video
  // JADI. Video uji terunggah PRIVAT ke YouTube Studio tenant dan bisa mereka ubah jadi Publik —
  // artinya tenant yang tak berlangganan tetap bisa memanen konten. SSOT: §10 dokumen payment-gate.
  test_gate_enabled: {
    label: { id: "Gerbang Uji Aktif", en: "Test Gate Enabled" }, group: G_GERBANG, unit: U_NONE,
    options: ["1", "0"], optionLabels: { "1": { id: "Ya — gerbang menjaga", en: "Yes — gate active" }, "0": { id: "Tidak — gerbang mati", en: "No — gate off" } },
    desc: { id: "Saklar induk. Ya = tenant yang langganannya tidak aktif TIDAK bisa menjalankan uji produksi, uji niche, maupun jalankan-ulang. Tidak = gerbang mati total, perilaku kembali seperti sebelum gerbang dipasang.", en: "Master switch. Yes = tenants without an active subscription cannot run channel tests, niche tests, or re-runs. No = gate fully off, behaviour reverts to before the gate existed." },
    hint: { id: "jaring pengaman: bisa dimatikan seketika tanpa deploy", en: "safety net: can be switched off instantly, no deploy" },
  },

  channel_claim_enabled: {
    label: { id: "Kuncian Klaim Channel", en: "Channel Claim Lock" }, group: G_GERBANG, unit: U_NONE,
    options: ["1", "0"], optionLabels: { "1": { id: "Ya — channel terkunci ke satu akun", en: "Yes — channel locked to one account" }, "0": { id: "Tidak — kuncian mati", en: "No — lock off" } },
    desc: { id: "Channel YouTube yang sudah terdaftar di satu akun MesinViral tidak bisa disambungkan ke akun lain — menutup masa coba berulang dengan email baru.", en: "A YouTube channel registered to one MesinViral account cannot be connected to another — closes repeat trials via a new email." },
    hint: { id: "Pelepasan klaim hanya lewat admin. Matikan hanya bila kuncian salah menolak tenant sah.", en: "Claims are released by admin only. Turn off only if the lock wrongly refuses a legitimate tenant." },
  },
  test_allowed_statuses: {
    label: { id: "Status Yang Boleh Menguji", en: "Statuses Allowed To Test" }, group: G_GERBANG, unit: U_NONE,
    desc: { id: "Daftar status langganan yang boleh menjalankan uji. Masa tenggang (grace) sengaja TIDAK termasuk: produksi rutinnya tetap jalan, tapi tombol ujinya dikunci sampai tagihan dibayar.", en: "Subscription statuses allowed to run tests. Grace is deliberately excluded: routine production keeps running, but test buttons stay locked until the invoice is paid." },
    hint: { id: 'nilai sah: active · trial · grace · trial_expired · suspended · cancelled · blocked', en: 'valid values: active · trial · grace · trial_expired · suspended · cancelled · blocked' },
  },
  trial_test_quota: {
    label: { id: "Jatah Uji Masa Coba", en: "Trial Test Quota" }, group: G_GERBANG, unit: U_VIDEO,
    desc: { id: "Berapa video uji yang boleh dihasilkan tenant selama masa coba. 0 = tanpa batas. Tenant berbayar tidak dibatasi kenop ini.", en: "How many test videos a trial tenant may produce during the trial. 0 = unlimited. Paying tenants are not limited by this." },
  },
  trial_test_quota_counts: {
    label: { id: "Jatah Menghitung Apa", en: "What Counts Against Quota" }, group: G_GERBANG, unit: U_NONE,
    options: ["success", "all"], optionLabels: { success: { id: "Hanya uji yang BERHASIL", en: "Only SUCCESSFUL tests" }, all: { id: "Semua percobaan", en: "Every attempt" } },
    desc: { id: "Hanya-berhasil = uji yang gagal karena kredensial atau kuota AI tidak menghukum tenant (tenant baru wajar gagal beberapa kali saat menyetel channel). Semua-percobaan = setiap tekan tombol memotong jatah.", en: "Only-successful = tests that fail on credentials or AI quota don't punish the tenant (new tenants normally fail a few times while configuring). Every-attempt = each press consumes quota." },
  },
  trial_quota_reset_on_extend: {
    label: { id: "Jatah Segar Saat Diperpanjang", en: "Reset Quota On Extension" }, group: G_GERBANG, unit: U_NONE,
    options: ["1", "0"], optionLabels: { "1": { id: "Ya — jatah segar", en: "Yes — quota resets" }, "0": { id: "Tidak — tetap dihitung", en: "No — keeps counting" } },
    desc: { id: "Saat Anda memperpanjang masa coba seseorang secara sengaja, apakah jatah ujinya ikut segar? Ya = perpanjangan berarti memang sedang diberi kesempatan. Tidak = jatah tetap dihitung sejak masa coba pertama dimulai.", en: "When you deliberately extend someone's trial, does their test quota refresh too? Yes = an extension means you are giving them a real chance. No = quota still counts from the original trial start." },
  },
  auto_resume_on_reactivate: {
    label: { id: "Lepas Rem Otomatis Saat Aktif Kembali", en: "Auto-Resume On Reactivation" }, group: G_GERBANG, unit: U_NONE,
    options: ["1", "0"], optionLabels: { "1": { id: "Ya — otomatis jalan lagi", en: "Yes — resumes automatically" }, "0": { id: "Tidak — tenant pulihkan sendiri", en: "No — tenant recovers manually" } },
    desc: { id: "Saat langganan tenant aktif kembali (bayar, atau Anda aktifkan dari layar admin), channel yang berstatus \"Dihentikan sistem\" otomatis dijalankan lagi. Tanpa ini tenant terjebak: channelnya berhenti sementara satu-satunya tombol pemulih justru terkunci.", en: "When a tenant's subscription becomes active again (payment, or you activate it from admin), channels marked \"Halted by system\" resume automatically. Without this the tenant is trapped: production is stopped while the only recovery button is locked." },
  },

  // ── [DURASI 2026-08-01] Ambang rantai DURASI · NASKAH · SUARA ───────────────────────────────────
  // Sebelumnya SELURUHNYA hanya variabel lingkungan dengan angka bawaan di kode, dan `.env` server tak
  // memuat satu pun — jadi tak terlihat di layar mana pun dan mengubahnya butuh deploy. Pola yang sama
  // membuat `voice_catalog.default_settings` diam-diam memperlambat suara 17% berbulan-bulan.
  qc_min_size_mb:            { label: { id: "Ukuran Video Minimum", en: "Minimum Video Size" }, group: G_DURASI, unit: U_MB, desc: { id: "Video di bawah ukuran ini dianggap rusak/kosong dan tidak dipublikasikan. Disesuaikan otomatis untuk preset pendek.", en: "Videos smaller than this are treated as broken and never published. Auto-scaled for short presets." } },
  qc_max_duration_sec:       { label: { id: "Durasi Maksimum yang Diterima", en: "Maximum Accepted Duration" }, group: G_DURASI, unit: U_DETIK, desc: { id: "Batas atas durasi video. Hanya berlaku bila preset channel di bawah batas ini — video Regular (2–12 menit) tidak ikut dibatasi.", en: "Upper duration bound. Only applies when the channel preset is below it — Regular videos (2–12 min) are unaffected." } },
  qc_min_duration_sec:       { label: { id: "Durasi Minimum yang Wajar", en: "Minimum Sane Duration" }, group: G_DURASI, unit: U_DETIK, desc: { id: "Di bawah ini pasti render terpotong.", en: "Below this the render is certainly truncated." } },
  qc_min_clips:              { label: { id: "Jumlah Potongan Visual Minimum", en: "Minimum Visual Clips" }, group: G_DURASI, unit: U_NONE, desc: { id: "Dipakai hanya bila jumlah adegan tidak diketahui dari preset.", en: "Used only when the scene count is unknown from the preset." } },
  qc_require_audio:          { label: { id: "Video Wajib Bersuara", en: "Audio Required" }, group: G_DURASI, unit: U_NONE, options: ["1", "0"], desc: { id: "1 = video tanpa jalur suara ditolak (narasi gagal ter-mux). 0 = tidak diperiksa.", en: "1 = videos without an audio track are rejected. 0 = not checked." } },
  qc_aspect:                 { label: { id: "Rasio Layar Video", en: "Video Aspect Ratio" }, group: G_DURASI, unit: U_NONE, desc: { id: "Bentuk layar yang diharapkan (lebar:tinggi). Video di luar rasio ini ditolak.", en: "Expected screen shape (width:height). Videos outside it are rejected." } },
  qc_aspect_tolerance_pct:   { label: { id: "Toleransi Rasio Layar", en: "Aspect Tolerance" }, group: G_DURASI, unit: U_PCT, desc: { id: "Selisih rasio yang masih diterima.", en: "Aspect deviation still accepted." } },
  tts_potong_ambang_pct:     { label: { id: "Ambang Narasi Terputus", en: "Truncated Narration Threshold" }, group: G_DURASI, unit: U_PCT, desc: { id: "Bila audio lebih pendek dari sekian persen ramalan, narasinya TERPUTUS → produksi dihentikan & diulang. Terukur terjadi 1 dari 73 render.", en: "If the audio is shorter than this share of the prediction, the narration was cut off → production stops and retries. Measured at 1 in 73 renders." } },
  tts_cakupan_min_pct:       { label: { id: "Cakupan Naskah Terucap Minimum", en: "Minimum Script Coverage" }, group: G_DURASI, unit: U_PCT, desc: { id: "Berapa persen naskah minimal yang benar-benar terucap menurut penanda penyedia suara.", en: "Minimum share of the script actually spoken, per the voice provider's markers." } },
  tts_timeout_dasar_sec:     { label: { id: "Batas Tunggu Penyedia Suara", en: "Voice Provider Timeout" }, group: G_DURASI, unit: U_DETIK, desc: { id: "Penyedia yang menggantung tanpa batas waktu akan mematikan satu utas pekerja selamanya — tanpa error dan tanpa notifikasi.", en: "A provider that hangs with no timeout kills a worker thread forever — no error, no notification." } },
  tts_timeout_per_huruf_ms:  { label: { id: "Tambahan Tunggu per Huruf", en: "Extra Wait per Character" }, group: G_DURASI_LANJUT, unit: U_MS, desc: { id: "Naskah panjang memang butuh waktu lebih lama; batas tunggu ikut panjang naskah.", en: "Long scripts legitimately take longer; the timeout scales with script length." } },
  tts_timeout_maks_sec:      { label: { id: "Batas Tunggu Tertinggi", en: "Maximum Wait" }, group: G_DURASI_LANJUT, unit: U_DETIK, desc: { id: "Berapa pun panjang naskahnya, tak pernah menunggu lebih lama dari ini.", en: "However long the script, never wait longer than this." } },
  script_perbeat_trigger_pct:   { label: { id: "Ambang Tulis Ulang Per Adegan", en: "Per-Scene Rewrite Trigger" }, group: G_DURASI, unit: U_PCT, desc: { id: "Naskah di bawah sekian persen batas bawah ditulis ULANG satu adegan per panggilan — model kecil jauh lebih patuh pada pekerjaan kecil.", en: "Scripts below this share of the lower bound are rewritten one scene per call — small models obey small tasks far better." } },
  script_perbeat_min_rasio_pct: { label: { id: "Lantai Panjang per Adegan", en: "Per-Scene Floor" }, group: G_DURASI_LANJUT, unit: U_PCT, desc: { id: "Adegan di bawah sekian persen jatahnya langsung diminta ditambah saat itu juga.", en: "A scene below this share of its quota is topped up immediately." } },
  script_perbeat_maks_rasio_pct:{ label: { id: "Plafon Panjang per Adegan", en: "Per-Scene Ceiling" }, group: G_DURASI_LANJUT, unit: U_PCT, desc: { id: "Adegan di atas sekian persen jatahnya langsung dirapatkan. Tanpa plafon, kelebihan menumpuk melewati semua adegan (terukur: 220 kata untuk jatah 155).", en: "A scene above this share of its quota is tightened immediately. Without a ceiling, overshoot accumulates across all scenes (measured: 220 words for a 155-word budget)." } },
  script_perbeat_markup_pct:    { label: { id: "Kelebihan Pesanan per Adegan", en: "Per-Scene Order Markup" }, group: G_DURASI_LANJUT, unit: U_PCT, desc: { id: "100 = minta persis sesuai jatah. Di atas 100 = minta lebih banyak agar kekurangan model tertutup (terbukti menyebabkan kelebihan ganda — biarkan 100).", en: "100 = ask exactly the quota. Above 100 asks for extra to absorb model shortfall (proved to double-count — keep at 100)." } },
  script_perbeat_trigger_atas_pct: { label: { id: "Ambang Tulis Ulang (naskah kepanjangan)", en: "Rewrite Trigger (script too long)" }, group: G_DURASI, unit: U_PCT, desc: { id: "Naskah di atas sekian persen batas ATAS ditulis ULANG satu adegan per panggilan. Pasangan dari ambang bawah — tanpa ini naskah yang kepanjangan tidak punya jalur perbaikan sama sekali.", en: "Scripts above this share of the UPPER bound are rewritten one scene per call. The counterpart of the lower trigger — without it, over-long scripts have no repair path at all." } },
  ffmpeg_timeout_sec:           { label: { id: "Batas Waktu Perintah Video (ffmpeg)", en: "Video Command Timeout (ffmpeg)" }, group: G_DURASI_LANJUT, unit: U_DETIK, desc: { id: "Render sehat terukur jauh di bawah angka ini (video 91 detik = 456 detik render). Batas ini hanya membebaskan proses yang menggantung — tanpanya satu perintah video yang macet mematikan satu utas pekerja selamanya.", en: "Healthy renders measure far below this (a 91s video took 456s). This only frees a hung process — without it one stuck video command kills a worker thread forever." } },
  ffprobe_timeout_sec:          { label: { id: "Batas Waktu Baca Metadata Video", en: "Video Metadata Read Timeout" }, group: G_DURASI_LANJUT, unit: U_DETIK, desc: { id: "Membaca durasi/dimensi berkas tak pernah lama secara sah.", en: "Reading a file's duration/dimensions is never legitimately slow." } },
  tts_chunk_maks_huruf:         { label: { id: "Batas Huruf per Permintaan Suara (umum)", en: "Voice Request Character Limit (fallback)" }, group: G_DURASI_LANJUT, unit: U_NONE, desc: { id: "Dipakai untuk penyedia yang batas resminya belum terverifikasi. Penyedia yang sudah diketahui memakai angkanya sendiri di Katalog > Voices.", en: "Used for providers whose official limit is not yet verified. Known providers use their own value in Catalog > Voices." } },
  script_perbeat_retry:         { label: { id: "Percobaan Ulang per Adegan", en: "Per-Scene Retries" }, group: G_DURASI_LANJUT, unit: U_KALI, desc: { id: "Berapa kali satu adegan dicoba ulang saat penyedia AI menolak sementara (kuota/jaringan).", en: "How many times a scene is retried when the AI provider fails temporarily (quota/network)." } },
  script_refit_rounds:          { label: { id: "Putaran Perbaikan Panjang Naskah", en: "Length-Fix Rounds" }, group: G_DURASI, unit: U_KALI, desc: { id: "Berapa kali model diminta merapatkan sendiri panjang naskahnya sebelum produksi berhenti jujur. Kode memverifikasi tiap angka & nama masih ada.", en: "How many times the model is asked to adjust its own script length before production stops honestly. Code verifies every number and name survives." } },
  script_refit_parse_retry:     { label: { id: "Percobaan Ulang Jawaban Rusak", en: "Malformed Reply Retries" }, group: G_DURASI_LANJUT, unit: U_KALI, desc: { id: "Jawaban AI yang formatnya rusak diminta ulang tanpa menghabiskan jatah putaran perbaikan.", en: "Malformed AI replies are re-requested without consuming a fix round." } },
  script_length_tolerance_pct:  { label: { id: "Toleransi Panjang (channel tanpa preset)", en: "Length Tolerance (no-preset channels)" }, group: G_DURASI_LANJUT, unit: U_PCT, desc: { id: "Hanya untuk channel yang belum memilih preset durasi. Channel ber-preset memakai batas titik-tengah antar-preset, bukan persen.", en: "Only for channels without a duration preset. Preset channels use the midpoint bounds between presets, not a percentage." } },
  qc_duration_tolerance_pct:    { label: { id: "Pagar Atas Toleransi Panjang", en: "Length Tolerance Cap" }, group: G_DURASI_LANJUT, unit: U_PCT, desc: { id: "Target internal tidak pernah lebih longgar dari angka ini.", en: "The internal target is never looser than this." } },
  script_margin_band_pct:       { label: { id: "Jarak Aman dari Tepi Rentang", en: "Safety Margin from Range Edge" }, group: G_DURASI, unit: U_PCT, desc: { id: "Saat menulis, mesin membidik menjauh dari tepi rentang sebanyak ini (persen lebar rentang) — sebab ramalan durasinya sendiri meleset 1–2 detik, dan berhenti tepat di tepi berarti menyerahkan hasil pada undian. Penilai akhir TIDAK memakai margin ini, jadi tak ada video sah yang ditolak.", en: "While writing, the machine aims away from the range edge by this share of the range width — its own duration forecast is off by 1–2 seconds, and stopping right at the edge leaves the result to chance. The final judge does NOT use this margin, so no valid video is rejected." } },
  script_maks_kata_per_kalimat: { label: { id: "Kalimat Terpanjang yang Wajar", en: "Longest Reasonable Sentence" }, group: G_DURASI, unit: U_NONE, desc: { id: "Kalimat lebih panjang dari sekian kata membuat narator membaca tanpa jeda sampai kehabisan napas — naskahnya ditandai cacat dan diminta diperbaiki. Lahir dari kejadian nyata: model pernah menulis 76 kata tanpa satu pun titik.", en: "Sentences longer than this make the narrator read without a breath — the script is flagged and sent back for repair. Born from a real incident: a model once wrote 76 words with no period at all." } },
  pace_calib_min_n:          { label: { id: "Render Minimum untuk Kalibrasi", en: "Minimum Renders to Calibrate" }, group: G_DURASI_LANJUT, unit: U_NASKAH, desc: { id: "Berapa render nyata sebelum sebuah suara boleh punya angka durasinya sendiri. Kurang dari ini = menebak.", en: "How many real renders before a voice earns its own duration numbers. Fewer than this is guessing." } },
  pace_calib_min_chars:      { label: { id: "Panjang Naskah Minimum (kalibrasi)", en: "Minimum Script Length (calibration)" }, group: G_DURASI_LANJUT, unit: U_NONE, desc: { id: "Naskah lebih pendek dari sekian huruf tidak dipakai mengkalibrasi — porsi jedanya tidak wajar.", en: "Scripts shorter than this many characters are not used for calibration — their pause share is unrepresentative." } },
  pace_calib_min_fitur_n:    { label: { id: "Naskah Minimum per Tanda Baca", en: "Minimum Scripts per Punctuation Mark" }, group: G_DURASI_LANJUT, unit: U_NASKAH, desc: { id: "Sebuah tanda baca hanya dapat angkanya sendiri bila muncul di sekian naskah. Tanda yang JARANG menghasilkan angka yang tampak masuk akal tapi salah (em-dash pernah 1,137 dtk padahal 0,424).", en: "A punctuation mark only earns its own number if it appears in this many scripts. Rare marks yield plausible-looking but wrong numbers (em-dash once read 1.137s when the truth is 0.424)." } },
  pace_calib_max_err_ms:     { label: { id: "Batas Kesalahan Kalibrasi", en: "Calibration Error Limit" }, group: G_DURASI_LANJUT, unit: U_MS, desc: { id: "Hasil kalibrasi yang melesetnya di atas ini DIBUANG — angka yang tak lebih baik dari bawaan tidak dipasang.", en: "Calibration results worse than this are discarded — numbers no better than the defaults are never installed." } },
  probe_min_teks:            { label: { id: "Teks Alat Ukur Minimum", en: "Minimum Probe Texts" }, group: G_DURASI_LANJUT, unit: U_NASKAH, desc: { id: "Berapa teks alat ukur yang harus berhasil sebelum biaya jeda sebuah suara dianggap terukur.", en: "How many probe texts must succeed before a voice's pause costs count as measured." } },
  probe_min_positif_pct:     { label: { id: "Konsistensi Arah Pengukuran", en: "Measurement Direction Consistency" }, group: G_DURASI_LANJUT, unit: U_PCT, desc: { id: "Berapa persen teks yang harus menunjukkan tanda itu MENAMBAH waktu. Di bawah ini arah pengukurannya sendiri tidak konsisten.", en: "What share of texts must show the mark ADDING time. Below this, even the direction is inconsistent." } },
  probe_maks_mad_ms:         { label: { id: "Sebaran Maksimum Antar-Teks", en: "Maximum Spread Across Texts" }, group: G_DURASI_LANJUT, unit: U_MS, desc: { id: "Penyedia yang tidak konsisten (ElevenLabs) menghasilkan sebaran besar — angkanya ditolak, bukan dipakai.", en: "Inconsistent providers (ElevenLabs) produce a wide spread — the number is rejected rather than used." } },
  probe_min_detik_ms:        { label: { id: "Biaya Jeda Terkecil yang Berarti", en: "Smallest Meaningful Pause" }, group: G_DURASI_LANJUT, unit: U_MS, desc: { id: "Di bawah ini tak terbedakan dari derau.", en: "Below this it is indistinguishable from noise." } },
  probe_ts_min_dasar:        { label: { id: "Pembanding Minimum (penanda waktu)", en: "Minimum Baseline Gaps (timestamps)" }, group: G_DURASI_LANJUT, unit: U_NONE, desc: { id: "Berapa jarak antar-kata TANPA tanda yang dibutuhkan sebagai pembanding saat mengukur dari penanda waktu penyedia.", en: "How many unmarked word gaps are needed as a baseline when measuring from provider timestamps." } },
  probe_ts_min_tanda:        { label: { id: "Kemunculan Minimum per Tanda", en: "Minimum Occurrences per Mark" }, group: G_DURASI_LANJUT, unit: U_NONE, desc: { id: "Berapa kemunculan sebuah tanda yang dibutuhkan saat mengukur dari penanda waktu penyedia.", en: "How many occurrences of a mark are needed when measuring from provider timestamps." } },
  drift_alarm_pct:           { label: { id: "Ambang Alarm Akurasi Durasi", en: "Duration Accuracy Alarm" }, group: G_DURASI, unit: U_PCT, desc: { id: "Bila rata-rata durasi video meleset lebih dari sekian persen, Anda dikabari lewat Telegram.", en: "If average video duration drifts more than this, you get a Telegram alert." } },
  drift_window_n:            { label: { id: "Jendela Penilaian Akurasi", en: "Accuracy Window" }, group: G_DURASI, unit: U_VIDEO, desc: { id: "Berapa video terakhir yang dinilai saat memeriksa akurasi durasi.", en: "How many recent videos are assessed when checking duration accuracy." } },
  drift_alarm_cooldown_h:    { label: { id: "Jeda Antar-Alarm Akurasi", en: "Accuracy Alarm Cooldown" }, group: G_DURASI, unit: U_JAM, desc: { id: "Jarak minimum antar-alarm supaya tidak berdering berkali-kali sehari.", en: "Minimum gap between alarms so it never rings repeatedly in a day." } },
  beat_align_min_n:          { label: { id: "Sampel Minimum Penyelarasan Adegan", en: "Minimum Samples for Scene Alignment" }, group: G_DURASI_LANJUT, unit: U_NONE, desc: { id: "Berapa sampel sebelum bobot sebuah adegan disesuaikan ke kenyataan.", en: "How many samples before a scene's weight is adjusted to reality." } },
  beat_align_max_step_pct:   { label: { id: "Langkah Maksimum Penyelarasan Adegan", en: "Maximum Scene Alignment Step" }, group: G_DURASI_LANJUT, unit: U_PCT, desc: { id: "Seberapa jauh bobot adegan boleh bergeser dalam satu siklus. Geser halus, tak pernah melompat.", en: "How far a scene weight may move in one cycle. Gentle drift, never a jump." } },
  // ── [B21] PROGRAM AGEN — 9 kenop terpusat (SPEC AGENT_AND_AFILIATION_ARCITECTURE.md §3.2) ──
  partner_program_enabled:          { label: { id: "Saklar Program", en: "Program Switch" }, group: G_PARTNER, unit: U_NONE, desc: { id: "1 = hidup; 0 = mati (kode agen/reseller DITOLAK di form daftar; komisi tenant lama tetap berjalan).", en: "1 = on; 0 = off (partner codes rejected at signup; existing tenants keep earning)." } },
  partner_payout_day:               { label: { id: "Tanggal Pencairan Bulanan", en: "Monthly Payout Day" }, group: G_PARTNER, unit: U_TGL, desc: { id: "Komisi periode bulan sebelumnya dicairkan tiap tanggal ini (pengingat Telegram otomatis ke Anda).", en: "Previous month's commissions are paid on this day (automatic Telegram reminder to you)." } },
  partner_min_payout_idr:           { label: { id: "Ambang Minimum Pencairan", en: "Minimum Payout Threshold" }, group: G_PARTNER, unit: U_RP, desc: { id: "Tagihan agen di bawah ini DIGULUNG ke bulan berikutnya (hemat biaya transfer receh).", en: "Agent bills below this roll over to next month (avoids petty transfers)." } },
  partner_default_commission_type:  { label: { id: "Tipe Komisi Default (Agen Baru)", en: "Default Commission Type (New Agent)" }, group: G_PARTNER, unit: U_NONE, options: ["percent", "flat_idr"], desc: { id: "Prefill saat membuat agen baru: percent = % dari pembayaran; flat_idr = Rupiah tetap per bulan-langganan. Nilai per-agen tetap diatur di halaman Program Agen.", en: "Prefill for new agents: percent of payment, or flat IDR per subscription-month. Per-agent value is still set on the Partner page." } },
  partner_default_commission_value: { label: { id: "Nilai Komisi Default (Agen Baru)", en: "Default Commission Value (New Agent)" }, group: G_PARTNER, unit: U_NONE, desc: { id: "Angka prefill agen baru — maknanya ikut tipe di atas (% atau Rp).", en: "Prefill number for new agents — meaning follows the type above (% or IDR)." } },
  partner_tax_pct_badan_npwp:       { label: { id: "PPh — Badan ber-NPWP", en: "Withholding — Company w/ Tax ID" }, group: G_PARTNER, unit: U_PCT, desc: { id: "Prefill potongan PPh 23 saat menyusun pencairan utk agen badan usaha ber-NPWP (bisa dikoreksi per-pencairan). Validasi konsultan pajak.", en: "PPh 23 withholding prefill for companies with tax ID (editable per payout). Validate with your tax consultant." } },
  partner_tax_pct_badan_non_npwp:   { label: { id: "PPh — Badan TANPA NPWP", en: "Withholding — Company w/o Tax ID" }, group: G_PARTNER, unit: U_PCT, desc: { id: "Prefill PPh 23 tarif ganda utk badan tanpa NPWP.", en: "Doubled PPh 23 prefill for companies without tax ID." } },
  partner_tax_pct_perorangan:       { label: { id: "PPh — Agen Perorangan", en: "Withholding — Individual Agent" }, group: G_PARTNER, unit: U_PCT, desc: { id: "Prefill PPh 21 bukan-pegawai (lapisan awal PMK 168/2023).", en: "PPh 21 non-employee prefill (first bracket, PMK 168/2023)." } },
  partner_tax_pct_pkp:              { label: { id: "PPh — Agen PKP", en: "Withholding — VAT-registered Agent" }, group: G_PARTNER, unit: U_PCT, desc: { id: "Prefill PPh 23 utk agen PKP (PPN-nya ditagih agen via faktur pajak, bukan potongan).", en: "PPh 23 prefill for VAT-registered agents (VAT is invoiced by the agent, not withheld)." } },
  // ── PENANDA INTERNAL (ditulis & dibaca MESIN — read-only di layar; anti-tersenggol) ──
  ops_partner_reminder_last:        { label: { id: "Penanda: Pengingat Pencairan Terakhir", en: "Marker: Last Payout Reminder" }, group: G_INTERNAL, unit: U_NONE, readonly: true, desc: { id: "Ditulis mesin — periode terakhir pengingat pencairan komisi terkirim (anti-spam 1×/bulan).", en: "Machine-written — last period the payout reminder was sent (anti-spam, once per month)." } },
  ops_tg_update_offset:             { label: { id: "Penanda: Posisi Baca Bot Telegram", en: "Marker: Telegram Bot Read Offset" }, group: G_INTERNAL, unit: U_NONE, readonly: true, desc: { id: "Ditulis mesin tiap beberapa detik — sampai pesan mana bot 'Hubungkan Telegram' sudah memproses (restart tidak mengulang pesan lama).", en: "Machine-written every few seconds — how far the connect-bot has processed messages (restarts don't replay old ones)." } },
  ops_drift_alarm_last_at:          { label: { id: "Penanda: Alarm Drift Durasi Terakhir", en: "Marker: Last Duration Drift Alarm" }, group: G_INTERNAL, unit: U_NONE, readonly: true, desc: { id: "Ditulis mesin — kapan alarm akurasi-durasi terakhir dikirim (jeda anti-banjir 24 jam).", en: "Machine-written — when the duration-drift alarm last fired (24h anti-flood cooldown)." } },
  // ── ENAM kenop yang TAMPIL SEBAGAI NAMA MENTAH di kelompok "Lainnya" (terlihat 2026-08-02 saat
  //    layarnya benar-benar dibuka dengan sesi admin). Persis pelanggaran yang owner tegur 17-Jul
  //    ("12 kenop partner berserakan di Lainnya tanpa label — asal jadi, tidak world-class").
  //    Isi label & penjelasan diambil dari deskripsi DB + pembacanya di kode, bukan dikarang.
  ops_drift_alarm_state:        { label: { id: "Penanda: Status Alarm Drift Durasi", en: "Marker: Duration Drift Alarm State" }, group: G_INTERNAL, unit: U_NONE, readonly: true, desc: { id: "Ditulis mesin tiap siklus pemeliharaan — median kemelesetan durasi terakhir, sedang berbunyi atau tidak, dan kapan terakhir berbunyi. Dibaca untuk memutuskan alarm berikutnya.", en: "Machine-written each maintenance cycle — last median duration error, whether the alarm is active, and when it last fired. Read to decide the next alarm." } },
  buffer_target_days:           { label: { id: "Stok Video di Depan", en: "Video Stock Ahead" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Berapa HARI kebutuhan tayang yang disiapkan lebih dulu. Target stok = jumlah slot publish per hari × angka ini. Channel yang mengatur kedalaman buffer sendiri tidak terpengaruh.", en: "How many DAYS of publishing demand to stock ahead. Target = publish slots per day × this. Channels with their own buffer depth are unaffected." } },
  test_result_ttl_hours:        { label: { id: "Umur Kartu Hasil Uji Channel", en: "Channel Test-Result Card Lifetime" }, group: G_LIFECYCLE, unit: U_JAM, desc: { id: "Berapa jam kartu hasil uji tetap tampil di halaman channel setelah pengujian selesai.", en: "How many hours the test-result card stays visible on the channel page after a test finishes." } },
  niche_new_badge_days:         { label: { id: "Umur Badge \"BARU\" di Pustaka Niche", en: "\"NEW\" Badge Age in Niche Library" }, group: G_OTHER, unit: U_HARI, desc: { id: "Selama sekian hari sejak dirilis, sebuah niche diberi badge BARU di etalase tenant.", en: "For this many days after release, a niche carries a NEW badge in the tenant storefront." } },
  niche_search_synonyms:        { label: { id: "Sinonim Pencarian Niche (ID→EN)", en: "Niche Search Synonyms (ID→EN)" }, group: G_OTHER, unit: U_NONE, desc: { id: "Supaya tenant yang mengetik bahasa Indonesia tetap menemukan niche yang kata kuncinya berbahasa Inggris (mis. \"hantu\" → horror, ghost).", en: "So tenants typing Indonesian still find niches whose keywords are English (e.g. \"hantu\" → horror, ghost)." }, hint: { id: 'JSON {"kata":"sinonim en"}', en: 'JSON {"word":"en synonyms"}' } },
  niche_tone_moods:             { label: { id: "Klasifikasi Nuansa Niche (Gelap/Cerah)", en: "Niche Tone Classification (Dark/Bright)" }, group: G_OTHER, unit: U_NONE, desc: { id: "Mengelompokkan mood DNA niche menjadi nuansa Gelap atau Cerah di etalase tenant. Mood yang tak terdaftar dianggap Netral.", en: "Groups a niche's DNA moods into Dark or Bright in the tenant storefront. Unlisted moods count as Neutral." }, hint: { id: 'JSON {"dark":[...],"bright":[...]}', en: 'JSON {"dark":[...],"bright":[...]}' } },
  trial_duration_days:          { label: { id: "Masa Trial Gratis", en: "Free Trial Length" }, group: G_BILLING, unit: U_HARI, desc: { id: "Berapa hari calon pelanggan bisa mencoba gratis sebelum harus berlangganan.", en: "How many days a prospect can try for free before subscribing." } },
  trial_reminder_days_before:   { label: { id: "Pengingat Sebelum Trial Habis", en: "Reminder Before Trial Ends" }, group: G_BILLING, unit: U_HARI, desc: { id: "Kirim email pengingat upgrade H-x sebelum trial berakhir (0 = matikan).", en: "Send an upgrade reminder x days before the trial ends (0 = off)." } },
  renewal_reminder_days_before: { label: { id: "Pengingat Sebelum Langganan Habis", en: "Renewal Reminder" }, group: G_BILLING, unit: U_HARI, desc: { id: "Kirim email pengingat perpanjangan H-x sebelum langganan berakhir (0 = matikan).", en: "Send a renewal reminder x days before the subscription ends (0 = off)." } },
  subscription_period_days:     { label: { id: "Durasi Periode Langganan", en: "Subscription Period" }, group: G_BILLING, unit: U_HARI, desc: { id: "Durasi satu periode langganan berbayar. Default 30 = bulanan.", en: "Length of one paid subscription period. Default 30 = monthly." } },
  annual_discount_pct:          { label: { id: "Diskon Paket Tahunan", en: "Annual Plan Discount" }, group: G_BILLING, unit: U_PCT, desc: { id: "Harga tahunan = bulanan × 12 × (100−nilai)%. 0 = pilihan tahunan disembunyikan dari pelanggan.", en: "Annual price = monthly × 12 × (100−value)%. 0 = the annual option is hidden from customers." } },
  billing_grace_days:           { label: { id: "Masa Tenggang Sebelum Dihentikan", en: "Grace Period Before Stop" }, group: G_BILLING, unit: U_HARI, desc: { id: "Setelah langganan berakhir, mesin MASIH jalan selama masa tenggang ini sambil menunggu pembayaran.", en: "After expiry, production keeps running during this grace period while awaiting payment." } },
  checkout_expiry_hours:        { label: { id: "Masa Berlaku Link Bayar", en: "Payment Link Validity" }, group: G_BILLING, unit: U_JAM, desc: { id: "Berapa jam link pembayaran Midtrans berlaku sebelum kedaluwarsa.", en: "How many hours a Midtrans payment link stays valid." } },
  ppn_percent:                  { label: { id: "PPN Invoice", en: "Invoice VAT" }, group: G_BILLING, unit: U_PCT, desc: { id: "PPN pada invoice. 0 = harga final tanpa PPN; isi 11 bila perusahaan PKP.", en: "VAT on invoices. 0 = final price, no VAT; set 11 if VAT-registered." } },
  ai_price_feed_url:            { label: { id: "URL Sumber Harga Model AI", en: "AI Price Source URL" }, group: G_HARGA, unit: U_NONE, desc: { id: "Alamat daftar harga model AI yang dibaca mesin tiap hari. Ganti di sini bila sumbernya pindah — berlaku TANPA deploy. Kosongkan = pakai bawaan mesin. PENTING: sumber ini tidak berwenang untuk semua model; harga yang sudah diketik manual TIDAK akan ditimpa (barisnya terkunci), dan penyedia agregator (mis. fal) tak boleh memakai tarif vendor di belakangnya.", en: "Address of the AI price list the engine reads daily. Change it here if the source moves — takes effect WITHOUT deploy. Empty = engine default. NOTE: this source is not authoritative for every model; manually entered prices are never overwritten (their row is locked), and aggregator providers (e.g. fal) must not use the underlying vendor's rates." } },
  ai_price_fallback_url:        { label: { id: "URL Sumber Harga Cadangan", en: "Fallback Price Source URL" }, group: G_HARGA, unit: U_NONE, desc: { id: "Sumber cadangan untuk model NASKAH saja (router). Dipakai hanya bila sumber utama tak memuat modelnya. TIDAK dipakai untuk penyedia agregator, sebab yang ditemukannya adalah tarif vendor asal — bukan tarif agregatornya.", en: "Fallback source for SCRIPT models only (router). Used only when the main source lacks the model. NOT used for aggregator providers, because it returns the underlying vendor's rate rather than the aggregator's." } },
  usd_idr_rate:                 { label: { id: "Kurs USD → IDR", en: "USD → IDR Rate" }, group: G_BILLING, unit: U_NONE, desc: { id: "Kurs untuk TAMPILAN biaya AI BYOK dalam Rupiah (biaya asli disimpan USD). Disinkron OTOMATIS harian dari kurs pasar; mengedit manual = otomatis terkunci.", en: "Rate used to DISPLAY BYOK AI costs in Rupiah (costs are stored in USD). Auto-synced daily from market data; editing manually locks it." } },
  usd_idr_rate_locked:          { label: { id: "Kunci Kurs Manual", en: "Manual Rate Lock" }, group: G_BILLING, unit: U_NONE, desc: { id: "1 = mesin TIDAK menimpa kurs (Anda kelola sendiri); 0 = kurs disinkron otomatis harian.", en: "1 = the engine never overwrites the rate (you manage it); 0 = auto-synced daily." }, hint: { id: "otomatis jadi 1 saat kurs diedit", en: "auto-set to 1 when rate is edited" } },
  nurture_enabled:                 { label: { id: "Nurture Trial-Lapse Aktif", en: "Trial-Lapse Nurture On" }, group: G_LIFECYCLE, unit: U_NONE, desc: { id: "Master ON/OFF mesin tindak-lanjut (nurture) trial yang lewat. 1 = nyala, 0 = mati.", en: "Master ON/OFF for the lapsed-trial nurture engine. 1 = on, 0 = off." } },
  nurture_trial_extend_days:       { label: { id: "Perpanjang Trial 1-Klik", en: "1-Click Trial Extension" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Berapa hari tambahan yang diberikan link 1-klik di email kepada calon pelanggan yang masa cobanya habis. 0 = matikan tuas ini sepenuhnya.", en: "How many extra days the 1-click email link grants a lapsed trial. 0 = disable this lever entirely." } },
  // [B24 §10e-3 CELAH C] Dulu link 1-klik bisa dipakai BERULANG tanpa batas: masa coba lapse lagi
  // beberapa hari kemudian sementara token email berlaku 90 hari → masa coba gratis selamanya.
  nurture_self_extend_max:         { label: { id: "Batas Perpanjang Mandiri", en: "Self-Extension Limit" }, group: G_LIFECYCLE, unit: U_KALI, desc: { id: "Berapa kali calon pelanggan boleh memperpanjang masa cobanya SENDIRI lewat link di email. Setelah habis, link mengarahkannya memilih paket. 0 = tidak boleh sama sekali (hanya Anda yang bisa memperpanjang, dari layar Tenant). Perpanjangan oleh admin tidak dibatasi kenop ini.", en: "How many times a prospect may extend their own trial via the email link. Once used up, the link routes them to pick a plan instead. 0 = never (only you can extend, from the Tenants screen). Admin-side extensions are not limited by this." } },
  winback_discount_pct:            { label: { id: "Diskon Comeback", en: "Winback Discount" }, group: G_LIFECYCLE, unit: U_PCT, desc: { id: "Diskon bulan pertama untuk lead yang kembali. 0 = matikan (harga normal).", en: "First-month discount for returning leads. 0 = off (normal price)." } },
  winback_discount_valid_days:     { label: { id: "Masa Berlaku Diskon Comeback", en: "Winback Discount Validity" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Masa berlaku diskon comeback sejak ditawarkan — menciptakan urgensi.", en: "How long the winback discount stays valid once offered — creates urgency." } },
  nurture_step1_days:              { label: { id: "Email Nurture #1", en: "Nurture Email #1" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Dikirim H+x hari setelah trial habis.", en: "Sent x days after the trial lapses." } },
  nurture_step2_days:              { label: { id: "Email Nurture #2", en: "Nurture Email #2" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Dikirim H+x hari setelah trial habis.", en: "Sent x days after the trial lapses." } },
  nurture_step3_days:              { label: { id: "Email Nurture #3 (diskon)", en: "Nurture Email #3 (discount)" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Dikirim H+x hari setelah trial habis.", en: "Sent x days after the trial lapses." } },
  nurture_step4_days:              { label: { id: "Email Nurture #4", en: "Nurture Email #4" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Dikirim H+x hari setelah trial habis.", en: "Sent x days after the trial lapses." } },
  nurture_step5_days:              { label: { id: "Email Nurture #5", en: "Nurture Email #5" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Dikirim H+x hari setelah trial habis (terakhir).", en: "Sent x days after the trial lapses (final)." } },
  suspend_window_days:             { label: { id: "Masa Suspended → Blokir", en: "Suspended → Blocked Window" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Lama status suspended (produksi stop, data utuh, bisa aktif lagi) sebelum akun dikunci.", en: "How long an account stays suspended (production stopped, data intact) before being blocked." } },
  suspend_dunning1_days:           { label: { id: "Penagihan Suspended #1", en: "Suspended Dunning #1" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Email penagihan H+x hari setelah masuk suspended.", en: "Dunning email x days after suspension." } },
  suspend_dunning2_days:           { label: { id: "Penagihan Suspended #2", en: "Suspended Dunning #2" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Email penagihan H+x hari setelah masuk suspended.", en: "Dunning email x days after suspension." } },
  suspend_dunning3_days:           { label: { id: "Penagihan Suspended #3", en: "Suspended Dunning #3" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Email penagihan H+x hari setelah masuk suspended.", en: "Dunning email x days after suspension." } },
  suspend_dunning4_days:           { label: { id: "Penagihan Suspended #4", en: "Suspended Dunning #4" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Email penagihan H+x hari setelah masuk suspended.", en: "Dunning email x days after suspension." } },
  suspend_dunning5_days:           { label: { id: "Penagihan Suspended #5", en: "Suspended Dunning #5" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Email penagihan H+x hari setelah masuk suspended.", en: "Dunning email x days after suspension." } },
  block_retention_days:            { label: { id: "Retensi Sebelum Hapus Data", en: "Retention Before Deletion" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Lama data disimpan setelah akun dikunci (blocked) sebelum DIHAPUS permanen.", en: "How long data is kept after an account is blocked before PERMANENT deletion." } },
  deletion_warn1_days:             { label: { id: "Peringatan Hapus #1", en: "Deletion Warning #1" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Peringatan H-x hari sebelum penghapusan data.", en: "Warning x days before data deletion." } },
  deletion_warn2_days:             { label: { id: "Peringatan Hapus #2", en: "Deletion Warning #2" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Peringatan H-x hari sebelum penghapusan data.", en: "Warning x days before data deletion." } },
  deletion_warn3_days:             { label: { id: "Peringatan Hapus #3", en: "Deletion Warning #3" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Peringatan terakhir H-x hari sebelum penghapusan data.", en: "Final warning x days before data deletion." } },
  s3_raw_purge_after_suspend_days: { label: { id: "Hapus Video Mentah S3", en: "Purge Raw Videos (S3)" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Hapus file video mentah di storage setelah suspended. 0 = segera (video sudah aman di YouTube).", en: "Delete raw video files from storage after suspension. 0 = immediately (videos already live on YouTube)." } },
  voice_div_volume_baseline:    { label: { id: "Voice Diversity: Ambang Volume", en: "Voice Diversity: Volume Baseline" }, group: G_OTHER, unit: { id: "video/bulan", en: "videos/month" }, desc: { id: "Volume publish per bulan yang masih wajar untuk SATU suara (di bawah ambang ini skor voice diversity = 100). Tuntutan variasi suara naik logaritmik di atasnya.", en: "Monthly publish volume considered normal for ONE voice (below this, voice diversity scores 100). Variety demand grows logarithmically above it." } },
  voice_div_max_expected:       { label: { id: "Voice Diversity: Maks Suara Diharapkan", en: "Voice Diversity: Max Expected Voices" }, group: G_OTHER, unit: { id: "suara", en: "voices" }, desc: { id: "Batas atas ekspektasi jumlah suara pada volume produksi sangat tinggi (pagar rumus).", en: "Upper bound of expected distinct voices at very high production volume (formula cap)." } },
  niche_eval_window_days:       { label: { id: "Masa Evaluasi Niche Custom", en: "Custom Niche Review Window" }, group: G_OTHER, unit: U_HARI, desc: { id: "Berapa hari tenant bisa mengevaluasi niche custom yang diserahkan sebelum pesanan otomatis ditutup.", en: "How many days a tenant can review a delivered custom niche before the order auto-closes." } },
  default_publish_slots:        { label: { id: "Jam Publish Awal Channel Baru", en: "Default Publish Times (New Channel)" }, group: G_OTHER, unit: U_NONE, desc: { id: "Jam publish awal untuk channel yang baru dibuat (zona waktu tenant). Tenant bebas mengubahnya di halaman Jadwal.", en: "Initial publish times for newly created channels (tenant timezone). Tenants can change them on the Schedule page." }, hint: { id: 'JSON ["HH:MM",...]', en: 'JSON ["HH:MM",...]' } },
  trend_weight_youtube:    { label: { id: "YouTube (utama)", en: "YouTube (primary)" }, group: G_TREND, unit: U_PCT, desc: { id: "Seberapa besar tren YouTube menentukan pemilihan topik. Sumber utama.", en: "How much YouTube trends drive topic selection. Primary source." } },
  trend_weight_trends:     { label: { id: "Google Trends", en: "Google Trends" }, group: G_TREND, unit: U_PCT, desc: { id: "Bobot tren pencarian Google pada pemilihan topik.", en: "Weight of Google search trends in topic selection." } },
  trend_weight_news:       { label: { id: "Google News", en: "Google News" }, group: G_TREND, unit: U_PCT, desc: { id: "Bobot berita terkini pada pemilihan topik.", en: "Weight of current news in topic selection." } },
  trend_weight_wikipedia:  { label: { id: "Wikipedia", en: "Wikipedia" }, group: G_TREND, unit: U_PCT, desc: { id: "Bobot halaman populer Wikipedia (pengaruh kecil).", en: "Weight of popular Wikipedia pages (minor influence)." } },
  trend_weight_hackernews: { label: { id: "HackerNews", en: "HackerNews" }, group: G_TREND, unit: U_PCT, desc: { id: "Bobot tren teknologi — hanya untuk niche teknologi.", en: "Weight of tech trends — tech niches only." } },
  analyst_enabled:        { label: { id: "Saklar Analis", en: "Analyst Switch" }, group: G_ANALYST, unit: U_NONE, desc: { id: "1 = analis AI jalan per channel (MODE BAYANGAN sampai fase A2: hanya mencatat keputusan ke buku keputusan, NOL efek produksi); 0 = mati total.", en: "1 = the AI analyst runs per channel (SHADOW MODE until phase A2: only records decisions, ZERO production effect); 0 = fully off." } },
  analyst_interval_days:  { label: { id: "Jarak Antar Siklus Analis", en: "Analyst Cycle Interval" }, group: G_ANALYST, unit: U_HARI, desc: { id: "Analis membaca dosir data channel & mengeluarkan keputusan tiap N hari. Default mingguan.", en: "The analyst reads the channel dossier & issues decisions every N days. Default weekly." } },
  analyst_min_videos:     { label: { id: "Gerbang Data Minimum", en: "Minimum Data Gate" }, group: G_ANALYST, unit: { id: "video", en: "videos" }, desc: { id: "Analis hanya jalan bila channel punya minimal N video teranalisis — di bawah itu datanya terlalu tipis untuk keputusan bermakna.", en: "The analyst only runs once a channel has at least N analyzed videos — below that the data is too thin for meaningful decisions." } },
  retention_curve_min_age_days:     { label: { id: "Umur Minimum Video Sebelum Diambil", en: "Minimum Video Age Before Fetch" }, group: G_RETENTION, unit: U_HARI, desc: { id: "Kurva retensi detik-per-detik baru tersedia beberapa hari setelah tayang — video lebih muda dari ini dilewati dulu (bukan error).", en: "Per-moment retention curves only become available a few days after publish — younger videos are skipped for now (not an error)." } },
  retention_curve_refresh_age_days: { label: { id: "Umur Ambil-Ulang (Kurva Matang)", en: "Refresh Age (Matured Curve)" }, group: G_RETENTION, unit: U_HARI, desc: { id: "Saat video melewati umur ini, kurvanya diambil ULANG sekali (versi matang) lalu final — maksimal 2 pengambilan seumur hidup video.", en: "Once a video passes this age its curve is re-fetched once (matured version) then finalized — at most 2 fetches per video lifetime." } },
  retention_curve_max_per_run:      { label: { id: "Batas Pengambilan per Siklus", en: "Fetch Limit per Cycle" }, group: G_RETENTION, unit: { id: "video/siklus", en: "videos/cycle" }, desc: { id: "Batas jumlah video yang kurvanya diambil per channel per siklus self-learning (pengaman kuota API YouTube; 1 request = 1 video).", en: "Cap on how many videos get their curve fetched per channel per self-learning cycle (YouTube API quota guard; 1 request = 1 video)." } },
  retention_curve_give_up_age_days: { label: { id: "Umur Menyerah (Video Sepi)", en: "Give-Up Age (Quiet Videos)" }, group: G_RETENTION, unit: U_HARI, desc: { id: "Video sepi yang kurvanya tetap kosong berhenti dicoba setelah umur ini — mencegah request sia-sia selamanya.", en: "Quiet videos whose curve stays empty stop being retried after this age — prevents wasted requests forever." } },
  learning_curve_window_days:  { label: { id: "Jendela Views Kurva Belajar", en: "Learning Curve Views Window" }, group: G_LEARNING, unit: U_HARI, desc: { id: "Metrik views kurva = views N hari PERTAMA tiap video (anti bias-umur: video lama tak menang karena menabung views).", en: "The curve's views metric = each video's FIRST N days of views (age-bias guard: old videos can't win by piling up views)." } },
  learning_curve_marker_date:  { label: { id: "Garis Penanda Kurva Belajar", en: "Learning Curve Marker Line" }, group: G_LEARNING, unit: U_NONE, desc: { id: "Tanggal garis vertikal \"mesin disehatkan\" di kurva (pembanding sebelum/sesudah). Kosongkan untuk menyembunyikan.", en: "Date of the vertical \"engine tuned\" marker on the curve (before/after comparison). Leave empty to hide." }, hint: { id: "YYYY-MM-DD", en: "YYYY-MM-DD" } },
  learning_curve_metrics:      { label: { id: "Metrik Kurva Belajar", en: "Learning Curve Metrics" }, group: G_LEARNING, unit: U_NONE, desc: { id: "Metrik yang bisa dipilih tenant di kurva; urutan pertama = tampilan awal.", en: "Metrics tenants can toggle on the curve; first item = default view." }, hint: { id: 'JSON ["retention","views7d"]', en: 'JSON ["retention","views7d"]' } },
  trend_cache_ttl_sec:     { label: { id: "Penyegaran Data Tren", en: "Trend Data Refresh" }, group: G_ENGINE, unit: U_DETIK, desc: { id: "Berapa lama data tren disimpan sebelum diambil ulang. Makin lama = makin hemat kuota.", en: "How long trend data is cached before re-fetching. Longer = less quota." }, hint: { id: "43200 = 12 jam", en: "43200 = 12 hours" } },
  trend_refresh_pacing_ms: { label: { id: "Jeda Ambil Data", en: "Fetch Pacing" }, group: G_ENGINE, unit: U_MS, desc: { id: "Jeda antar-pengambilan data tren agar tidak diblokir sumbernya.", en: "Delay between trend fetches to avoid being rate-limited." }, hint: { id: "3000 = 3 detik", en: "3000 = 3 seconds" } },
};

// Pesan error API (kode → dwibahasa) — server kirim kode, FE menerjemahkan.
const ERR_TXT: Record<string, BiTxt> = {
  empty_value:     { id: "Nilai kosong", en: "Empty value" },
  invalid_json:    { id: "JSON tidak valid", en: "Invalid JSON" },
  invalid_integer: { id: "Harus bilangan bulat", en: "Must be an integer" },
};

// Fase 2: Gerakan Kamera per Adegan (content_beats). Arah = dwibahasa.
type BeatRow = { beat_key: string; sort_order: number; label_id: string; label_en: string; motion_mode: string; motion_dir: string };
const MOTION_DIRS: [string, string, string][] = [
  ["zoom_in", "Zoom masuk", "Zoom in"], ["zoom_out", "Zoom keluar", "Zoom out"],
  ["pan_lr", "Geser kiri→kanan", "Pan left→right"], ["pan_rl", "Geser kanan→kiri", "Pan right→left"],
  ["pan_ud", "Geser atas→bawah", "Pan top→bottom"], ["pan_du", "Geser bawah→atas", "Pan bottom→top"],
  ["pan_diag", "Geser diagonal", "Pan diagonal"], ["pan_diag_rev", "Geser diagonal balik", "Pan diagonal reverse"],
  ["still", "Diam", "Still"],
];

export default function AppConfigPage() {
  const [cfg, setCfg] = useState<AppCfg[]>([]);
  const [beats, setBeats] = useState<BeatRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<React.ReactNode | null>(null);
  const [lang, setLang] = useState<"id" | "en">("id");   // utk <option> (tak bisa pakai <Bi> span)
  useEffect(() => { setLang((localStorage.getItem("mv-lang") as "id" | "en") || "id"); }, []);

  const load = useCallback(async () => {
    const [r, rb] = await Promise.all([fetch("/api/admin/app-config"), fetch("/api/admin/beats")]);
    const j = await r.json().catch(() => ({ app_config: [] }));
    const jb = await rb.json().catch(() => ({ beats: [] }));
    setCfg(j.app_config ?? []);
    setBeats(jb.beats ?? []);
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  async function patchBeat(beat_key: string, body: { motion_mode?: string; motion_dir?: string }) {
    const r = await fetch("/api/admin/beats", {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ beat_key, ...body }),
    });
    setToast(r.ok ? <Bi id="✓ Tersimpan" en="✓ Saved" /> : <Bi id="Gagal menyimpan" en="Save failed" />);
    if (r.ok) await load();
    setTimeout(() => setToast(null), 2200);
  }

  async function patch(key: string, body: { value: number } | { value_text: string }) {
    const r = await fetch(`/api/admin/app-config/${key}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      setToast(<Bi id="✓ Tersimpan" en="✓ Saved" />);
      await load();
    } else {
      const e = ERR_TXT[j.error as string];
      setToast(<><Bi id="Gagal menyimpan" en="Save failed" />{e ? <>: <Bi id={e.id} en={e.en} /></> : j.error ? `: ${j.error}` : null}</>);
    }
    setTimeout(() => setToast(null), 2600);
  }

  return (
    <>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 0.375rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <SlidersHorizontal size={20} /> <Bi id="Konfigurasi Sistem" en="System Configuration" />
        </h1>
        <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0, maxWidth: "65ch" }}>
          <Bi id="Parameter global mesin produksi & trial. Berlaku ke seluruh tenant. Tersimpan otomatis — tanpa tombol Save." en="Global production-engine & trial parameters. Applies to all tenants. Auto-saved — no Save button." />
        </p>
      </div>

      {loading ? (
        <div className="muted" style={{ padding: "3rem", textAlign: "center" }}>Memuat…</div>
      ) : (
        <div className="card" style={{ maxWidth: 720 }}>
          <div className="card-head">
            <h3 className="card-title"><SlidersHorizontal size={15} /> <Bi id="Parameter mesin & trial" en="Engine & trial parameters" /></h3>
            <span className="card-sub" style={{ color: "var(--success)", fontWeight: 500 }}><Bi id="✓ Tersimpan otomatis" en="✓ Auto-saved" /></span>
          </div>
          <div className="card-body" style={{ display: "grid", gap: "1.5rem" }}>
            {CFG_GROUPS.map(([grp, grpEn]) => {
              const items = cfg.filter((a) => (CFG_META[a.key]?.group ?? G_OTHER) === grp);
              if (items.length === 0) return null;
              const total = grp === G_TREND ? items.reduce((n, a) => n + (a.value || 0), 0) : null;
              return (
                <div key={grp}>
                  <div className="label" style={{ textTransform: "uppercase", letterSpacing: ".04em", marginBottom: ".5rem", display: "flex", alignItems: "center", gap: ".5rem" }}>
                    <span><Bi id={grp} en={grpEn} /></span>
                    {total != null && <span style={{ color: total === 100 ? "var(--success)" : "var(--warning)", fontWeight: 600 }}>total {total}%{total !== 100 && " ⚠"}</span>}
                  </div>
                  {items.map((a) => {
                    const m = CFG_META[a.key];
                    return (
                      <div key={a.key} style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "1rem", alignItems: "center", padding: ".7rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}>{m ? <Bi id={m.label.id} en={m.label.en} /> : a.key}</div>
                          <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "3px", lineHeight: 1.45 }}>
                            {m?.desc ? <Bi id={m.desc.id} en={m.desc.en} /> : a.description}
                            {m?.hint && <span style={{ marginLeft: ".375rem", opacity: .75 }}>(<Bi id={m.hint.id} en={m.hint.en} />)</span>}
                          </div>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: ".4rem", flex: "none" }}>
                          {m?.readonly ? (
                            /* Penanda internal: ditulis mesin — tampil demi transparansi, TIDAK bisa diedit */
                            <span className="muted" style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)" }}>{a.value_text ?? a.value} 🔒</span>
                          ) : m?.options && a.value_text != null ? (
                            /* Pilihan terbatas TEKS (mis. tipe komisi) — dropdown auto-save, anti salah-ketik */
                            <select className="input" style={{ width: "12rem", height: "2rem", fontSize: "var(--text-xs)" }} defaultValue={a.value_text} onChange={(e) => { const v = e.target.value; if (v !== a.value_text) patch(a.key, { value_text: v }); }}>
                              {m.options.map((o) => <option key={o} value={o}>{m.optionLabels?.[o] ? (lang === "en" ? m.optionLabels[o].en : m.optionLabels[o].id) : o}</option>)}
                            </select>
                          ) : m?.options && a.value_text == null ? (
                            /* [B24] Pilihan terbatas ANGKA (mis. saklar Ya/Tidak) — dulu tampil sebagai kotak
                               angka telanjang: pilihan terbatas yang tak terbaca = salah-ketik menunggu terjadi. */
                            <select className="input" style={{ width: "12rem", height: "2rem", fontSize: "var(--text-xs)" }} defaultValue={String(a.value)} onChange={(e) => { const n = parseInt(e.target.value, 10); if (Number.isInteger(n) && n !== a.value) patch(a.key, { value: n }); }}>
                              {m.options.map((o) => <option key={o} value={o}>{m.optionLabels?.[o] ? (lang === "en" ? m.optionLabels[o].en : m.optionLabels[o].id) : o}</option>)}
                            </select>
                          ) : a.value_text != null ? (
                            /* Baris TEKS/JSON (0125, value_text) — mis. default_publish_slots */
                            <input className="input" type="text" style={{ width: "13rem", height: "2rem", fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)" }} defaultValue={a.value_text} onBlur={(e) => { const v = e.target.value.trim(); if (v && v !== a.value_text) patch(a.key, { value_text: v }); }} />
                          ) : (
                            <input className="input" type="number" min={0} style={{ width: "5.5rem", height: "2rem", textAlign: "right" }} defaultValue={a.value} onBlur={(e) => { const n = parseInt(e.target.value, 10); if (Number.isInteger(n) && n !== a.value) patch(a.key, { value: n }); }} />
                          )}
                          <span className="muted" style={{ fontSize: "var(--text-xs)", width: "2.75rem" }}>{m ? <Bi id={m.unit.id} en={m.unit.en} /> : ""}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
            {cfg.length === 0 && <div className="muted" style={{ fontSize: "var(--text-xs)" }}>—</div>}
          </div>
        </div>
      )}

      {/* Fase 2: Gerakan Kamera per Adegan (level system, berlaku semua konten) */}
      {!loading && beats.length > 0 && (
        <div className="card" style={{ maxWidth: 720, marginTop: "1.5rem" }}>
          <div className="card-head">
            <h3 className="card-title"><SlidersHorizontal size={15} /> <Bi id="Gerakan Kamera per Adegan" en="Camera Motion per Scene" /></h3>
            <span className="card-sub" style={{ color: "var(--success)", fontWeight: 500 }}><Bi id="✓ Tersimpan otomatis" en="✓ Auto-saved" /></span>
          </div>
          <div className="card-body">
            <p className="muted" style={{ fontSize: "var(--text-xs)", margin: "0 0 1rem", maxWidth: "65ch" }}>
              <Bi id="Arah gerak kamera per adegan, berlaku ke SEMUA konten. Fix = arah tetap pilihan Anda; Cerdas = mesin variasikan otomatis (tak pernah dua adegan searah berturut). Intensitas (halus–cepat) diatur per-niche. Durasi video tidak berubah."
                  en="Camera motion direction per scene, applies to ALL content. Fix = your fixed direction; Smart = engine auto-varies (never two adjacent scenes same way). Intensity (subtle–fast) is set per-niche. Video duration is unchanged." />
            </p>
            {beats.map((b) => {
              const locked = b.beat_key === "hook";   // hook = pembuka utama, terkunci fix zoom (owner)
              return (
              <div key={b.beat_key} style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: ".75rem", alignItems: "center", padding: ".6rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}>
                  <Bi id={b.label_id} en={b.label_en} />
                  {locked && <span className="muted" style={{ fontSize: "0.625rem", marginLeft: ".4rem" }}>🔒 <Bi id="wajib zoom (pembuka)" en="always zoom (opener)" /></span>}
                </div>
                <select className="input" style={{ height: "2rem", width: "8rem", opacity: locked ? 0.5 : 1 }} value={b.motion_mode} disabled={locked}
                  onChange={(e) => patchBeat(b.beat_key, { motion_mode: e.target.value })}>
                  <option value="fix">Fix</option>
                  <option value="cerdas">{lang === "en" ? "Smart" : "Cerdas"}</option>
                </select>
                <select className="input" style={{ height: "2rem", width: "12rem", opacity: (b.motion_mode === "fix" && !locked) ? 1 : 0.4 }}
                  value={b.motion_dir} disabled={b.motion_mode !== "fix" || locked}
                  onChange={(e) => patchBeat(b.beat_key, { motion_dir: e.target.value })}>
                  {MOTION_DIRS.map(([v, idL, enL]) => <option key={v} value={v}>{lang === "en" ? enL : idL}</option>)}
                </select>
              </div>
            );})}
          </div>
        </div>
      )}

      {toast && (
        <div style={{ position: "fixed", bottom: "1.5rem", right: "1.5rem", background: "var(--surface-3)", border: "1px solid var(--border-strong)", borderRadius: "var(--r-md)", padding: ".625rem 1rem", fontSize: "var(--text-sm)", boxShadow: "var(--shadow-md)", zIndex: 50 }}>{toast}</div>
      )}
    </>
  );
}
