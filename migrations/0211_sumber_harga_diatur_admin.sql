-- 0211 — F3: URL sumber harga jadi kenop admin (arahan owner 23-Agu: "url sinkronisasi sebaiknya
-- bisa dikonfigurasi lewat admin panel").
--
-- KENAPA. Hari ini URL-nya tertanam di kode (default) + bisa ditimpa env di VPS — artinya mengganti
-- sumber harga butuh saya, dan owner tak bisa memeriksanya sendiri. Riset 23-Agu membuktikan sumber
-- harga umum BUKAN otoritas untuk semua model (3 kasus salah). Jadi sumbernya harus bisa diatur,
-- dan yang mengaturnya harus owner/admin — bukan tertanam di kode.
--
-- Nilai awal = URL yang MEMANG dipakai hari ini (nol perubahan perilaku saat migrasi ini jalan).
-- Kosongkan → mesin jatuh ke env/lalu default kode (gagal-aman, sinkron tak pernah mati total).
insert into public.app_config (key, value, value_text, description)
values
  ('ai_price_feed_url', 0,
   'https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json',
   'URL sumber harga model AI (umpan komunitas). Kosong = pakai bawaan mesin. Perubahan berlaku tanpa deploy.'),
  ('ai_price_fallback_url', 0, 'https://openrouter.ai/api/v1/models',
   'URL sumber harga CADANGAN untuk model naskah (router). TIDAK dipakai untuk baris penyedia agregator.')
on conflict (key) do nothing;
