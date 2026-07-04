-- 0118 — NICHE DNA (audit 2026-07-04, disepakati owner; spec = NICHE_DNA_AUDIT_REMEDIATION.md)
-- (1) Drop fosil hook_templates (nol konsumen — hook via HOOK_FORMULAS + persona.hook_style).
-- (2) Hapus niche 'test' (origin request, DNA kosong, nol referensi produksi; pesanan terkait di-null-kan).
-- (3) Tabel niche_property_presets — preset per-properti DNA ("pilih dulu, sunting kalau mau"),
--     admin-managed, dwibahasa. value = bentuk PERSIS kolom niches terkait (mesin tak berubah).
-- (4) moods.keywords → dwibahasa (deteksi mood dari naskah INDONESIA selama ini mati — keyword EN-only).

-- ── (1) fosil ────────────────────────────────────────────────────────────────
ALTER TABLE niches DROP COLUMN IF EXISTS hook_templates;

-- ── (2) niche test ───────────────────────────────────────────────────────────
UPDATE niche_requests SET niche_id = NULL WHERE niche_id = 'test';
DELETE FROM niches WHERE niche_id = 'test';

-- ── (3) preset per-properti ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS niche_property_presets (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property      text NOT NULL CHECK (property IN
                  ('narration_persona','visual_style','image_quality_tags','image_negative_prompt',
                   'mood_priority','section_timing','emotion_scoring_criteria')),
  preset_key    text NOT NULL,
  label         text NOT NULL,          -- nama (ID)
  label_en      text,
  description   text,                   -- penjelasan singkat (ID)
  description_en text,
  value         jsonb NOT NULL,         -- bentuk = kolom niches terkait (dict/list/string-as-json)
  apply_mode    text NOT NULL DEFAULT 'replace' CHECK (apply_mode IN ('replace','merge')),
  sort_order    integer DEFAULT 0,
  is_active     boolean DEFAULT true,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now(),
  UNIQUE (property, preset_key)
);
ALTER TABLE niche_property_presets ENABLE ROW LEVEL SECURITY;
-- Publik (anon/tenant) boleh BACA preset aktif (editor tenant butuh); tulis = service-role (admin).
CREATE POLICY npp_public_read ON niche_property_presets FOR SELECT USING (is_active = true);

-- ── SEED PRESET (kurasi awal; admin bebas tambah/ubah dari panel) ─────────────
-- 3a. KEPRIBADIAN NARASI (replace) — 5 key persis konsumen script_engine: tone/style/avoid/hook_style/emotion_arc
INSERT INTO niche_property_presets (property, preset_key, label, label_en, description, description_en, value, apply_mode, sort_order) VALUES
('narration_persona','documentary_authority','Narator Dokumenter Berwibawa','Authoritative Documentary Narrator','Serius, membangun ketegangan, memukau — seperti narator dokumenter kelas dunia.','Serious, tension-building, awe-inspiring — like a world-class documentary narrator.',
 '{"tone":"authoritative yet awe-inspiring, like a world-class documentary narrator","style":"dramatic pauses, building tension, sense of wonder and scale","avoid":"casual language, humor, sarcasm, weak openers, generic phrases","hook_style":"impossible_claim or number_shock","emotion_arc":"curiosity → shock → wonder → awe"}','replace',1),
('narration_persona','dark_storyteller','Pendongeng Kelam Mencekam','Dark Gripping Storyteller','Suara rendah menahan rahasia; membawa penonton masuk ke sisi gelap cerita.','A low voice holding secrets; pulls viewers into the dark side of the story.',
 '{"tone":"grave and haunting, like someone who witnessed history''s darkest hours","style":"slow reveals, heavy pauses, chilling details delivered calmly","avoid":"jokes, lightness, sensational screaming, graphic gore, disrespect to victims","hook_style":"story_open or you_dont_know","emotion_arc":"unease → dread → shock → sober reflection"}','replace',2),
('narration_persona','energetic_fun','Energik & Seru','Energetic & Fun','Cepat, penuh semangat, bikin penonton ikut excited dari detik pertama.','Fast, high-energy, gets viewers hyped from the first second.',
 '{"tone":"upbeat and infectious, like an excited friend who just found something amazing","style":"fast pace, punchy short sentences, playful exclamations","avoid":"monotone delivery, long-winded sentences, academic jargon, boring lists","hook_style":"number_shock or question","emotion_arc":"excitement → surprise → delight → wow"}','replace',3),
('narration_persona','warm_calming','Hangat & Menenangkan','Warm & Calming','Lembut dan meyakinkan — cocok untuk kesehatan, mindfulness, dan topik kehidupan.','Gentle and reassuring — great for health, mindfulness, and life topics.',
 '{"tone":"warm, caring and trustworthy, like a wise friend who genuinely cares","style":"flowing calm rhythm, simple everyday words, reassuring transitions","avoid":"fear-mongering, medical scare tactics, absolute claims, preachy lecturing","hook_style":"question or you_dont_know","emotion_arc":"curiosity → recognition → relief → motivation"}','replace',4),
('narration_persona','curious_teacher','Guru yang Bikin Penasaran','Curiosity-Sparking Teacher','Menjelaskan hal rumit jadi sederhana sambil terus memancing rasa ingin tahu.','Makes complex things simple while constantly feeding curiosity.',
 '{"tone":"smart but approachable, like a favorite teacher who makes you love learning","style":"question-driven flow, vivid analogies, aha-moment reveals","avoid":"condescension, textbook dryness, unexplained jargon, information dumps","hook_style":"question or impossible_claim","emotion_arc":"curiosity → intrigue → understanding → satisfaction"}','replace',5),
('narration_persona','mysterious_whisper','Misterius Penuh Teka-teki','Mysterious & Enigmatic','Setiap kalimat terasa menyimpan rahasia; penonton bertahan demi jawabannya.','Every sentence feels like it hides a secret; viewers stay for the answer.',
 '{"tone":"enigmatic and quietly intense, like a keeper of forbidden knowledge","style":"withheld information, rhetorical teases, slow-burn reveals","avoid":"giving away the answer early, casual filler, over-explaining","hook_style":"you_dont_know or impossible_claim","emotion_arc":"intrigue → suspense → revelation → lingering wonder"}','replace',6);

-- 3b. GAYA VISUAL (replace) — key inti base_style/color_palette/atmosphere (konsumen hook-frame & rewrite) + key ekstra (konsumen generik)
INSERT INTO niche_property_presets (property, preset_key, label, label_en, description, description_en, value, apply_mode, sort_order) VALUES
('visual_style','cinematic_photoreal','Sinematik Fotorealistis','Cinematic Photorealistic','Seperti film dokumenter mahal: nyata, dramatis, detail tajam.','Like an expensive documentary film: real, dramatic, razor-sharp detail.',
 '{"base_style":"hyper-photorealistic cinematic photography","color_palette":"deep contrast, rich natural tones, moody shadows","atmosphere":"dramatic, awe-inspiring, larger than life","camera":"shot on ARRI Alexa 65, 35mm anamorphic lens, shallow depth of field","lighting":"volumetric god-rays, dramatic chiaroscuro","realism":"physically-based rendering, true-to-life textures and scale"}','replace',1),
('visual_style','dark_documentary','Dokumenter Gelap Berkabut','Dark Moody Documentary','Nuansa kelam, kabut, cahaya remang — pas untuk sejarah gelap & misteri.','Dark tones, fog, dim light — perfect for dark history & mystery.',
 '{"base_style":"dark archival documentary photography, film grain","color_palette":"desaturated sepia and cold grey, deep blacks","atmosphere":"ominous, heavy, haunted by the past","camera":"vintage 50mm lens, slight vignette","lighting":"low-key single-source light, long shadows, fog diffusion","realism":"aged textures, weathered surfaces, historical authenticity"}','replace',2),
('visual_style','bright_vibrant','Cerah & Vibrant','Bright & Vibrant','Warna hidup, energik, bersih — cocok untuk fakta seru & hiburan.','Lively colors, energetic, clean — great for fun facts & entertainment.',
 '{"base_style":"crisp modern editorial photography","color_palette":"vibrant saturated colors, bright complementary accents","atmosphere":"playful, optimistic, full of energy","camera":"sharp 35mm lens, dynamic angles","lighting":"bright even lighting, soft highlights, sunny warmth","realism":"clean detailed textures, polished contemporary look"}','replace',3),
('visual_style','soft_3d','Ilustrasi 3D Halus','Soft 3D Illustration','Gaya render 3D lembut ramah semua umur — beda dari footage nyata.','Soft friendly 3D render style — stands out from real footage.',
 '{"base_style":"soft polished 3D render illustration, subtle stylization","color_palette":"pastel gradients with gentle contrast","atmosphere":"friendly, inviting, softly magical","camera":"medium focal length, gentle depth of field","lighting":"soft global illumination, ambient occlusion, warm rim light","realism":"smooth materials, clay-like softness, refined details"}','replace',4),
('visual_style','underwater_ethereal','Bawah Laut Etereal','Ethereal Underwater','Cahaya menembus air, partikel melayang — dunia sunyi yang megah.','Light piercing water, floating particles — a silent majestic world.',
 '{"base_style":"deep ocean cinematography, ethereal underwater photography","color_palette":"deep teal to abyssal black, bioluminescent accents","atmosphere":"silent, vast, mysteriously beautiful","camera":"wide underwater housing lens, suspended particles in frame","lighting":"god-rays through water surface, bioluminescent glow","realism":"volumetric water, caustic light patterns, true deep-sea scale"}','replace',5),
('visual_style','retro_film','Retro Film Grain','Retro Film Grain','Nostalgia film analog 70-80an: grain, warna pudar hangat.','70s-80s analog film nostalgia: grain, warm faded colors.',
 '{"base_style":"vintage analog film photography, kodachrome look","color_palette":"warm faded tones, amber highlights, muted greens","atmosphere":"nostalgic, timeless, quietly cinematic","camera":"vintage prime lens, natural flares, film grain","lighting":"golden-hour warmth, soft halation","realism":"authentic film texture, era-accurate details"}','replace',6);

-- 3c. KUALITAS GAMBAR (merge — string digabung koma)
INSERT INTO niche_property_presets (property, preset_key, label, label_en, description, description_en, value, apply_mode, sort_order) VALUES
('image_quality_tags','ultra_cinematic','Ultra Detail Sinematik','Ultra Detailed Cinematic','Paket kualitas tertinggi: detail 8K, pencahayaan sinematik.','Top quality pack: 8K detail, cinematic lighting.',
 '"ultra detailed, highly textured, sharp focus, cinematic lighting, volumetric lighting, global illumination, high contrast, realistic textures, depth of field, professional composition, 8k detail"','merge',1),
('image_quality_tags','clean_natural','Bersih & Natural','Clean & Natural','Tampilan natural tanpa efek berlebihan.','Natural look without heavy effects.',
 '"clean composition, natural color grading, soft shadows, balanced exposure, realistic reflections, fine details"','merge',2),
('image_quality_tags','dramatic_contrast','Dramatis Kontras Tinggi','Dramatic High Contrast','Bayangan pekat & sorotan kuat untuk kesan intens.','Deep shadows & strong highlights for intensity.',
 '"dramatic lighting, high contrast, deep shadows, rim lighting, moody atmosphere, chiaroscuro"','merge',3);

-- 3d. LARANGAN GAMBAR (merge — string digabung koma)
INSERT INTO niche_property_presets (property, preset_key, label, label_en, description, description_en, value, apply_mode, sort_order) VALUES
('image_negative_prompt','safe_standard','Standar Aman','Safe Standard','Cegah cacat umum: blur, distorsi, watermark, teks nyasar.','Prevents common defects: blur, distortion, watermarks, stray text.',
 '"blurry, low detail, flat lighting, distorted, deformed, unrealistic, bad proportions, text, words, letters, numbers, signs, logos, watermarks, typography"','merge',1),
('image_negative_prompt','no_humans','Tanpa Manusia','No Humans','Larang wajah/figur manusia (hindari wajah AI aneh).','Bans human faces/figures (avoids uncanny AI faces).',
 '"human faces, people, person, portrait, hands, fingers, crowd"','merge',2),
('image_negative_prompt','no_brands','Tanpa Merek & Properti','No Brands & IP','Larang logo merek, karakter berhak-cipta, kemasan produk.','Bans brand logos, copyrighted characters, product packaging.',
 '"brand logos, trademarks, copyrighted characters, product packaging, celebrity likeness"','merge',3);

-- 3e. PAKET MOOD MUSIK (merge — list digabung urut, dedup) — nilai HARUS ada di tabel moods
INSERT INTO niche_property_presets (property, preset_key, label, label_en, description, description_en, value, apply_mode, sort_order) VALUES
('mood_priority','dark_mysterious','Misterius Gelap','Dark Mysterious','Untuk misteri, sejarah kelam, kisah menyeramkan.','For mystery, dark history, chilling stories.',
 '["mysterious","eerie","ominous","dark","tense"]','merge',1),
('mood_priority','epic_dramatic','Epik Dramatis','Epic Dramatic','Untuk topik megah: alam semesta, sejarah besar, pencapaian.','For grand topics: universe, big history, achievements.',
 '["dramatic","epic","tense","suspense"]','merge',2),
('mood_priority','upbeat_fun','Ceria Enerjik','Upbeat Fun','Untuk konten seru, fakta unik, hiburan ringan.','For fun content, cool facts, light entertainment.',
 '["upbeat","energetic","happy","playful"]','merge',3),
('mood_priority','calm_soothing','Tenang & Damai','Calm & Soothing','Untuk kesehatan, mindfulness, keindahan alam.','For health, mindfulness, nature beauty.',
 '["calm","ambient","inspirational"]','merge',4);

-- 3f. STRUKTUR DURASI (replace) — 8 key WAJIB (validasi ketat script_engine); basis 51s preset-60
INSERT INTO niche_property_presets (property, preset_key, label, label_en, description, description_en, value, apply_mode, sort_order) VALUES
('section_timing','balanced_standard','Standar Seimbang','Balanced Standard','Struktur teruji 4 niche dasar — aman untuk semua topik.','Proven structure of the 4 base niches — safe for any topic.',
 '{"hook":3,"mystery_drop":5,"build_up":12,"pattern_interrupt":2,"core_facts":15,"curiosity_bridge":3,"climax":8,"cta":3}','replace',1),
('section_timing','punchy_fast','Cepat & Punchy','Fast & Punchy','Hook + fakta beruntun; cocok untuk fakta cepat dan audiens tak sabar.','Rapid hook + fact barrage; for quick facts and impatient audiences.',
 '{"hook":4,"mystery_drop":4,"build_up":8,"pattern_interrupt":3,"core_facts":18,"curiosity_bridge":3,"climax":8,"cta":3}','replace',2),
('section_timing','slow_burn','Slow-burn Klimaks Besar','Slow-burn Big Climax','Bangun ketegangan panjang, ledakan di akhir; cocok cerita misteri.','Long tension build, big payoff at the end; great for mystery stories.',
 '{"hook":3,"mystery_drop":6,"build_up":15,"pattern_interrupt":2,"core_facts":10,"curiosity_bridge":3,"climax":10,"cta":2}','replace',3);

-- 3g. KRITERIA PENILAIAN EMOSI (replace — string)
INSERT INTO niche_property_presets (property, preset_key, label, label_en, description, description_en, value, apply_mode, sort_order) VALUES
('emotion_scoring_criteria','existential_awe','Kekaguman Eksistensial','Existential Awe','Skor tinggi bila penonton merasa kecil sekaligus terhubung dengan sesuatu yang maha luas.','High score when viewers feel tiny yet connected to something infinite.',
 '"Score 80+ if the climax delivers EXISTENTIAL AWE — viewer feels simultaneously insignificant and connected to something vast. Valid techniques: scale contrast, counterintuitive reversal, infinite implication. Score LOW for generic amazement without a specific mind-bending fact."','replace',1),
('emotion_scoring_criteria','chills_dread','Merinding & Ngeri','Chills & Dread','Skor tinggi bila detail membuat bulu kuduk berdiri tanpa gore murahan.','High score when details raise goosebumps without cheap gore.',
 '"Score 80+ if the script builds genuine CREEPING DREAD — a specific chilling detail that lingers after watching. Valid techniques: mundane-turned-sinister, survivor testimony framing, unanswered question. Score LOW for shock-value gore or clickbait without payoff."','replace',2),
('emotion_scoring_criteria','curiosity_gap','Penasaran Tak Tahan','Irresistible Curiosity','Skor tinggi bila tiap bagian memaksa penonton bertahan demi jawaban.','High score when every section forces viewers to stay for the answer.',
 '"Score 80+ if the script sustains an IRRESISTIBLE CURIOSITY GAP — each section opens a new question while paying off the last. Valid techniques: withheld key detail, escalating stakes, pattern break. Score LOW if the answer is given too early or the question is trivial."','replace',3),
('emotion_scoring_criteria','delight_surprise','Terhibur & Kaget','Delight & Surprise','Skor tinggi bila fakta benar-benar tak terduga dan menyenangkan.','High score when facts are truly unexpected and fun.',
 '"Score 80+ if the script delivers GENUINE DELIGHT — at least one fact that makes viewers say ''no way!'' out loud. Valid techniques: absurd-but-true comparison, everyday-object twist, record-breaking scale. Score LOW for widely-known trivia or listicle monotony."','replace',4),
('emotion_scoring_criteria','inspired_uplift','Terinspirasi','Inspired & Uplifted','Skor tinggi bila penonton merasa mampu dan tergerak bertindak.','High score when viewers feel capable and moved to act.',
 '"Score 80+ if the climax leaves viewers UPLIFTED AND EMPOWERED — a concrete takeaway they can act on today. Valid techniques: underdog arc, small-step framing, vivid before-after. Score LOW for vague motivation cliches without an actionable insight."','replace',5);

-- ── (4) moods.keywords dwibahasa (deteksi mood naskah Indonesia hidup) ────────
UPDATE moods SET keywords = keywords || '["mengejutkan","luar biasa","tak terduga","mengubah segalanya"]'::jsonb WHERE mood_id='dramatic';
UPDATE moods SET keywords = keywords || '["cepat","dahsyat","meledak","terobosan","luar biasa cepat"]'::jsonb WHERE mood_id='energetic';
UPDATE moods SET keywords = keywords || '["tenang","damai","lembut","hening","luas","dalam"]'::jsonb WHERE mood_id='calm';
UPDATE moods SET keywords = keywords || '["misteri","misterius","rahasia","tersembunyi","aneh","tak terjelaskan"]'::jsonb WHERE mood_id='mysterious';
UPDATE moods SET keywords = keywords || '["menyeramkan","merinding","janggal","hantu","gaib"]'::jsonb WHERE mood_id='eerie';
UPDATE moods SET keywords = keywords || '["kelam","gelap","mengerikan","tragedi","kejam"]'::jsonb WHERE mood_id='dark';
UPDATE moods SET keywords = keywords || '["firasat buruk","ancaman","bahaya","malapetaka"]'::jsonb WHERE mood_id='ominous';
UPDATE moods SET keywords = keywords || '["tegang","mencekam","genting","kritis"]'::jsonb WHERE mood_id='tense';
UPDATE moods SET keywords = keywords || '["epik","megah","kolosal","raksasa","agung"]'::jsonb WHERE mood_id='epic';
UPDATE moods SET keywords = keywords || '["menegangkan","penasaran","teka-teki","misteri belum terpecahkan"]'::jsonb WHERE mood_id='suspense';
UPDATE moods SET keywords = keywords || '["ceria","semangat","asyik","keren"]'::jsonb WHERE mood_id='upbeat';
UPDATE moods SET keywords = keywords || '["bahagia","senang","gembira","menyenangkan"]'::jsonb WHERE mood_id='happy';
UPDATE moods SET keywords = keywords || '["inspirasi","memotivasi","membangkitkan","semangat juang","pantang menyerah"]'::jsonb WHERE mood_id='inspirational';
UPDATE moods SET keywords = keywords || '["jenaka","seru","lucu","kocak","unik"]'::jsonb WHERE mood_id='playful';
UPDATE moods SET keywords = keywords || '["atmosferik","sunyi","samar","melayang"]'::jsonb WHERE mood_id='ambient';
