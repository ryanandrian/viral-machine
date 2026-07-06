-- 0140_openai_anthropic_catalog_complete.sql (2026-07-06)
-- Koreksi owner: katalog OpenAI/Anthropic setengah-terisi (warisan seed awal) — BUKAN karena beda
-- parameter. Lengkapi dengan model ber-protokol IDENTIK:
--   AKTIF: GPT-4.1 family (chat completions penuh) + gpt-image-1 (transport gpt-image SAMA dgn mini
--          yang sudah teruji produksi) + Claude Sonnet 5 & Opus 4.8 (Messages API standar).
--   NONAKTIF + alasan: GPT-5 family = reasoning model yang MENOLAK parameter temperature yang
--          dikirim adapter kita → butuh penyesuaian adapter dulu (jangan seed bom waktu).
begin;
insert into ai_models (model_key, provider_key, component, model_id, display_name, quality_tier, is_active, sort_order, cost_hint) values
  ('gpt-4.1',      'openai', 'llm', 'gpt-4.1',      'GPT-4.1',              'premium',  true,  20, '{"unit":"per_token","note":"Penerus 4o — konteks besar, instruksi kuat"}'),
  ('gpt-4.1-mini', 'openai', 'llm', 'gpt-4.1-mini', 'GPT-4.1 Mini',         'standard', true,  21, '{"unit":"per_token","note":"Seimbang harga-kualitas"}'),
  ('gpt-4.1-nano', 'openai', 'llm', 'gpt-4.1-nano', 'GPT-4.1 Nano — hemat', 'basic',    true,  22, '{"unit":"per_token","note":"Termurah & tercepat keluarga 4.1"}'),
  ('gpt-5',        'openai', 'llm', 'gpt-5',        'GPT-5',                'premium',  false, 18, '{"unit":"per_token","note":"NONAKTIF: reasoning model menolak param temperature adapter — aktif setelah penyesuaian adapter"}'),
  ('gpt-5-mini',   'openai', 'llm', 'gpt-5-mini',   'GPT-5 Mini',           'standard', false, 19, '{"unit":"per_token","note":"NONAKTIF: alasan sama gpt-5"}'),
  ('gpt-image-1',  'openai', 'image', 'gpt-image-1', 'GPT Image 1 (kualitas penuh)', 'premium', true, 20, '{"unit":"per_image","approx_usd":0.06,"note":"Transport sama gpt-image-1-mini yang teruji produksi"}'),
  ('claude-sonnet-5',  'anthropic', 'llm', 'claude-sonnet-5',  'Claude Sonnet 5',   'premium', true, 20, '{"unit":"per_token","note":"Generasi terbaru Sonnet"}'),
  ('claude-opus-4-8',  'anthropic', 'llm', 'claude-opus-4-8',  'Claude Opus 4.8',   'premium', true, 21, '{"unit":"per_token","note":"Flagship Anthropic"}')
on conflict (model_key) do nothing;
commit;
