-- 0106: penanda agar email pengingat masa-evaluasi (H-1) tidak terkirim berulang oleh worker.
ALTER TABLE niche_requests ADD COLUMN IF NOT EXISTS reminder_sent_at timestamptz;
