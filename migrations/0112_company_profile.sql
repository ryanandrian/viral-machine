-- 0112 — Profil PERUSAHAAN (penerbit) — dipakai invoice/bukti bayar + kebutuhan sistem ke depan.
-- Single-row (id=1), admin-editable. NO-HARDCODE: info perusahaan di DB, bukan tertanam di kode.
CREATE TABLE IF NOT EXISTS company_profile (
  id             int PRIMARY KEY DEFAULT 1,
  legal_name     text,   -- badan hukum (untuk invoice/faktur)
  brand          text,
  tagline        text,
  website        text,
  email          text,
  phone          text,
  address        text,
  npwp           text,
  nib            text,
  sk_menkum      text,
  business_scope text,
  updated_at     timestamptz DEFAULT now(),
  CONSTRAINT company_profile_singleton CHECK (id = 1)
);

INSERT INTO company_profile
  (id, legal_name, brand, tagline, website, email, phone, address, npwp, nib, sk_menkum, business_scope)
VALUES
  (1, 'PT. LUMITE AUTOMASI INDONESIA', 'Lumite', 'Bring More Profit to Your Business',
   'lumite.biz.id', 'info@lumite.biz.id', '0858 8018 1816',
   'Depok Town Square, 2nd Floor, Block SS 2 / 9. Jl. Margonda Raya No. 1, Pondok Cina, Beji, Depok 16525',
   '1000 0000 0485 5800', '0908250052541', 'AHU-0065942.AH.01.01.TAHUN 2025',
   'Industrial Automation | Pneumatic System | Internet of Things | Application System')
ON CONFLICT (id) DO NOTHING;

-- RLS: info perusahaan PUBLIK (tampil di invoice) → boleh dibaca semua; tulis = service_role (admin).
ALTER TABLE company_profile ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS company_profile_read ON company_profile;
CREATE POLICY company_profile_read ON company_profile FOR SELECT USING (true);

-- PPN (%) invoice — no-hardcode. 0 = harga final tanpa PPN; set 11 bila PKP (PPN 11%). Muncul di System Config.
INSERT INTO app_config (key, value, description) VALUES
  ('ppn_percent', 0, 'PPN (%) pada invoice. 0 = harga final tanpa PPN. Set 11 bila perusahaan PKP (PPN 11%).')
ON CONFLICT (key) DO NOTHING;
