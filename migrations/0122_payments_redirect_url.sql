-- 0122 — Lanjutkan-pembayaran (owner 2026-07-04): simpan link Snap di ledger agar tenant bisa
-- membuka ulang tagihan pending dari halaman Billing (email Midtrans tak memuat link — kanal kita sendiri
-- yang menyediakannya: banner Billing + email ber-brand "Selesaikan pembayaran").
ALTER TABLE payments ADD COLUMN IF NOT EXISTS redirect_url text;
