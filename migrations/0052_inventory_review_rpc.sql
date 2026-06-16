-- 0052: OPSI C review/approve (D1) — RPC tenant utk tinjau video 'ready_with_issues'.
-- FE = anon, panggil via supabase.rpc (TANPA service_role/S3 di frontend). SECURITY DEFINER,
-- scope ketat tenant_id = auth.uid() (anti cross-tenant). Idempotent (create or replace).
--
-- approve_inventory_item: tenant PAKAI video bermasalah → promote ready_with_issues → 'ready'.
--   Publisher akan mempublish saat SLOT (ber-kuota di publish — tutup cheat: hanya jadi publik via
--   jalur kita yang ber-kuota). Tandai metadata.approved_with_issues utk provenance.
-- discard_inventory_item: tenant BUANG → status 'failed' + expires_at=now → janitor hapus S3 + baris.

create or replace function public.approve_inventory_item(p_inv_id bigint)
returns void language plpgsql security definer set search_path = public as $$
begin
  update content_inventory
     set status   = 'ready',
         metadata = coalesce(metadata, '{}'::jsonb) || '{"approved_with_issues": true}'::jsonb,
         updated_at = now()
   where id = p_inv_id
     and status = 'ready_with_issues'
     and tenant_id = (auth.uid())::text;
  if not found then
    raise exception 'Item tidak ditemukan / bukan milik Anda / status bukan ready_with_issues';
  end if;
end $$;

create or replace function public.discard_inventory_item(p_inv_id bigint)
returns void language plpgsql security definer set search_path = public as $$
begin
  update content_inventory
     set status   = 'failed',
         expires_at = now(),
         metadata = coalesce(metadata, '{}'::jsonb) || '{"discarded_by_tenant": true}'::jsonb,
         updated_at = now()
   where id = p_inv_id
     and status = 'ready_with_issues'
     and tenant_id = (auth.uid())::text;
  if not found then
    raise exception 'Item tidak ditemukan / bukan milik Anda / status bukan ready_with_issues';
  end if;
end $$;

revoke execute on function public.approve_inventory_item(bigint) from public;
revoke execute on function public.discard_inventory_item(bigint) from public;
revoke execute on function public.approve_inventory_item(bigint) from anon;
revoke execute on function public.discard_inventory_item(bigint) from anon;
grant  execute on function public.approve_inventory_item(bigint) to authenticated;
grant  execute on function public.discard_inventory_item(bigint) to authenticated;
