-- 0154 — Testimoni/Case Studies = SOFTCODE admin (mandat owner 2026-07-12)
-- ============================================================================
-- Ganti 2 fosil hardcode FE: TST (landing "Dipercaya creator Indonesia") + CASES (blog tab
-- Case Studies, yang link-nya nyasar ke /docs). Konsep owner: case studies = testimoni →
-- SATU tabel, dua wajah (kartu landing via show_on_landing; kartu+cerita panjang di blog tab;
-- slug → halaman /case-studies/[slug] bila story terisi).
-- Avatar: photo_url (S3 testimonial-photos/) menang; kosong → inisial dari nama + avatar_color.
-- Seed = 4 persona ilustratif pra-launch (keputusan owner 2026-06-28 dipertahankan) yang
-- DIRAPIKAN sesuai kesepakatan konsistensi 2026-07-12: 1 kartu = 1 pilar produk & metrik yang
-- mengukur pilar itu · label channel tanpa angka subscriber fiktif · kutipan bebas angka volatil.
-- Tuas kejujuran: begitu ada testimoni NYATA, admin tambah baris asli + nonaktifkan ilustratif.
-- ============================================================================

create table if not exists testimonials (
  id              uuid primary key default gen_random_uuid(),
  person_name     text not null,
  channel_label   text,
  quote           text not null,
  quote_en        text,
  metric_value    text,
  metric_label    text,
  metric_label_en text,
  rating          int not null default 5 check (rating between 1 and 5),
  avatar_color    text,                -- fallback lingkaran inisial (foto menang bila ada)
  photo_url       text,                -- S3 testimonial-photos/ (upload admin)
  story_body      text,                -- opsional: cerita panjang (markdown) → kartu bisa diklik
  story_body_en   text,
  slug            text unique,         -- wajib bila ber-cerita: alamat /case-studies/[slug]
  show_on_landing boolean not null default false,
  is_active       boolean not null default true,
  sort_order      int not null default 100,
  updated_at      timestamptz not null default now()
);

alter table testimonials enable row level security;
drop policy if exists testimonials_public_read on testimonials;
create policy testimonials_public_read on testimonials
  for select to anon, authenticated using (is_active);
-- tulis = service-role saja (route admin ber-guard super-admin)

-- Seed idempoten: hanya saat tabel KOSONG (pk uuid acak — on-conflict tak bisa jadi pagar re-run)
insert into testimonials
  (person_name, channel_label, quote, quote_en, metric_value, metric_label, metric_label_en,
   avatar_color, show_on_landing, sort_order)
select * from (values
  ('Riko Pratama', 'Misteri Samudra · niche misteri',
   'Set & forget — mesinnya benar-benar belajar dari channel saya dan makin pintar tiap minggu. Saya tinggal memantau hasilnya.',
   'Set & forget — the engine genuinely learns from my channel and gets smarter every week. I just watch the results.',
   '5/hari', 'publish otomatis', 'auto-publish', '#1d4ed8', true, 10),
  ('Sarah Wibowo', 'Agency konten · multi-klien',
   'Sebagai agency, saya mengelola channel semua klien dari satu dashboard. Compliance score membuat saya tenang soal kebijakan YouTube.',
   'As an agency, I manage every client channel from one dashboard. The compliance score keeps me calm about YouTube policy.',
   '8 channel', 'satu dashboard', 'one dashboard', '#9f1239', true, 20),
  ('Dimas Aryo', 'Fakta Yang Bikin Mikir · niche fakta',
   'Biaya AI transparan — ada struknya per video, dibayar langsung ke provider dengan harga asli. Tidak ada tebak-tebakan kredit.',
   'AI costs are transparent — a receipt per video, paid straight to providers at official prices. No credit guesswork.',
   'Rp 0', 'markup biaya AI', 'AI cost markup', '#047857', true, 30),
  ('Bagus Pratomo', 'Jejak Kelam Sejarah · niche sejarah',
   'Channel saya akhirnya upload konsisten tiap hari tanpa saya menyentuh editing — dan skor compliance menjaga channel tetap aman.',
   'My channel finally uploads consistently every day without me touching an editor — and the compliance score keeps it safe.',
   '90+', 'skor compliance', 'compliance score', '#7c3aed', true, 40)
) as seed(person_name, channel_label, quote, quote_en, metric_value, metric_label, metric_label_en,
          avatar_color, show_on_landing, sort_order)
where not exists (select 1 from testimonials);
