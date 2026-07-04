-- 0125 — [B3] batch disetujui owner 2026-07-05 (Temuan 2 + Temuan 3):
-- (a) app_config bisa nilai TEKS/JSON (value_text) + seed default jam publish channel baru
--     (menggantikan hardcode ["13:00"] di FE /channels/new).
-- (b) Zona waktu tenant: deteksi otomatis dari browser (auto) + bisa dikunci manual dari Settings.
--     tenant_configs.timezone SUDAH dipakai publisher (slot dibandingkan di zona tenant) — gap-nya:
--     tenant tak punya cara mengaturnya → semua tenant baru terjebak UTC (effi/kumala terbukti UTC).
-- (c) Fosil OPTIMAL_PUBLISH_SLOTS dihapus di kode (tenant_config.py) — nol pemakai (bukti grep;
--     publisher baca channels.publish_slots per-channel). Tidak ada DDL utk (c).

-- (a) app_config nilai teks
ALTER TABLE app_config ADD COLUMN IF NOT EXISTS value_text TEXT;

INSERT INTO app_config (key, value, value_text, description) VALUES
  ('default_publish_slots', 0, '["13:00"]',
   'Jam publish AWAL utk channel yang BARU dibuat (zona waktu tenant), format JSON ["HH:MM",...]. Tenant bebas mengubahnya di halaman Jadwal.')
ON CONFLICT (key) DO NOTHING;

-- (b) penanda "timezone diset manual oleh tenant" — auto-detect tak boleh menimpa pilihan manual
ALTER TABLE tenant_configs ADD COLUMN IF NOT EXISTS timezone_set_by_user BOOLEAN NOT NULL DEFAULT FALSE;

-- RPC: satu pintu ubah timezone (auth-scoped, SECURITY DEFINER — pola set_tenant_config 0031/0044).
-- p_manual=false (auto-detect saat login): hanya berlaku bila tenant BELUM pernah set manual.
-- p_manual=true  (dari Settings): selalu berlaku + mengunci (set_by_user=true).
CREATE OR REPLACE FUNCTION public.set_tenant_timezone(p_timezone text, p_manual boolean DEFAULT false)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
begin
  if p_timezone is null or length(p_timezone) > 64 or p_timezone !~ '^[A-Za-z0-9_+/\-]+$' then
    raise exception 'timezone tidak valid';
  end if;
  -- Validasi NYATA ke daftar zona IANA milik Postgres (bukan sekadar format) — config rusak mustahil masuk.
  if not exists (select 1 from pg_timezone_names where name = p_timezone) then
    raise exception 'timezone % tidak dikenal', p_timezone;
  end if;
  update tenant_configs set
    timezone = case when p_manual or not timezone_set_by_user then p_timezone else timezone end,
    timezone_set_by_user = timezone_set_by_user or p_manual,
    updated_at = now()
  where tenant_id = (auth.uid())::text;
end; $$;

REVOKE EXECUTE ON FUNCTION public.set_tenant_timezone(text, boolean) FROM anon;
GRANT  EXECUTE ON FUNCTION public.set_tenant_timezone(text, boolean) TO authenticated;
