# Audit UX — AI Provider/Model (Admin Catalog · Integrasi Tenant · Channel Setting)

> Audit 2026-07-07, berbasis kode nyata (file:baris terverifikasi). Standar = world-class best practice untuk ribuan tenant awam + admin. Tolok ukur internal = halaman **Integrasi tenant** yang sudah baik.

## 🟩 STATUS REALISASI (update 2026-07-08)
- **FASE 1 = ✅ SELESAI + DEPLOYED + DISEGEL.** Commits `f2defec` (1a-1e) + `2861ec1` (fix status `published`) + `390b406` (siklus hidup kartu hasil: Tutup/TTL `app_config.test_result_ttl_hours` migr 0145/terganti test baru). Disegel via **verifikasi 10-butir end-to-end** (panel tenang; konfirmasi; stepper dari 16 baris STEP nyata; sukses+tautan Studio+channel unpause LIVE; gagal sopan; dismiss persisten; usang 24j; terganti; reaper teruji sintetis; call-site niche/admin tak berubah). Insiden selama Fase 1 & pelajarannya: reuse komponen TANPA verifikasi vocab status (`published` vs `done`) → bug "antre"; kartu hasil tanpa siklus hidup → tampil permanen. Keduanya ditutup.
- **FASE 2-4 = ⬜ BELUM DIMULAI** — menunggu perintah owner (sengaja tidak menumpuk fase di atas fondasi yang belum dinyatakan tenang).
- Temuan Katalog admin yang sudah tertutup lebih dulu (sesi 2026-07-07, commits `1996423`/`8c22b83`/`0b7a989`): dropdown enum semua field + validasi server + tombol "Uji model" + badge status uji + probe harga. Sisa temuan form admin (A1-A4 label/help/duplikat-PK/inline-error) = bagian Fase 2.

## Ringkasan verdict
- **Integrasi tenant** (`(app)/integrations/page.tsx`) — **sudah baik** (baseline). Label manusiawi, deskripsi per-elemen ("AI penulis cerita, hook & narasi"), badge Gratis, error **inline** per field, pengelompokan LLM/TTS/Visual. Hanya 1 gap kecil.
- **Katalog admin** (`admin/(panel)/catalog/page.tsx` + `api/admin/catalog/route.ts`) — **belum world-class.** Label = nama kolom DB, panduan sempit, error mentah/transient, tak menskala.
- **Channel Setting** (`(app)/channels/[id]/page.tsx`) — **1 gap vision-critical**: pemilih model buta-budget.

---

## TEMUAN (dengan bukti + tingkat keparahan)

### 🔴 KRITIS — meleset dari visi inti
| ID | Temuan | Bukti | Kenapa di bawah world-class |
|---|---|---|---|
| **C1** | Pemilih model tenant **buta-budget** — tak ada harga/tier/tanda gratis saat memilih | `channels/[id]/page.tsx`: kemunculan `pricing/cost/tier` = **0** | Visi = tenant memilih **sesuai budget (gratis/regular/premium)**. Tanpa info biaya di titik pilih, tenant memilih dalam gelap. |
| **C4** | **Test now / Run & recover** buta: ADA konfirmasi (`ConfirmDialog`), TAPI **tak ada progres berjalan** & **tak ada laporan hasil** (sukses/gagal) | `channels/[id]/page.tsx`: `testNow()` hanya set `testMsg` sekejap; tak ada polling/stepper; `<TestNichePanel>` (yg punya ketiganya) TAK dipakai di sini | Tenant menekan → buta total → mengira nihil. Sudah ada solusi matang (`TestNichePanel` + `lib/test-run.latestTestResult`) yang dipakai Niche Studio & Admin Niche — tinggal dipakai. |
| **C5** | Job direct "producing" bisa **nyangkut berjam-jam** tanpa timeout/penjaga → recover tak pernah jalan | insiden nyata 2026-07-07: job 08:42 "producing" 7 jam, channel tetap pause | Butuh reaper: job melewati batas-waktu → tandai gagal + beri tahu. |

### 🟠 TINGGI — kejelasan & kebenaran admin
| ID | Temuan | Bukti | Kenapa di bawah world-class |
|---|---|---|---|
| **A1** | Nama kolom DB jadi label UI | `catalog/page.tsx` `ADD_FIELDS`: `"provider_key (PK)"`, `"auth_type (api_key/none)"`, `"model_id (ID resmi di provider — SERTAKAN versi…)"` | Label harus manusiawi + jargon disembunyikan. |
| **A2** | Panduan field sempit/menyesatkan, tak ada contoh/bantuan terpisah | label = petunjuk yang dijejalkan; tak ada help-text/tooltip | Admin rawan salah isi (mis. `model_id`, `base_url`). |
| **A3** | Duplikat PK → error **mentah Postgres** di toast 2,2 dtk, HTTP 500 | `route.ts`: `.insert()` → `if(error) status 500 error.message`; FE `setToast("Gagal: "+error)` | Data AMAN (insert bukan upsert → ditolak, tak menimpa), TAPI feedback tak jelas. Harusnya 409 + "ID sudah dipakai" + cek ketersediaan sebelum submit. |

### 🟡 SEDANG — skala & konsistensi
| ID | Temuan | Bukti | Kenapa di bawah world-class |
|---|---|---|---|
| **A4** | Error (termasuk penolakan enum) via **toast 2,2 dtk**, bukan inline di field | `catalog/page.tsx` `setToast` untuk semua galat form | Integrasi tenant sudah pakai error inline — Katalog belum. |
| **A5** | Tak ada **cari/saring/kelompok** model | `catalog/page.tsx` tak ada input search untuk models (tabel padat) | Visi "sediakan sebanyak-banyaknya model" → ratusan baris tak terpakai tanpa cari/saring. |
| **C2** | Urutan admin (`sort_order`) **diabaikan** di pemilih tenant | `channels/[id]/page.tsx`: model dimuat `.order("display_name")`, bukan `sort_order` | Admin tak bisa menonjolkan model rekomendasi/termurah. |
| **X1** | Konsistensi antar-halaman | Katalog (toast+label mentah) vs Integrasi (inline+label manusiawi) | Satu produk harus konsisten di bar tertinggi. |

### 🟢 RENDAH — poles
| ID | Temuan | Bukti | Catatan |
|---|---|---|---|
| **I1** | Status "Tersimpan" vs "Valid" tak dijelaskan | `integrations/page.tsx` badge tanpa tooltip | Owner pernah bingung bedanya. Tooltip: "Tersimpan = belum teruji". |
| **C3** | Tak ada estimasi biaya per video saat memilih | — | Melengkapi C1. |
| **A6** | "Uji model" minta tempel kunci tiap kali; tak ada peringatan bahwa uji memakai kuota nyata | `model_tester` butuh key | Bisa reuse kunci pool + info "uji memakai kuota". |
| **A7** | `key_group` free text (typo → kredensial 1 vendor terpisah) | `ADD_FIELDS` providers | Datalist (saran nilai existing). |

---

## Rencana perbaikan bertahap (usulan urutan)

**Fase 1 — Channel Setting: vision-critical + alur test (paling berdampak, satu halaman):**
- **1a** C1: tampilkan **tier + tanda gratis + estimasi biaya** di pemilih model (LLM/TTS/Visual) — [pakai-ulang: `ai_models.pricing` + `quality_tier` + `auth_type` sudah ada].
- **1b** C2: hormati `sort_order` (urutan kurasi admin) + **1c** C3 (estimasi biaya per video).
- **1d** C4: ganti flow "Test now / Run & recover" yang buta dengan **`<TestNichePanel>`** (konfirmasi + progres live + hasil sukses/gagal + preview video) — [pakai-ulang komponen + `lib/test-run.latestTestResult`; tambah endpoint tipis `/api/channels/[id]/test` + keying per-`channel_id` di helper].
- **1e** C5: **reaper job "producing" nyangkut** (batas-waktu → gagal + notif) — satu-satunya bagian benar-benar baru.

### Aset yang DIPAKAI-ULANG (bukan bikin baru — aturan world-class)
| Aset | Sudah mengerjakan | Dipakai di |
|---|---|---|
| `components/test-niche-panel.tsx` | konfirmasi + progres live (stepper STEP n/7 + bar + log) + status QC lolos/catatan/gagal + preview video + polling 5s | Niche Studio (tenant), Pustaka Niche (admin) |
| `lib/test-run.latestTestResult()` | rakit status + progres nyata (parse `pipeline_run_logs`) + video_url | endpoint niche-test |
| `components/confirm-dialog.tsx` | popup konfirmasi standar (`open`, `busy`, onConfirm/onCancel) | banyak halaman |
| auto-recover worker (`producer.py`) | 1 test sukses → unpause channel otomatis | — |

**Fase 2 — kualitas form admin:**
- A1 label manusiawi + A2 help-text/contoh per field + A3 duplikat PK ramah (409 + "ID sudah dipakai" + cek sebelum submit) + A4 error inline.

**Fase 3 — skala & konsistensi:**
- A5 cari/saring/kelompok model + X1 samakan bar Katalog ke Integrasi.

**Fase 4 — poles:**
- I1 tooltip status + A6 + A7 datalist.

Tiap fase lewat gerbang kerja: proposal detail → persetujuan → eksekusi + bukti nyata → (baru) deploy per batch. Tak ada klaim "selesai" tanpa bukti.
