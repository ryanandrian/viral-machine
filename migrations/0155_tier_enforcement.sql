-- 0155 — TIER ENFORCEMENT: gerbang LAHIR kuota channel (finalisasi_tier_plan.md Tahap 1.1,
-- mandat owner 2026-07-13). SEBELUM: INSERT channels hanya cek kepemilikan → tenant bisa membuat
-- channel MELEBIHI paket via klien langsung (anon key publik + sesi login) — bocor tuas harga utama
-- (max_channels 1/3/10). SESUDAH: jumlah channel tenant harus < plan_limits.max_channels
-- (config-driven — admin ubah kuota → pagar ikut; pola gerbang RLS = 0130 niche_requests).
--
-- Catatan desain:
--  • service_role (worker/admin/Next API admin) bypass RLS — tidak terpengaruh.
--  • Subquery count(channels) memicu policy SELECT channels_tenant_read (sederhana:
--    tenant_id=auth.uid()) — tidak rekursif, dan justru menghitung hanya channel milik tenant.
--  • Fail-CLOSED: tenant tanpa baris tenant_configs / plan_type tak dikenal → subquery kanan NULL
--    → predikat NULL → DITOLAK (aman; tenant sah selalu punya baris via trigger handle_new_tenant).
--  • Gerbang JALAN (channel berlebih pasca-downgrade berhenti dilayani) = src/billing/limits.py
--    gate_for_channel (Tahap 1.2) — bukan di sini.
BEGIN;

DROP POLICY IF EXISTS channels_tenant_insert ON channels;
CREATE POLICY channels_tenant_insert ON channels
  FOR INSERT
  WITH CHECK (
    tenant_id = (auth.uid())::text
    AND (SELECT count(*) FROM channels c WHERE c.tenant_id = (auth.uid())::text)
        < (SELECT pl.max_channels
             FROM tenant_configs tc
             JOIN plan_limits pl ON pl.plan_type = tc.plan_type
            WHERE tc.tenant_id = (auth.uid())::text)
  );

COMMIT;
