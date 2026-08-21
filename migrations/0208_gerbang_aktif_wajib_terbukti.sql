-- 0208 — "MODEL AKTIF = PASTI JALAN" akhirnya DITEGAKKAN MESIN, bukan disiplin.
-- SSOT: ARSITEKTUR_AI_PROVIDER_MODEL.md §8 (janji) + §9.1 langkah 5-6 (koridor)
-- Penjaga: tests/test_panel_mengatakan_kebenaran_status_model.py
--
-- ═══ JANJI YANG SUDAH TERTULIS, TAPI TAK PERNAH DIJAGA ═══
-- Dokumen arsitektur §8 menulis: "Model aktif = pasti jalan → ditegakkan tombol Uji + stempel
-- cost_hint.audit + badge FE." Sampai 22-Agu itu bersandar DISIPLIN: tak ada yang mencegah model
-- belum-teruji dinyalakan, dan tenant-lah yang menemukan masalahnya.
--
-- ═══ KASUS NYATA YANG MELAHIRKAN GERBANG INI (22-Agu) ═══
-- `gemini-2.5-flash` dinyalakan kembali dari panel. Lencananya berbunyi "✓ Teruji" — dari 6 JULI.
-- Model itu TERBUKTI MATI di vendor 18-Agu (3 kegagalan `model_unavailable`), dan `Abyss ID`
-- (channel AKTIF, tenant nyata) memakainya. Audit lama tidak membuktikan apa pun tentang keadaan
-- sekarang. ⇒ syaratnya BUKAN "pernah LULUS", tapi "LULUS dan LEBIH BARU dari bukti kematiannya".
--
-- ═══ KENAPA DI DB, BUKAN DI PANEL ═══
-- Jalur yang MEMUTARI panel sudah terbukti dipakai — oleh saya sendiri, waktu menyalakan mesin
-- suara Gemini lewat skrip. Penjaga yang hanya hidup di panel tidak menahan tangan itu.
--
-- ═══ AMAN SECARA TERUKUR ═══
-- Diukur pada katalog produksi sebelum ditulis: 43 model aktif, dan 43/43 ber-`cost_hint.audit`
-- LULUS ⇒ NOL baris yang terkunci. Trigger hanya menyala pada TRANSISI ke aktif, jadi baris yang
-- sudah aktif tak pernah diperiksa (jawaban untuk baris LAMA).
-- Khusus SATU tabel (`ai_models`) ⇒ `new.model_key` sah dipakai langsung; `tg_table_name` SENGAJA
-- tidak dipakai (pelajaran 0206: `case tg_table_name … then new.<kolom>` menggagalkan tabel lain).

begin;

create or replace function public.trg_ai_models_aktif_wajib_terbukti()
returns trigger
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  v_audit text;
  v_mati  timestamptz;
  v_stamp timestamptz;
begin
  -- Hanya TRANSISI menjadi aktif. Mematikan tetap bebas (vendor bisa mematikan model sewaktu-waktu
  -- dan admin WAJIB bisa menyusul — blokir keras = "kunci tanpa jalur buka", PAYMENT §10e-2).
  if not (coalesce(new.is_active, false) = true and not coalesce(old.is_active, false)) then
    return new;
  end if;

  v_audit := coalesce(new.cost_hint ->> 'audit', '');
  v_mati  := new.unavailable_since;

  if v_audit not like 'LULUS%' then
    raise exception 'MODEL_BELUM_TERBUKTI: belum_lulus_uji'
      using errcode = 'check_violation';
  end if;

  -- Umur bukti. Stempel `model_tester` berbentuk "LULUS … <YYYY-MM-DD> …"; tanggal pertama di
  -- dalamnya = kapan uji itu dijalankan. Tak ada tanggal ⇒ bukti tak bisa ditimbang umurnya, dan
  -- kalau model itu punya jejak kematian, ia HARUS diuji ulang.
  v_stamp := nullif(substring(v_audit from '\d{4}-\d{2}-\d{2}'), '')::timestamptz;

  if v_mati is not null and (v_stamp is null or v_stamp < v_mati) then
    -- Inti kasus 22-Agu: audit LULUS 6-Jul, model mati 18-Agu. Uji lama tak membuktikan apa pun.
    raise exception 'MODEL_BELUM_TERBUKTI: uji_lebih_tua_dari_kematian'
      using errcode = 'check_violation';
  end if;

  return new;
end $function$;

drop trigger if exists trg_gate_aktif_terbukti on ai_models;
create trigger trg_gate_aktif_terbukti before update on ai_models
  for each row execute function trg_ai_models_aktif_wajib_terbukti();

commit;
