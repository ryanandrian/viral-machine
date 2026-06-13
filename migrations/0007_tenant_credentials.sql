-- Migration 0007 — Phase 4 BYO-CC: tenant_credentials (OAuth terenkripsi)
-- Ref: project_byocc_roadmap + decisions_auth_rbac. Target: v2. JANGAN apply ke v1 sampai cutover.
-- Kredensial Google OAuth (YouTube) per-tenant, kolom *_enc = Fernet (src/utils/crypto.py).
-- Plaintext TIDAK pernah disimpan. tenant_id PK (1 user = 1 tenant). RLS: service_role only
-- (kredensial sensitif — frontend TIDAK pernah baca raw; tak ada policy → hanya service_role).

CREATE TABLE IF NOT EXISTS public.tenant_credentials (
  tenant_id                 text PRIMARY KEY,
  google_client_id          text,
  google_client_secret_enc  text,        -- Fernet
  google_refresh_token_enc  text,        -- Fernet (paling sensitif)
  google_access_token_enc   text,        -- Fernet (short-lived; di-refresh)
  token_expiry              timestamptz,
  channel_id                text,
  scopes                    jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now()
);

-- RLS ON tanpa policy → HANYA service_role (worker/backend) yang akses. Aman: kredensial
-- sensitif tak boleh dibaca anon/tenant langsung.
ALTER TABLE public.tenant_credentials ENABLE ROW LEVEL SECURITY;
