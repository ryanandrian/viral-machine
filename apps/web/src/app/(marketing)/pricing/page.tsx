"use client";

import { useState, useEffect } from "react";
import { fetchPricing, idrK } from "@/lib/pricing";
import { fetchPlans, paidPlans, type Plan } from "@/lib/plans";
import {
  Users, Check, X, ChevronDown, DollarSign,
  Wand2, type LucideIcon,
} from "lucide-react";
import "./pricing.css";

// A2 Pricing (PoC) — port dari design-source/Pricing.html. Harga LITERAL = mock;
// produksi: config-driven dari pricing_config (lihat decisions_niche_model). FAQ Xendit→Midtrans.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

// Konten KUALITATIF per tier (marketing copy) — keyed by plan_type. NAMA / HARGA / CHANNEL / VIDEO-HARI /
// NICHE-STUDIO = config-driven (plan_limits + pricing_config via fetchPlans) → no-hardcode (owner 2026-06-21).
// Kelas/visual = Claude Design (pricing.css/marketing.css), tak diubah.
type TierCopy = { ttId: string; ttEn: string; feats: string[]; pop: boolean };
const TIER_COPY: Record<string, TierCopy> = {
  starter:  { ttId: "Untuk mulai scaling", ttEn: "To start scaling", feats: ["Niche dasar", "Self-learning", "Telegram notif"], pop: false },
  pro:      { ttId: "Paling diminati creator serius", ttEn: "Most chosen by serious creators", feats: ["Semua niche", "Quality Gate + Compliance", "Custom voice", "Captions & hashtags"], pop: true },
  business: { ttId: "Untuk agency & power user", ttEn: "For agencies & power users", feats: ["Priority queue", "Multi-channel dashboard", "Webhook & API", "Quiet hours"], pop: false },
};

type FRow = { grp: [string, string] } | { row: [string, boolean | string, boolean | string, boolean | string, boolean | string] };
// Baris Channel/Video-hari/Niche-Studio = config-driven (plan_limits via fetchPlans); Enterprise = literal.
function makeFcmp(pm: Record<string, Plan | undefined>): FRow[] {
  const ch = (k: string) => (pm[k] ? String(pm[k]!.max_channels) : "—");
  const vd = (k: string) => (pm[k] ? String(pm[k]!.max_videos_per_day) : "—");
  const ns = (k: string): boolean => Boolean(pm[k]?.niche_studio);
  return [
  { grp: ["Produksi", "Production"] },
  { row: ["Channel", ch("starter"), ch("pro"), ch("business"), "∞"] },
  { row: ["Video / hari", vd("starter"), vd("pro"), vd("business"), "custom"] },
  { row: ["Self-learning engine", true, true, true, true] },
  { row: ["BYOK (bawa API keys)", true, true, true, true] },
  { row: ["Multi-channel paralel", false, true, true, true] },
  { grp: ["AI & Kualitas", "AI & Quality"] },
  { row: ["Niche tersedia", "3", "semua", "semua", "semua"] },
  { row: ["Niche Studio (DNA kustom)", ns("starter"), ns("pro"), ns("business"), true] },
  { row: ["Quality Gate kustom", false, true, true, true] },
  { row: ["Compliance detail", false, true, true, true] },
  { row: ["Custom voice (ElevenLabs)", false, true, true, true] },
  { row: ["Captions style kustom", false, true, true, true] },
  { row: ["Hashtags kustom", false, true, true, true] },
  { grp: ["Kolaborasi & Integrasi", "Collaboration & Integrations"] },
  { row: ["Telegram & Email notif", true, true, true, true] },
  { row: ["Webhook", false, false, true, true] },
  { row: ["Priority queue", false, false, true, true] },
  { row: ["API access", false, false, true, true] },
  { grp: ["Dukungan", "Support"] },
  { row: ["Support", "Email", "Priority", "Priority", "Dedicated"] },
  ];
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

const makeFaq = (d: number): [string, string][] => [
  ["Bisa upgrade / downgrade kapan saja?", "Bisa. Perubahan paket berlaku langsung dan biaya di-prorate otomatis di tagihan berikutnya."],
  ["Bagaimana refund policy-nya?", `Trial ${d} hari gratis penuh. Setelah berlangganan, kami menawarkan refund 7 hari untuk pembayaran pertama jika belum cocok.`],
  ["Bagaimana biaya AI dihitung?", "Biaya AI mengikuti pemakaian aktual API milikmu (BYOK) dan dibayar langsung ke provider yang kamu pilih — bukan ke MesinViral. Besarnya sangat bervariasi tergantung provider & model: bisa mulai dari Rp 0 bila memakai tier/model gratis."],
  ["Apakah harga sudah termasuk biaya AI?", "Harga langganan terpisah dari biaya AI (BYOK) — dan biaya AI itu kamu yang kendalikan penuh, mulai dari Rp 0 dengan provider/model gratis."],
  ["Pembayaran pakai apa?", "Kami pakai Midtrans — mendukung transfer bank, e-wallet (GoPay, ShopeePay), QRIS, kartu kredit, dan Virtual Account."],
];

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);
  const [faqOpen, setFaqOpen] = useState(0);
  const [pricing, setPricing] = useState<Record<string, number>>({});
  const [plans, setPlans] = useState<Plan[]>([]);
  const [trialDays, setTrialDays] = useState(7);
  useEffect(() => {
    fetchPricing().then(setPricing);
    fetchPlans().then(({ plans, trialDays }) => { setPlans(plans); setTrialDays(trialDays); });
  }, []);
  const pm: Record<string, Plan | undefined> = Object.fromEntries(plans.map((p) => [p.plan_type, p]));
  const fcmp = makeFcmp(pm);

  return (
    <>
      <div className="mk-container">
        <div className="ph-head">
          <span className="mk-kicker"><Bi id="Harga transparan" en="Transparent pricing" /></span>
          <h1><Bi id="Pilih paket untuk channelmu" en="Pick a plan for your channel" /></h1>
          <p className="mk-lead mk-center"><Bi id="Langganan + biaya AI (BYOK) dibayar langsung ke provider. Tanpa markup." en="Subscription + AI cost (BYOK) paid directly to providers. No markup." /></p>
          <div className="bill-toggle">
            <span className="secondary" style={{ fontSize: "var(--text-sm)" }}><Bi id="Bulanan" en="Monthly" /></span>
            <label className="switch"><input type="checkbox" checked={annual} onChange={(e) => setAnnual(e.target.checked)} /><span className="track" /><span className="thumb" /></label>
            <span className="secondary" style={{ fontSize: "var(--text-sm)" }}><Bi id="Tahunan" en="Annual" /></span>
            <span className="save"><Bi id="Hemat 20%" en="Save 20%" /></span>
          </div>
        </div>

        <div className="tiers">
          {paidPlans(plans).map((p) => {
            const copy = TIER_COPY[p.plan_type] ?? { ttId: "", ttEn: "", feats: [], pop: false };
            const baseK = Math.round((p.price_idr ?? 0) / 1000);
            const price = annual ? Math.round(baseK * 0.8) : baseK;
            const feats = [`${p.max_channels} channel`, `${p.max_videos_per_day} video / hari`, ...(p.niche_studio ? ["Niche Studio (DNA kustom)"] : []), ...copy.feats];
            return (
              <div className={`tier${copy.pop ? " pop" : ""}`} key={p.plan_type}>
                {copy.pop && <span className="pop-badge">Most Popular</span>}
                <div className="tn">{p.display_name}</div>
                <div className="tt"><Bi id={copy.ttId} en={copy.ttEn} /></div>
                <div className="tp-strike">{annual ? `Rp ${baseK}K` : ""}</div>
                <div className="tp">Rp {price}K<small>/bln</small></div>
                <div className="muted" style={{ fontSize: "var(--text-xs)" }}>{annual ? <Bi id="ditagih tahunan" en="billed annually" /> : " "}</div>
                <ul>{feats.map((f, k) => <li key={k}><Check size={15} /> {f}</li>)}</ul>
                <a href="/auth?view=signup" className={`btn ${copy.pop ? "btn-default" : "btn-outline"}`} style={{ width: "100%" }}><Bi id={`Pilih ${p.display_name}`} en={`Choose ${p.display_name}`} /></a>
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
            <tbody>{fcmp.map((r, i) => "grp" in r ? (
              <tr className="grp" key={i}><td colSpan={5}><Bi id={r.grp[0]} en={r.grp[1]} /></td></tr>
            ) : (
              <tr key={i}><td>{r.row[0] as string}</td><td><Fc v={r.row[1]} /></td><td className="popcol"><Fc v={r.row[2]} pop /></td><td><Fc v={r.row[3]} /></td><td><Fc v={r.row[4]} /></td></tr>
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
          {makeFaq(trialDays).map(([q, a], i) => (
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
