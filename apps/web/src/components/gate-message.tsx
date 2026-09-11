"use client";

import Link from "next/link";

// [B24 §10c] Penerjemah KODE gerbang uji → kalimat dwibahasa.
//
// API dan worker sengaja mengirim KODE (`GATE:subscription`, `GATE:trial_quota:3:3`), bukan kalimat
// jadi — aturan dwibahasa kita (§3.5) mewajibkan layar yang menerjemahkan, supaya satu pesan tidak
// terkunci di satu bahasa. Karena worker menulis kode yang sama ke `direct_jobs.error`, layar cukup
// punya SATU penerjemah untuk kedua sumber (jawaban API langsung & hasil job yang gagal).
//
// Teks apa pun yang BUKAN kode gerbang dikembalikan apa adanya — pesan galat lama tetap tampil
// seperti sebelumnya (nol regresi).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

export type GateInfo = { reason: string; used?: number; max?: number };

/** "GATE:trial_quota:5:3" → { reason:"trial_quota", used:5, max:3 }. Bukan kode gerbang → null. */
export function parseGate(text?: string | null): GateInfo | null {
  if (!text || !text.startsWith("GATE:")) return null;
  const [, reason, used, max] = text.split(":");
  if (!reason) return null;
  return {
    reason,
    used: used !== undefined ? Number(used) : undefined,
    max: max !== undefined ? Number(max) : undefined,
  };
}

/** Kalimat dwibahasa untuk satu alasan penolakan. */
export function GateText({ info }: { info: GateInfo }) {
  switch (info.reason) {
    case "subscription":
      return <Bi
        id="Langganan Anda sedang tidak aktif, jadi uji produksi dikunci. Produksi terjadwal tidak terpengaruh."
        en="Your subscription is not active, so production tests are locked. Scheduled production is unaffected." />;
    case "trial_quota":
      return <Bi
        id={`Jatah uji masa coba sudah habis (batas ${info.max ?? 0} video uji). Berlangganan untuk menguji sepuasnya.`}
        en={`Your trial test quota is used up (limit ${info.max ?? 0} test videos). Subscribe to keep testing.`} />;
    case "gate_unavailable":
      return <Bi
        id="Sistem sedang tidak bisa memeriksa status langganan Anda. Coba lagi beberapa saat lagi — tidak ada biaya yang terpakai."
        en="We can't verify your subscription status right now. Please try again shortly — nothing was charged." />;
    case "tenant_unknown":
      return <Bi id="Akun tidak dikenali. Muat ulang halaman atau masuk kembali."
                 en="Account not recognised. Reload the page or sign in again." />;
    case "forbidden":
      return <Bi id="Permintaan ini tidak sah." en="This request is not permitted." />;
    default:
      return <Bi id="Uji produksi sedang tidak tersedia untuk akun Anda."
                 en="Production tests are currently unavailable for your account." />;
  }
}

/**
 * Tampilan penolakan lengkap: kalimat + ajakan berlangganan.
 * Terkunci = AJAKAN, bukan tombol hilang dan bukan gagal senyap — tenant harus tahu kenapa dan
 * apa langkah berikutnya. Alasan yang bukan soal langganan (gangguan sistem) tidak diberi ajakan
 * bayar, karena bukan uang yang menjadi masalahnya.
 */
export function GateNotice({ code, style }: { code: string; style?: React.CSSProperties }) {
  const info = parseGate(code);
  if (!info) return <span>{code}</span>;
  const perluBayar = info.reason === "subscription" || info.reason === "trial_quota";
  return (
    <span style={style}>
      <GateText info={info} />
      {perluBayar && (
        <>
          {" "}
          <Link href="/billing" className="link" style={{ whiteSpace: "nowrap" }}>
            <Bi id="Lihat paket →" en="View plans →" />
          </Link>
        </>
      )}
    </span>
  );
}

// ── PESAN SESAAT (toast/notice sesudah tenant menekan tombol) ─────────────────────────────────
//
// [11-Sep] Diukur atas pertanyaan owner: label & tulisan TETAP di layar sudah bersih (dijaga
// `test_dwibahasa_fe_tak_pincang`), tapi **13 pesan sesaat** hanya berbahasa Indonesia. Penjaga lama
// tak menjangkaunya: ia menghitung KESEIMBANGAN `data-id`/`data-en`, sedangkan teks yang sama sekali
// tak memakai mekanisme dwibahasa tak terlihat olehnya.
//
// Rancangan pertama saya hendak menyalin pola "garis miring" (`"Tersimpan / saved"`, 4 tempat
// warisan) ke 13 pesan lain. Owner menegur — dan benar: itu BUKAN jalur resmi (tenant melihat KEDUA
// bahasa berjejer sekaligus), dan menyalinnya = memperbanyak jalur kedua.
//
// Jalur resminya SUDAH ADA di berkas ini: pesan disimpan sebagai **KODE** teks biasa, diterjemahkan
// SAAT DITAMPILKAN (preseden `GATE:…`, B24). Karena kodenya tetap `string`, tipe state di layar nol
// berubah ⇒ nol risiko pada logika yang sudah ada.
//
// Kode berparameter memakai `MSG:<nama>:<nilai>` — nilainya diteruskan apa adanya (mis. nama niche).
const MSG_TEKS: Record<string, (v: string) => React.ReactNode> = {
  duration_saved:      () => <Bi id="Durasi tersimpan" en="Duration saved" />,
  niche_saved:         () => <Bi id="Niche tersimpan" en="Niche saved" />,
  schedule_saved:      () => <Bi id="Jadwal disimpan" en="Schedule saved" />,
  dna_saved:           () => <Bi id="DNA tersimpan" en="DNA saved" />,
  activate_incomplete: () => <Bi id="Belum bisa diaktifkan — lengkapi konfigurasi dulu (lihat checklist)."
                                  en="Can't activate yet — complete the configuration first (see the checklist)." />,
  server_unreachable:  () => <Bi id="Server tak terjangkau." en="Server unreachable." />,
  name_required:       () => <Bi id="Nama channel wajib." en="Channel name is required." />,
  niche_min_1:         () => <Bi id="Pilih minimal 1 niche." en="Pick at least 1 niche." />,
  niche_min_2:         () => <Bi id="Mode rotasi butuh minimal 2 niche." en="Rotation mode needs at least 2 niches." />,
  session_invalid:     () => <Bi id="Sesi tak valid." en="Your session is invalid." />,
  niche_created:       (v) => <Bi id={`Niche dibuat: ${v}`} en={`Niche created: ${v}`} />,
  slots_full:          (v) => <Bi id={`Channel ini sudah ${v}/${v} slot (batas paket)`}
                                  en={`This channel is already at ${v}/${v} slots (plan limit)`} />,
  save_failed:         (v) => <Bi id={`Gagal: ${v}`} en={`Failed: ${v}`} />,
  // Layar DAFTAR channel (ditemukan saat audit pra-deploy 11-Sep — pemindai pertama saya
  // melewatkannya sebab teksnya diawali tanda kutip di dalam template).
  activate_incomplete_named: (v) => <Bi id={`"${v}" belum bisa diaktifkan — lengkapi dulu (buka Kelola).`}
                                        en={`"${v}" can't be activated yet — complete its setup first (open Manage).`} />,
  activate_incomplete_creds: () => <Bi id="Belum bisa diaktifkan — lengkapi konfigurasi & kredensial dulu (buka Kelola)."
                                       en="Can't activate yet — complete the configuration and credentials first (open Manage)." />,
  // Empat pesan ber-PETUNJUK yang dulu memakai pola "garis miring" (dua bahasa berjejer dalam satu
  // kalimat, sehingga tenant melihat keduanya sekaligus). Dipindah ke jalur resmi ini — pola itu
  // kini NOL di seluruh layar tenant.
  saved_need_video_preset: () => <Bi id="Tersimpan — LANGKAH BERIKUT: ubah Durasi channel ke preset text-to-video (8s), lalu Simpan"
                                     en="Saved — NEXT: set the channel Duration to the text-to-video preset (8s), then Save" />,
  saved_leave_video_preset: () => <Bi id="Tersimpan — LANGKAH BERIKUT: ubah Durasi channel keluar dari preset text-to-video"
                                      en="Saved — NEXT: change the channel Duration away from the text-to-video preset" />,
  duration_need_video_model: () => <Bi id="Durasi tersimpan — LANGKAH BERIKUT: pilih MODEL VIDEO di kartu Model AI (Visual), lalu Simpan (produksi menolak jalan sampai keduanya serasi)"
                                       en="Duration saved — NEXT: pick a VIDEO model in the AI Models (Visual) card, then Save (production won't run until both match)" />,
  duration_need_image_model: () => <Bi id="Durasi tersimpan — LANGKAH BERIKUT: ganti model visual ke model GAMBAR di kartu Model AI (produksi menolak jalan sampai keduanya serasi)"
                                       en="Duration saved — NEXT: switch the visual model to an IMAGE model in the AI Models card (production won't run until both match)" />,
};

/** Kode pesan sesaat → simpan di state apa adanya, terjemahkan saat tampil. */
export function msg(nama: keyof typeof MSG_TEKS, nilai?: string | number): string {
  return `MSG:${nama}` + (nilai === undefined ? "" : `:${nilai}`);
}

/** Pesan ini mengabarkan KEBERHASILAN? Dipakai layar untuk memilih warna — menggantikan endusan
 *  kata di dalam teks (`.includes("tersimpan")`) yang rapuh dan langsung salah begitu teks jadi kode. */
export function pesanSukses(text?: string | null): boolean {
  return !!text && /^MSG:(duration_saved|niche_saved|schedule_saved|dna_saved|niche_created|saved_need_video_preset|saved_leave_video_preset|duration_need_video_model|duration_need_image_model)/.test(text);
}

function parseMsg(text?: string | null): React.ReactNode | null {
  if (!text || !text.startsWith("MSG:")) return null;
  const sisa = text.slice(4);
  const potong = sisa.indexOf(":");
  const nama = potong === -1 ? sisa : sisa.slice(0, potong);
  const nilai = potong === -1 ? "" : sisa.slice(potong + 1);
  const f = MSG_TEKS[nama];
  return f ? f(nilai) : null;
}

/** Pesan apa pun (kode gerbang · kode pesan sesaat · teks galat biasa) — satu titik pakai. */
export function PesanGalat({ text, style }: { text?: string | null; style?: React.CSSProperties }) {
  if (!text) return null;
  if (parseGate(text)) return <GateNotice code={text} style={style} />;
  const m = parseMsg(text);
  // Teks tak dikenal (mis. galat mentah dari penyedia) lewat apa adanya — perilaku lama, fail-soft.
  return <span style={style}>{m ?? text}</span>;
}
