-- ============================================================
-- Migration s88: Font Management
-- Tabel fonts untuk Admin Panel — tenant bisa pilih font branding
-- Jalankan di Supabase SQL Editor
-- ============================================================

-- 1. Tabel fonts — daftar font yang tersedia untuk tenant
--    file_name: nama file di server (/usr/local/share/fonts/)
--    Admin Panel upload font baru → insert row di sini
CREATE TABLE IF NOT EXISTS fonts (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,   -- "Anton", "Bebas Neue", dll
    file_name   VARCHAR(200) NOT NULL,          -- "Anton-Regular.ttf"
    preview_url VARCHAR(500) DEFAULT '',        -- URL preview font (opsional)
    is_active   BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 2. Seed: Anton sebagai font default
INSERT INTO fonts (name, file_name, is_active)
VALUES ('Anton', 'Anton-Regular.ttf', true)
ON CONFLICT (name) DO NOTHING;

-- 3. RLS policy — anon bisa SELECT (untuk dropdown font di UI)
ALTER TABLE fonts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fonts_select_anon" ON fonts
    FOR SELECT USING (true);

-- 4. Verifikasi
SELECT id, name, file_name, is_active FROM fonts ORDER BY id;
