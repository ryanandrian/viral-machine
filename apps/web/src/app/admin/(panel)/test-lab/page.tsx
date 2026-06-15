"use client";

import { useState, useEffect, useCallback } from "react";
import { FlaskConical, CheckCircle, XCircle, KeyRound, Loader2 } from "lucide-react";

// Test Lab (admin) — isi SELURUH kredensial channel internal "admin_test" untuk test produksi niche,
// + "Test semua kredensial" (validasi NYATA ke provider). Channel ini direct-only (is_active=false).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
type Res = { ok: boolean; msg: string };

export default function TestLabPage() {
  const [llmLib, setLlmLib] = useState("openai");
  const [llmKey, setLlmKey] = useState(""); const [visualKey, setVisualKey] = useState(""); const [ttsKey, setTtsKey] = useState("");
  const [has, setHas] = useState<Record<string, boolean>>({});
  const [channel, setChannel] = useState<{ id: string | null; name: string | null }>({ id: null, name: null });
  const [busy, setBusy] = useState(false); const [testing, setTesting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, Res> | null>(null);
  const [ready, setReady] = useState<boolean | null>(null);

  const load = useCallback(async () => {
    const r = await fetch("/api/admin/test-lab");
    if (r.ok) { const j = await r.json(); setLlmLib(j.llm_library); setHas(j.has); setChannel({ id: j.channel_id, name: j.channel_name }); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function save() {
    setBusy(true); setMsg(null);
    const body: Record<string, string> = { llm_library: llmLib };
    if (llmKey.trim()) body.llm_api_key = llmKey.trim();
    if (visualKey.trim()) body.visual_api_key = visualKey.trim();
    if (ttsKey.trim()) body.tts_api_key = ttsKey.trim();
    const r = await fetch("/api/admin/test-lab", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    setBusy(false);
    if (r.ok) { setMsg("Kredensial tersimpan (terenkripsi di transport, tak di-log)"); setLlmKey(""); setVisualKey(""); setTtsKey(""); await load(); }
    else setMsg("Gagal menyimpan");
  }
  async function testAll() {
    setTesting(true); setResult(null); setReady(null);
    const r = await fetch("/api/admin/test-lab/test", { method: "POST" });
    setTesting(false);
    if (r.ok) { const j = await r.json(); setResult(j.result); setReady(j.ready); } else setMsg("Gagal test");
  }

  const ph = (set: boolean) => set ? "•••••••• (tersimpan — isi untuk ganti)" : "Tempel API key";
  const Row = ({ k, label }: { k: string; label: string }) => {
    const res = result?.[k];
    return (
      <div style={{ display: "flex", alignItems: "center", gap: ".75rem", padding: ".5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
        <span style={{ width: 110, fontSize: "var(--text-sm)" }}>{label}</span>
        <span className={`badge ${has[k] ? "badge-success" : "badge-default"}`} style={{ fontSize: "0.625rem" }}>{has[k] ? "tersimpan" : "kosong"}</span>
        {res && <span style={{ marginLeft: "auto", display: "inline-flex", alignItems: "center", gap: ".35rem", fontSize: "var(--text-xs)", color: res.ok ? "var(--success)" : "var(--danger)" }}>{res.ok ? <CheckCircle size={14} /> : <XCircle size={14} />} {res.msg}</span>}
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 640 }}>
      <h1 style={{ fontSize: "1.375rem", marginBottom: ".25rem", display: "flex", alignItems: "center", gap: ".5rem" }}><FlaskConical size={22} /> Test Lab</h1>
      <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1.25rem" }}>
        <Bi id="Kredensial channel internal untuk uji-produksi niche. Channel: " en="Internal channel credentials for niche test-production. Channel: " />
        <b>{channel.name ?? "—"}</b> <span className="muted">(direct-only)</span>
      </p>

      <div className="card card-pad" style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: ".5rem", marginBottom: ".875rem" }}><KeyRound size={17} /><strong>Kredensial AI (BYOK)</strong></div>
        <div style={{ display: "grid", gap: ".75rem" }}>
          <div><label className="label">LLM library</label><div className="radio-row">{["openai", "anthropic"].map((o) => <span key={o} className={`radio-pill${llmLib === o ? " sel" : ""}`} onClick={() => setLlmLib(o)} style={{ textTransform: "capitalize" }}>{o}</span>)}</div></div>
          <div><label className="label">LLM API key</label><input className="input input-mono" type="password" placeholder={ph(!!has.llm)} value={llmKey} onChange={(e) => setLlmKey(e.target.value)} /></div>
          <div><label className="label">Visual API key (OpenAI image)</label><input className="input input-mono" type="password" placeholder={ph(!!has.visual)} value={visualKey} onChange={(e) => setVisualKey(e.target.value)} /></div>
          <div><label className="label">TTS API key (ElevenLabs)</label><input className="input input-mono" type="password" placeholder={ph(!!has.tts)} value={ttsKey} onChange={(e) => setTtsKey(e.target.value)} /></div>
          <div style={{ display: "flex", alignItems: "center", gap: ".75rem" }}><button className="btn btn-default btn-sm" disabled={busy} onClick={save}>{busy ? "Menyimpan…" : <Bi id="Simpan kredensial" en="Save credentials" />}</button>{msg && <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{msg}</span>}</div>
        </div>
      </div>

      <div className="card card-pad">
        <div style={{ display: "flex", alignItems: "center", marginBottom: ".75rem" }}>
          <strong><Bi id="Test semua kredensial" en="Test all credentials" /></strong>
          <button className="btn btn-primary btn-sm" style={{ marginLeft: "auto" }} disabled={testing} onClick={testAll}>{testing ? <><Loader2 size={14} className="spin" /> Menguji…</> : <Bi id="Jalankan test" en="Run test" />}</button>
        </div>
        <Row k="llm" label="LLM" />
        <Row k="visual" label="Visual" />
        <Row k="tts" label="TTS" />
        <Row k="youtube" label="YouTube" />
        {ready != null && <div style={{ marginTop: ".875rem", padding: ".625rem .875rem", borderRadius: "var(--r-md)", background: ready ? "var(--success-soft)" : "var(--warning-soft)", color: ready ? "var(--success)" : "var(--warning)", fontSize: "var(--text-sm)", fontWeight: 600 }}>{ready ? <Bi id="✅ Siap untuk test produksi niche" en="✅ Ready for niche test-production" /> : <Bi id="⚠️ Lengkapi kredensial yang gagal sebelum test niche" en="⚠️ Fix failing credentials before testing niches" />}</div>}
      </div>
    </div>
  );
}
