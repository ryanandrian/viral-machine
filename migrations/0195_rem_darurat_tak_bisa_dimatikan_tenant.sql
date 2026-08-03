-- 0195 — Rem darurat channel: TIDAK bisa dimatikan tenant sendiri
-- SSOT: PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §10e-4.
--
-- CELAH D (dibuktikan: PATCH langsung → HTTP 200, rem mati)
-- Aturan UPDATE pada `channels` mengizinkan tenant mengubah SELURUH kolom miliknya. `production_paused`
-- ikut di dalamnya. Artinya tenant cukup satu permintaan langsung ke database untuk:
--   • melewati seluruh gerbang pemulihan yang baru dibangun (tombol "Pulihkan produksi" jadi hiasan)
--   • dan yang lebih penting: MELUMPUHKAN REM DARURAT KITA — pelindung yang menghentikan channel
--     setelah 3 produksi gagal beruntun. Rem itu ada untuk melindungi slot render KAMI, bukan tenant.
--     Tanpa ini, channel yang kredensialnya rusak bisa dilepas berulang kali dan membakar antrean
--     produksi tanpa henti.
--
-- Kolom rem kini READ-ONLY bagi pemanggil ber-sesi. Yang boleh mengubahnya: mesin produksi & jalur
-- pemulihan resmi — keduanya memakai kunci layanan (tanpa auth.uid()).
--
-- Kolom lain channel TIDAK tersentuh: tenant tetap bebas mengatur niche, jadwal, suara, branding, dsb.

CREATE OR REPLACE FUNCTION public.trg_channels_rem_readonly()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
begin
  -- Kunci layanan (worker, API internal, jalur pemulihan) tak punya auth.uid() → berwenang penuh.
  if auth.uid() is null then
    return NEW;
  end if;
  if NEW.production_paused        IS DISTINCT FROM OLD.production_paused
     or NEW.production_paused_at     IS DISTINCT FROM OLD.production_paused_at
     or NEW.production_paused_reason IS DISTINCT FROM OLD.production_paused_reason then
    raise exception
      'Rem darurat channel hanya bisa dilepas lewat jalur pemulihan resmi, bukan diubah langsung.'
      using errcode = 'insufficient_privilege';
  end if;
  return NEW;
end
$function$;

COMMENT ON FUNCTION public.trg_channels_rem_readonly() IS
  'Kolom production_paused* READ-ONLY bagi pemanggil ber-sesi. Rem darurat (3 kegagalan beruntun) '
  'melindungi slot render platform — tenant tak boleh mematikannya sendiri. Kunci layanan bebas.';

DROP TRIGGER IF EXISTS channels_rem_readonly ON channels;
CREATE TRIGGER channels_rem_readonly
  BEFORE UPDATE ON channels
  FOR EACH ROW
  EXECUTE FUNCTION public.trg_channels_rem_readonly();
