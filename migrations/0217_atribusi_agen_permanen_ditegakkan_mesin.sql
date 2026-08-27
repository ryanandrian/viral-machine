-- 0217 — ATRIBUSI AGEN jadi PERMANEN yang ditegakkan MESIN (bukan lagi disiplin kode).
--
-- KENAPA SEKARANG. Agen AGEN01 komplen 27-Agu: pelanggan bawaannya tak tercatat. Akarnya: pintu
-- daftar Google tak pernah membawa kode rujukan (100% karya saya — SSOT §5a saya lengkapi hanya
-- untuk pintu email). Perbaikannya menambah PENULIS KEDUA atribusi (penerima OAuth), dan sejak
-- penulisnya dua, aturan SSOT §1b/§4 — *"ditulis SEKALI saat signup, tidak pernah di-update"* —
-- tidak boleh lagi bersandar pada disiplin kode saja: satu kekeliruan di salah satu penulis bisa
-- MEMINDAHKAN pelanggan dari satu agen ke agen lain tanpa jejak, dan uang mengikuti atribusi.
--
-- Diperiksa sebelum dipasang (nol jalur sah yang dipecahkan):
--   • `api/auth/signup` memakai upsert ignoreDuplicates  → INSERT, bukan UPDATE  ✓
--   • `src/billing/renewal.py` **sengaja TIDAK menghapus** atribusi saat data tenant dibersihkan,
--     dengan alasan tertulis "dihapus = agen kehilangan komisi bila tenant kembali"             ✓
--   • `api/admin/partners`, `api/agent/*`, `api/reseller/*` hanya MEMBACA                        ✓
--   ⇒ pagar ini menegakkan keputusan yang SUDAH ADA, bukan aturan baru.
--
-- JALUR BUKA (owner pernah menegur "kunci tanpa jalur buka"): koreksi administratif tetap mungkin
-- lewat akses DB langsung — `alter table public.tenant_attribution disable trigger
-- trg_atribusi_permanen;` → koreksi → `enable trigger`. Sengaja TIDAK bisa dari aplikasi: uang agen
-- tak boleh bergeser karena satu tombol tersenggol.
--
-- INSERT tetap BEBAS — itu jalur normal lahirnya atribusi.
-- AMBANG: trigger terpasang · INSERT masih boleh · UPDATE & DELETE ditolak · nol baris data berubah.

begin;

create or replace function public.atribusi_agen_permanen() returns trigger
language plpgsql as $$
begin
  raise exception
    'ATRIBUSI AGEN PERMANEN (AGENT_AND_AFILIATION §1b/§4): baris atribusi tidak boleh %s. '
    'Atribusi terkunci sejak tenant mendaftar — uang komisi mengikutinya. Koreksi administratif '
    'hanya lewat akses DB langsung (nonaktifkan trigger trg_atribusi_permanen sementara).',
    lower(tg_op);
end $$;

comment on function public.atribusi_agen_permanen is
  'Penegak SSOT §1b/§4: tenant_attribution ditulis SEKALI, tak pernah di-update/dihapus. '
  'Dipasang 27-Agu-2026 saat penulis atribusi menjadi dua (signup email + penerima OAuth).';

drop trigger if exists trg_atribusi_permanen on public.tenant_attribution;
create trigger trg_atribusi_permanen
  before update or delete on public.tenant_attribution
  for each row execute function public.atribusi_agen_permanen();

do $$
declare n int;
begin
  select count(*) into n from pg_trigger
   where tgrelid = 'public.tenant_attribution'::regclass
     and tgname = 'trg_atribusi_permanen' and not tgisinternal;
  if n <> 1 then
    raise exception 'AMBANG 0217: trigger tidak terpasang (n=%)', n;
  end if;
end $$;

commit;
