-- 0104: Custom Niche Request — lifecycle penuh A-Z (CUSTOM_NICHE_REQUEST_FLOW.md).
-- Aman utk sistem LIVE: kolom additive + status SUPERSET (legacy 'approved'/'live' tetap diterima
-- sampai FE baru deploy) + RPC batal (pemilik & saat pending saja) + config N-hari evaluasi (admin-editable).
-- niche_requests = 0 baris saat migrasi ini → tak ada data yang melanggar.

BEGIN;

-- (a) Kolom pondasi (termasuk pondasi PEMBAYARAN: paid_at, order_id — integrasi Midtrans menyusul, §7 doc).
ALTER TABLE niche_requests
  ADD COLUMN IF NOT EXISTS paid_at       timestamptz,
  ADD COLUMN IF NOT EXISTS order_id      text,
  ADD COLUMN IF NOT EXISTS delivered_at  timestamptz,
  ADD COLUMN IF NOT EXISTS closed_at     timestamptz,
  ADD COLUMN IF NOT EXISTS revision_note text,
  ADD COLUMN IF NOT EXISTS delivery_note text;

-- (b) Status set baru (SUPERSET: sertakan legacy agar FE/route lama tak pecah selama window pra-deploy).
ALTER TABLE niche_requests DROP CONSTRAINT IF EXISTS niche_requests_status_check;
ALTER TABLE niche_requests ADD CONSTRAINT niche_requests_status_check CHECK (
  status = ANY (ARRAY[
    'pending','cancelled','rejected','awaiting_payment','in_progress','delivered','closed',
    'approved','live'  -- legacy: dipensiunkan setelah FE+route baru deploy
  ])
);

-- (c) Pembatalan oleh TENANT — HANYA status 'pending' & pemilik (gerbang server, bukan RLS UPDATE langsung).
CREATE OR REPLACE FUNCTION public.cancel_niche_request(p_request_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public' AS $fn$
declare v_uid text := (auth.uid())::text;
begin
  update niche_requests
     set status = 'cancelled', updated_at = now()
   where request_id = p_request_id and tenant_id = v_uid and status = 'pending';
  if not found then
    raise exception 'Pesanan tak bisa dibatalkan (bukan milik Anda atau sudah diproses admin).';
  end if;
end; $fn$;
revoke all on function public.cancel_niche_request(uuid) from anon, public;
grant execute on function public.cancel_niche_request(uuid) to authenticated;

-- (d) Config N-hari masa evaluasi (admin-editable via panel System Configuration; no-hardcode).
INSERT INTO app_config (key, value, description, updated_at)
VALUES ('niche_eval_window_days', 3,
  'Berapa hari tenant punya waktu mengevaluasi niche custom yang sudah diserahkan sebelum pesanan otomatis ditutup (Selesai).',
  now())
ON CONFLICT (key) DO NOTHING;

COMMIT;
