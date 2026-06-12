"use client";

import { useState } from "react";
import { Plus, Sparkles, X, Copy, Settings, Pause } from "lucide-react";
import "./schedule.css";

// D7 Schedule (PoC) — port dari design-source/Schedule.html. View week/month/list. Mock deterministik.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const CH: Record<string, { n: string; c: string }> = {
  ms: { n: "Misteri Samudra", c: "#6366F1" }, fb: { n: "Fakta Menarik", c: "#10B981" }, js: { n: "Sejarah Kelam", c: "#EC4899" },
};
const DAYS: [string, string][] = [["Sen", "9"], ["Sel", "10"], ["Rab", "11"], ["Kam", "12"], ["Jum", "13"], ["Sab", "14"], ["Min", "15"]];
const SLOTS = [{ t: "10:00", ch: "ms", ct: "short" }, { t: "14:00", ch: "fb", ct: "short" }, { t: "19:00", ch: "js", ct: "short" }];

function Switch({ checked }: { checked: boolean }) {
  return (
    <label className="switch" onClick={(e) => e.stopPropagation()}>
      <input type="checkbox" defaultChecked={checked} /><span className="track" /><span className="thumb" />
    </label>
  );
}

function Slot({ s, paused }: { s: typeof SLOTS[number]; paused: boolean }) {
  const c = CH[s.ch];
  return (
    <div className={`slot${paused ? " paused" : ""}`}>
      <div className="st">{s.t} <label className="switch" style={{ width: "1.75rem", height: "1rem" }} onClick={(e) => e.stopPropagation()}>
        <input type="checkbox" defaultChecked={!paused} /><span className="track" /><span className="thumb" style={{ width: "0.75rem", height: "0.75rem" }} /></label></div>
      <div className="sn">{c.n}</div>
      <div className="sc"><span className="dot-ch" style={{ background: c.c }} />{s.ct} · WIB</div>
    </div>
  );
}

type View = "week" | "month" | "list";

export default function SchedulePage() {
  const [view, setView] = useState<View>("week");

  return (
    <>
      <div className="page-head">
        <div>
          <h1><Bi id="Jadwal" en="Schedule" /></h1>
          <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="21 slot aktif / minggu · 3 channel" en="21 active slots / week · 3 channels" /></div>
        </div>
        <button className="btn btn-default"><Plus size={16} /> <Bi id="Tambah Slot" en="Add Slot" /></button>
      </div>

      <div className="opt-banner">
        <span className="ic"><Sparkles size={18} /></span>
        <div className="t"><span data-id>Mesin mendeteksi slot <b>14:00 WIB</b> punya engagement <b>30% lebih tinggi</b>. Tambah slot di jam ini?</span><span data-en>Engine detected the <b>14:00 WIB</b> slot has <b>30% higher</b> engagement. Add a slot here?</span></div>
        <button className="btn btn-secondary btn-sm"><Bi id="Terapkan" en="Apply" /></button>
        <button className="btn btn-ghost btn-icon btn-sm"><X size={14} /></button>
      </div>

      <div className="toolbar">
        <div className="segmented">
          <button aria-selected={view === "week"} onClick={() => setView("week")}><Bi id="Minggu" en="Week" /></button>
          <button aria-selected={view === "month"} onClick={() => setView("month")}><Bi id="Bulan" en="Month" /></button>
          <button aria-selected={view === "list"} onClick={() => setView("list")}>List</button>
        </div>
        <div className="right">
          <button className="btn btn-ghost btn-sm"><Copy size={14} /> <Bi id="Template" en="Template" /></button>
          <button className="btn btn-ghost btn-sm"><Settings size={14} /> <Bi id="Bulk edit" en="Bulk edit" /></button>
          <button className="btn btn-secondary btn-sm"><Pause size={14} /> <Bi id="Jeda semua" en="Pause all" /></button>
        </div>
      </div>

      {/* WEEK */}
      {view === "week" && (
        <div className="week">
          {DAYS.map(([dn, dd], di) => (
            <div className="day" key={di}>
              <div className={`day-h${di === 1 ? " today" : ""}`}><div className="dn">{dn}</div><div className="dd">{dd} Jun</div></div>
              <div className="day-body">
                {SLOTS.map((s, si) => <Slot key={si} s={s} paused={di === 5 && si === 2} />)}
                <button className="add-slot"><Plus size={12} /> Slot</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* MONTH */}
      {view === "month" && (
        <div className="card card-pad">
          <div className="mhead">{["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"].map((d) => <span key={d}>{d}</span>)}</div>
          <div className="month">
            {Array.from({ length: 35 }).map((_, i) => {
              const day = i - 2; const cur = day >= 1 && day <= 30;
              const pips = cur ? ["#6366F1", "#10B981", "#EC4899"].slice(0, (day % 3) + 1) : [];
              return (
                <div className={`mcell${cur ? " cur" : ""}`} key={i}>
                  <span className="mn">{cur ? day : ""}</span>
                  <div className="pips">{pips.map((c, k) => <span className="pip" key={k} style={{ background: c }} />)}</div>
                </div>
              );
            })}
          </div>
          <div style={{ display: "flex", gap: "1.25rem", marginTop: "1rem", fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>
            {Object.values(CH).map((c) => (
              <span key={c.n} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><span style={{ width: 8, height: 8, borderRadius: "50%", background: c.c }} />{c.n}</span>
            ))}
          </div>
        </div>
      )}

      {/* LIST */}
      {view === "list" && (
        <div>
          {DAYS.slice(0, 4).map(([dn, dd], di) => (
            <div className="list-day" key={di}>
              <h4>{dn}, {dd} Juni 2026</h4>
              {SLOTS.map((s, si) => {
                const c = CH[s.ch];
                return (
                  <div className="list-slot" key={si}>
                    <div style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{s.t}<span className="muted" style={{ fontSize: "0.625rem" }}> WIB</span></div>
                    <div><div style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>{c.n}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{s.ct}</div></div>
                    <span className="badge badge-default" style={{ fontSize: "0.625rem" }}>auto-rotation</span>
                    <Switch checked />
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
