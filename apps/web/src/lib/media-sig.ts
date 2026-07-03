// Deteksi format + dimensi media dari HEADER BYTE (tanpa lib gambar) — satu sumber utk semua route upload
// (channels/upload-logo · admin/content/upload-cover · admin/showcase/upload). Jangan duplikasi lagi.

export function isPng(buf: Buffer): boolean {
  return buf.length > 4 && buf.readUInt32BE(0) === 0x89504e47; // \x89 P N G
}

export function isJpeg(buf: Buffer): boolean {
  return buf.length > 2 && buf[0] === 0xff && buf[1] === 0xd8;
}

// MP4: box pertama umumnya "ftyp" di offset 4 ("....ftyp").
export function isMp4(buf: Buffer): boolean {
  return buf.length > 12 && buf.toString("latin1", 4, 8) === "ftyp";
}

// PNG: header IHDR (sig 8B + len 4B + "IHDR" 4B → width@16, height@20, big-endian).
export function pngDimensions(buf: Buffer): { w: number; h: number } | null {
  if (buf.length < 24 || !isPng(buf)) return null;
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}

// JPEG: scan marker sampai SOF0/1/2 (0xC0/C1/C2) → height@+5, width@+7 (big-endian).
export function jpegDimensions(buf: Buffer): { w: number; h: number } | null {
  if (!isJpeg(buf) || buf.length < 4) return null;
  let i = 2;
  while (i + 9 < buf.length) {
    if (buf[i] !== 0xff) { i++; continue; }
    const marker = buf[i + 1];
    if (marker === 0xc0 || marker === 0xc1 || marker === 0xc2) {
      return { w: buf.readUInt16BE(i + 7), h: buf.readUInt16BE(i + 5) };
    }
    if (marker === 0xd8 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) { i += 2; continue; }
    i += 2 + buf.readUInt16BE(i + 2);
  }
  return null;
}

// Dimensi gambar apa pun yang kita dukung (PNG/JPG). null bila bukan keduanya / tak terbaca.
export function imageDimensions(buf: Buffer): { w: number; h: number; ext: "png" | "jpg"; contentType: string } | null {
  if (isPng(buf)) { const d = pngDimensions(buf); return d ? { ...d, ext: "png", contentType: "image/png" } : null; }
  if (isJpeg(buf)) { const d = jpegDimensions(buf); return d ? { ...d, ext: "jpg", contentType: "image/jpeg" } : null; }
  return null;
}
