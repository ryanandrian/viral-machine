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

### BATCH 3 — FE  ⬜
- [ ] `channels/[id]` kartu niche: **pemilih skala-besar** (reuse `.input` cari + hasil `.radio-pill` + terpilih `.chip`/`.chip-input`); **mode disimpulkan** dari jumlah (1=fixed, >1=random); simpan via RPC (pool). Hapus toggle fixed/random eksplisit.
- [ ] `channels/[id]` kartu Caption & Hashtag: **input hashtag ikut `niche_pool`** (bukan semua niche) + **prefill dari `niches.default_hashtags`** bila channel belum override (tampilkan saran niche, boleh edit→jadi milik channel). (Pemisahan card caption vs hashtag — opsional, konfirmasi owner.)
- [ ] `channels/page.tsx` ChannelCard: label **"Menggunakan Niche / Used Niche"** dari `niche_pool`; >1 → ikon lucide `Shuffle` + "(acak)"; banyak → "+N".
- **Validasi:** build lokal; pilih 1→fixed, 3→random; hashtag input = pool; card tampil benar.

### BATCH 4 — Memory & dok  ⬜
- [ ] Update `[[decisions_niche_model]]`: random = **dari `niche_pool` pilihan** (bukan entitlement penuh); mode disimpulkan dari jumlah.
- [ ] Tandai doc ini SELESAI + DoD.

## 5. Definition of Done
- Random hanya memproduksi niche di dalam `niche_pool` (terbukti BE).
- FE: pemilih niche skala-besar (search+chip, komponen lama), card hashtag ikut pool, ChannelCard "Used Niche" + ikon acak.
- Hashtag: per-niche, channel-owned (RLS), seed dari niche-default, **nol hardcode #hashtag**, nol bocor antar tenant.
- Caption & Branded **tak tersentuh**; produksi/publish ryan tetap jalan (regresi aman).

## 6. ⛔ FOSIL DITUNDA — WAJIB dievaluasi mendalam SETELAH remediasi ini tuntas
> Owner 2026-06-27: catat & evaluasi mendalam setelahnya. Semua di `src/distribution/youtube_publisher.py`, hardcode per-4-niche-ryan (tidak aman multi-tenant):
1. **`NICHE_CTA`** (baris ~70) — kalimat ajakan per-niche. **Terkait card "Branded (CTA·logo·link)"** → evaluasi bareng desain Branded.
2. **`NICHE_CATEGORY`** (baris ~56) — `categoryId` YouTube per-niche → harus dari DB `niches` (kolom baru).
3. **`NICHE_BASE_TAGS`** (baris ~63) — tag kata-kunci video (beda dari #hashtag) → harus dari DB `niches`.
> Plus: `#Shorts` universal hardcode (`publisher` ~baris 102) — tinjau apakah jadi config format-level.
