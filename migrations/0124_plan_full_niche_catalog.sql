-- 0124 — Katalog niche per-tier jadi CONFIG-DRIVEN (keputusan owner 2026-07-04: opsi A+C).
-- SEBELUM: aturan "trial/starter hanya niche is_base; pro/business semua" TER-HARDCODE di
--   RPC set_channel_niche (0096) + 3 halaman FE + src/billing/limits.py — melanggar no-hardcode,
--   dan owner memutuskan Starter (berbayar) berhak lihat SEMUA niche publik.
-- SESUDAH: plan_limits.full_niche_catalog (admin-tunable) = satu sumber kebenaran.
--   Seed keputusan A: tier BERBAYAR (starter/pro/business) = katalog penuh; trial = niche dasar saja.

BEGIN;

ALTER TABLE plan_limits ADD COLUMN IF NOT EXISTS full_niche_catalog BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE plan_limits SET full_niche_catalog = (plan_type IN ('starter', 'pro', 'business'));

-- RPC gerbang server: entitlement publik kini baca plan_limits.full_niche_catalog (bukan daftar tier hardcode).
CREATE OR REPLACE FUNCTION public.set_channel_niche(
  p_channel_id uuid,
  p_niche      text,
  p_niche_mode text,
  p_niche_pool text[] DEFAULT NULL
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
declare
  v_uid  text := (auth.uid())::text;
  v_tier text;
  v_full boolean;
  v_pool text[];
  v_n    text;
begin
  if p_niche_mode not in ('fixed','random') then
    raise exception 'niche_mode harus fixed/random';
  end if;
  if not exists (select 1 from channels where id = p_channel_id and tenant_id = v_uid) then
    raise exception 'channel bukan milik Anda';
  end if;
  select plan_type into v_tier from tenant_configs where tenant_id = v_uid;
  -- Entitlement katalog publik per-tier: CONFIG-DRIVEN dari plan_limits (0124, owner 2026-07-04).
  select coalesce(full_niche_catalog, false) into v_full
    from plan_limits where plan_type = coalesce(v_tier, 'starter');
  v_full := coalesce(v_full, false);

  -- pool efektif: pakai p_niche_pool bila diberikan, else [p_niche]; pastikan p_niche termasuk.
  v_pool := coalesce(nullif(p_niche_pool, '{}'), array[p_niche]);
  if not (p_niche = any(v_pool)) then
    v_pool := array[p_niche] || v_pool;
  end if;

  -- SETIAP niche di pool WAJIB di entitlement tenant (publik per-tier ATAU custom milik tenant).
  foreach v_n in array v_pool loop
    if not exists (
      select 1 from niches n
      where n.niche_id = v_n and n.is_active = true
        and ( n.exclusive_to = v_uid
              or (n.access_type = 'public' and (v_full or n.is_base = true)) )
    ) then
      raise exception 'niche % bukan hak tenant Anda (di luar entitlement)', v_n;
    end if;
  end loop;

  update channels
    set niche       = p_niche,
        niche_mode  = p_niche_mode,
        niche_pool  = v_pool,
        updated_at  = now()
    where id = p_channel_id and tenant_id = v_uid;
end; $function$;

COMMIT;
