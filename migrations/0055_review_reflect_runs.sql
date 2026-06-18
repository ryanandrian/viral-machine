-- 0055 — Approve/Discard juga REFLEKSI ke production_runs (log yang dibaca /runs)
-- ============================================================================
-- Bug (owner 2026-06-18): item ready_with_issues yg di-APPROVE hilang dari /review, TAPI di /runs
-- statusnya tetap "Perlu Ditinjau". Sebab: RPC review hanya ubah content_inventory; production_runs
-- (sumber /runs) tetap 'qc_failed'. Fix: RPC approve/discard ALSO update production_runs lewat run_id
-- (content_inventory.metadata->>'run_id' = production_runs.run_id), scope tenant. SECURITY DEFINER.
--   approve  → production_runs.status='success'  (disetujui → akan tayang; /runs "Completed")
--   discard  → production_runs.status='failed'   (dibuang;            /runs "Failed")
-- (production_runs.status tanpa CHECK constraint → nilai bebas; tak menyentuh logika lain.)
-- ============================================================================

create or replace function public.approve_inventory_item(p_inv_id bigint)
returns void language plpgsql security definer set search_path = public as $$
declare _rid text; _tid text;
begin
  update content_inventory
     set status   = 'ready',
         metadata = coalesce(metadata, '{}'::jsonb) || '{"approved_with_issues": true}'::jsonb,
         updated_at = now()
   where id = p_inv_id
     and status = 'ready_with_issues'
     and tenant_id = (auth.uid())::text
  returning metadata->>'run_id', tenant_id into _rid, _tid;
  if not found then
    raise exception 'Item tidak ditemukan / bukan milik Anda / status bukan ready_with_issues';
  end if;
  if _rid is not null and _rid <> '' then
    update production_runs set status = 'success'
     where run_id = _rid and tenant_id = _tid and status = 'qc_failed';
  end if;
end $$;

create or replace function public.discard_inventory_item(p_inv_id bigint)
returns void language plpgsql security definer set search_path = public as $$
declare _rid text; _tid text;
begin
  update content_inventory
     set status   = 'failed',
         expires_at = now(),
         metadata = coalesce(metadata, '{}'::jsonb) || '{"discarded_by_tenant": true}'::jsonb,
         updated_at = now()
   where id = p_inv_id
     and status = 'ready_with_issues'
     and tenant_id = (auth.uid())::text
  returning metadata->>'run_id', tenant_id into _rid, _tid;
  if not found then
    raise exception 'Item tidak ditemukan / bukan milik Anda / status bukan ready_with_issues';
  end if;
  if _rid is not null and _rid <> '' then
    update production_runs set status = 'failed'
     where run_id = _rid and tenant_id = _tid and status = 'qc_failed';
  end if;
end $$;
