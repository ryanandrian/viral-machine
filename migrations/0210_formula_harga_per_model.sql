-- 0210 — F1: kolom FORMULA HARGA di tiap baris model (arahan owner 23-Agu-2026).
--
-- KENAPA. Selama ini cara menghitung biaya DITEBAK dari jenis model, dan pengetahuan itu tersebar di
-- 4 tempat yang tak saling tahu. Akibatnya (semuanya terukur 23-Agu): model gambar Gemini ditagih DUA
-- KALI (+7,6%), harga TEKS diterima sebagai harga SUARA (4× terlalu murah), dan model video tampil
-- berharga "/gambar" di layar tenant. Owner: *"sebaiknya kita memiliki kategorisasi pricing untuk
-- mengelompokkan beberapa model yang memiliki formulasi pricing yang sama."*
--
-- Kolom ini menyimpan NAMA formula (katalog di `src/billing/ai_cost.py` → FORMULA; SSOT
-- `ARSITEKTUR_AI_PROVIDER_MODEL.md` §7b/§7f). Nilai sahnya dicerminkan ke `catalog_valid_values`
-- tiap startup service, jadi panel & validasi tulis membacanya dari SATU tempat — nol daftar
-- yang diketik ulang, nol CHECK yang menanam daftar di DB.
--
-- JAWABAN UNTUK BARIS LAMA (wajib, §3): kolom nullable, TAPI ke-47 baris diisi di migrasi yang SAMA,
-- dengan formula yang MENGHASILKAN ANGKA IDENTIK dengan hari ini (dipilih dari kunci harga yang
-- sudah terisi, mengikuti urutan prioritas penghitung biaya). Jadi:
--   • nol perubahan pada biaya produksi mana pun (penghitung belum membaca kolom ini — itu F2)
--   • nol channel tenant terganggu; nol gerbang baru menyala di migrasi ini
-- Pemindahan ke formula yang lebih tepat (mis. gambar fal → per megapiksel, seedance → token video)
-- dikerjakan TERPISAH di F4, bersama tarif aslinya dari sumber resmi vendor.
alter table public.ai_models add column if not exists pricing_model text;

comment on column public.ai_models.pricing_model is
  'Nama FORMULA harga (katalog kode: src/billing/ai_cost.py FORMULA). Menentukan CARA mesin '
  'menghitung biaya, bukan cuma satuannya. Nilai sah = cermin catalog_valid_values pricing_model:<jenis>.';

-- Isi ke-47 baris: formula yang mereproduksi angka hari ini, dari kunci harga yang ADA.
update public.ai_models set pricing_model = case
  when component = 'llm'   and pricing ? 'per_request_usd'    and pricing->>'per_request_usd'    is not null then 'naskah_panggilan'
  when component = 'llm'   and (pricing->>'in_per_1m' is not null or pricing->>'out_per_1m' is not null)      then 'naskah_token'
  when component = 'tts'   and pricing->>'per_1m_chars' is not null                                          then 'suara_huruf'
  when component = 'tts'   and (pricing->>'in_per_1m' is not null or pricing->>'out_per_1m' is not null)      then 'suara_token'
  when component = 'tts'   and pricing->>'per_second_usd' is not null                                        then 'suara_detik'
  when component = 'image' and pricing->>'per_image' is not null                                             then 'gambar_satuan'
  when component = 'image' and (pricing->>'in_per_1m' is not null or pricing->>'out_per_1m' is not null)      then 'gambar_token'
  when component = 'video' and pricing->>'per_second_usd' is not null                                        then 'video_detik'
  when component = 'video' and pricing->>'per_video_base_usd' is not null                                    then 'video_klip'
  else pricing_model
end
where pricing_model is null;
