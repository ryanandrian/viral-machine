# 🎛️ MULTI YOUTUBE CHANNEL — Arsitektur + Plan vs Realisasi

> **STATUS: SPEC + tracker realisasi.** Backlog/status resmi = `SISA_KERJA_GO_LIVE.md` **[B11]** (hub). Marker di file ini BUKAN daftar kerja.
> **Dibuat 2026-07-08 dari audit mendalam** (3 penelusur kode + introspeksi DB live + uji fungsi `channel_missing` nyata). **Sesi baru: JANGAN audit ulang** — semua fakta di §2 sudah diverifikasi `file:baris`/DB pada commit `5250df0` era; cukup re-grep anchor sebelum menyentuh kode (kode bisa bergerak).
> **Kasus pemicu:** tenant ryan (`a410251c-cb09-492f-8342-0d829cd7de60`, plan business/10-channel) membuat channel YouTube KE-2 pada akun Google yang SAMA (`ryan.andrian.diputra@gmail.com`) → channel tambahan = identitas terpisah di sisi Google (brand/channel baru). Multi-channel belum pernah diuji A-Z.
> Dokumen pendahulu: `PER_CHANNEL_OAUTH_MIGRATION.md` (historis; model BYO-CC-nya superseded) · `CHANNEL_LOCK_ACTIVATION_PLAN.md` (model pool kredensial — tetap berlaku).

---

## §1. MODEL & ATURAN MAIN (tak berubah antar sesi)

1. **1 user = 1 tenant = MULTI channel** (kuota `plan_limits.max_channels`: trial 1 / starter 1 / pro 3 / business 10 — verified DB).
2. **Pool koneksi YouTube** = `tenant_youtube_accounts` (1 baris = 1 identitas channel YouTube ter-OAuth; token Fernet). Channel MesinViral menunjuk via `channels.youtube_account_id` + target `channels.platform_channel_id` (auto-fill dari `yt_channel_id` baris pool yang dipilih).
3. **⚠️ KENDALA GOOGLE (fakta platform, bukan pilihan kita):** SATU izin OAuth = SATU identitas channel. Layar pemilih channel (akun utama vs channel tambahan/brand) adalah **milik Google** saat consent; kode kita tidak bisa mendaftar semua channel milik akun Google dari satu token. Konsekuensi desain: daftar channel YouTube tenant di aplikasi = **akumulasi koneksi** (1 klik "Hubungkan" per channel), BUKAN hasil intip akun. `channels.list(mine=true)` mengembalikan channel milik identitas token itu saja.
4. **Aturan pemetaan (ditegakkan 3 lapis, lihat §3):** 1 channel YouTube nyata ↔ maksimal 1 channel MesinViral per tenant; koneksi duplikat (channel YouTube sama di-connect 2×) dilarang.
5. **Data & pembelajaran per-channel:** analytics penuh, `channel_insights`, dan bobot viral TIDAK boleh bocor antar channel (target Batch 2).

## §1b. PERJALANAN TENANT A-Z (verified 2026-07-08 — SATU jalur, tanpa cabang tersembunyi)

> Mandat owner: arsitektur tuntas dari registrasi pertama s/d penambahan channel — **nol turn-back**. Peta ini hasil verifikasi kode; setiap langkah menunjuk SATU implementasi (tidak ada duplikat jalur yang bisa membusuk terpisah).

| Langkah | Implementasi (satu-satunya) | Status multi-channel |
|---|---|---|
| 1. Registrasi | Supabase Auth → trigger `handle_new_tenant` (migr 0028): `tenant_configs` plan `trial` (kuota 1 channel), durasi dari `app_config.trial_duration_days` | ✅ netral (pool & channel belum ada) |
| 2. Onboarding | `/onboarding` = **PENGARAH murni** (status nyata: pool AI + `/api/youtube/status` + Telegram + RPC `channel_readiness`); TIDAK membuat apa pun sendiri — tombolnya menunjuk `/integrations` & `/channels/new` (`onboarding/page.tsx:37-46,80,91`) | ✅ nol duplikasi logika; perbaikan Batch 1 otomatis berlaku utk tenant baru |
| 3. Kredensial | `/integrations` (pool tenant-wide: `tenant_ai_accounts` + `tenant_youtube_accounts` + Telegram) | 🟡 Batch 1.5-1.6 (koneksi berwajah + used-by) |
| 4. Channel pertama | `/channels/new` (kuota FE) → draft → `/channels/[id]` checklist 7 item → Aktifkan (trigger DB) | 🟡 Batch 1.7 (picker galeri) |
| 5. Bayar/upgrade | Billing Midtrans ([A1] LIVE) → `plan_limits.max_channels` naik | ✅ (kuota server-side = Batch 3.1) |
| 6. Channel tambahan | ALUR YANG SAMA dgn langkah 4 (tidak ada jalur kedua) + connect channel YouTube tambahan di pool | 🎯 fokus Batch 1 |
| 7. Produksi & publish | worker per-channel (§2a) | ✅ + pagar 1.4 |
| 8. Analytics & belajar | self_learning per tenant→channel | 🔴 Batch 2 (G2/G3) |

## §2. HASIL AUDIT 2026-07-08 (verified — JANGAN diulang)

### §2a. SUDAH BENAR — jangan dikerjakan ulang
- **DB:** 52 kolom `channels` per-channel (niche_pool/publish_slots/voice/visual/caption/akun AI+YT); gerbang aktivasi = trigger `channels_activation_gate` (migr 0089) + fungsi `channel_missing` (migr 0094 + bahasa 0131) — SATU sumber dipakai DB+worker+FE, nol drift. Diuji live ke channel draft baru → jawaban akurat (`['penyedia naskah','penyedia suara','jenis visual','koneksi YouTube']`).
- **Producer:** iterasi & stok buffer PER-CHANNEL (`producer.py:472-514`, `inventory.py:56-60`); channel ke-2 otomatis ikut diproduksi saat aktif; pause/circuit-breaker per-channel.
- **Publisher:** klaim video terikat `channel_id` — video channel A mustahil terbit ke channel B (`inventory.py:63-80`); slot due per-channel + timezone per-tenant (`publisher.py:53-67`); cap harian per-channel (`limits.py:137-149`).
- **Config pipeline per-channel (overlay `tenant_config.py:341-398`):** llm_model/library, tts_provider/model/voice, visual_mode, image_quality, caption_style, niche_hashtags, music_*, script_min_viral_score/max_retry, content_language, duration_preset, kunci pool per-channel.
- **Kredensial:** resolusi per-channel `channels.{llm,tts,visual,youtube}_account_id` → pool; YouTube via `tenant_credentials.py:36-60`; refresh token per-baris inline.
- **FE:** kuota FE di `/channels/new` (form disembunyikan saat penuh, `new/page.tsx:53,96`); draft→checklist kesiapan 7 item + "Perbaiki →" (`channels/[id]/page.tsx:604-648`); `/integrations` multi-kunci AI + multi-koneksi YouTube; picker akun per-channel dgn ajakan ke /integrations saat pool kosong; jadwal per-channel; dwibahasa `Bi` (sebagian string kecil masih 1 bahasa).
- **Snapshot DB live 2026-07-08:** ryan = 2 channel (`410d4538` RAD The Explorer AKTIF ↔ akun pool `c3688388` `UCo5d8bH2MnNdIuwItgPtJ6Q` · `1764a359` "Mesin Viral Test" DRAFT id-ID kisah_teladan_islami slots ['13:00'] semua akun NULL); pool ryan = 1 koneksi; kumala = tenant LAIN (`fc1ab4f9`, koneksi `UCrxDh_gTK6EXfuLG4jhlPpg`); channel `67610c4a` = admin_test_internal. AI accounts ryan: elevenlabs/gemini/groq/openai/replicate semua valid *(catatan 2026-07-09: vendor Replicate+Together dibuang tuntas dari katalog+pool — commit `f2ea9a1`; akun replicate ryan sudah dihapus)*.

### §2b. GAP KRITIS (Batch 1-2) — bukti + kalibrasi jujur
| # | Gap | Bukti | Kalibrasi dampak |
|---|-----|-------|------------------|
| G1 | **Koneksi YouTube tanpa pagar human-error**: (a) consent tanpa kontrol pemilihan (`youtube_oauth.py:208-212` — hanya access_type/include_granted/prompt=consent); (b) callback simpan `yt_channel_id` saja `part="id"` tanpa nama/foto (`youtube_oauth.py:186-195,246`); (c) TIDAK ada unique `(tenant_id,yt_channel_id)` (verified index DB) → dobel-connect = baris ganda; (d) TIDAK ada guard 2 channel MV → 1 `platform_channel_id` sama; (e) publisher TIDAK memverifikasi identitas token vs target sebelum upload (`youtube_publisher.py:263-267`, grep onBehalfOf/platform_channel_id di publisher = nihil); (f) UI hanya label+ID mentah (`integrations/page.tsx:254-255`; `list_accounts` `youtube_oauth.py:311-324` tak kembalikan nama). | Alur normal FE KONSISTEN (target auto-fill dari koneksi terpilih, `channels/[id]/page.tsx:715`) → sistem TIDAK nyasar sendiri. Bahaya = manusia salah pilih di layar Google & tak ada satu pun lapis yang menangkap. Pelanggaran standar anti-human-error, bukan bug aktif. |
| G2 | **Analytics penuh channel ke-2 = nol**: `fetch_and_store` 1× per tenant pakai token channel PERTAMA (`self_learning.py:39-42`); query `ids=channel==MINE` tak memuat video channel lain (`channel_analytics.py:361-386`); `_get_videos_to_fetch` ambil semua video tenant (`channel_analytics.py:252-273`). | Views/likes dasar tetap BENAR (Data API publik). Yang nol = watch-time/retensi/subscriber-gain → self-learning channel ke-2 SETENGAH BUTA (bukan mati total). Gap ini sudah tercatat di `PER_CHANNEL_OAUTH_MIGRATION.md §7` sejak Juni — jangan "temukan" lagi. |
| G3 | **Otak & setelan bocor antar channel**: `viral_score_weights` per-tenant (`viral_weight_optimizer.py:172`, dibaca NicheSelector); 6 field konten masih per-tenant: `llm_models`(routing per-task), `hook_title_style`, `trailing_silence`, `tts_voice_settings`, `peak_region`, `duplicate_lookback_days` (`tenant_config.py:546-563`). | Nyata utk kasus ryan: channel id-ID Islami akan dituning data channel en-US misteri + bias geo tren salah. Channel-1 hari ini TIDAK terpengaruh. |
| G4 | **Telegram buta channel**: `notify_published` tanpa nama channel (`telegram_notifier.py:197-211`); notif lain pakai `tenant_configs.channel_name` per-tenant (`telegram_notifier.py:268-274`) → semua channel berlabel sama. | Membingungkan begitu ada 2 channel; bukan korupsi data. |
| G5 | ~~**invalid_grant senyap**: tak ada penandaan `status='invalid'`/nonaktif/notif saat refresh-token mati.~~ ✅ **DIBERESKAN + DEPLOYED 2026-07-18 (`dd8fcdc`, =3.2)** — lihat tabel Batch 3. | Melanggar "no silent degradation"; berlaku juga single-channel. |

### §2c. GAP SEDANG (Batch 3 — non-blocker uji)
kuota `max_channels` TIDAK ditegakkan server-side (`channel_quota` `limits.py:52-55` tak pernah dipanggil; RLS insert channels hanya cek tenant_id — verified) · dashboard agregat tanpa dimensi channel (KPI/Runs/compliance/self-learning card) · fallback senyap kunci AI se-vendor (`tenant_config.py:432-440`) & YT akun-pool-pertama (`tenant_credentials.py:43-44`) — dalam-tenant, tertutup gate utk channel aktif normal · `/integrations` tak tunjukkan "dipakai channel mana" (→ ditutup Batch 1) · string missing mentah DB di badge (`lib/channel-status.tsx:22`) · sebagian string FE 1-bahasa · 3 baris `videos` failed `channel_id=NULL` (2026-07-03) · tak ada rate-limit per-key / fairness core per-tenant (skala, bukan 2-channel) · log jalur direct tanpa `channel_id` terstruktur (`producer.py:283`).

## §3. DESAIN SOLUSI (disetujui owner 2026-07-08)

### Batch 1 — "Aman & mudah mengaktifkan channel ke-2" (pagar 3 lapis + wajah channel)
1. **Tangkap identitas saat connect:** callback ambil `channels.list(mine=true, part="id,snippet")` → simpan `yt_channel_id` + **`yt_channel_title` + `yt_channel_thumb` (+handle bila ada)** ke pool. Kegagalan fetch = koneksi GAGAL jujur (bukan best-effort NULL) — tanpa identitas, pagar lain buta.
2. **Anti-duplikat (lapis DB):** unique parsial `(tenant_id, yt_channel_id)` di `tenant_youtube_accounts`; callback: bila `yt_channel_id` sudah ada utk tenant → **UPDATE baris lama (token segar) + hapus baris placeholder baru** + redirect pesan "channel sudah terhubung — token diperbarui" (bukan error menakutkan).
3. **Anti-tabrakan target (lapis DB):** unique parsial `(tenant_id, platform_channel_id)` di `channels` (non-null, non-empty) → 2 channel MV mustahil menunjuk 1 channel YouTube; FE menampilkan pilihan terkunci "Sudah dipakai oleh <nama>".
4. **Pagar mesin (lapis publisher):** sebelum upload, verifikasi identitas token (`channels.list(mine=true).id`) == `channels.platform_channel_id`; selisih → run `failed` dgn alasan eksplisit + notif Telegram; TANPA upload. (1 panggilan API ringan per publish; cache per-publish.)
5. **FE `/integrations`:** kartu koneksi = foto + nama channel + badge "Dipakai oleh: <channel MV>" / "Belum dipakai"; `list_accounts` diperluas (title/thumb/used_by).
6. **FE picker "Channel YouTube tujuan"** (di `/channels/[id]`; juga tampil OPSIONAL di `/channels/new` bila pool ada): galeri radio foto+nama; terpakai channel lain = redup+🔒; tombol inline "＋ Hubungkan channel YouTube lain" (ret balik ke halaman asal). Dwibahasa penuh.
7. **Telegram sebut channel:** semua notif publish/gagal/QC memuat `channels.channel_name` (per-channel dari DB, bukan `tenant_configs.channel_name`).

### Batch 2 — "Data & otak per-channel" (G2+G3)
1. `fetch_and_store` per-CHANNEL: token masing-masing (`channel==MINE` per identitas) + filter video `videos.channel_id`; video `channel_id NULL` legacy tetap lewat jalur channel-pertama (jangan rusak single-channel — peringatan `PER_CHANNEL_OAUTH_MIGRATION.md §7`).
2. `viral_score_weights` per-channel (kolom/tabel baru per channel_id) + warisan: seed dari nilai tenant saat ini → perilaku channel-1 TIDAK berubah; optimizer & `_get_blended_weights` pindah kunci (tenant,channel).
3. 6 field per-tenant → per-channel (kolom `channels` nullable, NULL = warisi tenant — pola overlay yang sudah ada di `tenant_config.py:339-346`): `llm_models`, `hook_title_style`, `trailing_silence`, `tts_voice_settings`, `peak_region`, `duplicate_lookback_days`.

### Batch 3 — hardening world-class
kuota `max_channels` di DB (trigger/RLS insert channels) · invalid_grant → `status='invalid'`+pause channel+notif · dashboard ber-filter channel + nama channel di Runs · buang fallback senyap kunci (gagal jujur) · i18n sisa string · atribusi `channel_id` di jalur error/direct.

## §4. PLAN vs REALISASI (isi SETIAP selesai + tervalidasi; format: status · commit · bukti)

### Batch 1 — ✅ DEPLOYED + LIVE 2026-07-08 (commit `382afdf`; acceptance §5 = uji owner)
> Deploy verified: mv-worker/mv-webhook/mv-web restart & **active** · situs 200 · callback OAuth 302 · endpoint status PRODUKSI mengembalikan field baru (title="RAD The Explorer" + used_by) · worker.log bersih (self_learning jalan normal). Catatan minor (c) di bawah SELESAI (kode baru live).
| # | Item | Status | Commit | Bukti validasi |
|---|------|--------|--------|----------------|
| 1.1 | DB migr **0146**: pool +`yt_channel_title`/`yt_channel_thumb` + unique `(tenant_id,yt_channel_id)` + channels unique `(tenant_id,platform_channel_id)` + backfill title | ✅ APPLIED DB live | (0146) | Uji live-rollback: duplikat koneksi DITOLAK · tabrakan target DITOLAK · target beda DITERIMA · 2 placeholder NULL DITERIMA · residu 0 · backfill ryan title="RAD The Explorer" |
| 1.2 | BE callback: `_fetch_channel_identity` (id+nama+foto, gagal=`identity_failed` jujur + placeholder dibersihkan), dedup-merge token ke baris lama (`youtube=already`), redirect bawa nama channel | ✅ lokal | | `_find_existing_connection` diuji live: ketemu utk UCo5d… (id c3688388…), None utk channel asing; py_compile PASS |
| 1.3 | BE `list_accounts`: +yt_channel_title/thumb/used_by | ✅ lokal | | Dipanggil live: title="RAD The Explorer", used_by=[RAD The Explorer/410d4538] |
| 1.4 | BE publisher: pagar identitas token vs `platform_channel_id` pra-upload di `YouTubePublisher.publish` (menutup 3 jalur: buffer/direct/QC-private; `tenant_config_from_channel` +`platform_channel_id`) | ✅ lokal | | Token nyata ryan: `_token_channel_id`=UCo5d… == target ✓; simulasi target salah → dibatalkan ✓ |
| 1.5 | BE Telegram per-channel: `notify_published(+channel_name)` dari `channel_row`; overlay `config.channel_name`=`channels.channel_name` (failure/QC ikut benar); notif publisher buffer-empty/gagal pakai NAMA channel | ✅ lokal | | py_compile PASS; jalur data diverifikasi (overlay `_apply_channel_overlay`) |
| 1.6 | FE `/integrations`: kartu berwajah (foto+nama+ID) + "Dipakai oleh"/"Belum dipakai" + pesan connected/already/identity_failed dwibahasa | ✅ lokal | | tsc 0 err + next build PASS |
| 1.7 | FE picker galeri `/channels/[id]` (foto+nama, 🔒 "Dipakai oleh X", tombol "Hubungkan channel YouTube lain" inline ret balik, pesan hasil consent, error unique→manusiawi) + picker OPSIONAL `/channels/new` | ✅ lokal | | tsc 0 err + next build PASS |
| 1.8 | Validasi lokal menyeluruh | ✅ | | Semua baris di atas; DB uji via transaksi rollback (nol residu) |

> **Catatan minor disclosed:** (a) foto channel koneksi LAMA ryan masih kosong (foto baru terisi saat consent — reconnect channel-1 kapan saja akan mengisinya via dedup-merge; FE fallback ikon rapi). (b) Pagar 1.4 menambah 1 panggilan `channels.list` ringan per publish (kuota API minimal). (c) Hingga deploy VPS, callback OAuth produksi masih kode lama — dedup tetap aman karena index DB 1.1 sudah aktif (error mentah, bukan pesan ramah) → deploy segera.

### Batch 2
| # | Item | Status | Commit | Bukti |
|---|------|--------|--------|-------|
| 2.1 | Analytics per-channel (token per identitas + filter videos.channel_id, legacy NULL aman) | ✅ **SELESAI 2026-07-13** (koreksi tracker 18-Jul — dulu tertulis ⬜; realisasi via remediasi [B16], LUPUT dicerminkan ke sini) | `f554e38` (+`ee9bc01`) | fetch analytics PER-CHANNEL dgn koneksi masing2 (`self_learning.py:30-46`); `videos.channel_id` terisi (RAD 303/MVT 11); `channel_insights` TERPISAH per-channel (RAD 155/MVT 22, verified DB live 18-Jul). `channel_analytics` tak pernah jadi tabel — data di `videos`+`channel_insights`. |
| 2.2 | `viral_score_weights` per-channel + seed warisan | ⬜ **MASIH TERBUKA** (verified 18-Jul: `viral_score_weights` di `tenant_configs` per-TENANT; `niche_selector.py:183` baca level tenant → RAD & MVT berbagi 1 otak pemilih-topik) | | |
| 2.3 | 6 field konten → kolom channels (NULL=warisi tenant) | 🟡 2.3a | `f07d44c` | **2.3a (ditarik maju, insiden live):** penyedia channel ≠ tenant → `llm_models` tenant gugur, semua task pakai `channels.llm_model`; se-penyedia → perilaku lama utuh (ch-1 diverifikasi byte-sama). Sisa 2.3 penuh (kolom per-channel 6 field) tetap ⬜ |

### 🔥 INSIDEN LIVE 2026-07-08 (channel ke-2 ryan, "No topics selected" 5×) — 3 akar, SEMUA FIXED+DEPLOYED
| Akar | Fakta (bukan asumsi) | Fix | Commit |
|---|---|---|---|
| G3 (terdokumentasi §2b) | NicheSelector/script pakai `llm_models` per-TENANT (model OpenAI) + penyedia per-CHANNEL (gemini/groq) → 404 `model is not found` 3× → "No topics selected" | 2.3a di atas | `f07d44c` |
| Cache config abadi (bug BARU ditemukan) | `TenantConfigManager._cache` tanpa umur → worker TIDAK PERNAH membaca perubahan setelan tenant sampai restart (semua percobaan ganti provider owner sia-sia; log: 4 run beda waktu semua tetap Gemini). `invalidate_cache` juga no-op (kunci komposit vs pop kunci polos) | TTL 120s + invalidate per-prefix | `f07d44c` |
| Circuit-breaker buta jalur direct (bug BARU) | `recent_nonready_streak` baca `content_inventory` (buffer SAJA) → sukses "Jalankan Ulang" tak memutus streak → channel di-pause ULANG + alarm 🛑 palsu SETELAH video terbit | streak pindah ke `production_runs` (buffer+direct+test); validasi live ch2=0 ch1=0 | `7fe489e` |

> Bukti tuntas: run `direct-e0ae8246` **success** — https://www.youtube.com/shorts/hpkubUWtLDI (private, ch "Mesin Viral Test", niche kisah_teladan_islami id-ID, QC pass, hook 92/100, Telegram per-channel benar; acceptance §5 poin 5-6 esensinya terpenuhi). Pause palsu dilepas; 90dtk pantau pasca-deploy: nol pause ulang, producer mengisi stok ch-2 normal.
> Catatan minor tersisa dari log run sukses: (a) thumbnail custom 403 — akun YouTube channel-2 belum verifikasi nomor telepon (aksi tenant di YouTube, bukan bug kita; video tetap terbit); (b) musik fallback mood-only (niche belum punya track mood 'calm' — data katalog musik, non-blocker). (c) 4 cacat FE picker/integrations hasil review 2026-07-08 → **✅ SEMUA FIXED + DEPLOYED `d0e0575`** (mandat owner "selesaikan yang pending"): koneksi tanpa identitas tak bisa dipilih (+badge "Hubungkan ulang"/disembunyikan di new) · Hapus koneksi gagal kini terlihat (cek r.ok + Bi) · pesan OAuth generik & unique-violation kini Bi benar · used_by/🔒 juga match `platform_channel_id` (selaras pagar DB) · picker draft bisa unset. Validasi: list_accounts live ✓ · tsc 0 err · next build lokal+VPS PASS · mv-web active + situs 200.

### Batch 3
| # | Item | Status | Commit | Bukti |
|---|------|--------|--------|-------|
| 3.1 | Kuota max_channels server-side | ✅ **SELESAI** (koreksi tracker 18-Jul — dulu ⬜) | migr `0155_tier_enforcement` | RLS INSERT `channels_tenant_insert` menegakkan `plan_limits.max_channels` per paket (verified DB live 18-Jul) |
| 3.2 | invalid_grant → tandai+pause+notif | ✅ **SELESAI + DEPLOYED 2026-07-18 12:07 (`dd8fcdc`)** (ketok owner: rem segera). Tangkap `invalid_grant` di 2 titik refresh (`youtube_publisher._get_credentials:93` + `channel_analytics._load_credentials:143`) → `mark_youtube_account_invalid` (idempoten, notif tenant SEKALI) set `status='invalid'` → gerbang DB `channel_missing` (syarat status='valid') menutup → producer BERHENTI produksi channel (rem seketika, hemat biaya) → publish menahan video (bukan "akan diulang" menyesatkan) → badge invalid FE `/integrations`. Menempel [B22] kelas `AUTH_INVALID` (masuk FAST_FAIL). RefreshError non-invalid_grant = transien (tak ditandai). Pulih otomatis saat reconnect. | (pending) | Uji `tests/test_youtube_auth_invalid.py` **10/10**; py_compile+import worker bersih; regresi jalur inline/publish-biasa terjaga |
| 3.3 | Dashboard dimensi channel + nama channel di Runs | ⬜ | | |
| 3.4 | Buang fallback senyap kunci · i18n sisa · atribusi channel_id jalur direct | ⬜ | | |

## §5. ACCEPTANCE A-Z (uji nyata bersama owner — bukan klaim kode)
1. Owner buka `/integrations` → klik "Hubungkan channel YouTube lain" → di layar Google memilih **channel tambahan** → kembali: kartu baru tampil **dengan nama+foto channel tambahan** (owner konfirmasi visual channel benar).
2. Uji cegatan: connect ULANG channel yang sama → TIDAK muncul baris ganda; pesan "sudah terhubung, token diperbarui".
3. `/channels/1764a359…` ("Mesin Viral Test") → picker galeri: channel-1 tampil 🔒 "Sudah dipakai oleh RAD The Explorer"; owner pilih channel tambahan → target terisi otomatis.
4. Lengkapi sisa checklist (naskah/suara/visual — akun AI sudah valid) → semua 🟢 → **Aktifkan** sukses (gerbang DB lolos).
5. Produksi berjalan → 1 video terbit **ke channel tambahan yang benar** (owner cek di YouTube) + Telegram menyebut "Mesin Viral Test".
6. Negative-test pagar mesin: (simulasi) target diubah tak-cocok → publisher menolak dgn alasan eksplisit, TIDAK upload.
7. (Batch 2) `videos.channel_id` & analytics penuh terisi per-channel; insight channel-1 vs channel-2 terpisah.

## Changelog
- **2026-07-11** — **konteks utk Batch 2 (analytics+otak per-channel):** mesin hitung insight DIROMBAK (P5+P6+migr 0148 — per-VIDEO snapshot-terbaru, paginasi penuh, agregat tertimbang volume; isolasi per-channel diverifikasi SEMUA jalur baca/tulis, kebocoran NIHIL). Batch 2 kelak membangun di atas mesin ini — jangan audit ulang isolasi. Detail = memory `project_self_learning_remediation_2026_06_28` entri ⭐ 07-11.
- **2026-07-08** — dibuat dari audit mendalam (3 penelusur + DB live); desain UI/UX + batch disetujui owner; [B11] didaftarkan di `SISA_KERJA_GO_LIVE.md`.
