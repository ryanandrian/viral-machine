"use client";

import { useState } from "react";
import {
  Users, Check, X, ChevronDown, Info, DollarSign,
  Wand2, Mic, HelpCircle, Zap, Gauge, ShieldCheck, type LucideIcon,
} from "lucide-react";
import "./pricing.css";

// A2 Pricing (PoC) — port dari design-source/Pricing.html. Harga LITERAL = mock;
// produksi: config-driven dari pricing_config (lihat decisions_niche_model). FAQ Xendit→Midtrans.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Tier = { n: string; m: number; ttId: string; ttEn: string; feats: string[]; ctaId: string; ctaEn: string; pop: boolean };
const TIERS: Tier[] = [
  { n: "Starter", m: 149, ttId: "Untuk mulai scaling 1 channel", ttEn: "To start scaling 1 channel", feats: ["1 channel", "5 video / hari", "Niche dasar", "Self-learning", "Telegram notif"], ctaId: "Pilih Starter", ctaEn: "Choose Starter", pop: false },
  { n: "Pro", m: 349, ttId: "Paling diminati creator serius", ttEn: "Most chosen by serious creators", feats: ["3 channel", "10 video / hari", "Semua niche", "Quality Gate + Compliance", "Custom voice", "Captions & hashtags"], ctaId: "Pilih Pro", ctaEn: "Choose Pro", pop: true },
  { n: "Business", m: 699, ttId: "Untuk agency & power user", ttEn: "For agencies & power users", feats: ["10 channel", "24 video / hari", "Priority queue", "Cross-channel insights", "Webhook & API", "Quiet hours"], ctaId: "Pilih Business", ctaEn: "Choose Business", pop: false },
];

type FRow = { grp: [string, string] } | { row: [string, boolean | string, boolean | string, boolean | string, boolean | string] };
const FCMP: FRow[] = [
  { grp: ["Produksi", "Production"] },
  { row: ["Channel", "1", "3", "10", "∞"] },
  { row: ["Video / hari", "5", "10", "24", "custom"] },
  { row: ["Self-learning engine", true, true, true, true] },
  { row: ["BYOK (bawa API keys)", true, true, true, true] },
  { row: ["Multi-channel paralel", false, true, true, true] },
  { grp: ["AI & Kualitas", "AI & Quality"] },
  { row: ["Niche tersedia", "3", "semua", "semua", "semua"] },
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
  { row: ["Concierge setup", false, false, true, true] },
];
function Fc({ v, pop }: { v: boolean | string; pop?: boolean }) {
  if (v === true) return <span className="yes"><Check size={18} /></span>;
  if (v === false) return <span className="no"><X size={16} /></span>;
  return <span style={pop ? { color: "var(--brand)", fontWeight: 600 } : undefined}>{v}</span>;
}

const ADDONS: [LucideIcon, string, string, string][] = [
  [Wand2, "Niche Pack", "Rp 299K", "Niche kustom dibuat sesuai brief Anda, 3–5 hari delivery."],
  [Mic, "Voice Pack", "Rp 199K", "Koleksi 10 voice premium ElevenLabs untuk variasi channel."],
  [HelpCircle, "Concierge Setup", "Rp 499K", "Tim kami setup channel, API keys, & schedule untuk Anda."],
  [Zap, "Priority Queue", "Rp 149K/bln", "Run Anda diproses paling depan saat traffic tinggi."],
  [Gauge, "Channel Audit", "Rp 349K", "Analisis mendalam + rekomendasi growth dari ahli."],
  [ShieldCheck, "Extra Compliance", "Rp 99K/bln", "Monitoring compliance lebih ketat + alert prioritas."],
];

const FAQ: [string, string][] = [
  ["Bisa upgrade / downgrade kapan saja?", "Bisa. Perubahan paket berlaku langsung dan biaya di-prorate otomatis di tagihan berikutnya."],
  ["Bagaimana refund policy-nya?", "Trial 7 hari gratis penuh. Setelah berlangganan, kami menawarkan refund 7 hari untuk pembayaran pertama jika belum cocok."],
  ["Bagaimana biaya AI dihitung?", "Biaya AI mengikuti pemakaian aktual API milikmu (BYOK) dan dibayar langsung ke Anthropic/OpenAI/ElevenLabs. Dashboard menampilkan biaya real-time per video."],
  ["Apakah harga sudah termasuk biaya AI?", "Belum. Harga langganan terpisah dari biaya AI (BYOK). Gunakan kalkulator di atas untuk estimasi total."],
  ["Pembayaran pakai apa?", "Kami pakai Midtrans — mendukung transfer bank, e-wallet (GoPay, ShopeePay), QRIS, kartu kredit, dan Virtual Account."],
];

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);
  const [vids, setVids] = useState(5);
  const [faqOpen, setFaqOpen] = useState(0);

  const month = vids * 30 * 0.34;
  const ant = month * 0.21, el = month * 0.53, oai = month * 0.26;

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
          {TIERS.map((t) => {
            const price = annual ? Math.round(t.m * 0.8) : t.m;
            return (
              <div className={`tier${t.pop ? " pop" : ""}`} key={t.n}>
                {t.pop && <span className="pop-badge">Most Popular</span>}
                <div className="tn">{t.n}</div>
                <div className="tt"><Bi id={t.ttId} en={t.ttEn} /></div>
                <div className="tp-strike">{annual ? `Rp ${t.m}K` : ""}</div>
                <div className="tp">Rp {price}K<small>/bln</small></div>
                <div className="muted" style={{ fontSize: "var(--text-xs)" }}>{annual ? <Bi id="ditagih tahunan" en="billed annually" /> : " "}</div>
                <ul>{t.feats.map((f, k) => <li key={k}><Check size={15} /> {f}</li>)}</ul>
                <a href="/auth?view=signup" className={`btn ${t.pop ? "btn-default" : "btn-outline"}`} style={{ width: "100%" }}><Bi id={t.ctaId} en={t.ctaEn} /></a>
              </div>
            );
          })}
        </div>

        <div className="ent">
          <div className="et">
            <h3>Enterprise</h3>
            <p><Bi id="Butuh lebih dari 10 channel, white-label, atau SLA khusus? Mari bicara — kami susun paket sesuai kebutuhan agency atau tim Anda." en="Need more than 10 channels, white-label, or a custom SLA? Let's talk — we'll tailor a plan for your agency or team." /></p>
          </div>
          <a href="#" className="btn btn-secondary btn-lg"><Users size={16} /> <Bi id="Hubungi Sales" en="Contact Sales" /></a>
        </div>
      </div>

      {/* FULL COMPARISON */}
      <section className="mk-section"><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}><h2 className="mk-h2"><Bi id="Bandingkan semua fitur" en="Compare all features" /></h2></div>
        <div className="fcmp-wrap">
          <table className="fcmp">
            <thead><tr><th></th><th>Starter</th><th className="pop">Pro</th><th>Business</th><th>Enterprise</th></tr></thead>
            <tbody>{FCMP.map((r, i) => "grp" in r ? (
              <tr className="grp" key={i}><td colSpan={5}><Bi id={r.grp[0]} en={r.grp[1]} /></td></tr>
            ) : (
              <tr key={i}><td>{r.row[0] as string}</td><td><Fc v={r.row[1]} /></td><td className="popcol"><Fc v={r.row[2]} pop /></td><td><Fc v={r.row[3]} /></td><td><Fc v={r.row[4]} /></td></tr>
            ))}</tbody>
          </table>
        </div>
      </div></section>

      {/* CALCULATOR */}
      <section className="mk-section" style={{ background: "var(--bg-elevated)", borderBlock: "1px solid var(--border-subtle)" }}><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}>
          <span className="mk-kicker"><DollarSign size={13} /> BYOK Calculator</span>
          <h2 className="mk-h2"><Bi id="Hitung estimasi biaya AI-mu" en="Estimate your AI cost" /></h2>
        </div>
        <div className="calc">
          <div className="calc-slider">
            <label className="label"><Bi id="Berapa video per hari?" en="How many videos per day?" /></label>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginBottom: "1rem" }}><span className="calc-big">{vids}</span><span className="muted"><Bi id="video / hari" en="videos / day" /></span></div>
            <input type="range" min={1} max={24} value={vids} onChange={(e) => setVids(+e.target.value)} />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-xs)", color: "var(--text-muted)", marginTop: 6 }}><span>1</span><span>24</span></div>
            <div style={{ marginTop: "1.25rem", padding: "0.875rem 1rem", background: "var(--accent-soft)", border: "1px solid color-mix(in srgb,var(--accent) 22%,transparent)", borderRadius: "var(--r-md)", fontSize: "var(--text-xs)", color: "var(--text-secondary)", display: "flex", gap: "0.5rem" }}>
              <span style={{ color: "var(--accent)", flex: "none" }}><Info size={14} /></span><Bi id="Biaya AI dibayar langsung ke provider sesuai BYOK — bukan ke MesinViral." en="AI cost is paid directly to providers via BYOK — not to MesinViral." /></div>
          </div>
          <div>
            <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Estimasi biaya AI / bulan" en="Estimated AI cost / month" /></div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.625rem", margin: "0.25rem 0" }}><span className="calc-big">${Math.round(month)}</span><span className="muted">≈ Rp {Math.round(month * 16)}K</span></div>
            <div className="calc-bar"><span style={{ background: "var(--anthropic)", flex: 21 }} /><span style={{ background: "var(--elevenlabs)", flex: 53 }} /><span style={{ background: "var(--openai)", flex: 26 }} /></div>
            <div className="calc-row"><span className="sw" style={{ background: "var(--anthropic)" }} />Claude <span className="amt">${ant.toFixed(0)}</span></div>
            <div className="calc-row"><span className="sw" style={{ background: "var(--elevenlabs)" }} />ElevenLabs <span className="amt">${el.toFixed(0)}</span></div>
            <div className="calc-row"><span className="sw" style={{ background: "var(--openai)" }} />OpenAI <span className="amt">${oai.toFixed(0)}</span></div>
            <div className="calc-row" style={{ borderTop: "1px solid var(--border-subtle)", marginTop: "0.5rem", paddingTop: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}><Bi id="Per video" en="Per video" /> <span className="amt">≈ $0.34</span></div>
          </div>
        </div>
      </div></section>

      {/* ADD-ONS */}
      <section className="mk-section"><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}><h2 className="mk-h2">Add-ons</h2></div>
        <div className="addons">
          {ADDONS.map(([Icon, n, pr, d], i) => (
            <div className="addon" key={i}><span className="ai"><Icon size={20} /></span><h4>{n}</h4><div className="pr">{pr}</div><p>{d}</p></div>
          ))}
        </div>
      </div></section>

      {/* FAQ */}
      <section className="mk-section" style={{ background: "var(--bg-elevated)", borderTop: "1px solid var(--border-subtle)" }}><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}><h2 className="mk-h2">FAQ <Bi id="seputar harga" en="about pricing" /></h2></div>
        <div className="faq">
          {FAQ.map(([q, a], i) => (
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
