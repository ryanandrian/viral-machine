-- 0165: [DURASI-F5] fondasi swa-pemeliharaan — (a) rekam kata NYATA per-beat tiap render (ground-truth
-- utk penyelarasan bobot-beat; `_beat_words` LLM = laporan, ini = hitungan sistem dari naskah final);
-- (b) kunci admin per-beat (pola `pace_locked`): weight_locked=true → mesin TIDAK menyentuh bobot beat itu.
-- Keputusan owner (delegasi 2026-07-16): bobot-beat = dinamis-sederhana — mesin menyelaraskan berkala,
-- admin menyesuaikan/mengunci JIKA dan HANYA JIKA diperlukan. Additif murni; NULL/default = perilaku lama.
ALTER TABLE tts_delivery_samples
  ADD COLUMN IF NOT EXISTS beat_words jsonb;
ALTER TABLE content_beats
  ADD COLUMN IF NOT EXISTS weight_locked boolean NOT NULL DEFAULT false;
