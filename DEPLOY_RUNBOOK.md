# DEPLOY RUNBOOK — v2 Cutover (worker_decoupled + webhook_app)

> Panduan eksekusi GATE CUTOVER (§GATE CUTOVER di `PROGRESS.md`). **v1 produksi jangan disentuh sampai langkah F.**
> Catatan: file `.md` **tidak** ikut ke VPS (sparse-checkout exclude `*.md`) — runbook ini dibaca lokal.
> Prasyarat: §PERBAIKAN PRODUCE & PUBLISH = ✅ selesai.

## Arsitektur deploy (siapa di mana)
```
Tenant browser ─┬─► Vercel (apps/web, Next.js)        anon key + RLS · RPC whitelist
                │        │  server-to-server (X-Internal-Secret)
                │        ▼
                └─► VPS  ├─ webhook_app (FastAPI/uvicorn:8088)  ← Midtrans webhook + YouTube OAuth + /api/keys/set
                         └─ worker_decoupled.py (loop)          ← producer/publisher/janitor/self-learning/renewal/email_outbox/heartbeat
                              ▲
                         Supabase v2 (atliatnjhysdibmfypul) = papan antrian/state · S3 Biznet = buffer video
```
**🔑 Pemisahan kunci (WAJIB):** `ENCRYPTION_KEY` (Fernet) + `MV_INTERNAL_SECRET` + `OAUTH_STATE_SECRET` + service_role **hanya di VPS**. **JANGAN** taruh `ENCRYPTION_KEY`/service_role di Vercel.

## Env — apa di Vercel vs VPS
**Vercel (apps/web) — Project env:**
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (anon, publik)
- `SUPABASE_SERVICE_ROLE_KEY` (server-route admin saja — Vercel server env, bukan NEXT_PUBLIC)
- `MV_API_BASE` = `https://api.mesinviral.com` (host webhook_app VPS)
- `MV_INTERNAL_SECRET` (== nilai di VPS)
- `NEXT_PUBLIC_YT_REDIRECT_URI` = `https://api.mesinviral.com/api/youtube/oauth/callback`

**VPS (`.env`, gitignored) — worker + webhook_app:**
`SUPABASE_URL`, `SUPABASE_KEY`(service_role), `ENCRYPTION_KEY`, `OAUTH_STATE_SECRET`, `MV_INTERNAL_SECRET`,
`YOUTUBE_OAUTH_REDIRECT_URI`(=callback prod), `APP_BASE_URL`(=`https://app.mesinviral.com`),
`SMTP_*`, `MIDTRANS_*`(+`MIDTRANS_ENV=production`), AI/storage (OPENAI/ANTHROPIC/PEXELS/REPLICATE + S3/Biznet dari `S3-CONNECTION.md`), `TELEGRAM_*`, **`YOUTUBE_PLATFORM_API_KEY`** (velocity mining Trend Radar — di GCP **restrict ke IP VPS** saat prod, lihat `TREND_RADAR_ARCHITECTURE.md §7`), opsional `PRODUCER_MAX_RENDER`/`PRODUCER_BUFFER_DEPTH`/`HEARTBEAT_INTERVAL_SEC`.
> **Migrasi DB:** v2 DB sudah ter-apply **0001-0049** (incl. 0048 `trend_cache` + 0049 `source_weights`) — worker prod tinggal menunjuk DB v2; **tak ada langkah migrasi terpisah** saat cutover.
> **⚠️ ROTASI semua secret dev sebelum publik** (DB pw, service_role, anon, OAUTH_STATE_SECRET, MV_INTERNAL_SECRET, SMTP, Midtrans, ElevenLabs) — §GATE CUTOVER E1.

## A. Persiapan kode di VPS
```bash
ssh -i ~/.ssh/vps_key rad4vm@103.103.22.227
cd ~/viral-machine && git fetch origin && git checkout v2-backend && git pull   # (saat cutover; v1=main)
python3.11 -m pip install -r requirements.txt   # fastapi+uvicorn+cryptography sudah masuk (migr A1)
```

## B1. systemd — worker_decoupled (produksi/publish/buffer/heartbeat)
`/etc/systemd/system/mv-worker.service`:
```ini
[Unit]
Description=MesinViral v2 worker (decoupled)
After=network-online.target
[Service]
User=rad4vm
WorkingDirectory=/home/rad4vm/viral-machine
EnvironmentFile=/home/rad4vm/viral-machine/.env
ExecStart=/usr/bin/python3.11 scripts/worker_decoupled.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
```

## B2. systemd — webhook_app (Midtrans + YouTube OAuth + keys-vault)
`/etc/systemd/system/mv-webhook.service`:
```ini
[Unit]
Description=MesinViral v2 webhook_app (FastAPI)
After=network-online.target
[Service]
User=rad4vm
WorkingDirectory=/home/rad4vm/viral-machine
EnvironmentFile=/home/rad4vm/viral-machine/.env
ExecStart=/usr/bin/python3.11 -m uvicorn src.billing.webhook_app:app --host 127.0.0.1 --port 8088
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now mv-worker mv-webhook
journalctl -u mv-worker -f   # cek loop hidup; journalctl -u mv-webhook -f
```

## B3. nginx — route ke webhook_app (api.mesinviral.com → :8088)
```nginx
server {
  server_name api.mesinviral.com;
  location / {
    proxy_pass http://127.0.0.1:8088;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
# (certbot --nginx -d api.mesinviral.com untuk TLS)
```
Endpoint yang terlayani: `/api/webhooks/midtrans*`, `/api/youtube/oauth/{init,callback,disconnect,status}`, `/api/keys/set`, `/health`.

## C. Konfigurasi akun eksternal (dashboard owner)
- **C1 Midtrans:** isi Server/Client key **produksi** + `MIDTRANS_ENV=production`; daftarkan 3 Notification URL → `https://api.mesinviral.com/api/webhooks/midtrans` (+/recurring,/account); Finish/Error → app domain.
- **C2 Supabase Auth:** custom SMTP (`mail.lumite.biz.id`) + aktifkan Google OAuth provider.
- **C3 DNS:** `api.mesinviral.com` → VPS; `app.mesinviral.com` → Vercel.
- **YouTube BYO-CC:** redirect URI yang tenant daftarkan di GCP app mereka = `https://api.mesinviral.com/api/youtube/oauth/callback` (dokumentasikan di onboarding).

## D. Smoke test (setelah deploy)
1. `curl https://api.mesinviral.com/health` → `{"ok":true}`.
2. **YouTube OAuth 1× consent NYATA** (GCP app uji + browser) → cek row `tenant_credentials` terisi (Fernet).
3. SMTP egress dari VPS (kirim test) → email diterima.
4. Midtrans 1× transaksi → webhook → `payments` + aktivasi.
5. 1 video e2e via worker (cek `production_runs` + publish slot dari `channels.publish_slots`).

## E. Keamanan
- Rotasi semua secret (lihat atas) · isi kredensial channel admin-test (Test Lab) · (opsional) ElevenLabs re-subscribe.

## F. Cutover (flip)
1. Stop worker v1 (VPS): matikan crontab `@reboot ... worker.py` + kill proses v1.
2. Pastikan `.env` VPS → DB v2 (sudah). Aktifkan `mv-worker` + `mv-webhook`.
3. Vercel pointing DB v2 + env di atas → go-live `app.mesinviral.com`.
4. Pantau 1–2 siklus produksi/publish. v1 pensiun penuh.
