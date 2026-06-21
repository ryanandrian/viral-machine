-- 0075 — Deskripsi app_config ditulis ulang ke BAHASA ADMIN (mudah dipahami, bukan istilah teknis).
-- Ditampilkan di Admin → Konfigurasi Harga (card Pengaturan Sistem). Tak mengubah perilaku (cuma teks).
update app_config set description = 'Berapa hari calon pelanggan bisa mencoba gratis sebelum harus berlangganan.'              where key = 'trial_duration_days';
update app_config set description = 'Seberapa besar tren YouTube menentukan pemilihan topik konten. Ini sumber UTAMA.'             where key = 'trend_weight_youtube';
update app_config set description = 'Seberapa besar tren pencarian Google menentukan pemilihan topik konten.'                     where key = 'trend_weight_trends';
update app_config set description = 'Seberapa besar berita terkini menentukan pemilihan topik konten.'                            where key = 'trend_weight_news';
update app_config set description = 'Seberapa besar halaman populer Wikipedia menentukan pemilihan topik (pengaruh kecil).'        where key = 'trend_weight_wikipedia';
update app_config set description = 'Seberapa besar tren teknologi (HackerNews) menentukan topik — hanya untuk niche teknologi.'  where key = 'trend_weight_hackernews';
update app_config set description = 'Berapa lama data tren disimpan sebelum diambil ulang dari sumbernya. Makin lama = makin hemat kuota.' where key = 'trend_cache_ttl_sec';
update app_config set description = 'Jeda antar-pengambilan data dari sumber tren, supaya tidak diblokir karena terlalu sering.'  where key = 'trend_refresh_pacing_ms';
