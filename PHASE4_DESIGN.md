# PHASE 4 — BYO-CC + Auth Foundation — Rencana Desain

> Status: 🛠️ 4.1 DONE · 4.2-4.5 pending. Status LIVE = `PROGRESS.md` §PHASE 4. Keputusan auth = [[decisions_auth_rbac]].
> Tujuan akhir aplikasi: **tenant sebanyak-banyaknya** — Phase 4 = fondasi multi-tenant (isolasi data + kredensial aman per-tenant).

## Konteks tenant (owner)
`ryan` = tenant **developer + tester** (tenant #1, milik owner). Ke depan: **kupon diskon 100%/bulan by-system** → fitur **Phase 8 (payment/coupon)**, bukan Phase 4.

## Kondisi nyata v2 (verified 2026-06-13)
- 10 tabel ber-`tenant_id` (text): tenant_configs, channels, channel_insights, production_runs, production_schedules, video_analytics, videos, pipeline_queue, pipeline_run_logs, music_library. `tenant_id`=`"ryan_andrian"`.
- `auth.users`=0 (ryan belum punya Auth user). RLS parsial (8 ON tanpa policy → service_role only; 5 OFF).
- OAuth YouTube = FILE (`tokens/{tenant_id}.json`; refresh nulis balik file) — `youtube_publisher` + `channel_analytics`.
- AI keys (llm/tts/visual/youtube_api_key) di `tenant_configs` (plaintext, BYOK).

## Keputusan terkunci
`tenant_id = auth.uid()` (1 user=1 tenant, no team) · RLS `tenant_id=auth.uid()` · super-admin via `app_metadata` · simpan `display_handle`. **Senior call:** AI keys cukup RLS-protected (tak dienkripsi sekarang); `tenant_credentials` fokus OAuth (paling sensitif).

## Sub-phase
- **✅ 4.1 — Crypto + tenant_credentials (DONE):** `src/utils/crypto.py` (Fernet; `ENCRYPTION_KEY` di `.env`). Migr `0007` `tenant_credentials` (`google_*_enc`, RLS service_role-only). Validasi: encrypt≠plaintext + decrypt match + DB roundtrip ✅.
- **⏳ 4.2 — Auth user + migrasi tenant_id→UUID:** buat Supabase Auth user ryan (email `ryan@lumite.biz.id`) via service_role admin → UUID → UPDATE `tenant_id` 10 tabel + set `display_handle="ryan_andrian"`. **BUTUH v2 service_role key.** Reversibel (v2 dev). Snapshot mapping + verify count.
- **⏳ 4.3 — RLS go-live:** enable RLS semua tabel tenant + policy `tenant_id=auth.uid()` + bypass super_admin. Worker pakai **service_role** (bypass RLS — wajib). Test worker + simulasi anon SEBELUM commit.
- **⏳ 4.4 — OAuth dari DB:** `youtube_publisher` + `channel_analytics` muat OAuth dari `tenant_credentials` (decrypt) DB-first + **file-fallback** (non-breaking); refresh nulis balik ke DB (encrypt). Seed token ryan (file di VPS v1) → e2e.
- **⏳ 4.5 — Mandatory key validation:** cek key per provider terpilih di pipeline start → fail-loud + Telegram; hapus fallback file/`.env`.

## Dependency yang HANYA bisa disediakan owner
1. **v2 SUPABASE service_role key** (Supabase dashboard → Settings → API → `service_role`) — untuk 4.2 (bikin Auth user) + 4.3 (worker bypass RLS) + e2e insert. (Juga wajib worker produksi.)
2. **Token OAuth YouTube ryan** (`tokens/ryan_andrian.json`, kemungkinan di VPS v1) — untuk seed 4.4.
> Tanpa keduanya: 4.1 selesai; 4.4/4.5 bisa dibangun (code + file-fallback + dummy-test); 4.2/4.3 di-gate sampai key tersedia (selaraskan dgn build login ≈Phase 9).

## Risiko + mitigasi
- Migrasi tenant_id→UUID (ubah 10 tabel + RLS) → v2 dev (nol risiko v1), transaksi tunggal, verify count, worker service_role tak terkunci.
- Lockout RLS → test worker+anon sebelum commit; rollback = drop policy.
- v1 produksi TIDAK disentuh (branch v2-backend; cutover terpisah).
