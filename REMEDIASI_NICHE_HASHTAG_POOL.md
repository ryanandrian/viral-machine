# Remediasi: Niche-Pool (random dari pilihan) + Hashtag per-niche channel-owned

> **Dibuat:** 2026-06-27 · Format: **Plan vs Realisasi** (disiplin aturan kerja).
> **Fokus terkunci owner:** **caption + hashtag SAJA.** Card "Branded (CTA·logo·link)" + fosil CTA/kategori/tag = **DITUNDA** (lihat §6).
> **Prinsip:** nol asumsi liar · tanpa merusak yang sudah baik · reuse komponen design-source (nol komponen baru) · validasi lokal per-batch sebelum deploy.

---

## 1. Konteks & keputusan (disepakati owner)

- **Caption (subtitle) SUDAH BENAR** — channel-level (`channels.caption_style`) + default (`DEFAULT_CAPTION_STYLE` BE) + override-save per channel. **TIDAK DIUBAH.**
- **Random niche WAJIB dari `niche_pool` (pilihan tenant), BUKAN seluruh entitlement.** Niche bisa puluhan/ratusan → UX pemilih harus skala-besar (pencarian), bukan daftar centang panjang.
- **Mode disimpulkan dari jumlah pilihan:** 1 niche = `fixed`, >1 niche = `random` (otomatis). Tenant tak perlu paham istilah teknis.
- **Hashtag:** 1 niche → hashtag channel = hashtag niche itu; >1 niche → per-niche. **Milik channel tenant tsb (privat/RLS), tidak bocor antar tenant. Tidak ada hashtag global channel.**
- **Card channel** tampilkan **"Menggunakan Niche / Used Niche"** dari `niche_pool`; >1 → tanda **acak** (ikon lucide `Shuffle`).
- **Ikon & komponen** ikut nuansa yang ada (lucide; `.chip`/`.chip-input`/`.radio-pill`/`.input`).

## 2. Fakta terverifikasi (DB LIVE + kode, bukan asumsi)

| Area | Temuan (file:baris) |
|---|---|
| BE producer | `producer.py:39-46` — random = **seluruh entitlement**, komentar: "`niche_pool` deprecated, TIDAK dipakai". ❌ harus pool. |
| BE pipeline | `pipeline.py:738-741` — random dari `niche_pool` (jalur cadangan, konsisten dgn target). ✓ |
| FE detail | `channels/[id]/page.tsx:711` — input hashtag map `nicheOpts` (semua niche akses, baris 359-363), **bukan** pool. ❌. Tak ada UI pilih pool utk random. |
| FE create | `channels/new/page.tsx:55,72` — sudah multi-select + simpan `niche_pool` (pola `.radio-pill`+`Check` ditiru). ✓ |
| RPC | `set_channel_niche(p_channel_id, p_niche, p_niche_mode)` — **belum** terima `niche_pool` → perlu diperluas. |
| DB hashtag | `channels.niche_hashtags` (JSON per-niche, RLS per-tenant ✓) · `niches.default_hashtags` **KOSONG** semua → perlu seed. |
| BE publisher | `youtube_publisher.py:90-110` — niche-tags hanya dari `channels.niche_hashtags[niche]`; bila kosong → tak ada niche-tag. Perlu **fallback ke `niches.default_hashtags`**. |
| Caption | `video_renderer.py:135-140` default+override ✓ — **tak disentuh**. |

## 3. Target arsitektur (hashtag = 2 LAPIS — terkonfirmasi 2026-06-27)

> Niche Studio (admin) SUDAH punya field "Default hashtags" → `niches.default_hashtags` (`niche-studio/page.tsx:132,68`).
> Jadi niche-default = fitur nyata. Model 2 lapis: niche kasih default, channel override (channel pegang nilai final).

| Lapis | Diatur di | Milik | Peran |
|---|---|---|---|
| Default hashtag niche | Niche Studio (admin) → `niches.default_hashtags` | topik (umum per-niche) | nilai default |
| Hashtag channel | Pengaturan Channel (tenant) → `channels.niche_hashtags[niche]` | channel (privat/RLS) | override |

**Resolusi saat publish (per niche video):** `channels.niche_hashtags[niche]` (bila non-kosong) **→ else `niches.default_hashtags[niche]`** → + topic-tags (script) + `#Shorts` (format). Jumlah input FE = mengikuti `niche_pool`. **Tak ada hardcode #hashtag di kode** (yang hardcode = `NICHE_BASE_TAGS`/CTA/category = ditunda §6). Tak bocor antar tenant (override channel privat).

## 4. BATCH (urut; validasi lokal tiap batch sebelum deploy)

### BATCH 1 — DB (migrasi 0096)  ✅ SELESAI (2026-06-27)
- [x] **Perluas RPC `set_channel_niche`** → terima `p_niche_pool text[]` (default NULL); validasi entitlement tiap niche di pool; simpan `niche`, `niche_mode`, `niche_pool`. (Pertahankan validasi entitlement yang ada.)
- Fasilitas admin default-hashtag **SUDAH ADA** (Niche Studio `niche-studio/page.tsx:132` → `niches.default_hashtags`). Tak perlu bikin.
- [ ] **(OPSIONAL — nunggu OK owner)** Seed `niches.default_hashtags` utk 4 niche dari data nyata channel ryan (proven) biar tak mulai kosong. Sisanya admin isi via Niche Studio.
- **Validasi:** RPC dipanggil dgn pool → tersimpan; ryan tetap valid.

### BATCH 2 — BE  ✅ SELESAI (2026-06-27, validasi lokal lolos)
- [x] `producer.py` `_resolve_niche` — random dari `channels.niche_pool` (bukan entitlement); fixed → `channels.niche`; hindari 1-2 terakhir dalam pool.
- [x] `youtube_publisher.py` — `_niche_default_hashtags()` helper + niche-tags fallback ke `niches.default_hashtags[niche]` saat channel kosong.
- **Validasi lokal:** py_compile OK · random 100× selalu ∈ pool · fixed→base · pool kosong→base · default niche terbaca dari DB. (Deploy bareng BATCH 3.)

### BATCH 3 — FE  ✅ SELESAI (2026-06-27, build EXIT=0, deployed)
- [x] `channels/[id]` kartu niche: pemilih skala-besar (kotak cari `.input` + chip `.chip-input`/`.chip` + hasil `.radio-pill`); mode disimpulkan dari jumlah; simpan via RPC `p_niche_pool`. State `niche`/`nicheMode` mati dibuang.
- [x] `channels/[id]` kartu hashtag: input IKUT `niche_pool` + placeholder dari `niches.default_hashtags`.
- [x] `channels/page.tsx` ChannelCard: label "Menggunakan Niche/Used Niche" + ikon `Shuffle` + "(acak)" saat >1 + truncate "+N".
- **Validasi:** `next build` EXIT=0 nol error; deployed (commit `fea42a4`), mv-web active.

### BATCH 4 — Memory & dok  ✅ SELESAI (2026-06-27)
- [x] `[[decisions_niche_model]]`: tambah keputusan 2026-06-27 (random = dari `niche_pool`; mode disimpulkan) → supersede keputusan 2026-06-18.
- [x] Doc ini SELESAI + DoD (lihat §5).

## 5. Definition of Done
- Random hanya memproduksi niche di dalam `niche_pool` (terbukti BE).
- FE: pemilih niche skala-besar (search+chip, komponen lama), card hashtag ikut pool, ChannelCard "Used Niche" + ikon acak.
- Hashtag: per-niche, channel-owned (RLS), seed dari niche-default, **nol hardcode #hashtag**, nol bocor antar tenant.
- Caption & Branded **tak tersentuh**; produksi/publish ryan tetap jalan (regresi aman).

## 6. BATCH 5 — Fosil per-niche → DB (KEPUTUSAN OWNER 2026-06-27, siap eksekusi)

> 🔵 **MULAI DI SINI (sesi baru).** BATCH 1-4 (random-pool + hashtag 2-lapis + FE picker/card + pisah card caption/hashtag) **SELESAI + deployed + regresi ryan aman**. Yang TERSISA = 3 fosil hardcode di `src/distribution/youtube_publisher.py` (terikat 4 niche ryan: universe_mysteries/dark_history/ocean_mysteries/fun_facts → niche lain SALAH/KOSONG). Owner sudah memutuskan pendekatannya (di bawah). **Urutan: 5A dulu (tag video) → lapor → 5B (kategori) → 5C (CTA, bareng Branded).** Disiplin: validasi LOKAL penuh tiap sub-batch → deploy. JANGAN bikin bug baru.
>
> **Konteks "tag video":** field `snippet.tags` YouTube = label TERSEMBUNYI (penonton tak lihat) untuk pencarian & rekomendasi YouTube. BEDA dari #hashtag (terlihat). Saat ini diisi hardcode `NICHE_BASE_TAGS`.

### 5A — TAG VIDEO  ✅ SELESAI (2026-06-27, commit `5899824`, deployed mv-worker, regresi aman)
**Keputusan owner: Opsi A — pakai-ulang `niches.keywords`** (kolom SUDAH ada + SUDAH terisi + SUDAH bisa diedit di Admin Niche Library `Identity tab` & Niche Studio). Tak perlu kolom/field baru.
- File: `src/distribution/youtube_publisher.py`.
  - Hapus dict hardcode **`NICHE_BASE_TAGS`** (saat ini ~baris 79-84).
  - Di `_build_metadata`, baris yang isi `tags` (saat ini ~baris 166: `tags = list(self.NICHE_BASE_TAGS.get(niche, []))`) → ganti baca **`niches.keywords`** dari DB via helper baru `_niche_video_tags(niche)` (pola SAMA dgn `_niche_default_hashtags()` yg sudah ada di file ini — fungsi modul-level, fail-soft `[]`, baca `sb.table("niches").select("keywords").eq("niche_id",niche)`).
  - Daftar universal video-tags (saat ini ~baris 174: `["shorts","youtubeshorts","viral","facts"]`) → **buang `"facts"`** (mengasumsikan niche fakta). Sisakan `["shorts","youtubeshorts","viral"]`.
- **JANGAN sentuh** #hashtag (sudah benar), `_niche_default_hashtags` (sudah benar), CTA, kategori.
- **Validasi lokal (WAJIB sebelum deploy):** `py_compile`; grep nol sisa `NICHE_BASE_TAGS`; uji `_niche_video_tags("ocean_mysteries")` → `['ocean','deep sea',...]` (dari DB), niche tak-ada → `[]`; pastikan `_build_metadata` masih hasilkan `tags` non-kosong (keywords + script.hashtags + kata judul + universal).
- **Deploy:** BE-only → `git pull` di `/home/rad4vm/viral-machine-v2` + restart **`mv-worker`** (publisher dipakai worker). Tak ada FE/DB. Regresi: produksi/publish ryan tetap jalan.
- **niches.keywords saat ini (verified):** universe_mysteries=[space,universe,galaxy,black hole,nasa,cosmos,astronomy] · dark_history=[history,mystery,ancient,secret,civilization,unsolved] · ocean_mysteries=[ocean,deep sea,marine,underwater,creature,abyss] · fun_facts=[did you know,facts,amazing,incredible,surprising,world record] · imunitas_tubuh=[] (admin isi nanti — graceful).

### 5B — KATEGORI YOUTUBE per-niche  ✅ SELESAI (2026-06-27): migr 0097 + BE helper `_niche_category` + FE dropdown admin & tenant + 2 allowlist API. Validasi lokal lolos (BE compile+helper; FE build EXIT=0). Deploy: worker + web.
**Keputusan owner: kategori = sifat TOPIK → field per-niche (dropdown). FE BELUM ADA (verified) → harus ditambah di admin + tenant.**
- **DB (migrasi 0097):** `ALTER TABLE niches ADD COLUMN youtube_category_id text;` + seed 4 dari `NICHE_CATEGORY` lama (universe=28, dark_history=27, ocean=28, fun_facts=27).
- **BE:** `youtube_publisher.py` — `categoryId` (`self.NICHE_CATEGORY.get(niche,"28")`) → baca `niches.youtube_category_id` via helper baru `_niche_category(niche)` (pola sama `_niche_video_tags`), fallback `"27"` (Education) / `"24"` (Entertainment). Hapus dict `NICHE_CATEGORY`.
- **FE admin** `admin/(panel)/niches/page.tsx` tab Identity (dtab 0, dekat Keywords/Default hashtags): tambah **dropdown "Kategori YouTube"** (state `edit.youtube_category_id`). **+ WAJIB tambah `"youtube_category_id"` ke allowlist `EDITABLE`** di `api/admin/niches/[id]/route.ts` (baris 5-11) — kalau tidak, tak tersimpan.
- **FE tenant** `niche-studio/page.tsx` (Business, niche privat): tambah dropdown sama (state + di `openEdit` load + di `save` patch). **+ WAJIB tambah `"youtube_category_id"` ke allowlist `EDITABLE`** di `api/niches/mine/route.ts` (baris 11-15).
- **Daftar kategori (dropdown, id→nama resmi YouTube):** 1 Film & Animation · 10 Music · 20 Gaming · 22 People & Blogs · 23 Comedy · 24 Entertainment · 25 News & Politics · 26 Howto & Style · 27 Education · 28 Science & Technology. (Definisikan sbg const bersama; default 27.)
- **Validasi:** migr applied + seed; py_compile BE; build FE; dropdown tampil & TERSIMPAN (cek DB) di admin & niche studio; publisher pakai kategori DB.
- **Deploy:** DB (migr) + BE (mv-worker) + FE (mv-web build).

### 5C — CTA deskripsi  ✅ SELESAI (2026-06-27): BE helper `_resolve_cta` ikut `channels.cta_mode` (implicit→tanpa baris CTA; soft_sell→`brand_cta_text`); dict `NICHE_CTA` dihapus; footer rapi. FE/DB nihil (card Branded sudah ada). Validasi lokal: compile+nol sisa+desc benar (implicit tanpa "Follow", soft_sell pakai teks brand). Deploy: mv-worker.
**FE SUDAH ADA (verified):** konfigurasi CTA = **tenant → Channel Settings → card "Branded (CTA · logo · link)"** = `channels.cta_mode` (implicit/soft_sell) + `brand_cta_text` (`channels/[id]/page.tsx` ~baris 747-770). **TIDAK di admin. TIDAK perlu FE baru.** → 5C = **perubahan BE kecil, bisa MANDIRI** (tak wajib nunggu kerja Branded besar).
**Temuan:** publisher MEMAKSA "Follow for more…" per-niche (`NICHE_CTA`, dipakai di `cta = self.NICHE_CTA.get(...)` lalu `footer = f"\n{cta}\n\n{hashtag_str}"`), **padahal narasi DILARANG menyuruh follow/subscribe** → kontradiksi; juga di-tempel ke SEMUA preset (termasuk 8/15s yg tak punya beat cta).
- **BE:** `youtube_publisher.py` — HAPUS dict `NICHE_CTA`; footer deskripsi ikut `channels.cta_mode` (dari `tenant_config`): `implicit` → **tanpa baris CTA** (bersih); `soft_sell` → `brand_cta_text` (kalau kosong → tanpa baris). `cta_mode`/`brand_cta_text` sudah ada di `tenant_config` (config.py:24-31,47-68).
- **DB/FE:** tidak ada.
- **Catatan:** CTA NARASI (beat, dari preset+section_timing) & MODE (implicit/soft_sell) = SUDAH benar, JANGAN disentuh. 5C hanya footer deskripsi.

### Definition of Done BATCH 5
- Nol dict hardcode per-niche di `youtube_publisher.py` (`NICHE_BASE_TAGS`, `NICHE_CATEGORY`, `NICHE_CTA` — 5C bareng Branded).
- Tag video & kategori dari DB `niches` (admin/tenant atur via editor niche). CTA dari channel (Branded).
- Niche baru apa pun dapat tag/kategori benar (tak lagi fallback ke "fun_facts"/"28"/[]).
- Regresi ryan aman; nol bug baru; validasi lokal tiap sub-batch.
