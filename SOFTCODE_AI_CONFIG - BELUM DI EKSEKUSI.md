# Refactor: Softcode Semua AI Library, Model, dan Provider Config

> ✅🔴 **SUDAH TEREALISASI — NAMA BERKAS INI ("BELUM DI EKSEKUSI") BASI. Diverifikasi 2026-08-05.**
> Tujuan dokumen ini (*"tidak boleh ada nama AI library/model/provider yang hardcode di business logic"*)
> **SUDAH TERCAPAI**, dibuktikan dengan pengukuran — bukan klaim:
> - **nol** nama model terpatri di `src/` di luar adapter & katalog (disapu: gpt-4o · claude-3 · gemini-2 ·
>   llama-3 · flux · dall-e)
> - **48 baris `ai_models`** + **9 baris `ai_providers`** hidup di DB; **12 titik** kode membaca katalog itu
>   (`get_models()` / `get_providers()`)
> - adapter LLM = registry **per-PROTOKOL** (`ADAPTERS` di `providers/llm/adapters.py`) ⇒ vendor baru yang
>   memakai protokol sama = **+1 baris DB, nol koding**
> - **nol** nominal rupiah terpatri di kode; **117 kenop** `app_config` semuanya ber-label di `/admin/app-config`
>
> **JANGAN dijadikan daftar kerja.** Status hidup = `SISA_KERJA_GO_LIVE.md`. Arsitektur AI provider/model
> yang berlaku = `ARSITEKTUR_AI_PROVIDER_MODEL.md` (berspanduk "REFERENSI — SELESAI").
> Berkas ini disimpan sebagai rekaman rancangan awal; **nama berkasnya tidak diubah** agar tautan lama
> di dokumen/commit tidak putus.

## Tujuan
Tidak boleh ada nama AI library, model, atau provider yang hardcode di business logic.
Semua harus baca dari konfigurasi tenant di database (`tenant_configs`).

---

## Aturan Utama

1. **Satu library per tenant** — jika tenant pakai `anthropic`, seluruh pipeline pakai Anthropic. Tidak ada cross-library fallback.
2. **Semua model dari DB** — tidak ada string model hardcode di luar file provider itu sendiri.
3. **Model catalog visual dari DB** — `AI_IMAGE_MODELS` di `ai_image.py` harus pindah ke Supabase.
4. **Fallback dalam library yang sama** — jika model utama gagal, fallback ke model lain dalam library yang sama, bukan pindah library.
5. **File provider boleh sebut nama library** — `elevenlabs.py`, `openai.py`, `claude.py` boleh sebut nama library karena memang file implementasinya. Yang dilarang adalah business logic menyebut nama model/library secara hardcode.

---

## Perubahan per Kategori

### 1. LLM

**Kondisi saat ini:**
- `script_engine.py:415` → hardcode `"claude-sonnet-4-6"`
- `script_engine.py:442` → hardcode `"gpt-4o-mini"`
- `script_analyzer.py:149` → hardcode `"gpt-4o-mini"`
- `hook_optimizer.py:143` → hardcode `"gpt-4o-mini"`
- `niche_selector.py:412` → hardcode `"gpt-4o-mini"`
- `ai_image.py:310` → hardcode `"claude-haiku-4-5-20251001"` (untuk prompt rewrite)
- `ai_image.py:319` → hardcode `"gpt-4o-mini"` (untuk prompt rewrite fallback)
- Cross-library fallback: jika Claude gagal → otomatis ke GPT (harus dihapus)

**Struktur config baru di `tenant_configs`:**
```json
"llm_library": "anthropic",
"llm_models": {
    "script":   "claude-sonnet-4-6",
    "utility":  "claude-haiku-4-5-20251001",
    "rewrite":  "claude-haiku-4-5-20251001",
    "analyzer": "claude-haiku-4-5-20251001",
    "fallback": "claude-haiku-4-5-20251001"
}
```
Atau jika library `openai`:
```json
"llm_library": "openai",
"llm_models": {
    "script":   "gpt-4o",
    "utility":  "gpt-4o-mini",
    "rewrite":  "gpt-4o-mini",
    "analyzer": "gpt-4o-mini",
    "fallback": "gpt-4o-mini"
}
```

**Yang harus diubah di kode:**
- `script_engine.py` — baca `llm_library` dan `llm_models.script` dari run_config
- `script_analyzer.py` — baca `llm_models.analyzer` dari run_config
- `hook_optimizer.py` — baca `llm_models.utility` dari run_config
- `niche_selector.py` — baca `llm_models.utility` dari run_config
- `ai_image.py` — baca `llm_models.rewrite` dari run_config untuk prompt rewrite
- Hapus seluruh cross-library fallback (Claude gagal → GPT) — ganti dengan retry dalam library yang sama

---

### 2. TTS

**Kondisi saat ini:**
- `tts_engine.py:154` → hardcode fallback chain `["elevenlabs", "openai_tts", "edge_tts"]`
- `tts_engine.py:156` → hardcode fallback chain `["openai_tts", "edge_tts"]`
- Cross-library fallback: ElevenLabs gagal → OpenAI TTS → Edge TTS (harus dihapus)

**Struktur config baru di `tenant_configs`:**
```json
"tts_library": "elevenlabs",
"tts_fallback": "edge_tts"
```
Fallback harus dalam ekosistem yang sama atau ke `edge_tts` sebagai free fallback universal.
`openai_tts` tidak boleh muncul di fallback chain jika primary adalah `elevenlabs`.

**Yang harus diubah di kode:**
- `tts_engine.py` — bangun fallback chain dari `tts_library` dan `tts_fallback` di run_config
- Hapus hardcode chain array di `tts_engine.py`

---

### 3. Visual Image

**Kondisi saat ini:**
- `ai_image.py:20-38` → `AI_IMAGE_MODELS` catalog hardcode di kode:
  ```python
  AI_IMAGE_MODELS = {
      "flux-schnell":     {"platform": "replicate", "model_id": "...", ...},
      "gpt-image-1-mini": {"platform": "openai",    "model_id": "...", ...},
      "stable-diffusion": {"platform": "replicate", "model_id": "...", ...},
  }
  ```
- `visual_assembler.py:217` → default `"gpt-image-1-mini"` hardcode
- `visual_assembler.py:134` → `"pexels"` hardcode di config dict

**Yang harus dilakukan:**
- Buat tabel baru `ai_image_models` di Supabase:
  ```
  model_key    (text, PK) — contoh: "gpt-image-1-mini"
  platform     (text)     — "openai" | "replicate"
  model_id     (text)     — model string untuk API call
  description  (text)
  size         (text)     — ukuran output default
  is_active    (bool)
  ```
- `ai_image.py` load catalog dari Supabase, bukan dari dict hardcode
- `visual_assembler.py` — hapus default `"gpt-image-1-mini"`, wajib ada di config tenant

---

### 4. Visual Video (DISABLED v0.2)

**Kondisi saat ini:**
- Provider list (`runway-gen3`, `kling`, `luma`) hanya di komentar — tidak ada hardcode di logic
- Status: DISABLED, belum aktif

**Yang harus dilakukan:**
- Saat di-aktifkan nanti, pastikan model catalog juga dari Supabase (tabel `ai_video_models`)
- Jangan aktifkan sebelum catalog DB sudah siap
- Untuk sekarang: tambahkan TODO comment di `ai_video.py` sebagai pengingat

---

### 5. Music (Cloudflare R2)

**Kondisi saat ini:**
- `music_selector.py:88` → hardcode default mood `"dramatic"` jika DB kosong
- `music_selector.py:193` → `R2_BUCKET` default `"viral-machine"` dari `os.getenv`
- `intelligence/config.py:35` → `r2_bucket` default `"viral-machine"`

**Yang harus dilakukan:**
- `"dramatic"` default mood → pindah ke `tenant_configs` sebagai `music_default_mood`
- R2 bucket tidak boleh ada default — jika `R2_BUCKET` tidak ada di `.env`, raise error dengan pesan jelas
- R2 credentials (`R2_ENDPOINT`, `R2_ACCESS_KEY`, `R2_SECRET_KEY`) tetap di `.env` — tidak perlu ke DB karena ini infrastructure config, bukan tenant config

---

### 6. Niche Fallback

**Kondisi saat ini:**
Hardcode `"universe_mysteries"` sebagai default/fallback di banyak tempat:
- `orchestrator/pipeline.py:575,595,599` — fallback niche saat tidak ada di config
- `intelligence/schedule_manager.py:110-111` — ultimate fallback jika semua layer gagal
- `intelligence/config.py:14` — default di dataclass `TenantConfig`
- `config/tenant_config.py:86,452,488,503` — defaults di `TenantRunConfig`
- `scripts/worker.py:79` — fallback saat read dari run_config
- `production/visual_assembler.py:287` — fallback saat read dari config
- Semua provider (TTS, visual) — fallback saat baca dari config

**Struktur config baru di `tenant_configs`:**
```json
"niche_fallback": "universe_mysteries"
```

Field ini adalah **ultimate fallback** jika niche tidak tersedia dari route apapun.
Setiap tenant bisa set niche_fallback mereka sendiri (default: `"universe_mysteries"`).

**Yang harus diubah di kode:**
- `orchestrator/pipeline.py` — baca `niche_fallback` dari run_config, bukan hardcode
- `intelligence/schedule_manager.py` — baca `niche_fallback` dari run_config
- `intelligence/config.py` — hapus default, wajib pass niche atau baca dari config
- `config/tenant_config.py` — tambah field `niche_fallback`, hapus hardcode default
- `scripts/worker.py` — baca `niche_fallback` dari run_config
- `production/visual_assembler.py` — baca `niche_fallback` dari run_config
- Semua provider (TTS, visual) — baca `niche_fallback` dari config

**Yang BOLEH tetap hardcode (bukan fallback):**
- `youtube_publisher.py` — mapping niche ke category/tags/description (ini data config, bukan fallback logic)
- Test code dengan hardcode `universe_mysteries` — tidak perlu diubah

---

## Yang TIDAK Perlu Diubah

- File provider itu sendiri (`elevenlabs.py`, `edge_tts.py`, `openai.py`, `claude.py`, `pexels.py`) — boleh sebut nama library karena memang implementasinya
- `tts_engine.py` routing string (`"elevenlabs"`, `"edge_tts"`) untuk load provider class — ini router, bukan hardcode model
- Komentar dan docstring — tidak perlu diubah
- `.env` untuk R2 credentials — tetap di environment variable

---

## Urutan Implementasi

1. **Baca semua file yang disebutkan** sebelum mulai — jangan berasumsi
2. **Buat migration SQL** untuk:
   - Tambah kolom `llm_library`, `llm_models` (jsonb) ke `tenant_configs`
   - Tambah kolom `tts_library`, `tts_fallback` ke `tenant_configs`
   - Tambah kolom `music_default_mood` ke `tenant_configs`
   - Tambah kolom `niche_fallback` ke `tenant_configs` (default: `"universe_mysteries"`)
   - Buat tabel `ai_image_models`
3. **Update `tenant_config.py`** — tambah field baru ke dataclass `TenantRunConfig`
4. **Update business logic** per kategori (LLM → TTS → Visual → Music → Niche)
5. **Update nilai di Supabase** untuk tenant `ryan_andrian` sesuai struktur baru
6. **Jangan hapus field lama** sebelum semua kode sudah baca dari field baru

---

## Catatan Penting

- Sebelum mulai: `git status` harus bersih
- Setiap perubahan file: commit terpisah per kategori
- Jangan eksekusi SQL migration — tulis dulu, konfirmasi ke user
- Jika ada yang tidak yakin → tanya user, jangan berasumsi
