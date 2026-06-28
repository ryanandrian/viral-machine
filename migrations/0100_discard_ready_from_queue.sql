-- 0100 — discard_ready_item: tenant BUANG konten 'ready' dari antrean publish (konten basi/kurang pas)
-- ============================================================================
-- Konten lolos QC menunggu tayang (content_inventory.ready) → tenant buang → janitor hapus S3+baris
-- (expires_at=now); production_runs ditandai 'discarded'. Producer auto-isi ulang buffer (deficit <
-- buffer_depth) → konten SEGAR menggantikan. Beda dari discard_inventory_item (itu utk 'ready_with_issues'
-- di /review). Anti-race: guard status='ready' (tak bisa buang item yang sedang/sudah tayang).
-- ============================================================================

create or replace function public.discard_ready_item(p_inv_id bigint)
returns void language plpgsql security definer set search_path = public as $$
declare v_run_id text;
begin
  update content_inventory
     set status   = 'failed',
         expires_at = now(),
         metadata = coalesce(metadata, '{}'::jsonb) || '{"discarded_from_queue": true}'::jsonb,
         updated_at = now()
   where id = p_inv_id
     and status = 'ready'
     and tenant_id = (auth.uid())::text
   returning metadata->>'run_id' into v_run_id;
  if not found then
    raise exception 'Item tidak ditemukan / bukan milik Anda / status bukan ready (mungkin sudah tayang)';
  end if;
  -- Tutup loop: run asal (success) → 'discarded' agar konsisten di Runs/dashboard.
  if v_run_id is not null then
    update production_runs
       set status = 'discarded'
     where run_id = v_run_id
       and tenant_id = (auth.uid())::text
       and status = 'success';
  end if;
end $$;

revoke execute on function public.discard_ready_item(bigint) from public, anon;
grant  execute on function public.discard_ready_item(bigint) to authenticated;
