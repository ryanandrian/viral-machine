-- 0066_channels_inactive_default.sql
-- F1-08 (REMEDIASI §10.E.7): channel baru DEFAULT NON-AKTIF — hanya boleh aktif lewat gerbang
-- aktivasi (readiness lengkap). Channel existing TIDAK berubah (hanya default utk INSERT tanpa is_active).
alter table channels alter column is_active set default false;
