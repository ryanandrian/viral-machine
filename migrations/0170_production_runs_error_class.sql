-- 0170: [ERROR-MGMT 2026-07-18] dimensi SEMANTIK error pada production_runs.
-- error_class = klasifikasi provider-agnostik (ErrorClass) → circuit-breaker berpikir MAKNA,
-- bukan teks. Nullable + additive → baris lama tak terpengaruh (nol risiko). SPEC =
-- AI_ERROR_MANAGEMENT_ARCHITECTURE.md.
alter table production_runs add column if not exists error_class text;
comment on column production_runs.error_class is
  '[ERROR-MGMT] kelas semantik error AI (account_billing|quota_exhausted|auth_invalid|rate_limit|transient|unknown). NULL=run bukan-gagal / pra-fitur.';
