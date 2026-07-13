"use client";

import { useState, useEffect } from "react";
import { fetchPricing, idrK } from "@/lib/pricing";
import { fetchPlans, paidPlans, type Plan } from "@/lib/plans";
import { createClient } from "@/lib/supabase/client";
import {
  Users, Check, X, ChevronDown, DollarSign,
  Wand2, type LucideIcon,
} from "lucide-react";
import "./pricing.css";

// A2 Pricing — SELURUHNYA config-driven (Tahap 4 finalisasi_tier_plan, 2026-07-13):
// harga+kuota = pricing_config/plan_limits · narasi kartu (tagline/fitur/populer) =
// plan_limits.marketing_* (admin-editable /admin/pricing) · matriks perbandingan = plan_matrix_rows
// (admin-editable; token auto:* dirender dari FAKTA plan_limits) · diskon tahunan = knob
// annual_discount_pct (0 = toggle disembunyikan). Kelas/visual = Claude Design, tak diubah.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

// Matriks perbandingan dari DB — sel: "true"/"false" → ikon; "auto:<fakta>" → nilai live plan_limits; lain = teks.
type MatrixRow = { id: number; sort_order: number; is_group: boolean; label_id: string; label_en: string;
                   v_starter: string | null; v_pro: string | null; v_business: string | null; v_enterprise: string | null };
function resolveCell(v: string | null, plan: Plan | undefined): boolean | string {
  if (v == null || v === "") return "—";
  if (v === "true") return true;
  if (v === "false") return false;
  if (v === "auto:max_channels") return plan ? String(plan.max_channels) : "—";
  if (v === "auto:max_videos_per_day") return plan ? String(plan.max_videos_per_day) : "—";
  if (v === "auto:niche_studio") return Boolean(plan?.niche_studio);
  return v;
}
function Fc({ v, pop }: { v: boolean | string; pop?: boolean }) {
  if (v === true) return <span className="yes"><Check size={18} /></span>;
  if (v === false) return <span className="no"><X size={16} /></span>;
  return <span style={pop ? { color: "var(--brand)", fontWeight: 600 } : undefined}>{v}</span>;
}

// [icon, label, pricing_config key ("" = pakai fallback literal), suffix, fallback, desc]
const ADDONS: [LucideIcon, string, string, string, string, string][] = [
  [Wand2, "Niche Pack", "custom_niche_public_90d", "", "Rp 299K", "Niche kustom dibuat sesuai brief Anda, 3–5 hari delivery."],
];

// FAQ JUJUR-OLEH-SISTEM (Tahap 4): prorate & tahunan kini benar-benar bekerja di mesin; refund =
// proses manual yang dijelaskan apa adanya (ratifikasi owner §3b-5).
const makeFaq = (d: number, ann: number): [string, string][] => [
  ["Bisa upgrade / downgrade kapan saja?", "Bisa. Saat ganti paket, sisa nilai paket lamamu otomatis dikonversi menjadi masa aktif di paket baru (prorate nilai-adil) — tidak ada hari yang hangus. Perpanjang paket yang sama pun menyambung sisa harimu utuh."],
  ...(ann > 0 ? [["Apakah ada paket tahunan?", `Ada. Bayar tahunan sekali dan hemat ${ann}% dibanding bulanan — pilih “Tahunan” saat checkout di halaman Billing.`]] as [string, string][] : []),
  ["Bagaimana refund policy-nya?", `Trial ${d} hari gratis penuh tanpa kartu kredit. Setelah pembayaran pertama, hubungi kami dalam 7 hari jika belum cocok — refund diproses manual oleh tim melalui Midtrans.`],
  ["Bagaimana biaya AI dihitung?", "Biaya AI mengikuti pemakaian aktual API milikmu (BYOK) dan dibayar langsung ke provider yang kamu pilih — bukan ke MesinViral. Besarnya sangat bervariasi tergantung provider & model: bisa mulai dari Rp 0 bila memakai tier/model gratis."],
  ["Apakah harga sudah termasuk biaya AI?", "Harga langganan terpisah dari biaya AI (BYOK) — dan biaya AI itu kamu yang kendalikan penuh, mulai dari Rp 0 dengan provider/model gratis."],
  ["Pembayaran pakai apa?", "Kami pakai Midtrans — mendukung transfer bank / Virtual Account, e-wallet (GoPay, ShopeePay), kartu kredit, dan metode lain yang aktif di halaman pembayaran."],
];

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);
  const [faqOpen, setFaqOpen] = useState(0);
  const [pricing, setPricing] = useState<Record<string, number>>({});
  const [plans, setPlans] = useState<Plan[]>([]);
  const [trialDays, setTrialDays] = useState(7);
  const [annualPct, setAnnualPct] = useState(0);           // knob admin; 0 = toggle tahunan disembunyikan
  const [matrix, setMatrix] = useState<MatrixRow[]>([]);   // matriks perbandingan (admin-editable)
  useEffect(() => {
    fetchPricing().then(setPricing);
    fetchPlans().then(({ plans, trialDays, annualDiscountPct }) => { setPlans(plans); setTrialDays(trialDays); setAnnualPct(annualDiscountPct); });
    createClient().from("plan_matrix_rows").select("*").order("sort_order")
      .then(({ data }) => setMatrix((data as MatrixRow[]) ?? []));
  }, []);
  const pm: Record<string, Plan | undefined> = Object.fromEntries(plans.map((p) => [p.plan_type, p]));

  return (
    <>
      <div className="mk-container">
        <div className="ph-head">
          <span className="mk-kicker"><Bi id="Harga transparan" en="Transparent pricing" /></span>
          <h1><Bi id="Pilih paket untuk channelmu" en="Pick a plan for your channel" /></h1>
          <p className="mk-lead mk-center"><Bi id="Langganan + biaya AI (BYOK) dibayar langsung ke provider. Tanpa markup." en="Subscription + AI cost (BYOK) paid directly to providers. No markup." /></p>
          {/* Toggle tahunan NYATA (Tahap 4): knob annual_discount_pct — 0 = disembunyikan; checkout tahunan hidup di Billing */}
          {annualPct > 0 && (
            <div className="bill-toggle">
              <span className="secondary" style={{ fontSize: "var(--text-sm)" }}><Bi id="Bulanan" en="Monthly" /></span>
              <label className="switch"><input type="checkbox" checked={annual} onChange={(e) => setAnnual(e.target.checked)} /><span className="track" /><span className="thumb" /></label>
              <span className="secondary" style={{ fontSize: "var(--text-sm)" }}><Bi id="Tahunan" en="Annual" /></span>
              <span className="save"><Bi id={`Hemat ${annualPct}%`} en={`Save ${annualPct}%`} /></span>
            </div>
          )}
        </div>

        <div className="tiers">
          {paidPlans(plans).map((p) => {
            // Narasi (tagline/fitur/populer) = DB plan_limits.marketing_* — admin-editable tanpa deploy (Tahap 4).
            const baseK = Math.round((p.price_idr ?? 0) / 1000);
            const showAnnual = annual && annualPct > 0;
            const price = showAnnual ? Math.round(baseK * (100 - annualPct) / 100) : baseK;
            return (
              <div className={`tier${p.is_popular ? " pop" : ""}`} key={p.plan_type}>
                {p.is_popular && <span className="pop-badge">Most Popular</span>}
                <div className="tn">{p.display_name}</div>
                <div className="tt"><Bi id={p.tagline_id} en={p.tagline_en || p.tagline_id} /></div>
                <div className="tp-strike">{showAnnual ? `Rp ${baseK}K` : ""}</div>
                <div className="tp">Rp {price}K<small>/bln</small></div>
                <div className="muted" style={{ fontSize: "var(--text-xs)" }}>{showAnnual ? <Bi id="ditagih tahunan" en="billed annually" /> : " "}</div>
                <ul>
                  <li><Check size={15} /> {p.max_channels} channel</li>
                  <li><Check size={15} /> <Bi id={`${p.max_videos_per_day} video / hari`} en={`${p.max_videos_per_day} videos / day`} /></li>
                  {p.niche_studio && <li><Check size={15} /> Niche Studio (DNA kustom)</li>}
                  {p.marketing_features.map((f, k) => <li key={k}><Check size={15} /> <Bi id={f.id} en={f.en || f.id} /></li>)}
                </ul>
                <a href="/auth?view=signup" className={`btn ${p.is_popular ? "btn-default" : "btn-outline"}`} style={{ width: "100%" }}><Bi id={`Pilih ${p.display_name}`} en={`Choose ${p.display_name}`} /></a>
              </div>
            );
          })}
        </div>

        <div className="ent">
          <div className="et">
            <h3>Enterprise</h3>
            <p><Bi id="Butuh lebih dari 10 channel, white-label, atau SLA khusus? Mari bicara — kami susun paket sesuai kebutuhan agency atau tim Anda." en="Need more than 10 channels, white-label, or a custom SLA? Let's talk — we'll tailor a plan for your agency or team." /></p>
          </div>
          <a href="/about" className="btn btn-secondary btn-lg"><Users size={16} /> <Bi id="Hubungi Sales" en="Contact Sales" /></a>
        </div>
      </div>

      {/* FULL COMPARISON */}
      <section className="mk-section"><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}><h2 className="mk-h2"><Bi id="Bandingkan semua fitur" en="Compare all features" /></h2></div>
        <div className="fcmp-wrap">
          <table className="fcmp">
            <thead><tr><th></th><th>{pm.starter?.display_name ?? "Starter"}</th><th className="pop">{pm.pro?.display_name ?? "Pro"}</th><th>{pm.business?.display_name ?? "Business"}</th><th>Enterprise</th></tr></thead>
            <tbody>{matrix.map((r) => r.is_group ? (
              <tr className="grp" key={r.id}><td colSpan={5}><Bi id={r.label_id} en={r.label_en || r.label_id} /></td></tr>
            ) : (
              <tr key={r.id}><td><Bi id={r.label_id} en={r.label_en || r.label_id} /></td>
                <td><Fc v={resolveCell(r.v_starter, pm.starter)} /></td>
                <td className="popcol"><Fc v={resolveCell(r.v_pro, pm.pro)} pop /></td>
                <td><Fc v={resolveCell(r.v_business, pm.business)} /></td>
                <td><Fc v={resolveCell(r.v_enterprise, undefined)} /></td></tr>
            ))}</tbody>
          </table>
        </div>
      </div></section>

      {/* BYOK — biaya AI di tangan tenant (ganti kalkulator ber-angka hardcode; keputusan owner 2026-07-04:
          harga AI sangat variatif — bisa Rp 0 dgn provider/model gratis; angka palsu = boomerang) */}
      <section className="mk-section" style={{ background: "var(--bg-elevated)", borderBlock: "1px solid var(--border-subtle)" }}><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}>
          <span className="mk-kicker"><DollarSign size={13} /> BYOK — Bring Your Own Key</span>
          <h2 className="mk-h2"><Bi id="Biaya AI di tanganmu — mulai dari Rp 0" en="Your AI costs, your control — starting at Rp 0" /></h2>
          <p className="mk-lead mk-center"><Bi id="Tidak seperti tools lain yang menjual kredit dengan markup, MesinViral memakai kunci API milikmu sendiri. Kamu bebas memilih provider dan model — dan membayar hanya ke mereka, sesuai pemakaian nyata." en="Unlike tools that resell credits with a markup, MesinViral runs on your own API keys. You choose the providers and models — and pay only them, for what you actually use." /></p>
        </div>
        <div className="addons">
          <div className="addon"><span className="ai"><Wand2 size={20} /></span><h4><Bi id="Mulai dari Rp 0" en="Start at Rp 0" /></h4><p><Bi id="Pilih provider dengan tier atau model gratis — mesin tetap memproduksi video penuh tanpa biaya AI sepeser pun." en="Pick a provider with a free tier or free models — the engine still produces complete videos with zero AI cost." /></p></div>
          <div className="addon"><span className="ai"><DollarSign size={20} /></span><h4><Bi id="Tanpa markup, tanpa perantara" en="No markup, no middleman" /></h4><p><Bi id="Kunci API milikmu, tagihan langsung dari provider. Kami tidak mengambil sepeser pun dari biaya AI-mu." en="Your keys, billed directly by the provider. We never take a cut of your AI spend." /></p></div>
          <div className="addon"><span className="ai"><Users size={20} /></span><h4><Bi id="Kamu yang pegang kendali" en="You stay in control" /></h4><p><Bi id="Naikkan kualitas dengan model premium, atau tekan biaya dengan model hemat — ganti kapan saja per channel, tanpa terkunci vendor." en="Scale up with premium models or keep costs lean — switch anytime per channel, with zero vendor lock-in." /></p></div>
        </div>
      </div></section>

      {/* ADD-ONS */}
      <section className="mk-section"><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}><h2 className="mk-h2">Add-ons</h2></div>
        <div className="addons">
          {ADDONS.map(([Icon, n, key, suffix, fallback, d], i) => (
            <div className="addon" key={i}><span className="ai"><Icon size={20} /></span><h4>{n}</h4><div className="pr">{key && pricing[key] ? `Rp ${idrK(pricing[key])}${suffix}` : fallback}</div><p>{d}</p></div>
          ))}
        </div>
      </div></section>

      {/* FAQ */}
      <section className="mk-section" style={{ background: "var(--bg-elevated)", borderTop: "1px solid var(--border-subtle)" }}><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}><h2 className="mk-h2">FAQ <Bi id="seputar harga" en="about pricing" /></h2></div>
        <div className="faq">
          {makeFaq(trialDays, annualPct).map(([q, a], i) => (
            <div className={`faq-item${faqOpen === i ? " open" : ""}`} key={i}>
              <div className="faq-q" onClick={() => setFaqOpen(faqOpen === i ? -1 : i)}>{q} <span className="chev"><ChevronDown size={18} /></span></div>
              <div className="faq-a"><p>{a}</p></div>
            </div>
          ))}
        </div>
      </div></section>
    </>
  );
}
