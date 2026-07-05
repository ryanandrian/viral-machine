-- 0127 — Ken Burns configurable ([B3] Fase 1, owner 2026-07-05): seed camera_motion per KARAKTER niche.
-- MERGE ke visual_style (jsonb_set, kunci lain UTUH). Idempotent (jalan ulang aman). Nilai: halus/normal/dinamis/cepat.
-- Mesin (ai_image._build_motion_vf) membaca visual_style.camera_motion.intensity; absen → 'normal' (fallback aman).
-- Durasi preset TAK terpengaruh (motion hanya cara gambar bergerak di dalam durasi yang dipaku `-t`).

UPDATE niches SET visual_style = jsonb_set(coalesce(visual_style,'{}'::jsonb), '{camera_motion}',
  jsonb_build_object('intensity',
    CASE niche_id
      WHEN 'fun_facts' THEN 'dinamis'        -- surprise+excitement, "snappy energetic, lively"
      ELSE 'halus'                            -- misteri/sejarah/imunitas: slow/deliberate/calm
    END::text), true)
WHERE niche_id IN ('universe_mysteries','ocean_mysteries','dark_history','fun_facts',
                   'imunitas_tubuh','misteri_perang_dunia_c8f3e6');
