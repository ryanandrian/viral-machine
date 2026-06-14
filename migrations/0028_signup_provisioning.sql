-- 0028 — Provisioning tenant otomatis saat signup (Phase 9.1, fork A=DB trigger, idiomatic Supabase).
-- auth.users INSERT → baris tenant_configs (RLS langsung valid) + trial MULAI (durasi dari app_config).
-- Trial dari signup ≈ DESAIN §3 (onboarding step-a langsung setelah signup). plan_type='trial' (caps tier trial).
create or replace function public.handle_new_tenant()
returns trigger language plpgsql security definer set search_path = public as $$
declare _days int;
begin
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
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_tenant();
