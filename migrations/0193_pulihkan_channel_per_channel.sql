-- 0193 — JALUR BUKA untuk rem channel: memulihkan TANPA memproduksi apa pun
-- SSOT: PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §10c. Perintah owner 2026-08-02:
-- "pastikan setiap kuncian otomatis ada jalur buka yang sesuai aturan".
--
-- JEBAKAN YANG DITUTUP (bug yang lahir dari gerbang uji itu sendiri)
-- Rem darurat channel (3 produksi gagal beruntun) selama ini HANYA bisa dilepas oleh tombol
-- "Jalankan ulang" yang sukses. Setelah gerbang uji dipasang, tombol itu terkunci untuk:
--   • tenant masa tenggang (grace) — padahal produksi rutinnya SENGAJA tetap dibiarkan jalan
--   • tenant masa coba yang jatah ujinya habis — padahal produksi rutinnya juga masih jalan
-- Keduanya jadi terjebak: mesin berhenti, dan satu-satunya pemulih justru dikunci. Terverifikasi
-- nyata: m.yusroon (trial, jatah uji habis, produksi boleh) tinggal menunggu 3 kegagalan beruntun —
-- kegagalan seperti itu terjadi pada 3 channel lain di hari yang sama.
--
-- KENAPA AMAN: melepas rem TIDAK menghasilkan video, tidak memanggil AI, tidak mengunggah apa pun.
-- Ia hanya mencabut penghenti darurat. Gerbang kesiapan channel & gerbang langganan tetap berlaku
-- sesudahnya, dan bila sebabnya belum diperbaiki rem akan menyala lagi setelah 3 kegagalan. Karena
-- itu jalur buka ini boleh diberikan kepada siapa pun yang PRODUKSINYA memang masih boleh jalan —
-- bukan kepada yang langganannya sudah mati.

-- Ganti signature: tambah channel opsional. Pemanggil lama (kirim p_tenant_id saja) tetap bekerja
-- persis seperti sebelumnya — melepas SELURUH channel tenant, yang memang benar untuk reaktivasi.
DROP FUNCTION IF EXISTS public.tenant_resume_channels(text);

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
         updated_at = now()
   where tenant_id = p_tenant_id
     and production_paused = true
     -- NULL = seluruh channel tenant (jalur reaktivasi). Terisi = satu channel (jalur pemulihan
     -- manual tenant dari layar channel).
     and (p_channel_id is null or id::text = p_channel_id);
  get diagnostics v_n = row_count;
  return v_n;
end
$function$;

COMMENT ON FUNCTION public.tenant_resume_channels(text, text) IS
  'Lepas rem circuit-breaker. Tanpa p_channel_id = seluruh channel tenant (dipanggil kelima jalur '
  'reaktivasi). Dengan p_channel_id = satu channel (jalur buka manual dari layar channel, untuk '
  'tenant yang produksinya boleh tapi tombol ujinya terkunci). Dijaga kenop auto_resume_on_reactivate. '
  'HANYA service_role — pemanggilnya wajib memverifikasi kepemilikan + gerbang produksi lebih dulu.';

REVOKE ALL ON FUNCTION public.tenant_resume_channels(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.tenant_resume_channels(text, text) FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.tenant_resume_channels(text, text) TO service_role;
