import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

// Upload FONT (admin): berkas .ttf/.otf → S3 mesinviral-assets/fonts/ (public-read, karena layar
// tenant memuatnya lewat @font-face utk pratinjau) + baris `fonts` yang dibaca FE maupun mesin render.
// Pola meniru /api/admin/music/upload (guard → validasi → S3 → insert → admin_audit).
export const dynamic = "force-dynamic";

/**
 * Baca metrik font langsung dari berkasnya — TANPA pustaka tambahan.
 *
 * `ass_scale` = unitsPerEm / (usWinAscent + usWinDescent). Angka ini WAJIB benar: mesin subtitle
 * (libass) menskalakan huruf memakai metrik "win", bukan em, sehingga tanpa angka ini pratinjau di
 * layar tidak akan pernah sama dengan hasil video (selisih terukur 31–79% tergantung font).
 * Karena itu angkanya DIHITUNG dari berkas, tidak pernah diketik manual oleh admin.
 *
 * Yang dibaca: tabel `head` (unitsPerEm, offset 18) dan `OS/2` (usWinAscent/Descent, offset 74/76).
 * Mendukung TrueType (0x00010000 / 'true') dan OpenType-CFF ('OTTO').
 */
function bacaMetrikFont(buf: Buffer): { unitsPerEm: number; winAsc: number; winDesc: number } | null {
  if (buf.length < 12) return null;
  const tag = buf.readUInt32BE(0);
  if (tag !== 0x00010000 && tag !== 0x74727565 /* 'true' */ && tag !== 0x4f54544f /* 'OTTO' */) return null;
  const numTables = buf.readUInt16BE(4);
  if (numTables <= 0 || numTables > 512) return null;
  const tabel = new Map<string, { off: number; len: number }>();
  for (let i = 0; i < numTables; i++) {
    const p = 12 + i * 16;
    if (p + 16 > buf.length) return null;
    tabel.set(buf.toString("ascii", p, p + 4), { off: buf.readUInt32BE(p + 8), len: buf.readUInt32BE(p + 12) });
  }
  const head = tabel.get("head");
  const os2 = tabel.get("OS/2");
  if (!head || !os2) return null;
  if (head.off + 54 > buf.length || os2.off + 78 > buf.length) return null;
  const unitsPerEm = buf.readUInt16BE(head.off + 18);
  const winAsc = buf.readUInt16BE(os2.off + 74);
  const winDesc = buf.readUInt16BE(os2.off + 76);
  if (!unitsPerEm || !(winAsc + winDesc)) return null;
  return { unitsPerEm, winAsc, winDesc };
}

/** Nama keluarga font (tabel `name`, nameID 1) — dipakai memastikan nama yang diketik admin cocok. */
function bacaNamaKeluarga(buf: Buffer): string | null {
  try {
    const numTables = buf.readUInt16BE(4);
    let nameOff = 0;
    for (let i = 0; i < numTables; i++) {
      const p = 12 + i * 16;
      if (buf.toString("ascii", p, p + 4) === "name") { nameOff = buf.readUInt32BE(p + 8); break; }
    }
    if (!nameOff || nameOff + 6 > buf.length) return null;
    const count = buf.readUInt16BE(nameOff + 2);
    const strOff = nameOff + buf.readUInt16BE(nameOff + 4);
    for (let i = 0; i < count; i++) {
      const r = nameOff + 6 + i * 12;
      if (r + 12 > buf.length) break;
      const platformID = buf.readUInt16BE(r);
      const nameID = buf.readUInt16BE(r + 6);
      const len = buf.readUInt16BE(r + 8);
      const off = strOff + buf.readUInt16BE(r + 10);
      if (nameID !== 1 || off + len > buf.length) continue;
      // platform 3 (Windows) = UTF-16BE. Node hanya punya utf16le, jadi byte ditukar dulu —
      // tanpa ini nama terbaca sebagai aksara Tionghoa acak.
      if (platformID === 3) {
        const be = buf.subarray(off, off + len);
        const le = Buffer.allocUnsafe(be.length);
        for (let k = 0; k + 1 < be.length; k += 2) { le[k] = be[k + 1]; le[k + 1] = be[k]; }
        return le.toString("utf16le").replace(/\0/g, "").trim() || null;
      }
      return buf.toString("latin1", off, off + len).replace(/\0/g, "").trim() || null;
    }
  } catch { /* metadata rusak → nama tak bisa dibaca, bukan alasan menolak unggahan */ }
  return null;
}

export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;

  let form: FormData;
  try { form = await req.formData(); } catch { return NextResponse.json({ error: "form-data tidak valid" }, { status: 400 }); }
  const file = form.get("file");
  const name = String(form.get("name") || "").trim();

  if (!(file instanceof File)) return NextResponse.json({ error: "berkas font wajib" }, { status: 400 });
  if (!name) return NextResponse.json({ error: "nama font wajib" }, { status: 400 });
  const lower = file.name.toLowerCase();
  if (!lower.endsWith(".ttf") && !lower.endsWith(".otf")) {
    return NextResponse.json({ error: "harus berkas .ttf atau .otf" }, { status: 400 });
  }
  if (file.size > 10 * 1024 * 1024) return NextResponse.json({ error: "maksimal 10MB" }, { status: 400 });

  const body = Buffer.from(await file.arrayBuffer());
  const metrik = bacaMetrikFont(body);
  if (!metrik) {
    return NextResponse.json({ error: "berkas font tidak terbaca (bukan TTF/OTF yang sah)" }, { status: 400 });
  }
  const ass_scale = Number((metrik.unitsPerEm / (metrik.winAsc + metrik.winDesc)).toFixed(6));

  // NAMA KATALOG = nama keluarga DI DALAM BERKAS, bukan ketikan admin.
  // Mesin subtitle (libass) mencari font lewat nama keluarga, BUKAN nama berkas. Kalau keduanya
  // beda — mis. admin mengetik "Orbitron-SemiBold" padahal berkasnya "Orbitron SemiBold" — caption
  // diam-diam jatuh ke font cadangan. Memakai nama dari berkas menutup seluruh kelas kesalahan itu.
  const keluarga = bacaNamaKeluarga(body);
  const nama_final = keluarga || name;

  // Nama file DIBAKUKAN dari nama font → mesin render mencarinya lewat kolom file_name, dan nama
  // berkas asli yang aneh (spasi/karakter unik) tak bisa merusak jalur di server.
  const slug = nama_final.replace(/[^A-Za-z0-9]+/g, "");
  const ext = lower.endsWith(".otf") ? "otf" : "ttf";
  const file_name = `${slug}-Regular.${ext}`;
  const object_key = `fonts/${file_name}`;

  const endpoint = process.env.S3_ENDPOINT, accessKeyId = process.env.S3_ACCESS_KEY, secretAccessKey = process.env.S3_SECRET_KEY;
  const bucket = process.env.S3_ASSET_BUCKET || "mesinviral-assets";
  if (!endpoint || !accessKeyId || !secretAccessKey) return NextResponse.json({ error: "S3 config kurang di server" }, { status: 500 });

  const a = createAdminClient();
  const { data: sudahAda } = await a.from("fonts").select("name").eq("name", nama_final).maybeSingle();
  if (sudahAda) return NextResponse.json({ error: `font "${nama_final}" sudah ada — hapus dulu bila ingin mengganti` }, { status: 409 });

  const s3 = new S3Client({ endpoint, region: process.env.S3_REGION || "idn", credentials: { accessKeyId, secretAccessKey }, forcePathStyle: true });
  try {
    // public-read WAJIB: layar tenant memuat berkas ini lewat @font-face untuk pratinjau.
    await s3.send(new PutObjectCommand({
      Bucket: bucket, Key: object_key, Body: body, ACL: "public-read",
      ContentType: ext === "otf" ? "font/otf" : "font/ttf", CacheControl: "public, max-age=31536000",
    }));
  } catch (e) {
    return NextResponse.json({ error: `upload S3 gagal: ${(e as Error).message}` }, { status: 500 });
  }

  const file_url = `${endpoint.replace(/\/$/, "")}/${bucket}/${object_key}`;
  const { data, error } = await a.from("fonts")
    .insert({ name: nama_final, file_name, file_url, ass_scale, is_active: true })
    .select("*").single();
  if (error) return NextResponse.json({ error: `DB insert gagal: ${error.message}` }, { status: 500 });

  await a.from("admin_audit").insert({
    admin_uid: g.user.id, action: "fonts.upload",
    detail: { name: nama_final, diketik_admin: name, file_name, ass_scale },
  });
  return NextResponse.json({ ok: true, row: data, file_url, ass_scale, nama_final, diketik_admin: name });
}
