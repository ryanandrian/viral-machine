#!/usr/bin/env bash
# deploy_fe.sh — deploy frontend mesinviral.com di VPS: SATU perintah, path TERKUNCI.
# Lahir dari insiden 2026-07-09: build dijalankan di root repo (bukan apps/web) → gagal + buang waktu.
# Aturan kerja §5: perintah VPS yang lama = DETACHED + poll — DILARANG menunggu di SSH foreground
# (koneksi putus → error 255, build ikut mati). `start` kembali seketika; build + restart + verifikasi
# situs semuanya jalan di sisi VPS sendiri.
#
# Pakai (dari mana pun):
#   ssh vps '~/mesinviral-web/scripts/deploy_fe.sh start'    → pull + build detached (kembali ~detik)
#   ssh vps '~/mesinviral-web/scripts/deploy_fe.sh status'   → BUILDING / OK / FAIL (+bukti situs)
set -euo pipefail

FE_ROOT="/home/rad4vm/mesinviral-web"
APP_DIR="$FE_ROOT/apps/web"   # = WorkingDirectory mv-web.service — SATU-SATUNYA tempat build yang sah
BRANCH="v2-backend"
LOG="/tmp/deploy_fe.log"
STATUS="/tmp/deploy_fe.status"
SITE="https://mesinviral.com"

case "${1:-}" in
  start)
    # Gerbang anti-salah-tempat (pre-touch): APP_DIR harus app Next.js sungguhan.
    if ! grep -q '"build": "next build"' "$APP_DIR/package.json" 2>/dev/null; then
      echo "FATAL: $APP_DIR bukan app Next.js (package.json tanpa script 'next build') — STOP."
      exit 1
    fi
    if pgrep -f "next build" >/dev/null 2>&1; then
      echo "Build lain sedang berjalan — pantau dengan: $0 status"
      exit 1
    fi
    cd "$FE_ROOT"
    git pull origin "$BRANCH"
    echo "BUILDING sejak $(date '+%F %T') commit=$(git rev-parse --short HEAD)" > "$STATUS"
    nohup bash "$0" _build > "$LOG" 2>&1 &
    echo "Build dimulai (detached, PID $!). Pantau: $0 status"
    ;;

  _build)  # internal — dijalankan nohup oleh 'start'; JANGAN dipanggil manual.
    cd "$APP_DIR"
    if npm run build; then
      sudo systemctl restart mv-web
      sleep 5
      ACT="$(systemctl is-active mv-web || true)"
      HTTP="$(curl -s -o /dev/null -w '%{http_code}' "$SITE" || echo ERR)"
      if [ "$ACT" = "active" ] && [ "$HTTP" = "200" ]; then
        echo "OK $(date '+%F %T') mv-web=$ACT situs=$HTTP commit=$(git -C "$FE_ROOT" rev-parse --short HEAD)" > "$STATUS"
      else
        echo "FAIL $(date '+%F %T') build OK tapi mv-web=$ACT situs=$HTTP — periksa service/nginx" > "$STATUS"
      fi
    else
      echo "FAIL $(date '+%F %T') build gagal — log: $LOG" > "$STATUS"
    fi
    ;;

  status)
    if [ ! -f "$STATUS" ]; then
      echo "Belum pernah dijalankan di mesin ini."
      exit 0
    fi
    cat "$STATUS"
    # BUILDING tapi prosesnya sudah tidak ada = mati di tengah (mis. VPS reboot) — jangan diam.
    if grep -q '^BUILDING' "$STATUS" && ! pgrep -f "next build" >/dev/null 2>&1; then
      echo "PERINGATAN: status BUILDING tapi tidak ada proses build — kemungkinan mati di tengah. Log terakhir:"
      tail -10 "$LOG" 2>/dev/null || true
    fi
    if grep -q '^FAIL' "$STATUS"; then
      echo "--- 20 baris terakhir log ---"
      tail -20 "$LOG" 2>/dev/null || true
    fi
    ;;

  *)
    echo "Pakai: $0 start|status"
    exit 1
    ;;
esac
