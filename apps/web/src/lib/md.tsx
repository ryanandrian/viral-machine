import React from "react";

// Markdown → React minimal & AMAN (tanpa dependency). Escape HTML dulu, lalu whitelist:
// # ## ### heading · **bold** · *italic* · `code` · ```block``` · - list · [teks](url http/relatif) · paragraf.
// Konten = admin-authored; escape+whitelist mencegah injeksi HTML/script.
function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function inline(s: string): string {
  return esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|\/[^\s)]*)\)/g, '<a href="$2" rel="noopener">$1</a>');
}

export function Markdown({ source }: { source: string }) {
  const lines = (source || "").split("\n");
  const out: React.ReactNode[] = [];
  let i = 0, key = 0;
  let list: string[] = [];
  const flush = () => {
    if (list.length) { out.push(<ul key={key++}>{list.map((li, k) => <li key={k} dangerouslySetInnerHTML={{ __html: inline(li) }} />)}</ul>); list = []; }
  };
  while (i < lines.length) {
    const ln = lines[i];
    if (ln.startsWith("```")) {
      flush(); const buf: string[] = []; i++;
      while (i < lines.length && !lines[i].startsWith("```")) { buf.push(lines[i]); i++; }
      i++; out.push(<pre key={key++}><code>{buf.join("\n")}</code></pre>); continue;
    }
    const h = ln.match(/^(#{1,3})\s+(.*)$/);
    if (h) {
      flush(); const lvl = h[1].length;
      const props = { key: key++, dangerouslySetInnerHTML: { __html: inline(h[2]) } };
      out.push(lvl === 1 ? <h1 {...props} /> : lvl === 2 ? <h2 {...props} /> : <h3 {...props} />);
      i++; continue;
    }
    if (/^[-*]\s+/.test(ln)) { list.push(ln.replace(/^[-*]\s+/, "")); i++; continue; }
    if (ln.trim() === "") { flush(); i++; continue; }
    flush(); out.push(<p key={key++} dangerouslySetInnerHTML={{ __html: inline(ln) }} />); i++;
  }
  flush();
  return <>{out}</>;
}
