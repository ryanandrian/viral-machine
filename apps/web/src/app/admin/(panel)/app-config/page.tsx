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
const G_LIFECYCLE = "Pertumbuhan & Siklus-Hidup";
const G_TREND = "Bobot Sumber Tren";
const G_ENGINE = "Performa Mesin Tren";
const G_LEARNING = "Kurva Belajar (Self-Learning)";
const G_OTHER = "Lainnya";
const CFG_GROUPS: [string, string][] = [
  [G_BILLING, "Subscription, Trial & Billing"],
  [G_LIFECYCLE, "Growth & Lifecycle"],
  [G_TREND, "Trend Source Weights"],
  [G_ENGINE, "Trend Engine Performance"],
  [G_LEARNING, "Learning Curve (Self-Learning)"],
  [G_OTHER, "Others"],   // ← catch-all: SETIAP key app_config tanpa metadata TETAP tampil (anti-hilang selamanya)
];
// DWIBAHASA WAJIB ([[feedback_bilingual_mandatory]], owner 2026-07-05): label/desc/hint/unit = {id,en};
// desc FE ini = sumber tampilan (DB description = fallback teknis). Key baru TANPA meta = CACAT — lengkapi di sini.
type BiTxt = { id: string; en: string };
const U_HARI: BiTxt = { id: "hari", en: "days" }; const U_JAM: BiTxt = { id: "jam", en: "hours" };
const U_PCT: BiTxt = { id: "%", en: "%" }; const U_DETIK: BiTxt = { id: "detik", en: "sec" };
const U_MS: BiTxt = { id: "ms", en: "ms" }; const U_NONE: BiTxt = { id: "", en: "" };
const CFG_META: Record<string, { label: BiTxt; group: string; unit: BiTxt; desc?: BiTxt; hint?: BiTxt }> = {
  trial_duration_days:          { label: { id: "Masa Trial Gratis", en: "Free Trial Length" }, group: G_BILLING, unit: U_HARI, desc: { id: "Berapa hari calon pelanggan bisa mencoba gratis sebelum harus berlangganan.", en: "How many days a prospect can try for free before subscribing." } },
  trial_reminder_days_before:   { label: { id: "Pengingat Sebelum Trial Habis", en: "Reminder Before Trial Ends" }, group: G_BILLING, unit: U_HARI, desc: { id: "Kirim email pengingat upgrade H-x sebelum trial berakhir (0 = matikan).", en: "Send an upgrade reminder x days before the trial ends (0 = off)." } },
  renewal_reminder_days_before: { label: { id: "Pengingat Sebelum Langganan Habis", en: "Renewal Reminder" }, group: G_BILLING, unit: U_HARI, desc: { id: "Kirim email pengingat perpanjangan H-x sebelum langganan berakhir (0 = matikan).", en: "Send a renewal reminder x days before the subscription ends (0 = off)." } },
  subscription_period_days:     { label: { id: "Durasi Periode Langganan", en: "Subscription Period" }, group: G_BILLING, unit: U_HARI, desc: { id: "Durasi satu periode langganan berbayar. Default 30 = bulanan.", en: "Length of one paid subscription period. Default 30 = monthly." } },
  annual_discount_pct:          { label: { id: "Diskon Paket Tahunan", en: "Annual Plan Discount" }, group: G_BILLING, unit: U_PCT, desc: { id: "Harga tahunan = bulanan × 12 × (100−nilai)%. 0 = pilihan tahunan disembunyikan dari pelanggan.", en: "Annual price = monthly × 12 × (100−value)%. 0 = the annual option is hidden from customers." } },
  billing_grace_days:           { label: { id: "Masa Tenggang Sebelum Dihentikan", en: "Grace Period Before Stop" }, group: G_BILLING, unit: U_HARI, desc: { id: "Setelah langganan berakhir, mesin MASIH jalan selama masa tenggang ini sambil menunggu pembayaran.", en: "After expiry, production keeps running during this grace period while awaiting payment." } },
  checkout_expiry_hours:        { label: { id: "Masa Berlaku Link Bayar", en: "Payment Link Validity" }, group: G_BILLING, unit: U_JAM, desc: { id: "Berapa jam link pembayaran Midtrans berlaku sebelum kedaluwarsa.", en: "How many hours a Midtrans payment link stays valid." } },
  ppn_percent:                  { label: { id: "PPN Invoice", en: "Invoice VAT" }, group: G_BILLING, unit: U_PCT, desc: { id: "PPN pada invoice. 0 = harga final tanpa PPN; isi 11 bila perusahaan PKP.", en: "VAT on invoices. 0 = final price, no VAT; set 11 if VAT-registered." } },
  usd_idr_rate:                 { label: { id: "Kurs USD → IDR", en: "USD → IDR Rate" }, group: G_BILLING, unit: U_NONE, desc: { id: "Kurs untuk TAMPILAN biaya AI BYOK dalam Rupiah (biaya asli disimpan USD). Disinkron OTOMATIS harian dari kurs pasar; mengedit manual = otomatis terkunci.", en: "Rate used to DISPLAY BYOK AI costs in Rupiah (costs are stored in USD). Auto-synced daily from market data; editing manually locks it." } },
  usd_idr_rate_locked:          { label: { id: "Kunci Kurs Manual", en: "Manual Rate Lock" }, group: G_BILLING, unit: U_NONE, desc: { id: "1 = mesin TIDAK menimpa kurs (Anda kelola sendiri); 0 = kurs disinkron otomatis harian.", en: "1 = the engine never overwrites the rate (you manage it); 0 = auto-synced daily." }, hint: { id: "otomatis jadi 1 saat kurs diedit", en: "auto-set to 1 when rate is edited" } },
  nurture_enabled:                 { label: { id: "Nurture Trial-Lapse Aktif", en: "Trial-Lapse Nurture On" }, group: G_LIFECYCLE, unit: U_NONE, desc: { id: "Master ON/OFF mesin tindak-lanjut (nurture) trial yang lewat. 1 = nyala, 0 = mati.", en: "Master ON/OFF for the lapsed-trial nurture engine. 1 = on, 0 = off." } },
  nurture_trial_extend_days:       { label: { id: "Perpanjang Trial 1-Klik", en: "1-Click Trial Extension" }, group: G_LIFECYCLE, unit: U_HARI, desc: { id: "Perpanjangan trial 1-klik dari email nurture. 0 = matikan tuas ini.", en: "1-click trial extension offered in nurture emails. 0 = disable." } },
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
                          {a.value_text != null ? (
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
