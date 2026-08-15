# AUDIT ATRIBUSI NICHE/CHANNEL — SEMUA KONSUMEN CONFIG PRODUKSI (D3)

> **Mandat owner 2026-07-15 ("POINT 4 KRITIKAL — audit tuntas 5 area, tanpa asumsi setitik pun")**, pasca bug DNA
> (loader memuat visual_style niche default-tenant — fix deployed `ee125eb`, regresi 60s LULUS).
> **Metode:** inventaris SEMUA field turunan-niche → telusuri SETIAP titik baca (grep + baca konteks) →
> verdict per titik berdasarkan KODE, bukan dugaan. Kaitan backlog: `SISA_KERJA_GO_LIVE.md` changelog 2026-07-15.

## Verdict ringkas
**Pasca fix DNA (`ee125eb`): SEMUA jalur produksi ber-atribusi BENAR (niche run ter-resolve / baris data saat produksi).**
Dua temuan kelas-lain tercatat (F-2 latent, F-3 higiene) — bukan kebocoran aktif.

## Matriks titik-baca (BE, jalur produksi)

| Field turunan-niche | Titik baca | Kunci niche yang dipakai | Verdict |
|---|---|---|---|
| visual_style + visual_fallbacks (DNA) | loader `tenant_config.load()` → `_reload_niche_visual` | **niche EFEKTIF** (param run > channel > tenant) | ✅ FIXED `ee125eb` (uji 5/5) |
| section_timing | `script_engine._get_section_timing(niche)` (:96) | param = `tenant_config.niche` (run resolved) | ✅ |
| narration_persona / style / target_emotion | `script_engine` :120/:361 | `tenant_config.niche` | ✅ |
| emotion_scoring_criteria (skor emosional) | `script_engine` :1022 | `tenant_config.niche` | ✅ |
| Data hook niche | `hook_optimizer._build_prompt` :54 | `tenant_config.niche` | ✅ |
| keywords (sinyal tren) | `trend_radar` :439 | `tenant_config.niche` | ✅ |
| Profil niche seleksi topik | `niche_selector` :80/:373 | `tenant_config.niche` | ✅ |
| image_quality_tags / image_negative_prompt | `ai_image` :93 (`self.niche`) | `config["niche"]` = `tenant_config.niche` (via assembler) | ✅ |
| mood_priority (rotasi mood musik) | `producer` :184 | `niche` = `_resolve_niche(channel_row)` (:168, pool-aware) / direct `job.niche→ch.niche` (:307/:384) | ✅ |
| music_config + mood_priority (pemilih musik) | `music_selector` :49/:68 ← `renderer._mix_music` :918 | `tenant_config.niche` | ✅ |
| default_hashtags / keywords(tags) / youtube_category_id | `youtube_publisher` :131/:187/:203 ← `orchestrator/publisher` :109/:132 | **`item.get("niche")` = niche SAAT PRODUKSI (baris inventory)** → fallback channel | ✅ (video terbit membawa niche produksinya — aman walau channel ganti niche sebelum slot publish) |
| Analytics/insight/learning | `channel_analytics`/`performance_analyzer`/`self_learning` | per **channel_id** + per-video (B16 fix per-koneksi; B15 filter delisted) | ✅ (bukti era B16/B15, tidak diaudit ulang per §1.3) |

## Permukaan lain
- **DB:** duplikat vestigial `tenant_configs.niche`/`niche_pool` — TIDAK dibaca konsumen produksi mana pun di luar
  default-path loader (grep: nol konsumen); kandidat pembersihan → **[B5]** (F-3).
- **FE-tenant:** Runs/antrean = niche & channel dari BARIS run/inventory itu sendiri (`runs-table` :33/:114) ✅ ·
  Insights/Compliance = `channel_insights` by channel_id (F2-13b) ✅ · picker niche = entitlement per-channel ✅.
- **FE-admin:** editor niche menulis by `niche_id` ✅ · agregat admin via RPC ber-scope ✅.
- **FE-marketing:** kata "niche" hanya copy statis — NOL data ber-atribusi niche ✅.

## Temuan (bukan kebocoran aktif — keputusan owner)
- **F-2 (kelas §3.3) — ✅ SUDAH DITUTUP 2026-07-15, bukan "menunggu ketok".** 6 titik dulu memakai pola
  `niche tak dikenal → pakai niche AKTIF PERTAMA` (script_engine, hook_optimizer, niche_selector ×2, loader);
  substitusi senyap = kelas yang sama dengan pelanggaran fallback 14-Jul. Keenamnya **kini gagal-jujur**
  (run STOP + notifikasi), diverifikasi baris-per-baris 15-Agu.
  ⛔ **Baris ini sempat menulis "MENUNGGU KETOK" selama sebulan padahal kodenya sudah benar** — dan itu
  jenis kalimat yang membuat sesi berikutnya "memperbaiki" yang sudah beres, lalu merusaknya. Dikoreksi
  2026-08-15 (`SISA_KERJA [B32]` T8). Yang benar-benar kurang bukan kodenya, melainkan **penjaganya**:
  kini `tests/test_niche_tak_dikenal_gagal_jujur.py` (4 uji perilaku; sabotase 1 titik ⇒ merah).
- **F-3 (higiene):** duplikat `tenant_configs.niche`/`niche_pool` vestigial → masuk **[B5]** sapu fosil.

## Batas audit (jujur)
Audit ini = **atribusi jalur produksi + permukaan tampil**. Tidak mencakup: kebenaran ISI tiap field (kurasi admin),
dan modul billing/lifecycle (tak menyentuh niche — diverifikasi grep).
