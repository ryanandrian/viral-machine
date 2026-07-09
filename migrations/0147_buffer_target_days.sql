-- 0147_buffer_target_days.sql
-- Target stok buffer SADAR-JADWAL (mandat owner 2026-07-09, dasar: (1) stok statis > kebutuhan
-- harian → video menunggu > TTL 72j → disapu janitor = compute terbuang; (2) tenant model gratis
-- kuota-harian (Groq/Cloudflare) → produksi eager melebihi kuota → 3x gagal beruntun → circuit-break).
-- Rumus BE (producer.target_stock): channels.buffer_depth eksplisit MENANG apa adanya;
-- NULL → len(publish_slots) × buffer_target_days (clamp ≤ slots × hari-TTL); tanpa slot → 0.
-- Admin-editable, no-hardcode; BE fail-soft ke 1 bila baris tak terbaca.

INSERT INTO app_config (key, value, description)
VALUES ('buffer_target_days', 1,
        'Stok buffer = berapa HARI kebutuhan tayang di depan (target = jumlah slot/hari × nilai ini; channel dgn buffer_depth eksplisit tidak terpengaruh). BE fail-soft 1.')
ON CONFLICT (key) DO NOTHING;
