-- 0108 — Integrasi pembayaran Midtrans: langganan + add-on custom-niche (E1 / GATE A1).
-- (a) payments: bedakan kategori (subscription|addon) + tautkan ke entitas add-on (niche_requests).
-- (b) RPC settle_niche_request_paid: SATU sumber "pembayaran custom-niche lunas" — dipakai webhook
--     Midtrans (otomatis saat settlement) DAN admin "Tandai lunas" (concierge fallback). Anti-duplikat.
--     Idempotent (aman thd retry webhook). Auto-slug niche_id (admin isi DNA via editor niche).

-- (a) ────────────────────────────────────────────────────────────────────────
ALTER TABLE payments
  ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'subscription',  -- 'subscription' | 'addon'
  ADD COLUMN IF NOT EXISTS ref_id   TEXT;                                  -- addon: niche_requests.request_id

COMMENT ON COLUMN payments.category IS 'subscription = langganan bulanan; addon = pembelian sekali (mis. custom-niche)';
COMMENT ON COLUMN payments.ref_id   IS 'utk addon: id entitas terkait (mis. niche_requests.request_id)';

-- (b) ────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.settle_niche_request_paid(p_request_id uuid, p_order_id text DEFAULT NULL)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  r      niche_requests%ROWTYPE;
  v_slug text;
  v_excl timestamptz;
BEGIN
  SELECT * INTO r FROM niche_requests WHERE request_id = p_request_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'niche_request % tidak ditemukan', p_request_id;
  END IF;

  -- Idempotent: sudah lunas & niche dibuat → kembalikan yang ada (aman utk retry webhook Midtrans).
  IF r.status = 'in_progress' AND r.niche_id IS NOT NULL THEN
    RETURN r.niche_id;
  END IF;

  IF r.status <> 'awaiting_payment' THEN
    RAISE EXCEPTION 'status % bukan awaiting_payment (tak bisa settle)', r.status;
  END IF;

  -- Slug otomatis: valid [a-z0-9_], unik (via request_id). Nama tampil = title; DNA diisi admin di editor niche.
  v_slug := regexp_replace(lower(coalesce(nullif(btrim(r.title), ''), 'niche')), '[^a-z0-9]+', '_', 'g');
  v_slug := btrim(v_slug, '_');
  IF v_slug = '' THEN v_slug := 'niche'; END IF;
  v_slug := left(v_slug, 40) || '_' || substr(md5(p_request_id::text), 1, 6);

  v_excl := CASE WHEN r.request_type = 'public_90d' THEN now() + interval '90 days' ELSE NULL END;

  -- Buat baris niche (belum aktif; eksklusif ke tenant) — identik perilaku "Tandai lunas" lama.
  INSERT INTO niches (niche_id, name, is_active, is_base, access_type, exclusive_to, exclusive_until, origin)
  VALUES (v_slug, r.title, false, false, 'private', r.tenant_id, v_excl, 'request');

  UPDATE niche_requests
     SET status = 'in_progress', niche_id = v_slug, paid_at = now(),
         order_id = COALESCE(p_order_id, order_id), updated_at = now()
   WHERE request_id = p_request_id;

  -- Email konfirmasi (antre → worker SMTP). Fail-soft: kegagalan email tak membatalkan settlement.
  INSERT INTO email_outbox (tenant_id, subject, body)
  VALUES (r.tenant_id, 'Pembayaran diterima — ' || r.title,
          E'Halo,\n\nPembayaran untuk niche custom "' || r.title ||
          E'" sudah kami terima. Tim mulai menyiapkan niche Anda sekarang.\n' ||
          E'Anda akan kami beri tahu via email saat niche siap untuk dievaluasi.\n\n— Tim MesinViral');

  RETURN v_slug;
END
$$;

-- Hanya service_role (webhook + admin route) yang boleh panggil. Tenant/anon TIDAK.
REVOKE ALL ON FUNCTION public.settle_niche_request_paid(uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.settle_niche_request_paid(uuid, text) TO service_role;
