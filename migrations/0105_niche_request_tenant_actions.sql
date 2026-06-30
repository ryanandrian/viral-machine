-- 0105: Aksi TENANT pada pesanan custom niche saat masa Evaluasi (status 'delivered').
-- Gerbang server (SECURITY DEFINER) — pemilik & status benar saja. Bukan RLS UPDATE langsung.
--   accept   → 'closed'  (tenant puas, transaksi selesai) + closed_at
--   revision → 'in_progress' (minta perbaikan) + revision_note (niche tetap aktif, DNA diperbaiki admin)

BEGIN;

CREATE OR REPLACE FUNCTION public.tenant_niche_request_action(
  p_request_id uuid,
  p_action     text,           -- 'accept' | 'revision'
  p_note       text DEFAULT NULL
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public' AS $fn$
declare v_uid text := (auth.uid())::text;
begin
  if p_action not in ('accept','revision') then
    raise exception 'aksi harus accept/revision';
  end if;

  if p_action = 'accept' then
    update niche_requests
       set status = 'closed', closed_at = now(), updated_at = now()
     where request_id = p_request_id and tenant_id = v_uid and status = 'delivered';
  else
    update niche_requests
       set status = 'in_progress', revision_note = nullif(btrim(coalesce(p_note,'')),''), updated_at = now()
     where request_id = p_request_id and tenant_id = v_uid and status = 'delivered';
  end if;

  if not found then
    raise exception 'Pesanan tak bisa diproses (bukan milik Anda atau belum dalam masa evaluasi).';
  end if;
end; $fn$;

revoke all on function public.tenant_niche_request_action(uuid, text, text) from anon, public;
grant execute on function public.tenant_niche_request_action(uuid, text, text) to authenticated;

COMMIT;
