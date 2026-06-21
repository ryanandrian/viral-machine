-- 0076 — custom_niche = ONE-TIME per 1 niche (owner 2026-06-21), bukan add_on berulang.
-- Betulkan kategori → tampil di grup "one_time" di Admin/landing. Tak ubah harga/fungsi.
update pricing_config set category = 'one_time' where key in ('custom_niche_private', 'custom_niche_public_90d');
