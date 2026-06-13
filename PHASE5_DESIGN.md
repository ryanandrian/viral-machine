# PHASE 5 — Multi-Channel + Decouple Producer/Publisher — Rencana Desain

> Status LIVE = `PROGRESS.md`. Pondasi+pseudo-code = `DESAIN_PRODUK_SAAS.md §12c` + [[decisions_production_scaling]] (JANGAN analisa/benchmark ulang). Tujuan: scale tenant tanpa VPS-down.

## Kondisi nyata v2 (verified 2026-06-13)
- **`channels` lengkap** (id, tenant_id, channel_group, channel_name, platform, platform_channel_id, token_path, niche, niche_mode, niche_pool, production_cron, publish_slots, is_active, is_primary) — 1 row (ryan). Multi-channel SCHEMA sebagian besar ADA.
- `channel_id` ADA di production_schedules/videos/video_analytics/pipeline_run_logs; **ditambah** ke production_runs+pipeline_queue (migr 0011).
- **`content_inventory` DIBUAT (0011)**: tenant_id/channel_id/niche/s3_key/status(producing→ready→publishing→published/failed)/metadata/target_slot/expires_at. RLS tenant-private.
- Buffer storage = **Biznet Gio S3** (`nos.wjv-1.neo.id`, West Java, co-located). Util `src/utils/s3_buffer.py` (env-driven). **S3_SECRET_KEY + S3_BUCKET pending** (S3-CONNECTION cuma access key).

## Sub-phase
- **✅ 5.1 Foundation (DONE):** `content_inventory` + `channel_id` propagation (0011) + `s3_buffer.py` util + S3 env (partial).
- **⏳ 5.2 Channel_id propagation kode:** worker→pipeline→publisher pass `channel_id` (dari `channels`); analytics filter per channel; pipeline_run_logs.channel_id terisi. (Schema siap.)
- **🛠️ 5.3 DECOUPLE producer/publisher (INTI, RISIKO TINGGI):**
  - **✅ Step 1 data-layer:** `src/orchestrator/inventory.py` (content_inventory CRUD: record_producing/mark_ready/buffer_depth/claim_oldest_ready[anti-rebut]/mark_published/revert/failed) — **tervalidasi e2e vs v2** + buffer S3 e2e ✅.
  - **✅ Step 2 Producer (DONE):** `src/orchestrator/producer.py` — `produce_one` (pipeline.run(publish=False) → upload video+thumbnail S3 → simpan script di inventory.metadata → ready) + **loop persisten `plan_and_submit`/`run_forever` dgn semaphore `MAX_CONCURRENT_RENDER=core`**. `pipeline.run` ekspos `result["script"]`. **Rem anti-OOM TERVALIDASI** (render konkuren ≤MAX, mock). produce nyata = gated run.
  - **✅ Step 3 Publisher (DONE):** `src/orchestrator/publisher.py` — `slot_due` (**timezone-aware tenant = FIX Bug 1**, tervalidasi WIB≠UTC) + dedup `_already_handled` + `publish_due_for_channel` (claim → download S3 → publish via YouTubePublisher reuse → mark_published + hapus S3; gagal → revert_to_ready; kosong → skip+log) + `run_forever` 30s. (Tak refactor pipeline.run — publisher reuse YouTubePublisher langsung, lebih aman.)
  - **✅ Step 4 Cutover — KODE DONE:** `scripts/worker_decoupled.py` (entrypoint v2: Producer + Publisher loop konkuren via thread; setup_db_logging; signal handling). **Non-destruktif** — `worker.py` lama tetap utuh. Self-driven (no pg_cron → Bug1 tuntas). Tervalidasi struktural (compile+import+wiring; `main()` TIDAK dijalankan = picu render nyata). **GATE TERSISA = RUN PRODUKSI NYATA** (deploy v2 + render + posting YouTube + biaya) = keputusan owner. Deploy: env v2+service_role+ENCRYPTION_KEY+S3_*, `PRODUCER_MAX_RENDER` = core VPS (mis. 2).
  - **Producer**: loop persisten, jaga buffer per-channel (target depth config per-niche); render → upload S3 → `content_inventory` status=ready; concurrency cap = core (anti-OOM, terbukti). 
  - **Publisher**: loop slot (timezone tenant!) → ambil ready tertua → publish → hapus S3 → status=published; buffer kosong → skip+Telegram. 
  - Trigger = **loop persisten BUKAN cron** (pegang semaphore=core); klaim multi-node `FOR UPDATE SKIP LOCKED`. Pseudo-code lengkap di DESAIN §12c.
  - **Menutup Bug 1 dispatcher-timezone** (publisher baru timezone-aware by-design; gantikan pg_cron v1 yang treat UTC).
- **⏳ 5.4 Niche gate-enforcement:** niche/niche_pool WAJIB sebelum schedule/produksi (DB constraint + onboarding). Melengkapi fail-loud Phase 1.2.
- **⏳ 5.5 Optimasi render** (dari decisions §5, prioritas #1 scale): gabung 3-pass FFmpeg→1 (2,87×) + paralel image (asyncio.gather). 35→~13 mnt.

## Dependency (owner)
- ✅ **S3_SECRET_KEY + S3_BUCKET RESOLVED** (owner, 2026-06-13). Bucket=`tobe-submitted`. **Buffer e2e ke Biznet HIJAU** (upload/download/delete proven). 5.3 decouple siap dibangun.

## Risiko + mitigasi
- **5.3 decouple = rewrite alur inti produksi+publish** → RISIKO TINGGI. Mitigasi: **design-review dulu** (seperti Phase 4); v2 dev (v1 tak tersentuh); validasi buffer-flow dgn 1 channel sebelum multi; concurrency cap wajib (terbukti OOM tanpa rem).
- Bug 1 (pg_cron v1) tetap di v1 sampai cutover; v2 pakai publisher baru.

## Rekomendasi
5.2 + 5.4 + 5.5 (channel_id, niche-gate, optimasi render) bisa lanjut bertahap. **5.3 decouple = design-review + S3 secret dulu** (paling berisiko + butuh buffer e2e).
