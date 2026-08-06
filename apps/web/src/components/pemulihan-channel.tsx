"use client";

import Link from "next/link";
import { AlertTriangle, Clock, KeyRound, RefreshCw, Wallet, Wrench } from "lucide-react";

// [B25] PANEL PEMULIHAN CHANNEL — apa yang terjadi, apakah pulih sendiri, apa langkah Anda.
//
// SSOT: AI_ERROR_MANAGEMENT_ARCHITECTURE.md §9 (kontrak tampilan per-kelas).
//
// ATURAN YANG MENGIKAT KOMPONEN INI: pemetaan dilakukan per **KELAS ERROR**, TIDAK PERNAH per nama
// penyedia. Katalog penyedia & model akan terus bertambah; kelas berjumlah tujuh dan stabil. Penyedia
// baru cukup dipetakan ke kelas di registry backend → otomatis mendapat penjelasan, anjuran, dan
// tautan yang benar TANPA menyentuh berkas ini. Menulis nama penyedia di sini = pelanggaran, dan
// jaminan bahwa layar akan basi pada penyedia berikutnya.
//
// Sebelum ini, layar hanya menampilkan kalimat generik "3x produksi beruntun gagal/bermasalah" plus
// anjuran menebak "perbaiki penyebabnya (mis. saldo/kredensial AI)". Tenant tak pernah tahu pertanyaan
// yang paling menentukan: APAKAH INI PULIH SENDIRI? Satu channel tenant berbayar karena itu mati ±44
// jam menunggu sesuatu yang sebenarnya sudah pulih dengan sendirinya keesokan harinya.
//
// PEMULIHAN = KEPUTUSAN TENANT (arahan owner): sistem tidak pernah melepas rem sendiri karena sebab
// teknis dianggap sudah lewat. Tombolnya ada, penjelasannya lengkap, jarinya milik mereka.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type Ikon = typeof Clock;
type Aksi = { href: string; label_id: string; label_en: string };
type Resep = {
  ikon: Ikon;
  pulihSendiri: boolean | null;   // null = tak diketahui
  judul_id: string; judul_en: string;
  jelas_id: string; jelas_en: string;
  aksi?: (channelId: string) => Aksi;
};

/** Peta KELAS → penjelasan. Tujuh kelas, sama persis dengan `ErrorClass` di backend (§1 SSOT). */
const RESEP: Record<string, Resep> = {
  rate_limit: {
    ikon: Clock, pulihSendiri: true,
    judul_id: "Jatah penggunaan penyedia AI tercapai",
    judul_en: "AI provider usage limit reached",
    jelas_id: "Penyedia AI Anda sedang membatasi permintaan. Batas seperti ini pulih sendiri — ada yang dalam hitungan menit, ada yang saat pergantian hari. Anda tidak perlu mengubah apa pun.",
    jelas_en: "Your AI provider is throttling requests. Limits like this recover on their own — some within minutes, some when the day rolls over. You don't need to change anything.",
    aksi: (id) => ({ href: `/channels/${id}?tab=settings`, label_id: "Atau pakai penyedia/model lain", label_en: "Or switch provider/model" }),
  },
  transient: {
    ikon: RefreshCw, pulihSendiri: true,
    judul_id: "Gangguan sesaat saat produksi",
    judul_en: "Temporary glitch during production",
    jelas_id: "Sambungan atau layanan penyedia sempat terganggu. Gangguan seperti ini biasanya pulih sendiri dalam hitungan menit.",
    jelas_en: "A connection or provider service hiccuped. Glitches like this usually clear on their own within minutes.",
  },
  quota_exhausted: {
    ikon: Wallet, pulihSendiri: false,
    judul_id: "Kredit penyedia AI Anda habis",
    judul_en: "Your AI provider credit has run out",
    jelas_id: "Ini tidak akan pulih sendiri. Isi ulang saldo di akun penyedia AI Anda, lalu pulihkan produksi.",
    jelas_en: "This won't fix itself. Top up your AI provider account, then resume production.",
    aksi: () => ({ href: "/integrations", label_id: "Buka Integrasi", label_en: "Open Integrations" }),
  },
  account_billing: {
    ikon: Wallet, pulihSendiri: false,
    judul_id: "Pembayaran ke penyedia AI bermasalah",
    judul_en: "Payment to your AI provider failed",
    jelas_id: "Penyedia AI Anda menolak permintaan karena masalah pembayaran di akun mereka. Perbaiki di sisi penyedia, lalu pulihkan produksi.",
    jelas_en: "Your AI provider rejected the request due to a billing problem on their side. Fix it there, then resume production.",
    aksi: () => ({ href: "/integrations", label_id: "Buka Integrasi", label_en: "Open Integrations" }),
  },
  auth_invalid: {
    ikon: KeyRound, pulihSendiri: false,
    judul_id: "Kunci atau koneksi ditolak",
    judul_en: "Key or connection was rejected",
    jelas_id: "Kunci AI atau koneksi YouTube Anda tidak lagi diterima — biasanya karena dicabut atau kedaluwarsa. Perbarui dulu, baru pulihkan produksi.",
    jelas_en: "Your AI key or YouTube connection is no longer accepted — usually revoked or expired. Update it first, then resume production.",
    aksi: () => ({ href: "/integrations", label_id: "Perbarui kredensial", label_en: "Update credentials" }),
  },
  model_unavailable: {
    ikon: Wrench, pulihSendiri: false,
    judul_id: "Model AI yang dipilih sudah tidak tersedia",
    judul_en: "The selected AI model is no longer available",
    jelas_id: "Penyedia menghentikan model ini. Pilih model lain di pengaturan channel, lalu pulihkan produksi.",
    jelas_en: "The provider retired this model. Pick another model in the channel settings, then resume production.",
    aksi: (id) => ({ href: `/channels/${id}?tab=settings`, label_id: "Ganti model", label_en: "Change model" }),
  },
};

const RESEP_BAWAAN: Resep = {
  ikon: AlertTriangle, pulihSendiri: null,
  judul_id: "Produksi dihentikan setelah beberapa kegagalan",
  judul_en: "Production stopped after repeated failures",
  jelas_id: "Kami belum bisa memastikan penyebab pastinya. Lihat keterangan teknis di bawah — bila Anda ragu, hubungi dukungan dan sertakan keterangan itu.",
  jelas_en: "We can't pin down the exact cause. See the technical note below — if you're unsure, contact support and include it.",
  aksi: () => ({ href: "/support", label_id: "Hubungi dukungan", label_en: "Contact support" }),
};

export function resepUntuk(kelas: string | null | undefined): Resep {
  return (kelas && RESEP[kelas]) || RESEP_BAWAAN;
}

export default function PemulihanChannel({
  channelId, kelas, alasan, sejak, bisaUji, bolehPulihkan, sedangProses, onPulihkan,
}: {
  channelId: string;
  kelas: string | null | undefined;
  alasan: string | null | undefined;
  sejak: string | null | undefined;
  bisaUji: boolean;                // gerbang uji mengizinkan → jalur pemulihan yang BENAR adalah uji
  bolehPulihkan: boolean;          // langganan mengizinkan produksi
  sedangProses: boolean;
  onPulihkan: () => void;
}) {
  const r = resepUntuk(kelas);
  const Ikon = r.ikon;
  const aksi = r.aksi?.(channelId);
  // Uji PANTAS dijadikan jalur pemulihan hanya bila sebabnya butuh tindakan tenant — di situ uji
  // MEMBUKTIKAN bahwa perbaikannya berhasil. Untuk sebab yang pulih sendiri (jatah/laju/gangguan
  // sesaat) uji tak membuktikan apa pun DAN memanggil penyedia yang sedang menolak ⇒ gagal sambil
  // membakar sisa jatah hari itu. Sebab tak diketahui (kelas kosong — termasuk rem yang menyala
  // SEBELUM kelas mulai dicatat) juga tak boleh dipaksa lewat uji: kita tak tahu apa yang dibuktikan.
  const ujiJalurYangBenar = bisaUji && r.pulihSendiri === false;
  const jam = sejak
    ? Math.max(0, Math.floor((Date.now() - new Date(sejak).getTime()) / 3_600_000))
    : null;

  return (
    <div className="card card-pad" style={{ marginBottom: "1rem", borderLeft: "3px solid var(--danger, #ef4444)" }}>
      <div style={{ display: "flex", gap: "0.625rem", alignItems: "flex-start" }}>
        <Ikon size={18} style={{ color: "var(--danger, #ef4444)", flexShrink: 0, marginTop: 2 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <strong style={{ fontSize: "var(--text-sm)" }}><Bi id={r.judul_id} en={r.judul_en} /></strong>
          {jam !== null && (
            <span className="muted" style={{ fontSize: "var(--text-xs)", marginLeft: ".4rem" }}>
              {jam < 1 ? <Bi id="baru saja" en="just now" />
                : <Bi id={`berhenti ${jam} jam` } en={`stopped ${jam}h ago`} />}
            </span>
          )}

          <div style={{ fontSize: "var(--text-sm)", color: "var(--text-secondary)", marginTop: ".35rem" }}>
            <Bi id={r.jelas_id} en={r.jelas_en} />
          </div>

          {/* Pertanyaan yang paling menentukan bagi tenant — dijawab lebih dulu, bukan disembunyikan. */}
          {r.pulihSendiri !== null && (
            <div style={{ fontSize: "var(--text-xs)", marginTop: ".45rem", fontWeight: 600,
                          color: r.pulihSendiri ? "var(--success, #22c55e)" : "var(--warning, #f59e0b)" }}>
              {r.pulihSendiri
                ? <Bi id="⏳ Penyebabnya pulih sendiri — Anda tidak perlu mengubah pengaturan apa pun."
                      en="⏳ The cause clears on its own — you don't need to change any settings." />
                : <Bi id="⚠️ Penyebabnya tidak pulih sendiri — ada satu hal yang perlu Anda kerjakan dulu."
                      en="⚠️ The cause won't clear on its own — there's one thing you need to do first." />}
            </div>
          )}

          {/* ══ JALUR PEMULIHAN — ditentukan oleh SEBABNYA, bukan oleh "boleh menguji atau tidak" ══
              Pelajaran mahal 2026-08-03 (TETAP BERLAKU, jangan dicabut): tombol "Pulihkan produksi"
              pernah ditawarkan kepada SEMUA orang. Ia hanya melepas rem — tak memproduksi apa pun,
              tak membuktikan apa pun. Tenant menekannya tanpa memperbaiki apa pun, mesin mengerem
              lagi beberapa detik kemudian, dan tenant menyimpulkan aplikasinya rusak. Karena itu
              untuk sebab yang BUTUH TINDAKAN TENANT, uji tetap jalur yang ditawarkan.

              JEBAKAN yang ditemukan owner 2026-08-06: pelajaran itu terlanjur diterapkan ke SEMUA
              sebab ("selama uji boleh, arahkan ke uji"). Untuk sebab yang PULIH SENDIRI arahan itu
              mustahil berhasil: rem menyala karena jatah HARIAN penyedia habis, sedangkan uji =
              satu produksi NYATA yang memanggil penyedia yang jatahnya sedang habis ⇒ dijamin gagal,
              sambil MEMBAKAR sisa jatah hari itu. Terukur: channel tenant BERBAYAR berhenti 1-Agu
              dan masih berhenti 6-Agu — karena langganannya aktif ia "masih boleh menguji", jadi
              tombol pemulih tak pernah muncul untuknya, padahal melepas rem TIDAK memanggil AI
              sama sekali (lihat `api/channels/[id]/resume/route.ts`).

              Pemisahnya: butuh-tindakan → uji (membuktikan) · pulih-sendiri & tak-diketahui →
              pemulihan langsung + peringatan jujur (supaya insiden 3-Agu tak lahir kembali). */}
          <div style={{ display: "flex", gap: ".5rem", marginTop: ".7rem", flexWrap: "wrap", alignItems: "center" }}>
            {!bolehPulihkan ? (
              <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
                <Bi id="Aktifkan langganan dulu untuk memulihkan produksi."
                    en="Reactivate your subscription first to resume production." />
              </span>
            ) : ujiJalurYangBenar ? (
              <span style={{ fontSize: "var(--text-xs)" }}>
                <Bi id="👉 Tekan “Jalankan uji & pulihkan” di panel bawah. Satu video uji membuktikan perbaikan Anda berhasil, lalu produksi berjalan lagi dengan sendirinya."
                    en="👉 Press “Run & recover” in the panel below. One test video proves your fix worked, and production resumes on its own." />
              </span>
            ) : (
              <>
                <button className="btn btn-default btn-sm" disabled={sedangProses} onClick={onPulihkan}>
                  <RefreshCw size={14} />{" "}
                  {sedangProses
                    ? <Bi id="Memulihkan…" en="Resuming…" />
                    : <Bi id="Pulihkan produksi" en="Resume production" />}
                </button>
                <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
                  <Bi id="Tekan setelah penyebabnya lewat. Bila belum, produksi akan gagal lagi dan mesin berhenti lagi."
                      en="Press once the cause has passed. If it hasn't, production will fail again and the engine will stop again." />
                </span>
              </>
            )}
            {aksi && (
              <Link href={aksi.href} className="btn btn-secondary btn-sm">
                <Bi id={aksi.label_id} en={aksi.label_en} />
              </Link>
            )}
          </div>

          {/* Keterangan teknis TIDAK dibuang — hanya diturunkan ke tempat yang tidak menghalangi. */}
          {alasan && (
            <details style={{ marginTop: ".6rem" }}>
              <summary className="muted" style={{ fontSize: "var(--text-xs)", cursor: "pointer" }}>
                <Bi id="Keterangan teknis" en="Technical detail" />
              </summary>
              <div className="muted mono" style={{ fontSize: "0.625rem", marginTop: ".3rem", lineHeight: 1.5 }}>
                {alasan}
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
