-- 0046: PERBAIKAN PRODUCE & PUBLISH — Area B3 (jalur tulis channel ber-validasi).
-- FE menulis jadwal & niche channel HANYA lewat RPC ini (SECURITY DEFINER, scope auth.uid()):
--  • set_channel_publish_slots → validasi jumlah slot ≤ batas tier (plan_limits.max_videos_per_day).
--  • set_channel_niche        → validasi niche ∈ ENTITLEMENT tenant (katalog per-tier + exclusive milik tenant).
-- Pola = sama dgn set_tenant_config (anti tenant set di luar haknya). Dipakai FE C1 (jadwal) & C3 (niche).

create or replace function public.set_channel_publish_slots(
  p_channel_id uuid,
  p_slots      text[]
) returns void
language plpgsql security definer set search_path = public
as $$
declare v_uid text := (auth.uid())::text; v_tier text; v_cap int;
begin
  if not exists (select 1 from channels where id = p_channel_id and tenant_id = v_uid) then
    raise exception 'channel bukan milik Anda';
  end if;
  select plan_type into v_tier from tenant_configs where tenant_id = v_uid;
  select max_videos_per_day into v_cap from plan_limits where plan_type = coalesce(v_tier, 'starter');
  if coalesce(array_length(p_slots, 1), 0) > coalesce(v_cap, 1) then
    raise exception 'jumlah slot (%) melebihi batas tier (%/hari)', coalesce(array_length(p_slots,1),0), coalesce(v_cap,1);
  end if;
  update channels set publish_slots = p_slots, updated_at = now()
    where id = p_channel_id and tenant_id = v_uid;
end; $$;

create or replace function public.set_channel_niche(
  p_channel_id uuid,
  p_niche      text,
  p_niche_mode text
) returns void
language plpgsql security definer set search_path = public
as $$
declare v_uid text := (auth.uid())::text; v_tier text;
begin
  if p_niche_mode not in ('fixed','random') then
    raise exception 'niche_mode harus fixed/random';
  end if;
  if not exists (select 1 from channels where id = p_channel_id and tenant_id = v_uid) then
    raise exception 'channel bukan milik Anda';
  end if;
  select plan_type into v_tier from tenant_configs where tenant_id = v_uid;
  -- niche WAJIB di entitlement tenant: katalog publik per-tier (pro/business=semua, trial/starter=is_base)
  -- ATAU niche custom/private MILIK tenant (exclusive_to).
  if not exists (
    select 1 from niches n
    where n.niche_id = p_niche and n.is_active = true
      and ( n.exclusive_to = v_uid
            or (n.access_type = 'public'
                and (coalesce(v_tier,'starter') in ('pro','business') or n.is_base = true)) )
  ) then
    raise exception 'niche % bukan hak tenant Anda (di luar entitlement)', p_niche;
  end if;
  update channels set niche = p_niche, niche_mode = p_niche_mode, updated_at = now()
    where id = p_channel_id and tenant_id = v_uid;
end; $$;

-- Hanya user login; cabut anon (defense-in-depth, auth.uid()=NULL → tetap gagal scope).
revoke all     on function public.set_channel_publish_slots(uuid, text[]) from public;
revoke execute on function public.set_channel_publish_slots(uuid, text[]) from anon;
grant  execute on function public.set_channel_publish_slots(uuid, text[]) to authenticated;
revoke all     on function public.set_channel_niche(uuid, text, text) from public;
revoke execute on function public.set_channel_niche(uuid, text, text) from anon;
grant  execute on function public.set_channel_niche(uuid, text, text) to authenticated;
