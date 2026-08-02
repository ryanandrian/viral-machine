-- 0192 — Pasangan gerbang: "langganan tenant ini masih hidup untuk BERPRODUKSI?"
-- SSOT: PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §10.
--
-- KENAPA TERPISAH DARI tenant_test_gate
-- Dua pertanyaan yang berbeda, dan owner sudah mengetok bahwa jawabannya memang berbeda:
--   • "boleh menjalankan UJI?"      → masa tenggang (grace) DIKUNCI
--   • "boleh BERPRODUKSI / melihat hasil produksinya?" → masa tenggang TETAP JALAN
-- Menggabungkannya akan memaksa salah satu ikut salah.
--
-- DIPAKAI OLEH: pintu unduh stok gudang (/api/review/preview). Video di gudang adalah hasil produksi
-- yang belum terbit; tenant yang produksinya sudah berhenti tak boleh lagi memanennya lewat tautan
-- unduh. Saat ini stok milik tenant non-aktif berjumlah nol — gerbang ini menutup pintunya SEBELUM
-- ada yang lewat, bukan sesudah.
--
-- ⚠️ DUPLIKASI YANG DIJAGA UJI
-- Daftar status di bawah WAJIB sama persis dengan `PRODUCING_STATUSES` di src/billing/limits.py.
-- Daftar ini SENGAJA bukan kenop: mengubahnya bisa mematikan produksi semua tenant sekaligus —
-- itu keputusan arsitektur, bukan setelan harian. Karena tak terhindarkan ada di dua tempat,
-- `tests/test_gerbang_uji.py` membandingkan keduanya supaya perbedaan sekecil apa pun langsung merah.

CREATE OR REPLACE FUNCTION public.tenant_produce_allowed(p_tenant_id text)
RETURNS boolean
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path TO 'public'
AS $function$
declare tc tenant_configs%rowtype;
begin
  if p_tenant_id is null or p_tenant_id = '' then return false; end if;

  -- Pagar privasi: pemanggil ber-sesi hanya boleh menanyakan dirinya sendiri (sama dgn tenant_test_gate).
  if auth.uid() is not null and p_tenant_id <> (auth.uid())::text then return false; end if;

  select * into tc from tenant_configs where tenant_id = p_tenant_id limit 1;
  if not found then return false; end if;

  -- Comp — rumus WAJIB sama persis dengan src/billing/limits.py::is_comp_account.
  if coalesce(tc.is_developer, false)
     or (coalesce(tc.discount_pct, 0) >= 100
         and (tc.discount_until is null or tc.discount_until >= now())) then
    return true;
  end if;

  -- WAJIB sama dengan PRODUCING_STATUSES. NULL → 'active' (back-compat, sama dgn can_produce).
  return coalesce(tc.subscription_status, 'active') in ('active', 'trial', 'grace');
end
$function$;

COMMENT ON FUNCTION public.tenant_produce_allowed(text) IS
  'Langganan tenant masih hidup untuk berproduksi? Pasangan tenant_test_gate — BEDA jawaban untuk '
  'status grace (produksi: boleh; uji: dikunci). Daftar statusnya wajib sama dengan '
  'PRODUCING_STATUSES di src/billing/limits.py; kesamaan itu dijaga tests/test_gerbang_uji.py. '
  'TIDAK memeriksa kuota channel — itu urusan limits.gate_for_channel.';

GRANT EXECUTE ON FUNCTION public.tenant_produce_allowed(text) TO authenticated, service_role;
