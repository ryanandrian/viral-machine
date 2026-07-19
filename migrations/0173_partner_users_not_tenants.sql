-- ============================================================================
-- 0173 — [B21] user partner (agent/reseller) TIDAK dicetak sebagai tenant
-- BUG: handle_new_tenant (migr 0028) berjalan utk SETIAP auth user baru →
-- user agen/reseller (dibuat admin/approve) ikut lahir sebagai "tenant trial"
-- → tampil di daftar tenant admin + email nurture salah sasar.
-- Bukti insiden: agen THETANGGA (a3195614…) ber-baris tenant_configs 19-Jul 04:51.
-- FIX: pagari trigger — role partner dilewati. Sisanya byte-identik migr 0028.
-- PRASYARAT KODE (commit yang sama): invite/approve mengeset app_metadata.role
-- LANGSUNG saat createUser (bukan sesudahnya) supaya trigger bisa melihatnya.
-- ============================================================================

create or replace function public.handle_new_tenant()
returns trigger language plpgsql security definer set search_path = public as $$
declare _days int;
begin
  -- [B21 fix 2026-07-19] user partner (agen/reseller) BUKAN tenant — jangan cetak baris tenant.
  if coalesce(new.raw_app_meta_data->>'role', '') in ('agent', 'reseller') then
    return new;
  end if;
  select coalesce((select value from app_config where key='trial_duration_days'), 7) into _days;
  insert into public.tenant_configs
    (tenant_id, display_handle, subscription_status, plan_type, trial_started_at, current_period_end)
  values
    (new.id::text, split_part(coalesce(new.email,''), '@', 1), 'trial', 'trial', now(),
     now() + (_days || ' days')::interval)
  on conflict (tenant_id) do nothing;
  return new;
end;
$$;
