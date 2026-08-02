-- 0191 — GERBANG UJI: satu otak + lapis pertama (aturan akses database)
-- SSOT: PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §10c. Kenop ditanam lebih dulu oleh 0190.
--
-- KENAPA OTAKNYA DI DATABASE, BUKAN DI KODE APLIKASI
-- Tiga pintu uji masuk lewat jalur yang BERBEDA dan tidak ada satu titik kode yang dilewati semuanya:
--   • "Jalankan ulang" (halaman riwayat) menulis LANGSUNG dari browser ke tabel antrean — tidak
--     melewati kode server kita sama sekali. Satu-satunya yang bisa menahannya = aturan akses tabel.
--   • "Uji produksi channel" & "Uji niche" masuk lewat API yang memakai kunci layanan, dan kunci
--     layanan justru MELEWATI aturan akses tabel. Jadi API butuh pemeriksaannya sendiri.
--   • Pekerjaan yang sudah terlanjur mengantre lalu statusnya berubah — butuh pemeriksaan ulang di
--     mesin pekerja tepat sebelum dieksekusi.
-- Bila aturannya ditulis tiga kali, suatu hari ketiganya akan berbeda dan lahirlah bug. Karena itu:
-- SATU fungsi di database, dipanggil ketiga lapis.
--
-- FAIL-SAFE, BUKAN FALLBACK SENYAP
-- Setiap kenop dibaca dengan nilai bawaan yang SAMA PERSIS dengan 0190. Kenop terhapus atau isinya
-- rusak tidak boleh membuat tenant sah terkunci — ia jatuh ke perilaku bawaan yang terdokumentasi.
-- Ini pola yang sudah dipakai di seluruh sistem (`_cfg(sb, "billing_grace_days", 7)`).

-- ── 1. Jangkar penghitung jatah ──────────────────────────────────────────────────────────────────
-- Fakta "kapan masa coba terakhir diperpanjang". Sengaja kolom terpisah: `trial_started_at` TIDAK
-- PERNAH diubah oleh jalur perpanjangan mana pun (sudah diverifikasi ke ketiga kodenya), jadi ia
-- jangkar yang tak bisa di-reset diam-diam. Kolom ini merekam FAKTA perpanjangan; kenop
-- `trial_quota_reset_on_extend` yang memutuskan apakah fakta itu dipakai — supaya mengubah kebijakan
-- tidak merusak data historis.
ALTER TABLE tenant_configs ADD COLUMN IF NOT EXISTS trial_extended_at timestamptz;

COMMENT ON COLUMN tenant_configs.trial_extended_at IS
  'Kapan masa coba terakhir diperpanjang (admin atau link 1-klik). Dibaca tenant_test_gate() sebagai '
  'titik mulai hitung jatah uji bila kenop trial_quota_reset_on_extend=1. NULL = belum pernah.';

-- ── 2. OTAK: boleh menguji atau tidak, dan kenapa ────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.tenant_test_gate(p_tenant_id text)
RETURNS jsonb
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path TO 'public'
AS $function$
declare
  tc         tenant_configs%rowtype;
  v_enabled  int;
  v_statuses text[];
  v_quota    int;
  v_counts   text;
  v_reset    int;
  v_anchor   timestamptz;
  v_used     int;
  v_status   text;
begin
  if p_tenant_id is null or p_tenant_id = '' then
    return jsonb_build_object('allowed', false, 'reason', 'tenant_unknown');
  end if;

  -- Pagar privasi: pemanggil ber-sesi (tenant login) hanya boleh menanyakan DIRINYA SENDIRI.
  -- Kunci layanan (worker/API internal) tidak punya auth.uid() → lolos, memang perlu menanyakan
  -- tenant mana pun. Tanpa pagar ini, tenant bisa mengintip status langganan tenant lain via RPC.
  if auth.uid() is not null and p_tenant_id <> (auth.uid())::text then
    return jsonb_build_object('allowed', false, 'reason', 'forbidden');
  end if;

  select * into tc from tenant_configs where tenant_id = p_tenant_id limit 1;
  if not found then
    return jsonb_build_object('allowed', false, 'reason', 'tenant_unknown');
  end if;

  -- (a) Saklar induk mati → perilaku persis seperti sebelum gerbang dipasang.
  v_enabled := coalesce((select value from app_config where key = 'test_gate_enabled'), 1);
  if v_enabled = 0 then
    return jsonb_build_object('allowed', true, 'reason', 'gate_off');
  end if;

  -- (b) Akun comp = gratis selamanya, tak pernah disentuh gerbang mana pun.
  --     Rumus WAJIB sama persis dengan src/billing/limits.py::is_comp_account.
  if coalesce(tc.is_developer, false)
     or (coalesce(tc.discount_pct, 0) >= 100
         and (tc.discount_until is null or tc.discount_until >= now())) then
    return jsonb_build_object('allowed', true, 'reason', 'comp');
  end if;

  -- (c) Status langganan. NULL diperlakukan 'active' — back-compat, sama dgn limits.can_produce.
  v_status := coalesce(tc.subscription_status, 'active');
  begin
    select array(select jsonb_array_elements_text(a.value_text::jsonb))
      into v_statuses
      from app_config a where a.key = 'test_allowed_statuses';
  exception when others then
    v_statuses := null;   -- isi kenop rusak → jatuh ke bawaan di bawah
  end;
  if v_statuses is null or coalesce(array_length(v_statuses, 1), 0) = 0 then
    v_statuses := array['active', 'trial'];   -- bawaan = sama persis dengan 0190
  end if;
  if not (v_status = any(v_statuses)) then
    return jsonb_build_object('allowed', false, 'reason', 'subscription', 'status', v_status);
  end if;

  -- (d) Jatah masa coba. Hanya berlaku untuk status 'trial'; 0 = tanpa batas.
  v_quota := coalesce((select value from app_config where key = 'trial_test_quota'), 3);
  if v_status = 'trial' and v_quota > 0 then
    v_counts := coalesce((select value_text from app_config where key = 'trial_test_quota_counts'),
                         'success');
    v_reset  := coalesce((select value from app_config where key = 'trial_quota_reset_on_extend'), 1);
    v_anchor := case
                  when v_reset = 1 and tc.trial_extended_at is not null then tc.trial_extended_at
                  else coalesce(tc.trial_started_at, tc.created_at, '-infinity'::timestamptz)
                end;

    -- Ketiga jenis pekerjaan manual dihitung: semuanya menghasilkan video di LUAR kuota terjadwal.
    -- 'admin_test' sengaja TIDAK ikut — itu channel internal admin, bukan milik tenant.
    select count(*) into v_used
      from direct_jobs d
     where d.tenant_id = p_tenant_id
       and d.job_type in ('test', 'test_nopub', 'retry')
       and d.created_at >= v_anchor
       and (v_counts <> 'success' or d.status in ('published', 'done'));

    if v_used >= v_quota then
      return jsonb_build_object('allowed', false, 'reason', 'trial_quota',
                                'used', v_used, 'max', v_quota);
    end if;
    return jsonb_build_object('allowed', true, 'reason', 'ok', 'used', v_used, 'max', v_quota);
  end if;

  return jsonb_build_object('allowed', true, 'reason', 'ok');
end
$function$;

COMMENT ON FUNCTION public.tenant_test_gate(text) IS
  'SATU-SATUNYA sumber kebenaran "boleh menjalankan uji atau tidak". Dipanggil 3 lapis: aturan akses '
  'direct_jobs (jalur browser), API route (jalur kunci layanan), worker (job yang sudah antre). '
  'Hasil: {allowed, reason, [status|used|max]}. reason: gate_off|comp|ok|subscription|trial_quota|'
  'tenant_unknown|forbidden. SSOT = PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §10.';

-- ── 3. Pelepas rem channel — dipanggil KELIMA jalur reaktivasi ───────────────────────────────────
-- Sebelum ini, rem circuit-breaker hanya dilepas oleh "Jalankan ulang" yang sukses. Karena jalur itu
-- kini dikunci untuk tenant tak aktif, tenant yang baru membayar akan TERJEBAK: channel berhenti,
-- dan satu-satunya pelepasnya terkunci. Fungsi ini menutup jebakan itu.
CREATE OR REPLACE FUNCTION public.tenant_resume_channels(p_tenant_id text)
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

  -- Melepas rem TIDAK memaksa channel berproduksi: gerbang kesiapan (channel_missing) dan gerbang
  -- langganan tetap berlaku sesudahnya. Ini hanya mencabut penghenti darurat.
  update channels
     set production_paused = false,
         production_paused_reason = null,
         production_paused_at = null,
         updated_at = now()
   where tenant_id = p_tenant_id
     and production_paused = true;
  get diagnostics v_n = row_count;
  return v_n;
end
$function$;

COMMENT ON FUNCTION public.tenant_resume_channels(text) IS
  'Lepas rem circuit-breaker semua channel tenant. Dipanggil kelima jalur reaktivasi (bayar Midtrans, '
  'admin aktifkan, admin perpanjang, admin aktifkan-bersih, link 1-klik). Dijaga kenop '
  'auto_resume_on_reactivate. HANYA service_role — tenant tidak boleh melepas remnya sendiri.';

-- ── 4. Hak akses ─────────────────────────────────────────────────────────────────────────────────
-- Gerbang: authenticated WAJIB punya EXECUTE, karena aturan akses tabel memanggilnya dalam konteks
-- pengguna. Pagar privasi di dalam fungsi yang mencegah tenant mengintip tenant lain.
GRANT EXECUTE ON FUNCTION public.tenant_test_gate(text) TO authenticated, service_role;

-- Pelepas rem: MENULIS. Tenant tidak boleh memanggilnya — kalau bisa, mereka bisa melewati rem
-- circuit-breaker (3 kegagalan beruntun) dan membakar percobaan tanpa henti.
REVOKE ALL ON FUNCTION public.tenant_resume_channels(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.tenant_resume_channels(text) FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.tenant_resume_channels(text) TO service_role;

-- ── 5. LAPIS PERTAMA: aturan akses tabel antrean ─────────────────────────────────────────────────
-- Aturan lama hanya berbunyi "boleh, asal atas nama diri sendiri" — nol pemeriksaan status.
-- Inilah satu-satunya penjaga tombol "Jalankan ulang" yang menulis langsung dari browser.
DROP POLICY IF EXISTS direct_jobs_tenant_insert ON direct_jobs;
CREATE POLICY direct_jobs_tenant_insert ON direct_jobs
  FOR INSERT
  WITH CHECK (
    tenant_id = (auth.uid())::text
    AND coalesce((public.tenant_test_gate(tenant_id) ->> 'allowed')::boolean, false)
  );

COMMENT ON POLICY direct_jobs_tenant_insert ON direct_jobs IS
  'Tenant hanya boleh mengantre pekerjaan atas namanya sendiri DAN bila gerbang uji mengizinkan. '
  'Kunci layanan (API/worker) melewati aturan ini — pemeriksaannya ada di kode masing-masing.';
