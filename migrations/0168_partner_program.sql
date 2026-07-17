-- 0168: PROGRAM AGEN & AFILIASI [B21] F1 — mesin uang (SPEC = AGENT_AND_AFILIATION_ARCITECTURE.md §4)
-- 6 tabel + RLS + kenop config. RLS: TANPA policy anon/authenticated di F1 (akses HANYA service_role
-- via route ber-guard) — policy ber-skop agen/reseller menyusul F2/F3 saat login mereka lahir.

-- ── 1. AGEN (perusahaan mitra; komisi & status pajak DIATUR ADMIN — SPEC §1c) ─────────────────
create table if not exists agents (
  id                uuid primary key default gen_random_uuid(),
  company_name      text not null,
  pic_name          text,
  pic_email         text not null,
  pic_phone         text,
  status            text not null default 'active' check (status in ('active','suspended')),
  commission_type   text not null default 'percent' check (commission_type in ('flat_idr','percent')),
  commission_value  numeric not null default 0 check (commission_value >= 0),
  -- pajak (SPEC §6b): menentukan prefill potongan PPh di draft pencairan
  tax_status        text not null default 'badan_npwp'
                    check (tax_status in ('badan_npwp','badan_non_npwp','perorangan','pkp')),
  npwp              text,
  -- rekening tujuan transfer: NOMOR terenkripsi Fernet (ditulis/dibuka HANYA via mv-webhook, pola vault)
  bank_name         text,
  bank_account_enc  text,
  bank_holder       text,
  join_code         text unique,   -- tautan pendaftaran reseller khusus agen ini (dipakai F3)
  user_id           uuid,          -- login agen (diisi F2)
  notes             text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

-- ── 2. RESELLER (di bawah agen; komisi DIATUR AGEN — SPEC §1c; aktif hanya setelah agen setujui §2.4) ─
create table if not exists resellers (
  id                uuid primary key default gen_random_uuid(),
  agent_id          uuid not null references agents(id),
  user_id           uuid,          -- login reseller (diisi F3)
  name              text not null,
  email             text,
  phone             text,
  status            text not null default 'pending'
                    check (status in ('pending','active','suspended','rejected')),
  commission_type   text not null default 'flat_idr' check (commission_type in ('flat_idr','percent')),
  commission_value  numeric not null default 0 check (commission_value >= 0),
  bank_name         text,
  bank_account_enc  text,          -- terenkripsi (SPEC §2.5)
  bank_holder       text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

-- ── 3. REGISTRY KODE (SATU daftar lintas agen+reseller — unik GLOBAL, SPEC §5g.2) ─────────────
create table if not exists partner_codes (
  code         text primary key check (code ~ '^[A-Z0-9]{4,12}$'),  -- disimpan UPPERCASE
  owner_kind   text not null check (owner_kind in ('agent','reseller')),
  agent_id     uuid not null references agents(id),
  reseller_id  uuid references resellers(id),
  active       boolean not null default true,
  used_count   integer not null default 0,   -- >0 = kode BEKU selamanya (jejak atribusi, §5g.2)
  created_at   timestamptz not null default now(),
  constraint chk_code_owner check (
    (owner_kind = 'agent'    and reseller_id is null) or
    (owner_kind = 'reseller' and reseller_id is not null))
);

-- ── 4. ATRIBUSI TENANT (ditulis SEKALI saat daftar, PERMANEN — SPEC §1b; PK = anti-rebutan) ───
create table if not exists tenant_attribution (
  tenant_id    uuid primary key,   -- = auth.uid() (1 user = 1 tenant); tanpa FK lintas-schema auth
  agent_id     uuid not null references agents(id),
  reseller_id  uuid references resellers(id),
  code         text not null references partner_codes(code),
  locked_at    timestamptz not null default now()
);

-- ── 5. PENCAIRAN BULANAN ke AGEN (1 baris per agen per periode; gerbang owner — SPEC §1d/5c) ──
create table if not exists agent_payouts (
  id                    uuid primary key default gen_random_uuid(),
  agent_id              uuid not null references agents(id),
  period_month          date not null,              -- tanggal 1 bulan periode (kalender-settlement §5g.4)
  gross_commission_idr  numeric not null default 0,
  deduction_idr         numeric not null default 0, -- reversal refund menggantung (SPEC §2.3)
  tax_withheld_idr      numeric not null default 0, -- prefill dari tax_status (§6b), boleh dikoreksi admin
  net_paid_idr          numeric,
  status                text not null default 'draft' check (status in ('draft','approved','paid')),
  transfer_ref          text,
  notes                 text,
  approved_at           timestamptz,
  paid_at               timestamptz,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (agent_id, period_month)
);

-- ── 6. BUKU BESAR KOMISI (APPEND-ONLY: nilai tak pernah di-UPDATE; koreksi = baris reversal — §3.4) ─
create table if not exists commission_ledger (
  id                    bigint generated always as identity primary key,
  order_id              text not null,              -- payments.order_id
  tenant_id             uuid not null,
  agent_id              uuid not null references agents(id),
  reseller_id           uuid,
  gross_idr             numeric not null,           -- rupiah settlement (basis-net, SPEC §2.2)
  months_paid           integer not null default 1, -- aturan tahunan ×12 utk flat (SPEC §2.1)
  agent_rate_type       text not null,              -- snapshot rate saat kejadian (SPEC §3.6)
  agent_rate_value      numeric not null,
  agent_amount_idr      numeric not null,
  reseller_rate_type    text,
  reseller_rate_value   numeric,
  reseller_amount_idr   numeric not null default 0, -- INFORMASI utk agen (kewajiban agen, bukan kami)
  entry_kind            text not null default 'accrual' check (entry_kind in ('accrual','reversal')),
  reversal_of           bigint references commission_ledger(id),
  status                text not null default 'accrued'
                        check (status in ('accrued','approved','paid','reversed')),
  payout_id             uuid references agent_payouts(id),
  period_month          date not null,
  created_at            timestamptz not null default now(),
  unique (order_id, entry_kind)                     -- backstop idempotensi: 1 accrual + maks 1 reversal/order
);
create index if not exists idx_ledger_agent_period on commission_ledger (agent_id, period_month, status);
create index if not exists idx_ledger_tenant on commission_ledger (tenant_id);

-- ── RLS: kunci total di F1 (hanya service_role; policy ber-skop menyusul F2/F3) ───────────────
alter table agents            enable row level security;
alter table resellers         enable row level security;
alter table partner_codes     enable row level security;
alter table tenant_attribution enable row level security;
alter table agent_payouts     enable row level security;
alter table commission_ledger enable row level security;

-- ── KENOP CONFIG (SPEC §3.2 — nol angka mati di kode; description = label admin) ──────────────
insert into app_config (key, value, description) values
  ('partner_program_enabled', 1,      'Program Agen: saklar program (1=hidup, 0=mati — kode baru ditolak saat mati)'),
  ('partner_payout_day',      5,      'Program Agen: tanggal pencairan komisi tiap bulan (utk periode bulan sebelumnya)'),
  ('partner_min_payout_idr',  100000, 'Program Agen: ambang minimum pencairan (Rp); di bawah ini digulung ke bulan berikut'),
  ('partner_default_commission_value', 20, 'Program Agen: nilai komisi default saat membuat agen baru (angka; makna ikut tipe default)')
on conflict (key) do nothing;
insert into app_config (key, value, value_text, description) values
  ('partner_default_commission_type', 0, 'percent', 'Program Agen: tipe komisi default agen baru (percent | flat_idr)'),
  ('partner_tax_pct_badan_npwp',      0, '2',   'Program Agen: prefill potongan PPh23 %% — agen badan ber-NPWP (SPEC §6b; validasi konsultan)'),
  ('partner_tax_pct_badan_non_npwp',  0, '4',   'Program Agen: prefill potongan PPh23 %% — agen badan TANPA NPWP'),
  ('partner_tax_pct_perorangan',      0, '2.5', 'Program Agen: prefill potongan PPh21 %% — agen perorangan (lapisan awal PMK 168/2023)'),
  ('partner_tax_pct_pkp',             0, '2',   'Program Agen: prefill potongan PPh23 %% — agen PKP (PPN via faktur agen, bukan potongan)')
on conflict (key) do nothing;
