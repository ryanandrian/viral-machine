-- 0214 — F7: tarif yang MESIN tak bisa verifikasi dibetulkan, lalu diberi JEJAK & DIKUNCI.
--
-- KENAPA. §7e menyebut batasnya apa adanya: *nilai tarif yang salah-tapi-masuk-akal tak terdeteksi
-- mesin apa pun.* Dua buktinya nyata dan bertahan berbulan-bulan, keduanya lolos SELURUH pengaman:
--   • suara Gemini  — umpan publik menaruh tarif TEKS di kolom yang bermakna ganda ⇒ tercatat 4×
--     terlalu murah. 4 channel AKTIF. Biayanya tetap TERHITUNG, jadi laporan "biaya tak terhitung"
--     pun diam; penjaga lonjakan tak menyala karena tak ada lonjakan.
--   • eleven_v3     — umpan memberi tarif KELEBIHAN KUOTA ($180) alih-alih tarif API ($100).
--     Selisih 1,8× lolos penjaga lonjakan yang butuh 3×. Nol channel memakainya hari ini, tapi
--     angkanya salah dan sinkron akan mempertahankannya selamanya.
-- Yang menangkap keduanya cuma satu hal: PEMBANDINGAN KE HALAMAN TARIF RESMI VENDOR — pekerjaan
-- manusia. Maka migrasi ini tidak cuma membetulkan angka; ia meninggalkan JEJAKNYA (sumber +
-- tanggal, di `pricing.note`) dan MENGUNCI barisnya, supaya sinkron harian tak menghapus hasil
-- pemeriksaan itu besok pagi. Penjaganya: `tests/test_gerbang_rantai_biaya.py::G13` (dibuktikan
-- MERAH lebih dulu: 5 dari 6 baris ketikan-tangan melanggar aturan §7c yang sudah ada sejak 22-Agu).
--
-- YANG BERUBAH ANGKANYA: TEPAT 2 baris (suara Gemini, eleven_v3).
-- YANG HANYA DIBERI JEJAK: 5 baris yang angkanya sudah BENAR (dibanding ke halaman resmi 23-Agu)
--   tapi tak seorang pun bisa membuktikan asalnya. Nilai tarifnya TIDAK disentuh.
-- NOL kolom baru ⇒ tak ada pertanyaan "bagaimana baris lama". NOL formula bergeser. NOL data tenant.
-- Riwayat biaya per produksi TIDAK ditulis ulang (angka tersimpan per run; layar membaca yang
-- tersimpan) ⇒ nol angka lama tenant berubah; yang benar berlaku mulai produksi BERIKUTNYA.
--
-- AMBANG (transaksi DIBATALKAN bila tak terpenuhi): tepat 7 baris berubah · tepat 2 di antaranya
-- berubah ANGKA tarifnya · nol formula bergeser · nol baris lain tersentuh.

begin;

create temp table _sebelum_0214 on commit drop as
  select model_key, pricing, pricing_locked, pricing_model from public.ai_models;

-- ── 1. SUARA GEMINI — tarif resmi Google, satuan token AUDIO (bukan teks) ────────────────────
update public.ai_models set
  pricing = jsonb_build_object(
    'in_per_1m',  0.50,
    'out_per_1m', 10.00,
    'source',     'manual',
    'synced_at',  now(),
    'note',       'tarif resmi Google (ai.google.dev/gemini-api/docs/pricing, cek 2026-08-23): '
                  '$0,50 per 1jt token teks MASUK + $10,00 per 1jt token audio KELUAR. DIKUNCI: '
                  'umpan publik menaruh tarif TEKS ($2,5) pada kolom yang bermakna ganda, dan '
                  'sinkron menolak satuan ambigu — jadi angka ini wajib ketikan tangan.'),
  pricing_locked = true
where model_key = 'gemini-2.5-flash-preview-tts';

-- ── 2. eleven_v3 — tarif API resmi, bukan tarif kelebihan kuota ──────────────────────────────
update public.ai_models set
  pricing = jsonb_build_object(
    'per_1m_chars', 100,
    'source',       'manual',
    'synced_at',    now(),
    'note',         'tarif resmi ElevenLabs (elevenlabs.io/pricing/api, cek 2026-08-23): $0,10 per '
                    '1.000 huruf = $100 per 1jt huruf. DIKUNCI: umpan publik memberi $180 = tarif '
                    'KELEBIHAN KUOTA (1,8× — lolos penjaga lonjakan yang butuh 3×).'),
  pricing_locked = true
where model_key = 'eleven_v3';

-- ── 3–7. Angka SUDAH benar, yang hilang JEJAKNYA (nilai tarif tak disentuh) ──────────────────
update public.ai_models set
  pricing = pricing || jsonb_build_object('note',
    'tarif resmi ElevenLabs (elevenlabs.io/pricing/api, cek 2026-08-23): $0,10 per 1.000 huruf '
    '= $100 per 1jt huruf.')
where model_key = 'eleven_multilingual_v2';

update public.ai_models set
  pricing = pricing || jsonb_build_object('note',
    'tarif resmi ElevenLabs (elevenlabs.io/pricing/api, cek 2026-08-23): $0,05 per 1.000 huruf '
    '= $50 per 1jt huruf.')
where model_key in ('eleven_flash_v2_5', 'eleven_turbo_v2_5');

update public.ai_models set
  pricing = pricing || jsonb_build_object('note',
    'Edge TTS tidak menagih apa pun — nol akun, nol kunci berbayar (cek 2026-08-23).')
where model_key = 'edge-neural';

-- Cloudflare: "$0" itu BENAR hari ini, tapi hanya di bawah kuota. Jejaknya wajib memuat
-- aritmetikanya + batas kapan ia berhenti benar — kalau tidak, ia jadi angka yang tak bisa
-- diperiksa siapa pun, dan diam-diam salah begitu ada tenant yang berproduksi jauh lebih banyak.
update public.ai_models set
  pricing = pricing || jsonb_build_object('note',
    'Cloudflare Workers AI (developers.cloudflare.com/workers-ai/platform/pricing, cek 2026-08-23): '
    '10.000 neuron/hari GRATIS, di atasnya $0,011 per 1.000 neuron. flux-1-schnell = 4,8 neuron per '
    'petak 512x512 + 9,6 neuron per langkah; kita mengirim tanpa width/height (keluaran 1024x1024 = '
    '4 petak) dengan 8 langkah ⇒ 4x4,8 + 8x9,6 = 96 neuron/gambar ⇒ 104 gambar/hari per akun tenant '
    'masih GRATIS. Puncak NYATA terukur 22 gambar/hari (2.112 neuron) = kelonggaran 4,7x. '
    'BATAS JUJUR: di atas kuota biayanya jadi nyata sementara mesin tetap melaporkan $0 — formula '
    'kuota_gratis belum didukung penghitung (SSOT 7e).')
where model_key = 'cf-flux-schnell';

-- ── AMBANG ───────────────────────────────────────────────────────────────────────────────────
do $$
declare
  n_berubah int;
  n_angka   int;
  n_formula int;
begin
  select count(*) into n_berubah
    from public.ai_models m join _sebelum_0214 s using (model_key)
   where m.pricing::text <> s.pricing::text
      or coalesce(m.pricing_locked, false) <> coalesce(s.pricing_locked, false);
  if n_berubah <> 7 then
    raise exception 'AMBANG 0214: % baris berubah, seharusnya TEPAT 7 — dibatalkan', n_berubah;
  end if;

  select count(*) into n_angka
    from public.ai_models m join _sebelum_0214 s using (model_key)
   where (m.pricing - 'note' - 'synced_at' - 'source')::text
      <> (s.pricing - 'note' - 'synced_at' - 'source')::text;
  if n_angka <> 2 then
    raise exception 'AMBANG 0214: % baris berubah ANGKA tarifnya, seharusnya TEPAT 2 — dibatalkan', n_angka;
  end if;

  select count(*) into n_formula
    from public.ai_models m join _sebelum_0214 s using (model_key)
   where coalesce(m.pricing_model, '') <> coalesce(s.pricing_model, '');
  if n_formula <> 0 then
    raise exception 'AMBANG 0214: % formula bergeser — migrasi ini haram menyentuh formula', n_formula;
  end if;

  if (select count(*) from public.ai_models
       where (pricing->>'source') = 'manual'
         and (coalesce(pricing_locked, false) = false or coalesce(pricing->>'note', '') !~ '20[0-9][0-9]')) > 0 then
    raise exception 'AMBANG 0214: masih ada harga ketikan-tangan tanpa kunci atau tanpa tanggal';
  end if;
end $$;

commit;
