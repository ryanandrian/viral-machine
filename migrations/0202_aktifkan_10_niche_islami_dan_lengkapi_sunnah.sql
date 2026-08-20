-- 0202 (2026-08-20) — ketokan owner atas seed 0201. DATA-ONLY, idempoten.
--
-- (1) AKTIFKAN 10 niche Islam dari 0201 → masuk katalog publik tenant.
-- (2) LENGKAPI `sunnah_harian`: 2 kunci inti visual yang KOSONG sejak dibuat 15-Agu
--     (`color_palette`, `atmosphere`). Selama kosong, DUA konsumen — hook-frame & rewrite —
--     jatuh ke default HARDCODE, bukan ke DNA niche (NICHE_DNA_AUDIT_REMEDIATION baris 26).
--     Nilai disusun dari NYAWA niche itu ("sunnah yang terasa mudah dan hangat"), selaras
--     `lighting` yang sudah ada. Niche ini dipakai channel tenant → disentuh HANYA atas izin owner.
--
-- Sesudah migrasi ini: NOL niche di pustaka yang kekurangan 3 kunci inti (terukur 58/58).

begin;

update niches set is_active = true
 where niche_id in ('kisah_islami_dramatis','dosa_taubat_pengampunan','jodoh_cinta_pernikahan',
                    'kisah_nabi_rasul_sahabat','akhirat_kematian_ghaib','masalah_hidup_islami',
                    'rezeki_ujian_takdir','islam_psikologi_kehidupan','rahasia_fakta_islam',
                    'sejarah_peradaban_islam');

update niches
   set visual_style = visual_style
     || jsonb_build_object(
          'color_palette', 'warm lamp amber, morning window blue, kitchen cream, tea brown, soft sage green',
          'atmosphere',    'kehangatan rumah sehari-hari — amalan yang terasa ringan dan dekat, bukan tuntutan')
 where niche_id = 'sunnah_harian';

commit;
