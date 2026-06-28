-- 0099 — REJECT (Buang) menutup loop ke production_runs (bug: sinyal "perlu ditinjau" menggantung)
-- ============================================================================
-- Bug (2026-06-28): tenant Buang konten cacat → discard_inventory_item HANYA update content_inventory,
-- TIDAK menyentuh production_runs. Sinyal "perlu ditinjau" (dashboard/runs/detail) baca
-- production_runs.status='qc_failed' (ledger permanen) → tak pernah padam setelah reject → /review kosong
-- tapi sinyal tetap nyala. (Approve SUDAH benar: publisher.py:144-151 set production_runs.status='success'
-- via metadata.run_id saat publish — fix ini MENIRU pola simetris itu untuk reject.)
-- Arsitektur OPSI C/TTL/janitor/kuota TIDAK diubah. Hanya menutup loop reject.
-- ============================================================================

create or replace function public.discard_inventory_item(p_inv_id bigint)
returns void language plpgsql security definer set search_path = public as $$
declare v_run_id text;
begin
  update content_inventory
     set status   = 'failed',
         expires_at = now(),
         metadata = coalesce(metadata, '{}'::jsonb) || '{"discarded_by_tenant": true}'::jsonb,
         updated_at = now()
   where id = p_inv_id
     and status = 'ready_with_issues'
     and tenant_id = (auth.uid())::text
   returning metadata->>'run_id' into v_run_id;
  if not found then
    raise exception 'Item tidak ditemukan / bukan milik Anda / status bukan ready_with_issues';
  end if;
  -- TUTUP LOOP: run asal qc_failed → 'discarded' agar sinyal "perlu ditinjau" padam di semua layar
  -- (mirror publisher approve→'success'). qc_passed tetap false = fakta produksi terjaga.
  if v_run_id is not null then
    update production_runs
       set status = 'discarded'
     where run_id = v_run_id
       and tenant_id = (auth.uid())::text
       and status = 'qc_failed';
  end if;
end $$;

revoke execute on function public.discard_inventory_item(bigint) from public, anon;
grant  execute on function public.discard_inventory_item(bigint) to authenticated;

-- Backfill 1× — run qc_failed yang kontennya SUDAH tak ada di antrean live (di-reject/TTL-auto-buang
-- sebelum fix ini) → 'discarded' agar sinyal menggantung langsung bersih. Hanya menyentuh orphan
-- (item live ready_with_issues TIDAK tersentuh → tetap "perlu ditinjau"). Aman diulang.
update production_runs pr
   set status = 'discarded'
 where pr.status = 'qc_failed'
   and not exists (
     select 1 from content_inventory ci
     where ci.metadata->>'run_id' = pr.run_id
       and ci.status = 'ready_with_issues'
   );
