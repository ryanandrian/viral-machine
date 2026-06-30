-- 0107: provenans niche — pisahkan niche bikinan-sendiri (Niche Studio) dari pesanan custom (concierge).
-- Niche Studio HANYA kelola/edit origin='studio'; niche pesanan (origin='request') dikelola TIM, tak bisa
-- diedit tenant (cegah campur-aduk + rusak deliverable berbayar / niche public_90d yang akan jadi publik).
-- BE Python = read-only thd niches → penambahan kolom AMAN (additive). RLS niches OFF (tak berubah).
-- Backfill berbasis tautan PASTI niche_requests.niche_id (bukan tebakan).

BEGIN;

ALTER TABLE niches ADD COLUMN IF NOT EXISTS origin text NOT NULL DEFAULT 'admin';
ALTER TABLE niches DROP CONSTRAINT IF EXISTS niches_origin_check;
ALTER TABLE niches ADD CONSTRAINT niches_origin_check CHECK (origin IN ('admin','studio','request'));

-- request: niche yang niche_id-nya tertaut ke pesanan (dibangun tim)
UPDATE niches SET origin='request'
  WHERE niche_id IN (SELECT niche_id FROM niche_requests WHERE niche_id IS NOT NULL);
-- studio: niche privat MILIK tenant yang BUKAN dari pesanan (dibuat sendiri di Niche Studio)
UPDATE niches SET origin='studio'
  WHERE exclusive_to IS NOT NULL AND origin <> 'request';
-- sisanya (publik/base, exclusive_to NULL) tetap 'admin'

COMMIT;
