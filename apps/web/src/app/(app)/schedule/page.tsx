"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Plus, Sparkles, X, Clock } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "./schedule.css";

// D7 Schedule — model terkunci §12c: jadwal = JAM PUBLISH per-channel di `channels.publish_slots`
// (zona TENANT). Tulis via RPC set_channel_publish_slots (validasi jumlah ≤ tier max_videos_per_day).
// TIDAK pakai production_schedules (fosil V1) & TIDAK ada niche di sini (niche dikelola di Channel Detail).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
const CCOL = ["#6366F1", "#10B981", "#EC4899", "#F59E0B", "#0ea5e9"];

type Ch = { id: string; channel_name: string; publish_slots: string[] | null };

function norm(t: string): string { const [h, m] = (t || "").split(":"); return `${String(+h || 0).padStart(2, "0")}:${String(+m || 0).padStart(2, "0")}`; }

export default function SchedulePage() {
  const supabase = createClient();
  const [channels, setChannels] = useState<Ch[]>([]);
  const [cap, setCap] = useState(1);          // max video/hari per channel (tier)
  const [tz, setTz] = useState("UTC");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [add, setAdd] = useState<{ channel_id: string; time: string } | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [{ data: c }, { data: cfg }] = await Promise.all([
      supabase.from("channels").select("id, channel_name, publish_slots").order("created_at"),
      supabase.from("tenant_configs").select("plan_type, timezone").maybeSingle(),
    ]);
    setChannels(c ?? []);
    const tier = (cfg as { plan_type?: string; timezone?: string } | null)?.plan_type ?? "starter";
    setTz((cfg as { timezone?: string } | null)?.timezone ?? "UTC");
    const { data: pl } = await supabase.from("plan_limits").select("max_videos_per_day").eq("plan_type", tier).maybeSingle();
    setCap((pl as { max_videos_per_day?: number } | null)?.max_videos_per_day ?? 1);
    setLoading(false);
  }, [supabase]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2600); return () => clearTimeout(t); }, [toast]);

  const chColor = (id: string) => CCOL[Math.max(0, channels.findIndex((c) => c.id === id)) % CCOL.length];

  async function saveSlots(channel_id: string, slots: string[]) {
    setBusy(channel_id);
    const sorted = Array.from(new Set(slots.map(norm))).sort();
    const { error } = await supabase.rpc("set_channel_publish_slots", { p_channel_id: channel_id, p_slots: sorted });
    setBusy("");
    if (error) { setToast(error.message.includes("melebihi") ? `Melebihi batas tier (${cap}/hari)` : `Gagal: ${error.message}`); return false; }
    setChannels((arr) => arr.map((c) => c.id === channel_id ? { ...c, publish_slots: sorted } : c));
    return true;
  }
  async function addSlot() {
    if (!add?.channel_id || !add.time) return;
    const ch = channels.find((c) => c.id === add.channel_id); if (!ch) return;
    const cur = ch.publish_slots ?? [];
    if (cur.length >= cap) { setToast(`Channel ini sudah ${cap}/${cap} slot (batas tier)`); return; }
    if (await saveSlots(add.channel_id, [...cur, add.time])) { setAdd(null); setToast("Jadwal disimpan"); }
  }
  async function removeSlot(channel_id: string, time: string) {
    const ch = channels.find((c) => c.id === channel_id); if (!ch) return;
    await saveSlots(channel_id, (ch.publish_slots ?? []).filter((t) => t !== time));
  }

  const totalSlots = channels.reduce((n, c) => n + (c.publish_slots?.length ?? 0), 0);

  return (
    <>
      <div className="page-head">
        <div><h1><Bi id="Jadwal" en="Schedule" /></h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}>{loading ? "Memuat…" : <><b>{totalSlots}</b> slot · {channels.length} channel · max <b>{cap}</b>/hari/channel (tier)</>}</div></div>
      </div>

      <div className="opt-banner">
        <span className="ic"><Sparkles size={18} /></span>
        <div className="t"><Bi id="Jadwal = JAM PUBLISH per channel (zona waktu Anda). Produksi dijaga otomatis di buffer; video terbit saat slot tiba." en="Schedule = PUBLISH times per channel (your timezone). Production is auto-buffered; videos go live at each slot." /></div>
        <Link href="/insights" className="btn btn-secondary btn-sm"><Bi id="Lihat Wawasan" en="See Insights" /></Link>
      </div>

      {!loading && channels.length === 0 && <div className="card card-pad muted" style={{ textAlign: "center" }}><Bi id="Belum ada channel. Buat channel dulu." en="No channel yet. Create a channel first." /> <Link href="/channels/new" className="link">+ Channel</Link></div>}

      <div style={{ display: "grid", gap: "1rem" }}>
        {channels.map((c) => {
          const slots = (c.publish_slots ?? []).map(norm).sort();
          const full = slots.length >= cap;
          return (
            <div className="card card-pad" key={c.id}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.75rem" }}>
                <span className="dot-ch" style={{ background: chColor(c.id), width: 10, height: 10, borderRadius: "50%" }} />
                <b style={{ color: "var(--text-primary)" }}>{c.channel_name}</b>
                <span className="muted" style={{ fontSize: "var(--text-xs)", marginLeft: "auto" }}>{slots.length}/{cap} slot/hari · {tz}</span>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
                {slots.length === 0 && <span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Belum ada jam tayang." en="No publish time yet." /></span>}
                {slots.map((t) => (
                  <span key={t} className="badge" style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)", padding: "0.3rem 0.5rem" }}>
                    <Clock size={13} /> {t}
                    <button className="btn btn-ghost btn-icon" style={{ width: 18, height: 18 }} disabled={busy === c.id} onClick={() => removeSlot(c.id, t)} title="Hapus"><X size={12} /></button>
                  </span>
                ))}
                <button className="btn btn-secondary btn-sm" disabled={full || busy === c.id} title={full ? `Batas tier ${cap}/hari` : ""} onClick={() => setAdd({ channel_id: c.id, time: "13:00" })}><Plus size={14} /> <Bi id="Jam" en="Time" /></button>
              </div>
            </div>
          );
        })}
      </div>

      {add && (
        <>
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60 }} onClick={() => setAdd(null)} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(380px,92vw)", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}><strong><Bi id="Tambah jam publish" en="Add publish time" /></strong><button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} onClick={() => setAdd(null)}><X size={16} /></button></div>
            <div style={{ display: "grid", gap: "0.625rem" }}>
              <div><label className="label"><Bi id="Jam" en="Time" /> ({tz})</label><input className="input" type="time" value={add.time} onChange={(e) => setAdd({ ...add, time: e.target.value })} /></div>
              <p className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Bidik audiens lokal? Pakai jam Anda. Bidik luar negeri? Geser jam-nya sesuai zona target." en="Targeting local audience? Use your time. Targeting abroad? Offset the time to the target zone." /></p>
              <button className="btn btn-primary btn-sm" style={{ justifySelf: "end" }} disabled={busy !== ""} onClick={addSlot}><Bi id="Simpan" en="Save" /></button>
            </div>
          </div>
        </>
      )}

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 70, background: "var(--surface-raised, #1f2937)", color: "var(--text-primary)", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid var(--border)" }}>{toast}</div>}
    </>
  );
}
