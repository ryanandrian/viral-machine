-- 0141_price_feed_prefix.sql (2026-07-06)
-- NO-HARDCODE sinkron harga (owner): prefix feed LiteLLM per-provider jadi DATA.
-- NULL = pakai provider_key apa adanya. Provider baru = baris DB, TANPA bongkar skrip.
begin;
alter table ai_providers add column if not exists price_feed_prefix text;
comment on column ai_providers.price_feed_prefix is
  'Prefix entri feed harga LiteLLM utk provider ini (mis. together→together_ai). NULL = provider_key.';
update ai_providers set price_feed_prefix='together_ai' where provider_key='together';
update ai_providers set price_feed_prefix='openai'      where provider_key='openai_tts';
commit;
