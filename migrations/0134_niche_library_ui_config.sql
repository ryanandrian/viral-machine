-- 0134_niche_library_ui_config.sql (2026-07-06)
-- Config UI Pustaka Niche (no-hardcode, owner): ambang badge "Baru", klasifikasi nuansa mood,
-- kamus sinonim pencarian ID→EN — semua admin-editable via app_config; FE fail-soft ke default kode.
begin;
insert into app_config (key, value, value_text, description) values
 ('niche_new_badge_days', 14, null,
  'Pustaka Niche: umur maksimum (hari) sebuah niche diberi badge BARU di etalase tenant'),
 ('niche_tone_moods', 0,
  '{"dark":["dark","eerie","ominous","suspense","tense","mysterious"],"bright":["upbeat","happy","energetic","inspirational","calm","playful"]}',
  'Pustaka Niche: klasifikasi nuansa (Gelap/Cerah) dari mood_priority DNA; mood di luar daftar = Netral'),
 ('niche_search_synonyms', 0,
  '{"sejarah":"history war empire","hantu":"horror ghost scary paranormal","seram":"horror scary creepy","horor":"horror scary","misteri":"mystery unsolved crime","luar angkasa":"space universe cosmos","antariksa":"space universe","uang":"money finance invest wealth","keuangan":"finance money invest","kesehatan":"health wellness immune","otak":"brain neuroscience psychology mind","psikologi":"psychology behavior","hukum":"law legal rights","mobil":"car automotive racing","kendaraan":"car automotive","kisah":"story tale fable confession","cerita":"story tale fable","dongeng":"fable story moral","perjalanan":"travel places destinations","wisata":"travel hidden places","budaya":"culture traditions","buku":"book reading summary wisdom","motivasi":"motivation discipline mindset","teknologi":"tech ai technology","bisnis":"business startup company","filosofi":"philosophy stoicism wisdom","filsafat":"philosophy wisdom","bahasa":"language learning words","islami":"islam kisah nabi","alam":"nature earth geography","peta":"maps geography borders","nostalgia":"retro 90s childhood","puisi":"poetry poem verse","hemat":"saving money budget","properti":"real estate property housing","kripto":"crypto bitcoin blockchain","legenda":"legend mythology folklore","mitos":"myth mythology legend"}',
  'Pustaka Niche: sinonim pencarian Indonesia→English (tenant awam menemukan niche ber-keyword EN)')
on conflict (key) do nothing;
commit;
