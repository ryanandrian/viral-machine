-- 0213 — F4: alamat HARGA boleh berbeda dari penanda model (kasus agregator satu-pintu).
--
-- KENAPA (terbukti 23-Agu). API harga fal menjawab 404 untuk 3 baris naskah fal, sebab
-- `model_id`-nya berisi nama model VENDOR (`anthropic/claude-haiku-4.5`) — itu PARAMETER yang
-- dikirim ke fal, bukan alamat fal. Alamat fal-nya satu pintu: `fal-ai/any-llm`, dan tarifnya
-- $0,001 PER PERMINTAAN berapa pun modelnya (terverifikasi dari API resmi fal).
--
-- Jadi butuh satu keterangan: "kalau menanyakan HARGA, tanyakan alamat ini". Disimpan sebagai DATA
-- di `default_params.price_endpoint_id` (kolom JSON yang sudah ada & admin-editable) — nol kolom
-- baru, nol nama penyedia di kode, dan berlaku untuk agregator satu-pintu berikutnya.
update public.ai_models
   set default_params = coalesce(default_params, '{}'::jsonb)
                        || jsonb_build_object('price_endpoint_id', 'fal-ai/any-llm')
 where provider_key = 'fal' and component = 'llm';
