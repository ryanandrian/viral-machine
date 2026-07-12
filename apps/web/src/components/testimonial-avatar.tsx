"use client";

// [Testimoni softcode 2026-07-12] Avatar bersama: photo_url (S3) MENANG; kosong → lingkaran
// inisial otomatis dari nama + avatar_color. Dipakai landing + blog Case Studies + halaman cerita.
export type Testimonial = {
  id: string; person_name: string; channel_label: string | null;
  quote: string; quote_en: string | null;
  metric_value: string | null; metric_label: string | null; metric_label_en: string | null;
  rating: number; avatar_color: string | null; photo_url: string | null;
  story_body: string | null; story_body_en: string | null; slug: string | null;
  show_on_landing: boolean; sort_order: number;
};

export const initialsOf = (name: string) =>
  name.trim().split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("");

export function TestimonialAvatar({ t, size = 40 }: { t: Pick<Testimonial, "person_name" | "photo_url" | "avatar_color">; size?: number }) {
  if (t.photo_url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={t.photo_url} alt={t.person_name}
      style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover", flex: "none", display: "block" }} />;
  }
  return (
    <span style={{
      width: size, height: size, borderRadius: "50%", flex: "none",
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      background: t.avatar_color || "var(--brand)", color: "#fff",
      fontWeight: 700, fontSize: size * 0.36,
    }}>{initialsOf(t.person_name)}</span>
  );
}
