"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Tv, Check, Lock, Video } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

// Tambah channel (pasca-onboarding) — form fokus channel (bukan wizard akun). INSERT channels (client-RLS)
// + guard kuota max_channels per tier. Pola sama onboarding increment 1.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

export default function NewChannelPage() {
  const supabase = createClient();
  const router = useRouter();
  const [niches, setNiches] = useState<{ niche_id: string; name: string }[]>([]);
  const [langs, setLangs] = useState<{ locale: string; display_name: string }[]>([]);
  const [count, setCount] = useState<number | null>(null);
  const [maxCh, setMaxCh] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const [name, setName] = useState("");
  const [platform, setPlatform] = useState("youtube");
  const [sel, setSel] = useState<string[]>([]);
  const [nicheMode, setNicheMode] = useState<"fixed" | "random">("fixed");
  const [clang, setClang] = useState("id-ID");
  const [privacy, setPrivacy] = useState("private");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  // [B11] Batch 1.7 — picker channel YouTube tujuan (OPSIONAL di sini; wajibnya ditegakkan checklist kesiapan).
  type YtAcct = { id: string; connected: boolean; yt_channel_id: string | null; yt_channel_title?: string | null; yt_channel_thumb?: string | null; label: string; used_by?: { id: string; channel_name: string }[] };
  const [ytAccounts, setYtAccounts] = useState<YtAcct[]>([]);
  const [ytPick, setYtPick] = useState<YtAcct | null>(null);

  const load = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    const me = user?.id ?? "";
    const [{ data: nq }, { data: lq }, { count: c }, { data: cfg }] = await Promise.all([
      supabase.from("niches").select("niche_id, name, is_base, access_type, exclusive_to").eq("is_active", true).order("niche_id"),
      supabase.from("content_languages").select("locale, display_name").eq("is_active", true).order("sort_order"),
      supabase.from("channels").select("id", { count: "exact", head: true }),
      supabase.from("tenant_configs").select("plan_type").maybeSingle(),
    ]);
    const tier = cfg?.plan_type ?? "starter";
    const { data: pl } = await supabase.from("plan_limits").select("max_channels, full_niche_catalog").eq("plan_type", tier).maybeSingle();
    // Entitlement (SAMA dgn channel-detail): niche custom milik sendiri ATAU publik (full_niche_catalog dari plan_limits — 0124, else hanya is_base).
    const entitled = (nq ?? []).filter((n: { access_type: string; is_base: boolean; exclusive_to: string | null }) =>
      n.exclusive_to === me || (n.access_type === "public" && (Boolean(pl?.full_niche_catalog) || n.is_base)));
    setNiches(entitled.map((n: { niche_id: string; name: string }) => ({ niche_id: n.niche_id, name: n.name })));
    setLangs(lq ?? []); setCount(c ?? 0);
    setMaxCh(pl?.max_channels ?? null);
    if (lq?.[0]) setClang(lq[0].locale);
    // [B11] pool koneksi YouTube (berwajah + used_by) — opsional dipilih saat buat channel.
    try { const r = await fetch("/api/youtube/status"); if (r.ok) { const j = await r.json(); setYtAccounts(j.accounts || []); } } catch { /* non-fatal */ }
    setLoading(false);
  }, [supabase]);
  useEffect(() => { load(); }, [load]);

  const full = count != null && maxCh != null && count >= maxCh;
  // Fixed → single-select (selalu 1). Random → multi-select (2+). Konsisten dgn niche_mode.
  const pickNiche = (id: string) => setSel((s) => nicheMode === "fixed" ? [id] : (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  // Random → auto-pilih SEMUA niche hak tenant (rotasi penuh). Fixed → kosongkan (tenant pilih 1 sendiri).
  const changeMode = (m: "fixed" | "random") => {
    setNicheMode(m);
    setSel(m === "fixed" ? [] : niches.map((n) => n.niche_id));
  };

  async function create() {
    setErr(null);
    if (!name.trim()) return setErr("Nama channel wajib.");
    if (sel.length === 0) return setErr("Pilih minimal 1 niche.");
    if (nicheMode === "random" && sel.length < 2) return setErr("Mode rotasi butuh minimal 2 niche.");
    setBusy(true);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { setBusy(false); return setErr("Sesi tak valid."); }
    // Jam publish awal: app_config.default_publish_slots (0125, admin-editable — no-hardcode); fallback aman.
    let slots: string[] = ["13:00"];
    try {
      const { data: dc } = await supabase.from("app_config").select("value_text").eq("key", "default_publish_slots").maybeSingle();
      const parsed = JSON.parse((dc as { value_text?: string } | null)?.value_text || "");
      if (Array.isArray(parsed) && parsed.length > 0) slots = parsed.map(String);
    } catch { /* fallback ["13:00"] */ }
    const { data, error } = await supabase.from("channels").insert({
      tenant_id: user.id, channel_group: "default", channel_name: name.trim(), platform,
      niche: sel[0], niche_pool: sel, niche_mode: nicheMode,
      content_language: clang, publish_privacy: privacy, publish_slots: slots,
      // [B11] pilihan channel YouTube tujuan (opsional) — ikut tersimpan sejak awal.
      youtube_account_id: ytPick?.id ?? null, platform_channel_id: ytPick?.yt_channel_id ?? null,
      is_active: false,   // F2-01/§10.E.7: channel default NON-AKTIF (draft) → aktif setelah readiness lengkap di Manage.
    }).select("id").single();
    setBusy(false);
    // [B11] pagar DB ux_channels_tenant_target (race): target keburu dipakai channel lain.
    if (error) return setErr(error.message.includes("ux_channels_tenant_target")
      ? "Channel YouTube itu baru saja dipakai channel lain — pilih channel YouTube berbeda. / That YouTube channel was just taken by another channel — pick a different one."
      : error.message);
    router.push(`/channels/${data.id}`);
  }

  if (loading) return <div className="muted" style={{ padding: "3rem", textAlign: "center" }}>Memuat…</div>;

  return (
    <div style={{ maxWidth: 640 }}>
      <button className="btn btn-ghost btn-sm" style={{ marginBottom: ".75rem" }} onClick={() => router.push("/channels")}><ArrowLeft size={14} /> Kanal</button>
      <h1 style={{ fontSize: "1.375rem", marginBottom: ".25rem", display: "flex", alignItems: "center", gap: ".5rem" }}><Tv size={20} /> <Bi id="Tambah Channel" en="Add Channel" /></h1>
      <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1.25rem" }}>{count}/{maxCh ?? "—"} channel terpakai (paket Anda).</p>

      {full ? (
        <div className="card card-pad" style={{ textAlign: "center" }}>
          <Lock size={28} style={{ color: "var(--text-muted)", marginBottom: ".5rem" }} />
          <div style={{ fontWeight: 600, marginBottom: ".25rem" }}><Bi id="Kuota channel penuh" en="Channel quota full" /></div>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Upgrade paket untuk menambah channel." en="Upgrade your plan to add more channels." /></p>
          <a href="/billing" className="btn btn-default btn-sm">Upgrade</a>
        </div>
      ) : (
        <div className="card card-pad" style={{ display: "grid", gap: "1rem" }}>
          <div><label className="label"><Bi id="Nama channel" en="Channel name" /></label><input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="mis. Misteri Samudra" /></div>
          <div><label className="label">Platform</label><div className="radio-row">{["youtube"].map((p) => <span key={p} className={`radio-pill${platform === p ? " sel" : ""}`} onClick={() => setPlatform(p)}>{p}</span>)}<span className="radio-pill" style={{ opacity: .5, cursor: "not-allowed" }} title="Reels/TikTok per tier (segera)">reels/tiktok (segera)</span></div></div>
          <div><label className="label"><Bi id="Mode niche" en="Niche mode" /></label>
            <div className="radio-row">
              <span className={`radio-pill${nicheMode === "fixed" ? " sel" : ""}`} onClick={() => changeMode("fixed")}>{nicheMode === "fixed" && <Check size={12} />} <Bi id="Tetap (1 niche)" en="Fixed (1 niche)" /></span>
              <span className={`radio-pill${nicheMode === "random" ? " sel" : ""}`} onClick={() => changeMode("random")}>{nicheMode === "random" && <Check size={12} />} <Bi id="Rotasi otomatis (random)" en="Auto-rotate (random)" /></span>
            </div>
            <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".375rem" }}>{nicheMode === "random" ? <Bi id="Semua niche hak Anda dipilih & diputar bergiliran (boleh kurangi)." en="All your niches are selected & rotated (you may deselect some)." /> : <Bi id="Channel memakai 1 niche tetap." en="Channel uses one fixed niche." />}</div>
          </div>
          <div><label className="label">{nicheMode === "random" ? <Bi id="Niche (pilih 2+)" en="Niches (pick 2+)" /> : <Bi id="Niche (pilih 1)" en="Niche (pick 1)" />}</label>
            <div className="radio-row">{niches.map((n) => <span key={n.niche_id} className={`radio-pill${sel.includes(n.niche_id) ? " sel" : ""}`} onClick={() => pickNiche(n.niche_id)}>{sel.includes(n.niche_id) && <Check size={12} />} {n.name}</span>)}</div>
          </div>
          {/* [B11] Batch 1.7 — pilih channel YouTube tujuan (OPSIONAL; bisa nanti di Pengaturan Channel).
              Nama+foto = konfirmasi visual; terpakai channel lain = terkunci (cegatan redundant). */}
          {ytAccounts.filter((a) => a.connected).length > 0 && (
            <div><label className="label"><Bi id="Channel YouTube tujuan (opsional — bisa diatur nanti)" en="Target YouTube channel (optional — can set later)" /></label>
              <div style={{ display: "grid", gap: ".4rem" }}>
                {ytAccounts.filter((a) => a.connected).map((a) => {
                  const locked = (a.used_by?.length ?? 0) > 0;
                  const selY = ytPick?.id === a.id;
                  return (
                    <div key={a.id} role="radio" aria-checked={selY} aria-disabled={locked}
                      onClick={() => { if (!locked) setYtPick(selY ? null : a); }}
                      style={{ display: "flex", alignItems: "center", gap: ".6rem", padding: ".45rem .6rem", borderRadius: "var(--r-md)",
                        border: `1px solid ${selY ? "var(--accent)" : "var(--border-subtle)"}`, background: selY ? "var(--accent-soft)" : "transparent",
                        opacity: locked ? .55 : 1, cursor: locked ? "not-allowed" : "pointer" }}>
                      {a.yt_channel_thumb
                        ? <img src={a.yt_channel_thumb} alt="" style={{ width: 28, height: 28, borderRadius: "50%", objectFit: "cover", flex: "none" }} referrerPolicy="no-referrer" />
                        : <span style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--surface-2)", display: "grid", placeItems: "center", color: "var(--text-muted)", flex: "none" }}><Video size={13} /></span>}
                      <span style={{ flex: 1, minWidth: 0, fontSize: "var(--text-sm)", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.yt_channel_title || a.label}</span>
                      {selY ? <span className="badge badge-success" style={{ fontSize: ".625rem" }}><Check size={11} /> <Bi id="Dipilih" en="Selected" /></span>
                        : locked ? <span className="badge badge-default" style={{ fontSize: ".625rem" }}><Lock size={10} /> <Bi id={`Dipakai oleh ${a.used_by![0].channel_name}`} en={`Used by ${a.used_by![0].channel_name}`} /></span>
                        : <span className="badge badge-default" style={{ fontSize: ".625rem" }}><Bi id="Tersedia" en="Available" /></span>}
                    </div>
                  );
                })}
              </div>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".3rem" }}><Bi id="Channel YouTube lain belum ada di daftar? Hubungkan dulu di menu Kredensial." en="YouTube channel not listed? Connect it first in Credentials." /></div>
            </div>
          )}
          <div><label className="label"><Bi id="Bahasa konten" en="Content language" /></label><select className="input" value={clang} onChange={(e) => setClang(e.target.value)}>{langs.map((l) => <option key={l.locale} value={l.locale}>{l.display_name}</option>)}</select></div>
          <div><label className="label">Privacy publish</label><div className="radio-row">{["private", "public"].map((p) => <span key={p} className={`radio-pill${privacy === p ? " sel" : ""}`} onClick={() => setPrivacy(p)}>{p}</span>)}</div><div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".25rem" }}><Bi id="Default private (trial-safe). Ganti ke public saat hasil cocok." en="Default private (trial-safe). Switch to public when satisfied." /></div></div>
          {err && <div style={{ color: "var(--danger)", fontSize: "var(--text-sm)" }}>{err}</div>}
          <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Channel dibuat sebagai DRAFT (non-aktif). Di halaman berikutnya: lengkapi model AI + key (vault), voice, caption — ada checklist kesiapan; aktifkan saat lengkap." en="Created as a DRAFT (inactive). Next page: complete AI models + key (vault), voice, captions — a readiness checklist guides you; activate once complete." /></div>
          <div style={{ display: "flex", gap: ".5rem" }}>
            <button className="btn btn-default" disabled={busy} onClick={create}>{busy ? "Membuat…" : <Bi id="Buat channel" en="Create channel" />}</button>
            <button className="btn btn-secondary" disabled={busy} onClick={() => router.push("/channels")}><Bi id="Batal" en="Cancel" /></button>
          </div>
        </div>
      )}
    </div>
  );
}
