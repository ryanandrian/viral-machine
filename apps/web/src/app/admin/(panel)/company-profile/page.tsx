"use client";

import { useState, useEffect, useCallback } from "react";
import { Building2, Save } from "lucide-react";

// Company Profile (admin) — data perusahaan penerbit (dipakai di invoice) + Telegram ID admin (notifikasi tenant).
// Reuse design-system (.card/.card-head/.label/.input/.btn). Single-row via /api/admin/company-profile.
// TERPISAH dari System Configuration (app_config) — nol dampak ke setelan mesin yang vital.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Profile = Record<string, string | null>;
const G_ID = { id: "Identitas Perusahaan", en: "Company Identity" };
const G_CONTACT = { id: "Kontak", en: "Contact" };
const G_LEGAL = { id: "Legal & Pajak", en: "Legal & Tax" };
const G_NOTIF = { id: "Notifikasi Admin", en: "Admin Notifications" };
const GROUPS = [G_ID, G_CONTACT, G_LEGAL, G_NOTIF];

type Field = { key: string; id: string; en: string; group: { id: string; en: string }; area?: boolean; hintId?: string; hintEn?: string };
const FIELDS: Field[] = [
  { key: "legal_name", id: "Nama Legal (PT)", en: "Legal Name", group: G_ID },
  { key: "brand", id: "Merek / Brand", en: "Brand", group: G_ID },
  { key: "tagline", id: "Tagline", en: "Tagline", group: G_ID },
  { key: "website", id: "Website", en: "Website", group: G_ID },
  { key: "email", id: "Email", en: "Email", group: G_CONTACT },
  { key: "phone", id: "Telepon", en: "Phone", group: G_CONTACT },
  { key: "address", id: "Alamat", en: "Address", group: G_CONTACT, area: true },
  { key: "npwp", id: "NPWP", en: "Tax ID (NPWP)", group: G_LEGAL },
  { key: "nib", id: "NIB", en: "Business Reg. (NIB)", group: G_LEGAL },
  { key: "sk_menkum", id: "SK Menkumham", en: "Ministry Decree (SK)", group: G_LEGAL },
  { key: "business_scope", id: "Bidang Usaha", en: "Business Scope", group: G_LEGAL, area: true },
  {
    key: "admin_telegram_chat_id", id: "Telegram ID Admin", en: "Admin Telegram ID", group: G_NOTIF,
    hintId: "Chat ID Telegram yang menerima notifikasi tenant (mis. lead panas). Kosongkan untuk mematikan.",
    hintEn: "Telegram chat ID that receives tenant notifications (e.g. hot leads). Leave empty to disable.",
  },
];

export default function CompanyProfilePage() {
  const [form, setForm] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const r = await fetch("/api/admin/company-profile");
    const j = await r.json().catch(() => ({ profile: null }));
    setForm(j.profile ?? {});
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2600); return () => clearTimeout(t); }, [toast]);

  function set(k: string, v: string) { setForm((f) => ({ ...(f ?? {}), [k]: v })); }

  async function save() {
    if (!form) return;
    setSaving(true);
    const body: Record<string, string> = {};
    for (const f of FIELDS) body[f.key] = (form[f.key] ?? "") as string;
    const r = await fetch("/api/admin/company-profile", {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    setSaving(false);
    if (r.ok) { setToast("✓ Tersimpan"); await load(); } else setToast("Gagal menyimpan");
  }

  return (
    <>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 0.375rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Building2 size={20} /> <Bi id="Profil Perusahaan" en="Company Profile" />
        </h1>
        <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0, maxWidth: "65ch" }}>
          <Bi id="Data perusahaan penerbit — tampil di invoice & dokumen. Termasuk Telegram ID admin untuk notifikasi tenant." en="Issuer company data — shown on invoices & documents. Includes the admin Telegram ID for tenant notifications." />
        </p>
      </div>

      {loading ? (
        <div className="muted" style={{ padding: "3rem", textAlign: "center" }}>Memuat…</div>
      ) : (
        <div className="card" style={{ maxWidth: 720 }}>
          <div className="card-head">
            <h3 className="card-title"><Building2 size={15} /> <Bi id="Data perusahaan" en="Company data" /></h3>
            <span className="card-sub muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Dipakai di invoice & notifikasi" en="Used in invoices & notifications" /></span>
          </div>
          <div className="card-body" style={{ display: "grid", gap: "1.5rem" }}>
            {GROUPS.map((grp) => (
              <div key={grp.id}>
                <div className="label" style={{ textTransform: "uppercase", letterSpacing: ".04em", marginBottom: ".625rem" }}>
                  <Bi id={grp.id} en={grp.en} />
                </div>
                <div style={{ display: "grid", gap: "0.875rem" }}>
                  {FIELDS.filter((f) => f.group === grp).map((f) => (
                    <div key={f.key}>
                      <label className="label"><Bi id={f.id} en={f.en} /></label>
                      {f.area ? (
                        <textarea className="input" rows={2} value={(form?.[f.key] ?? "") as string} onChange={(e) => set(f.key, e.target.value)} />
                      ) : (
                        <input className="input" value={(form?.[f.key] ?? "") as string} onChange={(e) => set(f.key, e.target.value)} />
                      )}
                      {f.hintId && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "4px", lineHeight: 1.45 }}><Bi id={f.hintId} en={f.hintEn ?? f.hintId} /></div>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
            <div style={{ display: "flex", justifyContent: "flex-end", borderTop: "1px solid var(--border-subtle)", paddingTop: "1rem" }}>
              <button className="btn btn-primary" disabled={saving} onClick={save}>
                <Save size={15} /> {saving ? "Menyimpan…" : <Bi id="Simpan" en="Save" />}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 70, background: "#1f2937", color: "#fff", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid rgba(255,255,255,0.12)", boxShadow: "0 6px 20px rgba(0,0,0,0.35)", fontSize: "var(--text-sm)" }}>{toast}</div>}
    </>
  );
}
