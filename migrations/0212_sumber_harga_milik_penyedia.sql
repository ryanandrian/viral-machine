-- 0212 — F4: penyedia boleh punya SUMBER HARGA RESMINYA SENDIRI (URL API), sebagai DATA.
--
-- KENAPA. Riset 23-Agu: fal menerbitkan tarif resminya lewat API (`/v1/models/pricing`) BERIKUT
-- satuan tagihnya, dan itu satu-satunya sumber yang berwenang untuk baris fal (pagar agregator F3
-- menolak tarif vendor lain). Tanpa kolom ini, alamat sumber itu harus ditanam di kode — dan
-- agregator berikutnya (blackbox/apimaster/dst) akan menuntut bongkar skrip lagi.
--
-- Nol nama penyedia di kode: mesin memakai kolom ini bila terisi, dan mengambil kuncinya dari vault
-- memakai `key_group` penyedia itu. Kosong = penyedia tak punya sumber resmi (perilaku lama).
alter table public.ai_providers add column if not exists price_api_url text;

comment on column public.ai_providers.price_api_url is
  'URL API harga RESMI milik penyedia ini (opsional). Placeholder {model_id} diganti ID model. '
  'Balasan wajib menyebut unit_price + unit. Dipakai lebih dulu daripada umpan umum untuk penyedia '
  'agregator. Kunci diambil dari vault memakai key_group penyedia.';

update public.ai_providers
   set price_api_url = 'https://api.fal.ai/v1/models/pricing?endpoint_id={model_id}'
 where provider_key = 'fal' and price_api_url is null;

-- veo-3.1-fast: tarif fal TERGANTUNG PARAMETER yang KITA pilih — $0,15/detik dengan audio,
-- $0,10/detik tanpa audio (terverifikasi 23-Agu; pipeline kita mematikan audio). API harga fal hanya
-- menyebut satu angka utama (yang BERAUDIO), jadi sinkron otomatis akan membuat biaya 50% terlalu
-- mahal. Baris ini DIKUNCI supaya angka yang benar dipertahankan, dengan catatan asal + tanggal.
update public.ai_models
   set pricing_locked = true,
       pricing = jsonb_set(pricing, '{note}',
         to_jsonb('fal 2026-08-23: $0.10/detik TANPA audio ($0.15 dgn audio). Pipeline kita '
                  'generate_audio=false, jadi $0.10 yang benar. DIKUNCI: API harga fal hanya '
                  'menyebut angka beraudio — sinkron otomatis akan 50% terlalu mahal.'::text))
 where model_key = 'veo-3.1-fast';
