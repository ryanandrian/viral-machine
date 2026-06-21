-- 0077 — Hapus 4 harga add-on yang TAK FUNGSIONAL (owner 2026-06-22, "jangan ada data sampah").
-- Tak ada alur beli/fitur/entitlement di kode untuk ini (verified grep: hanya tampil di landing).
-- Kartu landing-nya juga dibuang (pricing/page.tsx ADDONS) agar tak mengiklankan yg tak bisa dibeli.
delete from pricing_config where key in ('priority_queue', 'voice_pack', 'concierge_setup', 'niche_audit');
