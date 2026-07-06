-- 0137_provider_free_tier_note.sql (2026-07-06)
-- Keterangan free-tier di tabel provider (owner): tenant melihat & memilih penyedia GRATIS
-- di halaman Integrations. Kolom di ai_providers (no-hardcode; admin-editable via catalog).
begin;
alter table ai_providers add column if not exists free_tier_note text;
update ai_providers set free_tier_note='Kredit gratis harian dari Google AI Studio — ada rate-limit; data dapat dipakai Google utk peningkatan layanan' where provider_key='gemini';
update ai_providers set free_tier_note='Kredit gratis harian (free tier Groq) — ada rate-limit per menit/hari' where provider_key='groq';
update ai_providers set free_tier_note='Model FLUX Schnell Free gratis (free tier Together AI) — ada rate-limit' where provider_key='together';
commit;
