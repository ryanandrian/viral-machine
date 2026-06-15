"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Plus, Sparkles, X } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "./schedule.css";

// D7 Schedule (Phase 9.4) — DATA NYATA dari production_schedules (RLS r/w) + channels. cron→jam.
// Toggle is_active (UPDATE RLS) + tambah slot (INSERT, cron "M H * * *"). Banner → link Insights (jujur).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
const DAYS = [["Sen", "Mon"], ["Sel", "Tue"], ["Rab", "Wed"], ["Kam", "Thu"], ["Jum", "Fri"], ["Sab", "Sat"], ["Min", "Sun"]];
const CCOL = ["#6366F1", "#10B981", "#EC4899", "#F59E0B", "#0ea5e9"];

type Sched = { schedule_id: string; channel_id: string; cron_expression: string; niche_id: string | null; niche_focus: string | null; is_active: boolean; content_type: string | null };
type Ch = { id: string; channel_name: string };

function cronTime(expr: string): string {
  const p = (expr || "").trim().split(/\s+/);
  if (p.length < 2) return "—";
  const h = p[1] === "*" ? "0" : p[1].split(",")[0];
  const m = p[0] === "*" ? "0" : p[0].split(",")[0];
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}
function cronDaily(expr: string): boolean { const p = (expr || "").trim().split(/\s+/); return !p[4] || p[4] === "*"; }

export default function SchedulePage() {
  const supabase = createClient();
  const [view, setView] = useState<"week" | "list">("list");
  const [scheds, setScheds] = useState<Sched[]>([]);
  const [channels, setChannels] = useState<Ch[]>([]);
  const [uid, setUid] = useState("");
  const [loading, setLoading] = useState(true);
  const [add, setAdd] = useState<{ channel_id: string; time: string; niche: string } | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [{ data: s }, { data: c }] = await Promise.all([
      supabase.from("production_schedules").select("schedule_id, channel_id, cron_expression, niche_id, niche_focus, is_active, content_type"),
      supabase.from("channels").select("id, channel_name"),
    ]);
    setScheds(s ?? []); setChannels(c ?? []); setLoading(false);
  }, [supabase]);
  useEffect(() => { supabase.auth.getUser().then(({ data }) => setUid(data.user?.id ?? "")); load(); }, [supabase, load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2200); return () => clearTimeout(t); }, [toast]);

  const chName = (id: string) => channels.find((c) => c.id === id)?.channel_name ?? id.slice(0, 6);
  const chColor = (id: string) => CCOL[Math.max(0, channels.findIndex((c) => c.id === id)) % CCOL.length];
  const active = scheds.filter((s) => s.is_active).length;

  async function toggle(s: Sched) {
    const { error } = await supabase.from("production_schedules").update({ is_active: !s.is_active }).eq("schedule_id", s.schedule_id);
    if (!error) { setScheds((arr) => arr.map((x) => x.schedule_id === s.schedule_id ? { ...x, is_active: !x.is_active } : x)); } else setToast("Gagal (RLS)");
  }
  async function addSlot() {
    if (!add?.channel_id || !add.time || !uid) return;
    const [h, m] = add.time.split(":");
    const cron = `${parseInt(m || "0", 10)} ${parseInt(h || "0", 10)} * * *`;
    const { error } = await supabase.from("production_schedules").insert({ tenant_id: uid, channel_id: add.channel_id, cron_expression: cron, niche_id: add.niche || null, is_active: true, content_type: "short" });
    if (!error) { setAdd(null); setToast("Slot ditambah"); await load(); } else setToast(`Gagal: ${error.message}`);
  }

  const Slot = ({ s }: { s: Sched }) => (
    <div className={`slot${s.is_active ? "" : " paused"}`}>
      <div className="st">{cronTime(s.cron_expression)} <label className="switch" style={{ width: "1.75rem", height: "1rem" }} onClick={(e) => e.stopPropagation()}><input type="checkbox" checked={s.is_active} onChange={() => toggle(s)} /><span className="track" /><span className="thumb" style={{ width: "0.75rem", height: "0.75rem" }} /></label></div>
      <div className="sn">{chName(s.channel_id)}</div>
      <div className="sc"><span className="dot-ch" style={{ background: chColor(s.channel_id) }} />{s.niche_id || s.content_type || "auto"} · WIB</div>
    </div>
  );

  return (
    <>
      <div className="page-head">
        <div><h1><Bi id="Jadwal" en="Schedule" /></h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}>{loading ? "Memuat…" : <><b>{active}</b> slot aktif · {channels.length} channel</>}</div></div>
        <button className="btn btn-default" onClick={() => setAdd({ channel_id: channels[0]?.id ?? "", time: "13:00", niche: "" })}><Plus size={16} /> <Bi id="Tambah Slot" en="Add Slot" /></button>
      </div>

      <div className="opt-banner">
        <span className="ic"><Sparkles size={18} /></span>
        <div className="t"><Bi id="Slot optimal dipelajari mesin dari analytics channelmu." en="Optimal slots are learned by the engine from your channel analytics." /></div>
        <Link href="/insights" className="btn btn-secondary btn-sm"><Bi id="Lihat Wawasan" en="See Insights" /></Link>
      </div>

      <div className="toolbar">
        <div className="segmented">
          <button aria-selected={view === "list"} onClick={() => setView("list")}>List</button>
          <button aria-selected={view === "week"} onClick={() => setView("week")}><Bi id="Minggu" en="Week" /></button>
        </div>
      </div>

      {!loading && scheds.length === 0 && <div className="card card-pad muted" style={{ textAlign: "center" }}>Belum ada jadwal. Tambah slot untuk mulai.</div>}

      {view === "list" && scheds.length > 0 && (
        <div>
          {scheds.map((s) => (
            <div className="list-slot" key={s.schedule_id}>
              <div style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{cronTime(s.cron_expression)}<span className="muted" style={{ fontSize: "0.625rem" }}> WIB</span></div>
              <div><div style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>{chName(s.channel_id)}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{s.niche_id || "auto-rotation"} · {cronDaily(s.cron_expression) ? "harian" : "mingguan"}</div></div>
              <span className="badge badge-default" style={{ fontSize: "0.625rem" }}>{s.content_type || "short"}</span>
              <label className="switch" onClick={(e) => e.stopPropagation()}><input type="checkbox" checked={s.is_active} onChange={() => toggle(s)} /><span className="track" /><span className="thumb" /></label>
            </div>
          ))}
        </div>
      )}

      {view === "week" && scheds.length > 0 && (
        <div className="week">
          {DAYS.map(([dn], di) => (
            <div className="day" key={di}>
              <div className="day-h"><div className="dn">{dn}</div></div>
              <div className="day-body">
                {scheds.filter((s) => cronDaily(s.cron_expression)).map((s) => <Slot key={s.schedule_id} s={s} />)}
              </div>
            </div>
          ))}
        </div>
      )}

      {add && (
        <>
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60 }} onClick={() => setAdd(null)} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(420px,92vw)", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}><strong>Tambah slot</strong><button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} onClick={() => setAdd(null)}><X size={16} /></button></div>
            <div style={{ display: "grid", gap: "0.625rem" }}>
              <div><label className="label">Channel</label><select className="input" value={add.channel_id} onChange={(e) => setAdd({ ...add, channel_id: e.target.value })}>{channels.map((c) => <option key={c.id} value={c.id}>{c.channel_name}</option>)}</select></div>
              <div><label className="label">Jam (WIB)</label><input className="input" type="time" value={add.time} onChange={(e) => setAdd({ ...add, time: e.target.value })} /></div>
              <div><label className="label">Niche (opsional)</label><input className="input" placeholder="kosong = auto-rotation" value={add.niche} onChange={(e) => setAdd({ ...add, niche: e.target.value })} /></div>
              <button className="btn btn-primary btn-sm" style={{ justifySelf: "end" }} disabled={!add.channel_id} onClick={addSlot}>Simpan slot</button>
            </div>
          </div>
        </>
      )}

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 70, background: "var(--surface-raised, #1f2937)", color: "var(--text-primary)", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid var(--border)" }}>{toast}</div>}
    </>
  );
}
