"use client";

import { useState, useEffect } from "react";
import { fetchPricing, idrK } from "@/lib/pricing";
import { fetchPlans, paidPlans, type Plan } from "@/lib/plans";
import {
  Sparkles, ArrowRight, Play, CheckCircle, Check, Clock, BarChart3, XCircle,
  Command, ShieldCheck, Zap, X, Loader2, ChevronDown, Star,
  Radar, Target, FileText, AudioLines, Image as ImageIcon, Film, Upload, type LucideIcon,
  Lock, KeyRound, EyeOff, Server, Send, Brain, TrendingUp, RotateCcw,
} from "lucide-react";
import "./landing.css";

// A1 Landing (PoC) — port dari design-source/Landing.html. Copy "Xendit" → "Midtrans" (keputusan final).
// Brand icons (anthropic/elevenlabs/openai/youtube) tak ada di lucide → substitusi chip teks/warna.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const PIPE: [LucideIcon, string, string][] = [
  [Radar, "Trend Radar", "Scan tren"], [Target, "Topic Select", "Pilih topik"],
  [FileText, "Script", "LLM agen"], [Sparkles, "Hook", "Optimasi"],
  [AudioLines, "TTS", "via 11labs"], [ImageIcon, "Visual", "AI image"],
  [Film, "Render", "Compose"], [Upload, "Publish", "YouTube"],
];
// 3 simpul umpan-balik (baris bawah) — kiri→kanan agar loop rapi (berlawanan arah jarum jam):
// Self-improvement (kiri, di bawah Trend Radar) → Self-learning (tengah) → Report (kanan, di bawah Publish).
const LOOP: [LucideIcon, string, string][] = [
  [TrendingUp, "Self-improvement", "tiap siklus"],
  [Brain, "Self-learning", "dari analytics"],
  [Send, "Report", "ke Telegram"],
];

const CMP_COLS = ["AutoShorts", "OpusClip", "Submagic", "Pictory"];
const CMP_ROWS: [string, boolean | string, ...(boolean | string)[]][] = [
  ["Auto-publish ke YouTube", true, true, false, false, false],
  ["Self-learning dari analytics", true, false, false, false, false],
  ["Konten multi-bahasa", true, false, false, false, false],
  ["BYOK (bawa API keys)", true, false, false, false, false],
  ["Diversity / AI Slop defense", true, false, false, false, false],
  ["Multi-channel paralel", true, true, false, false, true],
  ["Max video / hari", "24", "2", "—", "—", "—"],
  ["Custom voice (ElevenLabs)", true, false, true, false, false],
  ["Pembayaran Indonesia (Midtrans)", true, false, false, false, false],
  ["Harga / video", "Rp 75", "Rp 18.000", "—", "—", "—"],
];
function Cell({ v, us }: { v: boolean | string; us?: boolean }) {
  if (v === true) return <span className="yes"><Check size={18} /></span>;
  if (v === false) return <span className="no"><X size={16} /></span>;
  return <span style={us ? { color: "var(--brand)", fontWeight: 700 } : { color: "var(--text-secondary)" }}>{v}</span>;
}

const TST = [
  { q: "Set & forget — mesinnya benar-benar belajar dari channel saya dan makin pintar tiap minggu. Saya tinggal pantau hasilnya.", nm: "Riko Pratama", ch: "Misteri Samudra · 12.4K", av: "RP", c: "#1d4ed8", gr: "24/7", gl: "set & forget" },
  { q: "Sebagai agency, saya manage 8 channel klien dari satu dashboard. Compliance score bikin saya tenang soal policy YouTube.", nm: "Sarah Wibowo", ch: "Agency · 8 channel", av: "SW", c: "#9f1239", gr: "8", gl: "channel aktif" },
  { q: "Biaya AI transparan banget. Saya tahu persis Rp 75 per video — jauh lebih murah dari tools lain.", nm: "Dimas Aryo", ch: "Fakta Yang Bikin Mikir · 32.7K", av: "DA", c: "#047857", gr: "7.5×", gl: "lebih hemat" },
  { q: 'Niche "Sejarah Kelam" saya akhirnya konsisten upload 5×/hari tanpa saya sentuh editing sama sekali.', nm: "Bagus Pratomo", ch: "Jejak Kelam Sejarah · 8.2K", av: "BP", c: "#7c3aed", gr: "5/hari", gl: "auto-publish" },
];

const makeFaq = (d: number): [string, string][] => [
  ["Apa itu BYOK?", "BYOK = Bring Your Own Keys. Kamu pakai API keys Anthropic/OpenAI/ElevenLabs milikmu sendiri, jadi biaya AI dibayar langsung ke provider dengan harga asli — transparan, tanpa markup dari kami."],
  ["Bisa bikin konten dalam bahasa selain Indonesia (English, Malaysia, Thailand)?", "Bisa. Pilih bahasa konten per channel saat setup. Mesin memproduksi narasi, caption, dan script dalam bahasa itu. Bahasa official: Indonesia & English; bahasa Asia Tenggara lain (Malaysia, Filipina, Thailand, Vietnam) tersedia bertahap."],
  ["Apakah aman dari penalty YouTube AI policy 2026?", "Ya. AI Slop Defense Engine kami otomatis merotasi voice, niche, hook, dan menambahkan AI disclosure. Compliance score real-time membantumu menjaga channel tetap aman."],
  ["Berapa total biaya termasuk API?", "Langganan mulai Rp 149K/bln + biaya AI (BYOK) sekitar Rp 75/video. Untuk 5 video/hari, estimasi biaya AI ~Rp 340K/bln yang dibayar langsung ke provider."],
  ["Bisa cancel kapan saja?", `Bisa. Tidak ada kontrak. Cancel kapan saja sebelum trial ${d} hari berakhir tanpa biaya, atau berhenti berlangganan kapan pun setelahnya.`],
  ["Channel saya 0 subs, bisa pakai?", "Tentu. Mesin mulai dengan niche default terbaik, lalu belajar dari data channelmu seiring video mulai tayang."],
  ["Apakah mesin belajar antar-channel?", "Tidak. Self-learning bersifat per-channel — data dan adaptasi satu channel tidak bocor ke channel lain."],
];

export default function LandingPage() {
  const [faqOpen, setFaqOpen] = useState(0);
  const [pricing, setPricing] = useState<Record<string, number>>({});
  const [plans, setPlans] = useState<Plan[]>([]);
  const [trialDays, setTrialDays] = useState(7);
  useEffect(() => {
    fetchPricing().then(setPricing);
    fetchPlans().then(({ plans, trialDays }) => { setPlans(plans); setTrialDays(trialDays); });
  }, []);
  const pk = (k: string, fb: string) => pricing[k] ? `Rp ${idrK(pricing[k])}` : fb;
  // Preview harga config-driven (no-hardcode) — copy kualitatif singkat per tier; batas dari plan_limits.
  const PREVIEW_COPY: Record<string, { ttId: string; ttEn: string; feats: string[]; pop: boolean }> = {
    starter:  { ttId: "Untuk mulai scaling", ttEn: "To start scaling", feats: ["Niche dasar", "Self-learning"], pop: false },
    pro:      { ttId: "Paling diminati creator", ttEn: "Most chosen by creators", feats: ["Semua niche", "Quality Gate + Compliance", "Custom voice"], pop: true },
    business: { ttId: "Untuk agency & power user", ttEn: "For agencies & power users", feats: ["Priority queue", "Multi-channel dashboard"], pop: false },
  };

  return (
    <>
      {/* HERO */}
      <section className="hero">
        <div className="hero-bg" /><div className="hero-grid-lines" />
        <div className="mk-container hero-inner">
          <div>
            <span className="mk-kicker"><Sparkles size={14} /> <Bi id="Self-learning · BYOK · Indonesia-first" en="Self-learning · BYOK · Indonesia-first" /></span>
            <h1>
              <span data-id>Mesin produksi video YouTube yang <span className="grad">belajar dari channelmu sendiri.</span></span>
              <span data-en>The YouTube video machine that <span className="grad">learns from your own channel.</span></span>
            </h1>
            <p className="sub"><Bi id="5–24 video Shorts per hari dengan kualitas viral-grade. Tools lain bikin video. MesinViral belajar dari analytics channelmu — dan makin pintar tiap hari." en="5–24 Shorts per day at viral-grade quality. Other tools just make videos. MesinViral learns from your channel's analytics — and gets smarter every day." /></p>
            <div className="hero-cta">
              <a href="/auth?view=signup" className="btn btn-default btn-xl"><Bi id="Mulai Gratis 7 Hari" en="Start 7-Day Free Trial" /> <ArrowRight size={18} /></a>
              <a href="/demo" className="btn btn-outline btn-xl"><Play size={16} /> <Bi id="Tonton Demo" en="Watch Demo" /></a>
            </div>
            <div className="hero-fine"><CheckCircle size={15} style={{ color: "var(--success)" }} /> <Bi id="Tanpa kartu kredit · 5 video gratis · Cancel kapan saja" en="No credit card · 5 free videos · Cancel anytime" /></div>
            <div className="hero-trust">
              <Bi id="Didukung oleh" en="Powered by" />
              <div className="logos" style={{ fontWeight: 600 }}>
                <span style={{ color: "var(--anthropic)" }}>Claude</span>
                <span style={{ color: "var(--elevenlabs)" }}>ElevenLabs</span>
                <span style={{ color: "var(--openai)" }}>OpenAI</span>
                <span style={{ color: "var(--yt)" }}>YouTube</span>
              </div>
            </div>
          </div>
          <div className="mockup">
            <div className="mockup-card">
              <div className="mk-winbar"><div className="dots"><i /><i /><i /></div><span className="url">app.mesinviral.com/runs/97</span></div>
              <div className="mockup-body">
                <div className="mm-pl">
                  <div className="mm-step"><span className="mm-node" style={{ background: "var(--success-soft)", color: "var(--success)" }}><Check size={14} /></span> <b>Script</b> <span className="muted" style={{ marginLeft: "auto", fontSize: "0.6875rem" }}>Claude</span></div>
                  <div className="mm-step"><span className="mm-node" style={{ background: "var(--success-soft)", color: "var(--success)" }}><Check size={14} /></span> <b>TTS Audio</b> <span className="muted" style={{ marginLeft: "auto", fontSize: "0.6875rem" }}>11labs</span></div>
                  <div className="mm-step"><span className="mm-node" style={{ background: "var(--info-soft)", color: "var(--info)" }}><Loader2 size={14} className="mock-spin" /></span> <b>Visual</b> <span className="muted" style={{ marginLeft: "auto", fontSize: "0.6875rem" }}>OpenAI</span></div>
                  <div className="mm-step"><span className="mm-node" style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}><Clock size={14} /></span> <span className="muted">Render</span></div>
                  <div className="mm-step"><span className="mm-node" style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}><Clock size={14} /></span> <span className="muted">Publish</span></div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  <div className="mm-panel"><div className="muted" style={{ fontSize: "0.625rem" }}>Views hari ini</div><div className="mm-kpi">1.2K</div>
                    <svg viewBox="0 0 120 30" style={{ width: "100%", height: 26 }}><path d="M0 26 L20 22 L40 24 L60 16 L80 18 L100 8 L120 4" fill="none" stroke="#6366F1" strokeWidth={2} /></svg></div>
                  <div className="mm-panel"><div className="muted" style={{ fontSize: "0.625rem" }}>Biaya / video</div><div className="mm-kpi" style={{ fontSize: "1.125rem" }}>$0.34</div>
                    <div style={{ display: "flex", height: 6, borderRadius: 3, overflow: "hidden", gap: 1, marginTop: 4 }}><span style={{ flex: 21, background: "var(--anthropic)" }} /><span style={{ flex: 53, background: "var(--elevenlabs)" }} /><span style={{ flex: 26, background: "var(--openai)" }} /></div></div>
                </div>
              </div>
            </div>
            <div className="float-badge" style={{ top: -14, right: "8%" }}><Sparkles size={14} style={{ color: "var(--accent)" }} /> <Bi id="Hook 'gap' · viral-grade" en="Hook 'gap' · viral-grade" /></div>
            <div className="float-badge" style={{ bottom: "6%", left: -18 }}><ShieldCheck size={14} style={{ color: "var(--success)" }} /> Compliance 87</div>
          </div>
        </div>
      </section>

      {/* STATS */}
      <section className="mk-section-sm"><div className="mk-container">
        <div className="stats reveal">
          <div className="stat"><div className="big">50</div><div className="lbl"><Bi id="Video / hari" en="Videos / day" /></div><div className="desc"><Bi id="Hingga — Business 5/channel × 10 channel (kompetitor ~2/hari)" en="Up to — Business 5/channel × 10 channels (~2/day on competitors)" /></div></div>
          <div className="stat"><div className="big">7.5×</div><div className="lbl"><Bi id="Lebih murah" en="Cheaper" /></div><div className="desc"><Bi id="Rp 75/video vs Rp 18.000 di AutoShorts" en="Rp 75/video vs Rp 18,000 on AutoShorts" /></div></div>
          <div className="stat"><div className="big">100%</div><div className="lbl">BYOK</div><div className="desc"><Bi id="Tenant pegang API keys, biaya transparan" en="You hold the API keys, transparent cost" /></div></div>
        </div>
      </div></section>

      {/* PROBLEM */}
      <section className="mk-section"><div className="mk-container">
        <div className="mk-center reveal" style={{ marginBottom: "3rem" }}>
          <span className="mk-kicker"><Bi id="Masalahnya" en="The problem" /></span>
          <h2 className="mk-h2"><Bi id="Scaling channel YouTube itu melelahkan" en="Scaling a YouTube channel is exhausting" /></h2>
        </div>
        <div className="prob-grid reveal">
          <div className="prob"><span className="pic"><Clock size={22} /></span><h3><Bi id="4–8 jam per video" en="4–8 hours per video" /></h3><p><Bi id="Riset, script, voiceover, dan editing menghabiskan seharian penuh — hanya untuk satu video." en="Research, script, voiceover, and editing eat a full day — for a single video." /></p></div>
          <div className="prob"><span className="pic"><BarChart3 size={22} /></span><h3><Bi id="Tools lain max 2/hari" en="Other tools max 2/day" /></h3><p><Bi id="Auto-pilot kompetitor dibatasi 2 video/hari dengan harga $69/bulan. Tidak cukup untuk scale." en="Competitor auto-pilots cap at 2/day for $69/mo. Not enough to scale." /></p></div>
          <div className="prob"><span className="pic"><XCircle size={22} /></span><h3><Bi id="Tidak belajar darimu" en="They don't learn from you" /></h3><p><Bi id="Generic AI memberi output yang sama untuk semua orang. Tidak ada yang adaptasi ke channelmu." en="Generic AI gives everyone the same output. Nothing adapts to your channel." /></p></div>
        </div>
      </div></section>

      {/* SOLUTION pipeline */}
      <section className="mk-section" style={{ background: "var(--bg-elevated)", borderBlock: "1px solid var(--border-subtle)" }}><div className="mk-container">
        <div className="mk-center reveal" style={{ marginBottom: "2.5rem" }}>
          <span className="mk-kicker"><Zap size={13} /> <Bi id="Pipeline AI 11 langkah" en="11-step AI pipeline" /></span>
          <h2 className="mk-h2"><Bi id="Dari tren ke YouTube, otomatis" en="From trend to YouTube, automatically" /></h2>
          <p className="mk-lead"><Bi id="Setiap video melewati 8 langkah produksi otomatis + 3 simpul umpan-balik (report, self-learning, self-improvement) untuk menghasilkan konten dengan kualitas terbaik dan viral secara otomatis tanpa mengganggu waktu Anda." en="Every video flows through 8 automated production steps + 3 feedback nodes (report, self-learning, self-improvement) to deliver the highest-quality, viral content automatically — without taking up your time." /></p>
        </div>
        <div className="pipe-circuit reveal">
          <div className="pipe-circuit-in">
            {/* Track loop: cahaya mengalir atas(1→8) → turun kanan → bawah(R→L) → naik kiri → balik ke Trend Radar */}
            <svg className="pipe-track" viewBox="0 0 100 272" preserveAspectRatio="none" aria-hidden="true">
              <rect className="tk-base" x="6.25" y="26" width="87.5" height="158" rx="2.4" ry="16" pathLength={100} />
              <rect className="tk-flow" x="6.25" y="26" width="87.5" height="158" rx="2.4" ry="16" pathLength={100} />
            </svg>
            <div className="pipe-grid top">
              {PIPE.map(([Icon, n, c], i) => (
                <div className="pipe-node lit" key={i}><div className="ic"><Icon size={24} /></div><div className="n">{n}</div><div className="c">{c}</div></div>
              ))}
            </div>
            <div className="pipe-grid bottom">
              {LOOP.map(([Icon, n, c], i) => (
                <div className="pipe-node loop" key={i}><div className="ic"><Icon size={24} /></div><div className="n">{n}</div><div className="c">{c}</div></div>
              ))}
            </div>
          </div>
        </div>
        <div className="pipe-loopback reveal"><RotateCcw size={15} /> <Bi id="Hasil nyata kembali ke Trend Radar — robot belajar & membaik tiap siklus" en="Real results feed back into Trend Radar — the robot learns and improves every cycle" /></div>
      </div></section>

      {/* FEATURES */}
      <section className="mk-section" id="features"><div className="mk-container">
        <div className="mk-center reveal" style={{ marginBottom: "3rem" }}>
          <span className="mk-kicker"><Bi id="Kenapa MesinViral" en="Why MesinViral" /></span>
          <h2 className="mk-h2"><Bi id="Fitur yang tidak ada di tempat lain" en="Features you won't find elsewhere" /></h2>
        </div>
        <div className="feat-grid reveal">
          <div className="feat spotlight">
            <span className="badge badge-brand"><Sparkles size={12} /> <Bi id="Moat #1" en="Moat #1" /></span>
            <span className="fic"><Sparkles size={24} /></span>
            <h3><Bi id="Self-Learning Engine" en="Self-Learning Engine" /></h3>
            <p><Bi id="Belajar dari real YouTube Analytics channelmu. Mesin mengadaptasi niche, hook, dan topik otomatis — dan menghindari pola yang kurang perform — output makin viral tiap minggu, khusus untuk audiens-mu." en="Learns from your real YouTube Analytics. The engine adapts niche, hooks, and topics automatically — and avoids underperforming patterns — output gets more viral each week, tailored to your audience." /></p>
          </div>
          <div className="feat"><span className="fic"><Command size={22} /></span><h3><Bi id="BYOK Transparan" en="Transparent BYOK" /></h3><p><Bi id="Kamu pegang API keys Anthropic, OpenAI, ElevenLabs. Lihat biaya AI real-time per video. Tanpa markup." en="You hold your Anthropic, OpenAI, ElevenLabs keys. See AI cost per video in real time. No markup." /></p></div>
          <div className="feat"><span className="fic" style={{ background: "var(--success-soft)", color: "var(--success)" }}><ShieldCheck size={22} /></span><h3><Bi id="AI Slop Defense" en="AI Slop Defense" /></h3><p><Bi id="Diversity engine otomatis melindungi channel dari YouTube AI policy 2026. Compliance score real-time." en="A diversity engine automatically protects your channel from YouTube's 2026 AI policy. Real-time compliance score." /></p></div>
          <div className="feat"><span className="fic"><Zap size={22} /></span><h3><Bi id="5–24 Video / Hari" en="5–24 Videos / Day" /></h3><p><Bi id="Multi-channel paralel. Scale produksi tanpa hire tim editor." en="Parallel multi-channel. Scale production without hiring an editing team." /></p></div>
          <div className="feat"><span className="fic" style={{ background: "var(--warning-soft)", color: "var(--warning)" }}><Clock size={22} /></span><h3><Bi id="Beragam Opsi Durasi Konten" en="Flexible Content Durations" /></h3><p><Bi id="Pilih durasi 8–90 detik sesuai gaya & platform — teaser cepat 15 detik atau cerita utuh 60 detik. Tiap durasi diramu otomatis dengan struktur cerita yang pas, bukan sekadar dipotong, jadi tiap detik tetap menahan penonton." en="Pick 8–90s to match your style & platform — a fast 15s teaser or a full 60s story. Each duration is auto-crafted with the right story structure, never just trimmed, so every second keeps viewers watching." /></p></div>
          <div className="feat"><span className="fic" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}><Zap size={22} /></span><h3>🌐 <Bi id="Konten Multi-Bahasa" en="Multi-Language Content" /></h3><p><Bi id="Produksi narasi + caption dalam Bahasa Indonesia, English, dan bahasa Asia Tenggara. Pilih bahasa per channel — jangkau audiens lintas negara dari satu platform." en="Produce narration + captions in Indonesian, English, and Southeast Asian languages. Pick a language per channel — reach cross-border audiences from one platform." /></p><div style={{ display: "flex", gap: "0.4rem", marginTop: "0.875rem", fontSize: "var(--text-lg)" }}>🇮🇩 🇬🇧 🇲🇾 🇵🇭 🇹🇭 🇻🇳</div></div>
        </div>
      </div></section>

      {/* SECURITY — kredensial tenant (klaim hanya yang BENAR: BYOK + Fernet + isolasi + no-log) */}
      <section className="mk-section" id="security"><div className="mk-container">
        <div className="mk-center reveal" style={{ marginBottom: "2.5rem" }}>
          <span className="mk-kicker"><Lock size={13} /> <Bi id="Keamanan kredensial" en="Credential security" /></span>
          <h2 className="mk-h2"><Bi id="Kredensial Anda, terkunci" en="Your credentials, locked down" /></h2>
          <p className="mk-lead"><Bi id="BYOK: kunci AI & akun YouTube milik Anda sendiri. Kami menyimpannya terenkripsi — dan tidak pernah menyentuh konten Anda." en="BYOK: your own AI keys & YouTube account. We store them encrypted — and never touch your content." /></p>
        </div>
        <div className="feat-grid reveal">
          <div className="feat"><span className="fic" style={{ background: "var(--success-soft)", color: "var(--success)" }}><KeyRound size={22} /></span><h3><Bi id="Kunci milik Anda (BYOK)" en="Your own keys (BYOK)" /></h3><p><Bi id="API key Anthropic/OpenAI/ElevenLabs milik Anda sendiri; akun YouTube cukup hubungkan via Google (tanpa setup teknis). Biaya AI dibayar langsung ke provider — transparan, tanpa markup." en="Your own Anthropic/OpenAI/ElevenLabs keys; connect your YouTube account via Google (no technical setup). AI cost is billed straight to the provider — no markup." /></p></div>
          <div className="feat"><span className="fic"><Lock size={22} /></span><h3><Bi id="Dienkripsi (AES/Fernet)" en="Encrypted (AES/Fernet)" /></h3><p><Bi id="Setiap kredensial sensitif — API key maupun token Google — disimpan terenkripsi. Kunci master enkripsi ada di server kami dan tidak pernah menyentuh browser." en="Every sensitive credential — API keys and Google tokens alike — is stored encrypted. The master key lives on our server and never touches the browser." /></p></div>
          <div className="feat"><span className="fic" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}><Server size={22} /></span><h3><Bi id="Isolasi per-tenant" en="Per-tenant isolation" /></h3><p><Bi id="Data tiap tenant terpisah ketat di tingkat database (RLS). Kredensial paling sensitif hanya bisa diakses layanan backend — tak pernah dari sisi publik." en="Each tenant's data is strictly isolated at the database level (RLS). The most sensitive credentials are reachable only by backend services — never from the public side." /></p></div>
          <div className="feat"><span className="fic"><EyeOff size={22} /></span><h3><Bi id="Tidak pernah di-log / ditampilkan" en="Never logged or shown" /></h3><p><Bi id="Setelah disimpan, nilai kunci tidak pernah ditampilkan ulang atau ditulis ke log. Anda bisa memutus sambungan kapan saja." en="Once saved, key values are never displayed again or written to logs. You can disconnect anytime." /></p></div>
        </div>
      </div></section>

      {/* COMPARISON */}
      <section className="mk-section" style={{ background: "var(--bg-elevated)", borderBlock: "1px solid var(--border-subtle)" }}><div className="mk-container">
        <div className="mk-center reveal" style={{ marginBottom: "2.5rem" }}><h2 className="mk-h2"><Bi id="MesinViral vs Kompetitor" en="MesinViral vs Competitors" /></h2></div>
        <div className="cmp-wrap reveal">
          <table className="cmp">
            <thead><tr><th></th><th className="us"><div className="cmp-ushead"><Zap size={18} /> MesinViral</div></th>{CMP_COLS.map((c) => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>{CMP_ROWS.map((r, i) => (
              <tr key={i}><td>{r[0] as string}</td><td className="uscol"><Cell v={r[1]} us /></td>{r.slice(2).map((v, k) => <td key={k}><Cell v={v as boolean | string} /></td>)}</tr>
            ))}</tbody>
          </table>
        </div>
      </div></section>

      {/* HOW */}
      <section className="mk-section"><div className="mk-container">
        <div className="mk-center reveal" style={{ marginBottom: "2.5rem" }}>
          <span className="mk-kicker"><Bi id="Cara kerja" en="How it works" /></span>
          <h2 className="mk-h2"><Bi id="Jalan dalam 3 langkah" en="Live in 3 steps" /></h2>
        </div>
        <div className="how-grid reveal">
          <div className="how"><div className="num">01</div><h3><Bi id="Daftar & Connect Channel" en="Sign up & connect channel" /></h3><p><Bi id="Hubungkan channel YouTube-mu lewat tutorial terpandu." en="Connect your YouTube channel via a guided tutorial." /></p><span className="time"><Clock size={13} /> ~1 <Bi id="menit" en="min" /></span></div>
          <div className="how"><div className="num">02</div><h3><Bi id="Input API Keys" en="Add API keys" /></h3><p><Bi id="Masukkan keys AI-mu dengan tutorial step-by-step. Kontrol biaya penuh." en="Add your AI keys with a step-by-step tutorial. Full cost control." /></p><span className="time"><Clock size={13} /> ~5 <Bi id="menit" en="min" /></span></div>
          <div className="how"><div className="num">03</div><h3><Bi id="Mesin Jalan 24/7" en="Engine runs 24/7" /></h3><p><Bi id="Duduk santai. Mesin produksi, publish, dan belajar otomatis." en="Sit back. The engine produces, publishes, and learns automatically." /></p><span className="time"><Zap size={13} /> <Bi id="Otomatis" en="Automatic" /></span></div>
        </div>
      </div></section>

      {/* TESTIMONIALS */}
      <section className="mk-section" style={{ background: "var(--bg-elevated)", borderBlock: "1px solid var(--border-subtle)" }}><div className="mk-container">
        <div className="mk-center reveal" style={{ marginBottom: "2.5rem" }}><h2 className="mk-h2"><Bi id="Dipercaya creator Indonesia" en="Trusted by Indonesian creators" /></h2></div>
        <div className="tst-track reveal">
          {TST.map((t, i) => (
            <div className="tst" key={i}>
              <div className="stars">{Array.from({ length: 5 }).map((_, k) => <Star key={k} size={15} fill="#FBBF24" color="#FBBF24" />)}</div>
              <blockquote>&quot;{t.q}&quot;</blockquote>
              <div className="who"><span className="av" style={{ background: t.c }}>{t.av}</span><div><div className="nm">{t.nm}</div><div className="ch">{t.ch}</div></div><div className="gr"><div className="b">{t.gr}</div><div className="l">{t.gl}</div></div></div>
            </div>
          ))}
        </div>
      </div></section>

      {/* PRICING PREVIEW */}
      <section className="mk-section" id="pricing"><div className="mk-container">
        <div className="mk-center reveal" style={{ marginBottom: "3rem" }}>
          <span className="mk-kicker"><Bi id="Harga" en="Pricing" /></span>
          <h2 className="mk-h2"><Bi id="Pilih paket untuk channelmu" en="Pick a plan for your channel" /></h2>
        </div>
        <div className="price-grid reveal">
          {paidPlans(plans).map((p) => {
            const copy = PREVIEW_COPY[p.plan_type] ?? { ttId: "", ttEn: "", feats: [], pop: false };
            return (
              <div className={`pcard${copy.pop ? " pop" : ""}`} key={p.plan_type}>
                {copy.pop && <span className="pop-badge">Most Popular</span>}
                <div className="pn">{p.display_name}</div><div className="pp">{pk(`plan_${p.plan_type}`, "—")}<small>/bln</small></div><div className="ptag"><Bi id={copy.ttId} en={copy.ttEn} /></div>
                <ul>
                  <li><Check size={15} /> {p.max_channels} channel</li>
                  <li><Check size={15} /> {p.max_videos_per_day} video / <Bi id="hari" en="day" /></li>
                  {p.niche_studio && <li><Check size={15} /> Niche Studio</li>}
                  {copy.feats.map((f, k) => <li key={k}><Check size={15} /> {f}</li>)}
                </ul>
                <a href="/auth?view=signup" className={`btn ${copy.pop ? "btn-default" : "btn-outline"}`} style={{ width: "100%" }}><Bi id={`Pilih ${p.display_name}`} en={`Choose ${p.display_name}`} /></a>
              </div>
            );
          })}
        </div>
        <div className="mk-center" style={{ marginTop: "1.75rem" }}><a href="/pricing" style={{ color: "var(--brand)", textDecoration: "none", fontWeight: 500 }}><Bi id="Lihat semua paket & fitur" en="See all plans & features" /> →</a></div>
      </div></section>

      {/* FAQ */}
      <section className="mk-section" style={{ background: "var(--bg-elevated)", borderTop: "1px solid var(--border-subtle)" }}><div className="mk-container">
        <div className="mk-center reveal" style={{ marginBottom: "2.5rem" }}><h2 className="mk-h2">FAQ</h2></div>
        <div className="faq reveal">
          {makeFaq(trialDays).map(([q, a], i) => (
            <div className={`faq-item${faqOpen === i ? " open" : ""}`} key={i}>
              <div className="faq-q" onClick={() => setFaqOpen(faqOpen === i ? -1 : i)}>{q} <span className="chev"><ChevronDown size={18} /></span></div>
              <div className="faq-a"><p>{a}</p></div>
            </div>
          ))}
        </div>
      </div></section>

      {/* CTA */}
      <section className="mk-section-sm"><div className="mk-container">
        <div className="cta-strip reveal">
          <h2><Bi id="Siap scale channelmu ke 5+ video per hari?" en="Ready to scale to 5+ videos per day?" /></h2>
          <p className="mk-lead mk-center" style={{ marginBottom: "2rem" }}><Bi id="Mulai gratis hari ini. Mesinnya yang kerja, kamu yang menikmati hasilnya." en="Start free today. Let the machine work while you enjoy the results." /></p>
          <a href="/auth?view=signup" className="btn btn-ai btn-xl"><Bi id="Mulai Gratis 7 Hari" en="Start 7-Day Free Trial" /> <ArrowRight size={18} /></a>
          <div className="hero-fine mk-center" style={{ justifyContent: "center", marginTop: "1rem" }}><Bi id="Tanpa kartu kredit" en="No credit card required" /></div>
        </div>
      </div></section>
    </>
  );
}
