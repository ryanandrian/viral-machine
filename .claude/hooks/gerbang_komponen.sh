#!/usr/bin/env bash
# ============================================================================
# GERBANG KOMPONEN — menolak pembuatan berkas komponen FE BARU.
#
# Aturan owner: pakai pustaka komponen yang sudah ada (kini 20 berkas di
# apps/web/src/components/), jangan bikin baru. Sejalan CLAUDE.md §2.3(d):
# "elemen UI (tambah/ubah/hapus) = SELALU propose dulu".
#
# BATAS GERBANG INI — dibaca sebelum mempercayainya:
#   * Hanya menjaga berkas BARU di apps/web/src/components/.
#     MENGUBAH komponen lama tidak diblokir di sini — tetapi §2.3(d) tetap
#     menuntutnya diusulkan lebih dulu. Gerbang ini BUKAN pengganti pasal itu.
#   * Komponen yang ditanam langsung di dalam berkas halaman (bukan berkas
#     tersendiri) tidak terlihat oleh gerbang ini. Itu pintu samping yang
#     masih terbuka — owner sudah diberi tahu.
# ============================================================================
set -uo pipefail

MASUK="$(cat)"

BERKAS="$(printf '%s' "$MASUK" | python3.11 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input", {}).get("file_path", "") or "")
except Exception: print("")')"

case "$BERKAS" in
  */apps/web/src/components/*) ;;
  *) exit 0 ;;
esac

# Berkas sudah ada = menyunting yang lama, bukan membuat baru -> bukan urusan gerbang ini.
[ -e "$BERKAS" ] && exit 0

python3.11 - "$BERKAS" <<'PY'
import json, os, sys, glob
berkas = sys.argv[1]
dirn = os.path.dirname(berkas)
ada = sorted(os.path.basename(p) for p in glob.glob(os.path.join(dirn, "*.tsx")))
alasan = (
    "GERBANG KOMPONEN — PEMBUATAN BERKAS BARU DITOLAK.\n\n"
    f"Hendak dibuat: {os.path.basename(berkas)}\n\n"
    "Aturan owner: pakai pustaka komponen yang sudah ada, jangan bikin baru.\n"
    f"Yang tersedia sekarang ({len(ada)} berkas):\n"
    + "\n".join("  · " + n for n in ada)
    + "\n\nLangkah yang benar: pakai salah satu di atas. Bila memang TIDAK ADA yang\n"
      "cocok — berhenti, jelaskan kenapa kepada owner, dan tunggu izinnya (§2.3(d)).\n"
      "Jangan mengakalinya dengan menaruh komponen di folder lain."
)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": alasan}}))
PY
exit 0
