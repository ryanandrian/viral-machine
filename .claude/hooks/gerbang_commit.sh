#!/usr/bin/env bash
# ============================================================================
# GERBANG COMMIT — menolak `git commit` yang melanggar dua pasal CLAUDE.md.
#
#   PENJAGA 1 (§3.8 NOL REGRESI) : ada kode ter-stage tapi uji MERAH  -> TOLAK
#   PENJAGA 2 (§3.7 TUTUP ADMIN) : ada kode ter-stage tapi NOL dokumen -> TOLAK
#
# BATAS GERBANG INI — dibaca sebelum mempercayainya:
#   * Uji HIJAU **BUKAN** bukti runtime (§3.4). Gerbang ini menangkap REGRESI pada
#     yang sudah diuji; ia TIDAK menangkap salah-nalar. Bukti: cacat yang dikirim
#     pada commit 0d64f79 lolos seluruh 813 uji karena logikanya salah, bukan rusak.
#   * PENJAGA 2 hanya melihat dokumen DI DALAM repo. `MEMORY.md` ada di luar repo,
#     jadi §3.7 TIDAK selesai hanya karena gerbang ini lolos.
#   * PENJAGA 2 menuntut dokumen LAMA diperbarui — TIDAK PERNAH menuntut dokumen
#     .md baru (§1.1 melarang berkas .md baru).
#
# PINTU DARURAT, sengaja terlihat selamanya: sisipkan `[tanpa-dokumen: <alasan>]`
# di pesan commit. Alasannya tercetak di `git log` dan bisa owner audit kapan pun.
# ============================================================================
set -uo pipefail

AKAR="/home/rad/viral-machine"
MASUK="$(cat)"

tolak() {
  python3.11 - "$1" <<'PY'
import json, sys
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": sys.argv[1]}}))
PY
  exit 0
}

CMD="$(printf '%s' "$MASUK" | python3.11 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input", {}).get("command", "") or "")
except Exception: print("")')"

# Bukan perintah commit -> gerbang diam, nol perlambatan.
case "$CMD" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

cd "$AKAR" 2>/dev/null || exit 0

STAGED="$(git diff --cached --name-only 2>/dev/null || true)"
[ -z "$STAGED" ] && exit 0

KODE="$(printf '%s\n' "$STAGED" | grep -E '\.(py|ts|tsx|js|jsx|sql)$' || true)"
# Commit dokumen-saja / konfigurasi-saja tidak perlu dijaga -> lewat, tanpa 57 detik uji.
[ -z "$KODE" ] && exit 0

# ---------- PENJAGA 1: uji harus hijau (§3.8) ----------
LOG="$(mktemp)"
if ! python3.11 -m pytest tests/ -q >"$LOG" 2>&1; then
  EKOR="$(tail -n 12 "$LOG")"
  rm -f "$LOG"
  tolak "GERBANG NOL-REGRESI (CLAUDE.md §3.8) — COMMIT DITOLAK.

Ada kode ter-stage, tetapi suite uji MERAH:

${EKOR}

Perbaiki dulu sampai hijau. Jangan menonaktifkan atau melewati gerbang ini.
Catatan: hijau pun BUKAN bukti runtime (§3.4) — ia hanya berarti tak ada regresi
pada yang sudah diuji."
fi
rm -f "$LOG"

# ---------- PENJAGA 2: dokumen ikut diperbarui (§3.7) ----------
DOK="$(printf '%s\n' "$STAGED" | grep -E '\.md$' || true)"
if [ -z "$DOK" ]; then
  case "$CMD" in
    *"[tanpa-dokumen:"*) ;;
    *)
      tolak "GERBANG DOKUMEN-SSOT (CLAUDE.md §3.7) — COMMIT DITOLAK.

Kode ter-stage tanpa SATU pun berkas .md ikut ter-stage:

$(printf '%s\n' "$KODE" | sed 's/^/  · /')

Perbarui dokumen SSOT topik ini + kolom REALISASI di SISA_KERJA_GO_LIVE.md pada
commit YANG SAMA — bukan 'nanti'. Perbarui dokumen yang SUDAH ADA; jangan membuat
berkas .md baru (§1.1).

Bila commit ini memang tak menyentuh perilaku yang terdokumentasi, sisipkan di
pesan commit:  [tanpa-dokumen: <alasan singkat>]
Alasan itu akan terlihat selamanya di git log dan bisa owner audit.

INGAT: gerbang ini tidak melihat MEMORY.md (di luar repo). Lolos di sini TIDAK
berarti §3.7 sudah tuntas."
      ;;
  esac
fi

exit 0
