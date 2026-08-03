-- 0197 — Memulihkan produksi WAJIB memutus hitungan kegagalan beruntun
-- SSOT: AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8c.
--
-- BUG (dilaporkan owner 2026-08-03, terbukti di log produksi)
-- BISIK NUSANTARA "dihentikan mesin" berulang-ulang meski sudah dipulihkan dan sudah dijalankan uji.
-- Log membuktikan rem menyala DUA KALI hari itu (11:01 & 11:08 WIB) **tanpa satu pun percobaan
-- produksi baru** — nol baris `production_runs` dan nol stok bertanggal hari itu.
--
-- Sebabnya: `recent_nonready_streak` menghitung kegagalan dari 12 run TERAKHIR channel. Tiga kegagalan
-- dari HARI SEBELUMNYA masih terhitung. Melepas rem tidak menyentuh hitungan itu, jadi siklus penjadwal
-- berikutnya membaca streak=3 dan langsung mengerem lagi. Bagi tenant: "dipulihkan, lalu mati lagi
-- beberapa menit kemudian, berulang-ulang" — pemulihan yang hanya ilusi.
--
-- KEJUJURAN: ini lahir dari jalur buka yang baru ditambahkan ([B24] tombol "Pulihkan produksi").
-- Sebelumnya rem HANYA dilepas oleh produksi direct yang SUKSES — dan sukses itu sendiri memutus
-- streak, sehingga masalahnya tak pernah muncul. Menambah cara melepas rem tanpa ikut memutus
-- hitungannya = menambah pintu tanpa memasang lantainya.
-- Komentar `recent_nonready_streak` bahkan sudah merekam insiden BERPOLA SAMA pada 2026-07-08
-- ("channel di-pause ULANG tiap siklus + alarm palsu berulang") — sebab berbeda, akibat identik.
--
-- PERBAIKAN: catat KAPAN produksi dipulihkan. Hitungan kegagalan beruntun hanya menghitung kegagalan
-- yang terjadi SESUDAH titik itu. Riwayat lama tidak dipalsukan, tidak dihapus, tidak disembunyikan —
-- ia tetap ada untuk diagnosa; ia hanya berhenti dipakai menghukum periode yang sudah ditutup.
--
-- NULL = channel belum pernah dipulihkan sejak kolom ini ada → hitungan berjalan seperti semula
-- (nol perubahan perilaku untuk channel yang tak pernah menyentuh tombol pemulih).

ALTER TABLE channels ADD COLUMN IF NOT EXISTS production_resumed_at timestamptz;

COMMENT ON COLUMN channels.production_resumed_at IS
  'Kapan rem produksi terakhir DILEPAS (tombol Pulihkan produksi · reaktivasi langganan · produksi '
  'direct yang sukses). Hitungan kegagalan beruntun (circuit-breaker) hanya menghitung kegagalan '
  'SESUDAH titik ini — tanpa itu, kegagalan hari sebelumnya langsung mengerem ulang channel yang '
  'baru saja dipulihkan. NULL = belum pernah dipulihkan sejak kolom ada.';

-- Pelepas rem terpusat: catat titik pemulihan bersamaan dengan melepas remnya, dalam SATU pernyataan.
-- Dua pernyataan terpisah membuka celah: rem lepas tapi titiknya belum tercatat → siklus penjadwal
-- yang kebetulan lewat di antaranya mengerem lagi.
CREATE OR REPLACE FUNCTION public.tenant_resume_channels(
  p_tenant_id  text,
  p_channel_id text DEFAULT NULL
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
declare v_on int; v_n int;
begin
  if p_tenant_id is null or p_tenant_id = '' then return 0; end if;
  v_on := coalesce((select value from app_config where key = 'auto_resume_on_reactivate'), 1);
  if v_on = 0 then return 0; end if;

  update channels
     set production_paused = false,
         production_paused_reason = null,
         production_paused_at = null,
         production_paused_class = null,
         production_resumed_at = now(),   -- [0197] titik nol hitungan kegagalan
         updated_at = now()
   where tenant_id = p_tenant_id
     and production_paused = true
     and (p_channel_id is null or id::text = p_channel_id);
  get diagnostics v_n = row_count;
  return v_n;
end
$function$;

COMMENT ON FUNCTION public.tenant_resume_channels(text, text) IS
  'Lepas rem circuit-breaker DAN catat titik pemulihan (production_resumed_at) dalam satu pernyataan. '
  'Tanpa p_channel_id = seluruh channel tenant (jalur reaktivasi langganan). Dengan p_channel_id = satu '
  'channel (tombol "Pulihkan produksi"). Dijaga kenop auto_resume_on_reactivate. HANYA service_role — '
  'pemanggil wajib memverifikasi kepemilikan + gerbang produksi lebih dulu.';

REVOKE ALL ON FUNCTION public.tenant_resume_channels(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.tenant_resume_channels(text, text) FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.tenant_resume_channels(text, text) TO service_role;
