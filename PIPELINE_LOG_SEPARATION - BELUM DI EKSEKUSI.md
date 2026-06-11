# Feature: Pipeline Log Separation dari Worker Log

> ⛔ **SUPERSEDED oleh Phase 3 (Pipeline Run Logs DB-based) — JANGAN implementasi pendekatan file-based di bawah ini.** Log per-run akan masuk tabel `pipeline_run_logs` di Supabase (untuk live tail UI D5 via Realtime + multi-node + aturan VPS-bersih). Disimpan sebagai referensi historis; dihapus setelah Phase 3 selesai.

## Tujuan
Pisahkan log pipeline per-run dari worker log utama. Setiap pipeline run mendapat file log terpisah dengan format:
```
logs/pipeline_{tenant_id}_{queue_id}.log
```

Sehingga:
- `logs/worker.log` — hanya berisi polling status worker dan job routing
- `logs/pipeline_*.log` — berisi detail eksekusi pipeline per-run

---

## Kondisi Saat Ini

**File:** `scripts/worker.py`

Saat ini semua output (worker polling + pipeline execution) tercampur di satu file:
```
logs/worker.log
[Worker] Idle — next poll in 30s
[Worker] ▶ Start  tenant=ryan_andrian  queue_id=3
[AIImage] Scene 1: clip_01.mp4 (5.2MB) 5s
[AIImage] ✓ Scene 2: clip_02.mp4 (4.8MB) 5s
[Worker] ✅ Done  tenant=ryan_andrian  status=done  elapsed=1421s
```

Masalah:
- Log file bisa sangat besar (mix worker + pipeline)
- Sulit melacak error per-run — harus cari di antara 1000s baris worker polling
- Logrotate rotate seluruh file, tidak per-run

---

## Solusi

### Implementasi di `scripts/worker.py`

**Lokasi:** fungsi `_run_production()`

**Sebelum:**
```python
def _run_production(job: dict, sb) -> None:
    """Eksekusi pipeline untuk satu tenant."""
    tenant_id = job["tenant_id"]
    queue_id  = job["id"]
    logger.info(f"[Worker] ▶ Start  tenant={tenant_id}  queue_id={queue_id}")
    
    try:
        from src.orchestrator.pipeline import Pipeline
        # ... pipeline code ...
```

**Sesudah:**
```python
def _run_production(job: dict, sb) -> None:
    """Eksekusi pipeline untuk satu tenant. Per-run logs ke file terpisah."""
    tenant_id = job["tenant_id"]
    queue_id  = job["id"]
    
    # ── Per-run log sink ────────────────────────────────────────────────
    run_log = f"logs/pipeline_{tenant_id}_{queue_id}.log"
    sink_id = logger.add(run_log, level="DEBUG", encoding="utf-8")
    
    logger.info(f"[Worker] ▶ Start  tenant={tenant_id}  queue_id={queue_id}")
    
    try:
        from src.orchestrator.pipeline import Pipeline
        # ... pipeline code ...
    finally:
        logger.remove(sink_id)  # Hapus sink, tutup file
        logger.info(f"[Worker] Log saved: {run_log}")
```

### Detail Implementasi

**File baru:** `/home/rad4vm/viral-machine/logs/pipeline_{tenant_id}_{queue_id}.log`

**Contoh path:**
```
logs/pipeline_ryan_andrian_1.log
logs/pipeline_ryan_andrian_2.log
logs/pipeline_ryan_andrian_3.log
```

**Struktur log:**
```
2026-05-13 10:45:23 | INFO | [Worker] ▶ Start  tenant=ryan_andrian  queue_id=3
2026-05-13 10:45:25 | INFO | [ScriptEngine] Generating script for niche=universe_mysteries
2026-05-13 10:46:30 | INFO | [AIImage] Generating 6 clips
2026-05-13 10:47:15 | INFO | [AIImage] ✓ Scene 1: clip_01.mp4 (5.2MB) 5s
2026-05-13 10:48:00 | INFO | [VideoRenderer] Rendering final video
2026-05-13 10:52:30 | INFO | [YouTubePublisher] Upload completed: https://youtube.com/shorts/...
2026-05-13 10:52:31 | INFO | [Worker] ✅ Done  tenant=ryan_andrian  status=done  elapsed=1421s
```

---

## Implementasi Steps

### Step 1: Modifikasi `_run_production()`

**File:** `scripts/worker.py`

Lokasi tepatnya di awal fungsi `_run_production()` setelah deklarasi `tenant_id` dan `queue_id`:

```python
def _run_production(job: dict, sb) -> None:
    """Eksekusi pipeline untuk satu tenant. Per-run logs ke file terpisah."""
    tenant_id = job["tenant_id"]
    queue_id  = job["id"]
    
    # ── Per-run log sink ────────────────────────────────────────────────
    run_log = f"logs/pipeline_{tenant_id}_{queue_id}.log"
    sink_id = logger.add(run_log, level="DEBUG", encoding="utf-8")
    
    logger.info(f"[Worker] ▶ Start  tenant={tenant_id}  queue_id={queue_id}")
    logger.debug(f"Pipeline log: {run_log}")
    
    sb.table("pipeline_queue").update({
        "status":     "running",
        "started_at": _now(),
    }).eq("id", queue_id).execute()
    
    try:
        from src.intelligence.config import TenantConfig
        from src.config.tenant_config import load_tenant_config
        from src.orchestrator.pipeline import Pipeline
        
        run_config = load_tenant_config(tenant_id)
        niche      = getattr(run_config, "niche", "universe_mysteries")
        tenant     = TenantConfig(tenant_id=tenant_id, niche=niche)
        result = Pipeline().run(tenant, publish=True)
        
        # ... rest of existing code ...
        
        logger.info(
            f"[Worker] ✅ Done  tenant={tenant_id}  "
            f"status={final}  elapsed={result.get('elapsed_seconds')}s"
        )
    except Exception as e:
        logger.error(f"[Worker] ❌ Failed  tenant={tenant_id}  error={e}")
        sb.table("pipeline_queue").update({
            "status":        "failed",
            "completed_at":  _now(),
            "error_message": str(e)[:500],
        }).eq("id", queue_id).execute()
    finally:
        # ── Tutup per-run log sink ──────────────────────────────────────
        logger.remove(sink_id)
        logger.info(f"[Worker] Pipeline log saved: {run_log}")
```

### Step 2: Pastikan direktori `logs/` ada

Cek di VPS:
```bash
ls -la /home/rad4vm/viral-machine/logs/
```

Jika belum ada atau permissions salah, update `logrotate` config (sudah ada di `/etc/logrotate.d/viral-machine`).

### Step 3: Test

Setelah deploy ke VPS, pantau bahwa:
1. File `logs/pipeline_*.log` muncul saat pipeline jalan
2. File `logs/worker.log` hanya berisi worker polling messages
3. Logrotate masih berfungsi (rotasi log file daily)

---

## Expected Result

**Sebelum:**
```
logs/worker.log (429MB) — semua tercampur
```

**Sesudah:**
```
logs/worker.log (~10MB) — hanya worker polling
logs/pipeline_ryan_andrian_1.log (~5MB)
logs/pipeline_ryan_andrian_2.log (~4.5MB)
logs/pipeline_ryan_andrian_3.log (~6MB)
... (per-run files)
```

Kemudahan:
- Traceback error mudah dicari di file pipeline-specific
- Cleanup per-run logs lebih granular
- Worker log tetap bersih, mudah debug worker issues

---

## Catatan

- `logger.add()` dan `logger.remove()` dari loguru sudah built-in
- File permission: inherit dari parent process (user `rad4vm`)
- Pastikan `sink_id` di-remove di block `finally` agar tidak leak file handles
- Log level: `DEBUG` agar capture semua context (bisa di-adjust kalau verbose)
