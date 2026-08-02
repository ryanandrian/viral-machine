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

/** Pesan apa pun (kode gerbang ATAU teks galat biasa) — satu titik pakai untuk komponen. */
export function PesanGalat({ text, style }: { text?: string | null; style?: React.CSSProperties }) {
  if (!text) return null;
  return parseGate(text) ? <GateNotice code={text} style={style} /> : <span style={style}>{text}</span>;
}
