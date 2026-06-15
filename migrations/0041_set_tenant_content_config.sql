-- 0041 — RPC content-config (Phase 9.4 config tabs). Tenant tulis kolom KONTEN non-privilege via whitelist.
-- Pisah dari set_tenant_config (keys/identity) — INI hanya kolom konten (quality/visual/music/caption/hashtag).
-- TIDAK ada plan_type/subscription/is_developer/discount (anti self-upgrade). Per-kolom coalesce dari jsonb
-- (hanya kolom terdaftar yang bisa di-set; sisanya diabaikan). scope auth.uid(). grant authenticated, revoke anon.
create or replace function public.set_tenant_content_config(p jsonb)
returns void language plpgsql security definer set search_path = public as $$
begin
  update public.tenant_configs t set
    script_min_viral_score = coalesce((p->>'script_min_viral_score')::int, t.script_min_viral_score),
    script_max_retry        = coalesce((p->>'script_max_retry')::int, t.script_max_retry),
    visual_mode             = coalesce(p->>'visual_mode', t.visual_mode),
    image_quality           = coalesce(p->>'image_quality', t.image_quality),
    music_enabled           = coalesce((p->>'music_enabled')::boolean, t.music_enabled),
    music_volume            = coalesce((p->>'music_volume')::double precision, t.music_volume),
    music_default_mood      = coalesce(p->>'music_default_mood', t.music_default_mood),
    caption_style           = coalesce(p->'caption_style', t.caption_style),
    hook_title_style        = coalesce(p->'hook_title_style', t.hook_title_style),
    niche_hashtags          = coalesce(p->'niche_hashtags', t.niche_hashtags),
    thumbnail_enabled       = coalesce((p->>'thumbnail_enabled')::boolean, t.thumbnail_enabled),
    thumbnail_source        = coalesce(p->>'thumbnail_source', t.thumbnail_source),
    loop_ending_enabled     = coalesce((p->>'loop_ending_enabled')::boolean, t.loop_ending_enabled),
    loop_ending_duration    = coalesce((p->>'loop_ending_duration')::double precision, t.loop_ending_duration),
    trailing_silence        = coalesce((p->>'trailing_silence')::double precision, t.trailing_silence),
    duplicate_lookback_days = coalesce((p->>'duplicate_lookback_days')::int, t.duplicate_lookback_days),
    production_on_api_error = coalesce(p->>'production_on_api_error', t.production_on_api_error),
    updated_at = now()
  where t.tenant_id = (auth.uid())::text;
end $$;
revoke all on function public.set_tenant_content_config(jsonb) from anon;
grant execute on function public.set_tenant_content_config(jsonb) to authenticated;
