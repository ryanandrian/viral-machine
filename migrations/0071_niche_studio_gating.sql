-- 0071 — F3-03/F2-10: gating Niche Studio (config-driven, admin-editable)
-- ============================================================================
-- "Siapa boleh BUAT niche custom" = config-driven (§3.5/§3.20). app_config.value=INTEGER,
-- jadi pakai MIN-RANK: tenant boleh bila PLAN_RANK[plan] >= niche_studio_min_rank.
-- Default 3 = Business (rank: trial0/starter1/pro2/business3). Extensible ke Pro = set 2.
-- Niche custom dibuat via server-route (service_role) yang ENFORCE access_type='private' +
-- exclusive_to=tenant_id + gating ini. niches RLS tetap OFF (tak diubah) → nol-risiko mesin.
-- ============================================================================
insert into app_config (key, value, description) values
  ('niche_studio_min_rank', 3, 'Niche Studio: min plan-rank yg boleh BUAT niche custom (3=Business; set 2 utk Pro). Rank: trial0/starter1/pro2/business3.')
on conflict (key) do nothing;
