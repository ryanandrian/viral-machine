"use client";

import { useState, useEffect, useCallback } from "react";
import { FlaskConical, CheckCircle, XCircle, KeyRound, Loader2, Trash2, Settings2 } from "lucide-react";

// Test Lab (dirombak 2026-07-04, keputusan owner) — fasilitas uji-produksi niche ADMIN:
// 1) Kredensial AI channel test → vault POOL yang sama dgn tenant (validasi NYATA ke penyedia saat simpan).
// 2) Pilihan penyedia + model + voice per elemen = LENGKAP dari katalog DB (nol hardcode).
// 3) TANPA YouTube — test niche TIDAK pernah publish (video → S3, ditonton di drawer Pustaka Niche).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type Provider = { provider_key: string; display_name: string; key_group: string; auth_type: string };
type Model = { model_key: string; provider_key: string; component: string; display_name: string | null };
type Voice = { voice_key: string; provider_key: string; display_name: string | null };
type Account = { id: string; key_group: string; label: string | null; status: string; validated_at: string | null };
type Channel = { id: string; channel_name: string; llm_library: string | null; llm_model: string | null; tts_provider: string | null; tts_model: string | null; voice_key: string | null; visual_mode: string | null };
type Res = { ok: boolean; msg: string };

export default function TestLabPage() {
  const [channel, setChannel] = useState<Channel | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cfg, setCfg] = useState<Record<string, string>>({});
  const [newKey, setNewKey] = useState<{ vendor: string; key: string }>({ vendor: "", key: "" });
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, Res> | null>(null);
  const [ready, setReady] = useState<boolean | null>(null);

  const load = useCallback(async () => {
    const r = await fetch("/api/admin/test-lab");
    if (!r.ok) return;
    const j = await r.json();
    setChannel(j.channel); setProviders(j.catalog.providers); setModels(j.catalog.models);
    setVoices(j.catalog.voices); setAccounts(j.accounts);
    if (j.channel) setCfg({
      llm_library: j.channel.llm_library ?? "", llm_model: j.channel.llm_model ?? "",
      tts_provider: j.channel.tts_provider ?? "", tts_model: j.channel.tts_model ?? "",
      voice_key: j.channel.voice_key ?? "", visual_mode: j.channel.visual_mode ?? "",
    });
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!msg) return; const t = setTimeout(() => setMsg(null), 3200); return () => clearTimeout(t); }, [msg]);

  // Vendor ber-kunci yang relevan (auth_type≠none) — dari katalog, unik per key_group.
  const vendors = [...new Map(providers.filter((p) => p.auth_type !== "none").map((p) => [p.key_group, p])).values()];
  const accountsOf = (kg: string) => accounts.filter((a) => a.key_group === kg);

  async function saveKey() {
    if (!newKey.vendor || !newKey.key.trim()) return;
    setBusy(true);
    const r = await fetch("/api/admin/test-lab/credentials", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider_key: newKey.vendor, key: newKey.key.trim(), label: "Test Lab" }) });
    const j = await r.json().catch(() => ({}));
    setBusy(false);
    if (r.ok) { setMsg(j.status === "valid" ? "✅ Kunci VALID (diverifikasi ke penyedia)" : `⚠️ Kunci tersimpan tapi status: ${j.status}`); setNewKey({ vendor: "", key: "" }); await load(); }
    else setMsg(`Gagal: ${j.error ?? r.status}`);
  }
  async function delKey(account_id: string) {
    setBusy(true);
    const r = await fetch("/api/admin/test-lab/credentials", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ account_id }) });
    setBusy(false);
    if (r.ok) { setMsg("Kunci dihapus"); await load(); } else setMsg("Gagal hapus");
  }
  async function saveCfg() {
    setBusy(true);
    const r = await fetch("/api/admin/test-lab", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cfg) });
    const j = await r.json().catch(() => ({}));
    setBusy(false);
    if (r.ok) { setMsg("Konfigurasi channel test tersimpan"); await load(); } else setMsg(`Gagal: ${j.error ?? r.status}`);
  }
  async function checkReadiness() {
    setChecking(true); setResult(null); setReady(null);
    const r = await fetch("/api/admin/test-lab/test", { method: "POST" });
    setChecking(false);
    if (r.ok) { const j = await r.json(); setResult(j.result); setReady(j.ready); } else setMsg("Gagal cek kesiapan");
  }

  const upd = (k: string, v: string) => setCfg((c) => ({ ...c, [k]: v }));
  const modelsFor = (component: string, provider: string) => models.filter((m) => m.component === component && m.provider_key === provider);
  const providersFor = (component: string) => [...new Set(models.filter((m) => m.component === component).map((m) => m.provider_key))];
  const visualModels = models.filter((m) => m.component === "image" || m.component === "video");

  const StatusRow = ({ k, label }: { k: string; label: string }) => {
    const res = result?.[k];
    return (
      <div style={{ display: "flex", alignItems: "center", gap: ".75rem", padding: ".5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
        <span style={{ width: 110, fontSize: "var(--text-sm)" }}>{label}</span>
        {res ? <span style={{ marginLeft: "auto", display: "inline-flex", alignItems: "center", gap: ".35rem", fontSize: "var(--text-xs)", color: res.ok ? "var(--success)" : "var(--danger)" }}>{res.ok ? <CheckCircle size={14} /> : <XCircle size={14} />} {res.msg}</span>
          : <span className="muted" style={{ marginLeft: "auto", fontSize: "var(--text-xs)" }}>—</span>}
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 680 }}>
      <h1 style={{ fontSize: "1.375rem", marginBottom: ".25rem", display: "flex", alignItems: "center", gap: ".5rem" }}><FlaskConical size={22} /> Test Lab</h1>
      <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1.25rem" }}>
        <Bi id="Fasilitas uji-produksi niche (channel internal, TANPA publish ke YouTube). Channel: " en="Niche test-production facility (internal channel, NO YouTube publish). Channel: " />
        <b>{channel?.channel_name ?? "—"}</b>
      </p>

      <div className="card card-pad" style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: ".5rem", marginBottom: ".875rem" }}><KeyRound size={17} /><strong><Bi id="Kunci AI (per vendor — divalidasi NYATA saat simpan)" en="AI keys (per vendor — validated for real on save)" /></strong></div>
        {vendors.map((v) => (
          <div key={v.key_group} style={{ padding: ".5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: ".6rem" }}>
              <span style={{ width: 110, fontSize: "var(--text-sm)", textTransform: "capitalize" }}>{v.key_group}</span>
              {accountsOf(v.key_group).length === 0 ? <span className="badge badge-default" style={{ fontSize: "0.625rem" }}>kosong</span> :
                accountsOf(v.key_group).map((a) => (
                  <span key={a.id} style={{ display: "inline-flex", alignItems: "center", gap: ".3rem" }}>
                    <span className={`badge ${a.status === "valid" ? "badge-success" : a.status === "invalid" ? "badge-error" : "badge-warning"}`} style={{ fontSize: "0.625rem" }}>{a.status}</span>
                    <button className="btn btn-ghost btn-icon btn-sm" title="Hapus kunci" disabled={busy} onClick={() => delKey(a.id)}><Trash2 size={12} /></button>
                  </span>
                ))}
            </div>
          </div>
        ))}
        <div style={{ display: "flex", gap: ".5rem", marginTop: ".875rem", alignItems: "end", flexWrap: "wrap" }}>
          <div><label className="label"><Bi id="Vendor" en="Vendor" /></label><select className="input" value={newKey.vendor} onChange={(e) => setNewKey({ ...newKey, vendor: e.target.value })}><option value="">— pilih —</option>{vendors.map((v) => <option key={v.key_group} value={v.key_group}>{v.key_group}</option>)}</select></div>
          <div style={{ flex: 1, minWidth: 220 }}><label className="label">API key</label><input className="input input-mono" type="text" placeholder="Tempel API key" value={newKey.key} onChange={(e) => setNewKey({ ...newKey, key: e.target.value })} /></div>
          <button className="btn btn-default btn-sm" disabled={busy || !newKey.vendor || !newKey.key.trim()} onClick={saveKey}>{busy ? "…" : <Bi id="Simpan + validasi" en="Save + validate" />}</button>
        </div>
      </div>

      <div className="card card-pad" style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: ".5rem", marginBottom: ".875rem" }}><Settings2 size={17} /><strong><Bi id="Konfigurasi channel test (per elemen — katalog DB)" en="Test channel config (per element — DB catalog)" /></strong></div>
        <div style={{ display: "grid", gap: ".75rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: ".75rem" }}>
            <div><label className="label"><Bi id="Penulis Naskah (LLM) — penyedia" en="Script writer (LLM) — provider" /></label>
              <select className="input" value={cfg.llm_library ?? ""} onChange={(e) => { upd("llm_library", e.target.value); upd("llm_model", ""); }}><option value="">— pilih —</option>{providersFor("llm").map((p) => <option key={p} value={p}>{p}</option>)}</select></div>
            <div><label className="label">Model</label>
              <select className="input" value={cfg.llm_model ?? ""} onChange={(e) => upd("llm_model", e.target.value)}><option value="">— pilih —</option>{modelsFor("llm", cfg.llm_library ?? "").map((m) => <option key={m.model_key} value={m.model_key}>{m.display_name || m.model_key}</option>)}</select></div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: ".75rem" }}>
            <div><label className="label"><Bi id="Pengisi Suara (TTS) — penyedia" en="Voice (TTS) — provider" /></label>
              <select className="input" value={cfg.tts_provider ?? ""} onChange={(e) => { upd("tts_provider", e.target.value); upd("tts_model", ""); upd("voice_key", ""); }}><option value="">— pilih —</option>{providersFor("tts").map((p) => <option key={p} value={p}>{p}</option>)}</select></div>
            <div><label className="label">Model</label>
              <select className="input" value={cfg.tts_model ?? ""} onChange={(e) => upd("tts_model", e.target.value)}><option value="">— pilih —</option>{modelsFor("tts", cfg.tts_provider ?? "").map((m) => <option key={m.model_key} value={m.model_key}>{m.display_name || m.model_key}</option>)}</select></div>
            <div><label className="label">Voice</label>
              <select className="input" value={cfg.voice_key ?? ""} onChange={(e) => upd("voice_key", e.target.value)}><option value="">— pilih —</option>{voices.filter((v) => !cfg.tts_provider || v.provider_key === cfg.tts_provider).map((v) => <option key={v.voice_key} value={v.voice_key}>{v.display_name || v.voice_key}</option>)}</select></div>
          </div>
          <div><label className="label"><Bi id="Pembuat Visual — model (gambar/video)" en="Visual generator — model (image/video)" /></label>
            <select className="input" value={cfg.visual_mode ?? ""} onChange={(e) => upd("visual_mode", e.target.value)}><option value="">— pilih —</option>{visualModels.map((m) => { const vm = `${m.component === "video" ? "ai_video" : "ai_image"}:${m.model_key}`; return <option key={vm} value={vm}>{(m.display_name || m.model_key)} ({m.provider_key})</option>; })}</select></div>
          <div style={{ display: "flex", alignItems: "center", gap: ".75rem" }}>
            <button className="btn btn-default btn-sm" disabled={busy} onClick={saveCfg}>{busy ? "Menyimpan…" : <Bi id="Simpan konfigurasi" en="Save config" />}</button>
            {msg && <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{msg}</span>}
          </div>
        </div>
      </div>

      <div className="card card-pad">
        <div style={{ display: "flex", alignItems: "center", marginBottom: ".75rem" }}>
          <strong><Bi id="Kesiapan test" en="Test readiness" /></strong>
          <button className="btn btn-primary btn-sm" style={{ marginLeft: "auto" }} disabled={checking} onClick={checkReadiness}>{checking ? <><Loader2 size={14} className="spin" /> Memeriksa…</> : <Bi id="Cek kesiapan" en="Check readiness" />}</button>
        </div>
        <StatusRow k="llm" label="LLM" />
        <StatusRow k="tts" label="TTS + Voice" />
        <StatusRow k="visual" label="Visual" />
        {ready != null && <div style={{ marginTop: ".875rem", padding: ".625rem .875rem", borderRadius: "var(--r-md)", background: ready ? "var(--success-soft)" : "var(--warning-soft)", color: ready ? "var(--success)" : "var(--warning)", fontSize: "var(--text-sm)", fontWeight: 600 }}>{ready ? <Bi id="✅ Siap — jalankan test dari Pustaka Niche → detail niche → Test niche" en="✅ Ready — run tests from Niche Library → niche detail → Test niche" /> : <Bi id="⚠️ Lengkapi elemen yang merah dulu" en="⚠️ Fix the failing elements first" />}</div>}
      </div>
    </div>
  );
}
