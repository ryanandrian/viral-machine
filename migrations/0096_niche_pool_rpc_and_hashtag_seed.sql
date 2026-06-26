-- 0096: Niche-pool remediation (REMEDIASI_NICHE_HASHTAG_POOL.md BATCH 1)
-- (a) set_channel_niche terima p_niche_pool → random dipilih DARI POOL (bukan seluruh entitlement).
--     Tiap niche di pool tetap divalidasi entitlement (pertahankan keamanan lama).
-- (b) Seed niches.default_hashtags utk 4 niche dari data nyata channel ryan (lapis default niche;
--     channel boleh override via channels.niche_hashtags). Reversible.

BEGIN;

DROP FUNCTION IF EXISTS public.set_channel_niche(uuid, text, text);

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
              or (n.access_type = 'public'
                  and (coalesce(v_tier,'starter') in ('pro','business') or n.is_base = true)) )
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

-- (b) Seed default hashtags per-niche (data nyata channel ryan, proven). Lapis DEFAULT niche;
--     channel tetap bisa override. Tak menimpa channel mana pun.
UPDATE niches SET default_hashtags = '["#FunFacts","#MindBlown","#DidYouKnow","#AmazingFacts","#InterestingFacts","#LearnSomethingNew","#ScienceFacts","#CoolFacts","#RandomFacts","#WowFacts"]'::jsonb            WHERE niche_id = 'fun_facts';
UPDATE niches SET default_hashtags = '["#DarkHistory","#SecretHistory","#HiddenTruth","#HistoryFacts","#ForbiddenHistory","#AncientSecrets","#HistoryMysterious","#UntoldHistory","#ConspiracyFacts","#HistoricalSecrets"]'::jsonb WHERE niche_id = 'dark_history';
UPDATE niches SET default_hashtags = '["#OceanMysteries","#DeepSea","#MarineLife","#OceanFacts","#DeepOcean","#SeaCreatures","#OceanScience","#UnderwaterWorld","#MarineScience","#OceanSecrets"]'::jsonb         WHERE niche_id = 'ocean_mysteries';
UPDATE niches SET default_hashtags = '["#UniverseMysteries","#SpaceFacts","#CosmicSecrets","#AstroFacts","#SpaceScience","#Astronomy","#DeepSpace","#NASAFacts","#BlackHole","#DarkMatter"]'::jsonb              WHERE niche_id = 'universe_mysteries';

COMMIT;
