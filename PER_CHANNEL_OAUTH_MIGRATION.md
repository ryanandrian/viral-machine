# Migrasi OAuth/Kredensial: Single-channel-per-tenant → MULTI-channel-per-tenant

> **STATUS: Fase 1-6 SELESAI, tervalidasi, ter-deploy (2026-06-19).** Dokumen ini = sumber kebenaran migrasi INI (historis).
>
> **🔄 REKONSILIASI AUDIT 2026-07-01 — DOKUMEN INI SEBAGIAN SUPERSEDED:** model **BYO-CC + tabel `channel_credentials`/`tenant_credentials`** di doc ini **SUDAH DIGANTI** oleh: (a) **OAuth PLATFORM** ("Hubungkan dengan Google", `GOOGLE_CLIENT_ID/SECRET` platform — opsi B2 §8 = ADOPTED, lihat `GOOGLE_OAUTH_PLATFORM_MIGRATION.md`) + (b) **model POOL `tenant_youtube_accounts`** (koneksi 1..N per tenant, channel pilih via `channels.youtube_account_id`). **Tabel `channel_credentials`+`tenant_credentials` sudah di-DROP (migr 0095).** Multi-channel-per-tenant TETAP berlaku; hanya penyimpanan kredensial yang pindah ke pool. Arsitektur kredensial FINAL = **`CHANNEL_LOCK_ACTIVATION_PLAN.md`**. **Aksi owner tersisa** = verifikasi Google app (bukan lagi "daftar redirect URI BYO-CC per tenant").
> **Model:** 1 user = 1 tenant (TAK berubah). 1 tenant = **MULTI channel** (Pro 3, Business 10). Tiap channel = **koneksi YouTube SENDIRI**.

---

## 1. KENAPA (akar masalah)
`tenant_credentials` PK = `tenant_id` → **1 OAuth YouTube per tenant** → cuma 1 channel bisa publish. Padahal tier menjual multi-channel. Gap ini lolos sejak desain awal; diangkat & diperbaiki sesi ini.

## 2. KEPUTUSAN ARSITEKTUR (final, sudah dieksekusi)
- **Tabel BARU `channel_credentials`** (PK = `channels.id`), BUKAN mengubah PK `tenant_credentials` (hindari risiko tabel live).
- **`tenant_credentials` DIBIARKAN UTUH** sebagai **FALLBACK** (backward-compatible → produksi ryan tak putus).
- Semua fungsi BE terima `channel_id` **opsional**: ada → `channel_credentials`; tak ada → `tenant_credentials` (legacy).
- **BYO-CC tetap**: tiap tenant bawa OAuth app Google sendiri. (Opsi platform-app = B2, lihat §8.)
- **TIDAK menyentuh** kolom `channel_id` tabel lain (content_inventory/production_runs/pipeline_*/video_analytics/channel_insights) — masih TEXT-nullable; tak relevan untuk OAuth; konversi = proyek data-hygiene TERPISAH (risiko tinggi, JANGAN digabung).

## 3. FAKTA KUNCI (verified — JANGAN re-derive / asumsi)
- **Dua Google OAuth app BERBEDA:**
  - **Platform LOGIN** = `153190496639-i41l1fp3...` ("mesinviral.com") → redirect = `https://atliatnjhysdibmfypul.supabase.co/auth/v1/callback` (Supabase Auth signup/login). **JANGAN disentuh.**
  - **YouTube tenant (BYO-CC)** = ryan: `963179529813-vikbs304c29jm5ickodcvlla3q5scqna` → ini yang butuh redirect connect.
- **ryan** (`tenant_id=a410251c-cb09-492f-8342-0d829cd7de60`, channel `id=410d4538-cbbf-482a-b607-3f470031ee33`, nama YouTube **"RAD The Explorer"**, `UCo5d8bH2MnNdIuwItgPtJ6Q`, ~164 subs): kredensial YouTube **SUDAH ADA & berfungsi** (publish + analytics). `channel_credentials` ryan = backfill dari `tenant_credentials` (refresh_token cocok). **Channel ryan sudah `connected` — tak perlu aksi.**
- `MV_INTERNAL_SECRET` worker == mv-web (verified) — wajib sama (Next kirim, webhook cek).
- **NOL function/trigger Supabase terdampak** (audited): tak ada fungsi DB sentuh credentials; trigger `handle_new_tenant` (signup) tak terkait; FK `channel_credentials → channels.id ON DELETE CASCADE` (kredensial ikut terhapus saat channel dihapus = bersih).

## 3b. ⚠️ GOTCHA KRUSIAL — token = per-IDENTITAS CHANNEL, bukan per-akun-Google (insiden 2026-07-13)
Satu akun Google bisa memuat BEBERAPA channel (contoh nyata ryan: `ryan.andrian.diputra@gmail.com` =
RAD The Explorer [utama] + Mesin Viral (Test) [channel kedua] → 2 baris `tenant_youtube_accounts`,
2 token). Analytics API `channel==MINE` = channel IDENTITAS token itu SAJA — menanyakan video channel
lain memakai token ini dibalas Google **SUKSES-TAPI-KOSONG (tanpa error)**. Insiden nyata: gerbang
"fetch analytics sekali per tenant" di `self_learning.py` (peninggalan era 1-tenant-1-koneksi) menyapu
video SEMUA channel dgn token channel pertama → watch/retensi 0 senyap berminggu-minggu (saga retensi;
akar-1 scopes fix 11-Jul, akar-2 ini fix 13-Jul `f554e38`). **ATURAN: SEMUA konsumen API YouTube
ter-autentikasi (Data/Analytics/upload) WAJIB memakai koneksi channel terkait (`load_google_credentials(tenant, channel_id=...)`)
dan menyapu data HANYA channel itu — jangan pernah lintas-channel dgn satu token.**

## 4. FASE & STATUS (urut)
| Fase | Isi | Commit | Deploy | Validasi |
|---|---|---|---|---|
| **1 DB** | migr `0060_channel_credentials.sql`: tabel (PK channels.id FK CASCADE, service_role RLS) + backfill kredensial existing → channel tertua tenant | `7434301` | DB live (applied) | ✅ ryan channel_id=410d4538, refresh cocok, RLS aktif |
| **2 Loader** | `tenant_credentials.py`: `load_google_credentials(tenant_id, channel_id=None)` prefer channel_credentials→fallback; `save_google_access_token(...channel_id)`; helper `_row_to_creds` | `7434301` | (BE) | ✅ per-channel + fallback + konsisten + ch-tak-dikenal→fallback |
| **3 Konsumen BE** | `youtube_publisher._get_credentials(channel_id)` (pakai `tc.channel_id`); `channel_analytics`(__init__ channel_id, `_load_credentials`, **`sync_channel_meta(channel_id)` SCOPE ke channels.id** — fix multi-channel name-overwrite); `self_learning` per-channel | `b290bee` | mv-worker | ✅ ChannelAnalytics(channel_id)→channel_credentials→sync "RAD The Explorer"/164 |
| **4 OAuth** | `youtube_oauth.py`: `sign_state/verify_state` bawa channel_id; `save_client_creds/_store_tokens/_load_client/connection_status/disconnect` baca-tulis channel_credentials bila channel_id (else tenant_credentials); `handle_callback` ambil channel_id dari state + simpan `yt_channel_id`. `webhook_app.py`: 3 endpoint oper channel_id | `66f4e7d` | (BE) | ✅ state roundtrip t=RY/c=CH; status per-channel connected=true; ch-belum=false |
| **5 FE** | `api/youtube/{connect,status,disconnect}/route.ts` oper channel_id; `channels/[id]/page.tsx` kartu **"Koneksi YouTube" per-channel** (form client_id/secret→connect channel_id+ret=/channels/[id]; status; disconnect; tangani ?youtube=connected\|error; degradasi anggun) | `976a4bb` | mv-web | ✅ build PASS |
| **6 Deploy ops** | systemd **`mv-webhook`** (uvicorn `127.0.0.1:8088`, EnvironmentFile=worker .env) + nginx `https://mesinviral.com/api/youtube/oauth/*`→:8088 + env publik | (ops, tak di-repo) | VPS | ✅ callback publik 302; status ryan connected:true; no-secret 401 |

*Docs commit: `f13c4ff`, `a165dbd`, `bc211ca`.*

## 5. FILE YANG BERUBAH (peta lengkap)
**DB:** `migrations/0060_channel_credentials.sql`
**BE:** `src/utils/tenant_credentials.py` · `src/distribution/youtube_publisher.py` · `src/analytics/channel_analytics.py` · `src/orchestrator/self_learning.py` · `src/billing/youtube_oauth.py` · `src/billing/webhook_app.py`
**FE:** `apps/web/src/app/api/youtube/connect/route.ts` · `…/status/route.ts` · `…/disconnect/route.ts` · `apps/web/src/app/(app)/channels/[id]/page.tsx`
**OPS VPS (TIDAK di git — catat di sini):**
- `/etc/systemd/system/mv-webhook.service` (BARU): uvicorn `src.billing.webhook_app:app` :8088, User=rad4vm, EnvironmentFile=`/home/rad4vm/viral-machine-v2/.env`.
- nginx `/etc/nginx/sites-available/mesinviral`: `location /api/youtube/oauth/ { proxy_pass http://127.0.0.1:8088; ... }` (sebelum `location /`).
- worker `.env`: `YOUTUBE_OAUTH_REDIRECT_URI=https://mesinviral.com/api/youtube/oauth/callback`, `APP_BASE_URL=https://mesinviral.com`.
- mv-web `.env.local`: `NEXT_PUBLIC_YT_REDIRECT_URI=https://mesinviral.com/api/youtube/oauth/callback` (rebuild wajib — NEXT_PUBLIC di-bake). `MV_API_BASE=http://localhost:8088` (Next→vault internal).

## 6. ALUR CONNECT (cara kerja runtime)
1. FE `/channels/[id]`→Settings→Koneksi YouTube: tenant isi client_id/secret app Google-nya → POST `/api/youtube/connect` `{client_id, client_secret, channel_id, ret:/channels/[id]}`.
2. Route Next (authed, tenant_id dari sesi) → `vault(MV_API_BASE)/api/youtube/oauth/init` (+X-Internal-Secret) → `youtube_oauth.init_connection` simpan client ke `channel_credentials` + `sign_state(channel_id)` → balas `authorize_url` Google.
3. Browser → consent Google → Google redirect ke `https://mesinviral.com/api/youtube/oauth/callback?code&state` → nginx → `mv-webhook:8088` → `handle_callback`: tukar code→token, `_fetch_channel_id` (mine=true), `_store_tokens(channel_id, yt_channel_id)` ke `channel_credentials` → redirect browser ke `APP_BASE_URL/channels/[id]?youtube=connected`.
4. Worker publish/analytics: `load_google_credentials(tenant_id, channel_id)` → channel_credentials → refresh token sendiri per channel.

## 7. SISA / BELUM SELESAI (lanjutkan di sini)
- **[AKSI OWNER, eksternal Google]** Daftarkan `https://mesinviral.com/api/youtube/oauth/callback` di **Authorized redirect URIs app YouTube tenant** (ryan = `963179529813-vikbs304…`; tiap tenant di app-nya sendiri — BYO-CC). Lalu uji e2e connect channel BARU via /channels/[id]. **Tanpa ini, tombol connect channel baru gagal di langkah Google.** (Channel ryan existing TAK terpengaruh.)
- **[Belum, opsional refinement]** `channel_analytics.fetch_and_store` masih per-TENANT (sekali per tenant, pakai creds channel pertama) — belum filter video per-channel. AMAN untuk single-channel; untuk multi-channel, video channel lain ter-skip anggun (pakai creds salah). Perbaiki: fetch per-channel + filter `videos.channel_id` (HATI-HATI: video NULL channel_id bisa ter-exclude → jangan rusak single-channel).
- **[Belum, deferred — JANGAN gabung]** Konversi `channel_id` TEXT→UUID FK NOT NULL di content_inventory/production_runs/pipeline_*/video_analytics/channel_insights (data-hygiene, risiko tinggi).

## 8. OPSI MASA DEPAN — B2 (platform OAuth app, "sekali daftar untuk semua tenant")
Saat ini BYO-CC: tiap tenant bikin GCP app + daftar redirect + isi client_id/secret (friksi — lihat `ONBOARDING_FUNNEL_PLAN.md`). Alternatif **B2**: 1 OAuth app PLATFORM terverifikasi Google → tenant cukup klik "Authorize"+consent (tanpa GCP/secret). Perlu: verifikasi Google (sensitive scopes) + kuota bersama. **Kode per-channel sekarang SUDAH siap menampung B2** — tinggal ganti sumber client_id/secret dari "input tenant" → "app platform" (tanpa rombak alur per-channel).

## 9. CARA VERIFIKASI ULANG (perintah, pasca-compaction)
- DB: `select * from channel_credentials` (PK channels.id; ryan ada).
- Service: `ssh vps 'systemctl is-active mv-webhook'` (harus active, :8088).
- Callback publik: `curl -s -o /dev/null -w "%{http_code}" https://mesinviral.com/api/youtube/oauth/callback` → **302**.
- Loader/status (di VPS, `load_dotenv("/home/rad4vm/viral-machine-v2/.env")` dulu): `connection_status(RY, channel_id=CH)` → `connected:true`.

## 10. ANTRIAN LAIN (pre-existing, di luar epic ini — di PROGRESS.md)
`/compliance` multi-channel + bersihkan orphan `channel_insights.channel_id='ryan_andrian'` · BE cost-tracking (kartu Biaya AI) · dedup `top_hooks/top_topics` di `performance_analyzer` · sync 17 video belum ter-track · KPI header channel-detail (data sudah ada).
