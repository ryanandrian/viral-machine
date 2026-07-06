// Kategori YouTube resmi (categoryId → nama) untuk dropdown editor niche (Admin Niche Library + Niche Studio).
// Dipakai sebagai value snippet.categoryId saat publish. Single-source agar admin & tenant seragam.
// LENGKAP = 15 kategori assignable resmi YouTube Data API (videoCategories.assignable=true, region US).
// Audit 2026-07-06: daftar lama hanya 10 — kategori resmi 2/15/17/19/29 hilang → UI jatuh ke
// fallback "Kategori N" utk niche otomotif & travel. Jangan hapus entri: categoryId dipakai publish.
export const YT_CATEGORIES: [string, string][] = [
  ["1", "Film & Animation"],
  ["2", "Autos & Vehicles"],
  ["10", "Music"],
  ["15", "Pets & Animals"],
  ["17", "Sports"],
  ["19", "Travel & Events"],
  ["20", "Gaming"],
  ["22", "People & Blogs"],
  ["23", "Comedy"],
  ["24", "Entertainment"],
  ["25", "News & Politics"],
  ["26", "Howto & Style"],
  ["27", "Education"],
  ["28", "Science & Technology"],
];
