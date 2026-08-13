#!/usr/bin/env bash
# deploy_be.sh — deploy backend (mv-worker + mv-webhook) di VPS: SATU perintah, path TERKUNCI.
# Pasangan deploy_fe.sh (insiden 2026-07-09). Aturan kerja §5: jalan DETACHED — tidak menunggu
# di SSH foreground; pull + restart + verifikasi kesehatan semuanya di sisi VPS.
#
# Lokasi di VPS = repo worker (~/viral-machine-v2/scripts/).
# Pakai (dari mana pun):
#   ssh vps '~/viral-machine-v2/scripts/deploy_be.sh start'          → deploy detached (kembali ~detik)
#   ssh vps '~/viral-machine-v2/scripts/deploy_be.sh start --force'  → lewati pagar render-sedang-jalan
#   ssh vps '~/viral-machine-v2/scripts/deploy_be.sh status'         → DEPLOYING / OK / FAIL (+bukti)
set -euo pipefail

BE_ROOT="/home/rad4vm/viral-machine-v2"   # = WorkingDirectory mv-worker & mv-webhook
BRANCH="v2-backend"
LOG="/tmp/deploy_be.log"
STATUS="/tmp/deploy_be.status"
HEALTH_URL="http://127.0.0.1:8088/health"

case "${1:-}" in
  start)
    # Gerbang anti-salah-tempat (pre-touch): BE_ROOT harus repo worker sungguhan.
    if [ ! -f "$BE_ROOT/scripts/worker_decoupled.py" ]; then
      echo "FATAL: $BE_ROOT bukan repo worker (scripts/worker_decoupled.py tak ada) — STOP."
      exit 1
    fi
    if pgrep -f "deploy_be.sh _deploy" >/dev/null 2>&1; then
      echo "Deploy BE lain sedang berjalan — pantau dengan: $0 status"
      exit 1
    fi
    # Pagar §2.1 (insiden 2026-06-17): restart mv-worker di tengah render = video terbunuh.
    # ffmpeg aktif = indikasi kuat produksi sedang berjalan; reaper akan membereskan run yang
    # terputus, tapi default = TUNDA. Sadar-risiko → tambah --force.
    if [ "${2:-}" != "--force" ] && pgrep -x ffmpeg >/dev/null 2>&1; then
      echo "TUNDA: ffmpeg aktif — kemungkinan besar produksi video sedang render."
      echo "Tunggu selesai, atau jalankan sadar-risiko: $0 start --force"
      exit 1
    fi
    echo "DEPLOYING sejak $(date '+%F %T')" > "$STATUS"
    nohup bash "$0" _deploy > "$LOG" 2>&1 &
    echo "Deploy BE dimulai (detached, PID $!). Pantau: $0 status"
    ;;

  _deploy)  # internal — dijalankan nohup oleh 'start'; JANGAN dipanggil manual.
    cd "$BE_ROOT"
    OLD_REQ_HASH="$(md5sum requirements.txt 2>/dev/null | cut -d' ' -f1)"
    if ! git pull origin "$BRANCH"; then
      echo "FAIL $(date '+%F %T') git pull gagal — log: $LOG" > "$STATUS"
      exit 1
    fi
    NEW_REQ_HASH="$(md5sum requirements.txt 2>/dev/null | cut -d' ' -f1)"
    if [ "$OLD_REQ_HASH" != "$NEW_REQ_HASH" ]; then
      echo "[deploy_be] requirements.txt berubah → pip install"
      if ! "$BE_ROOT/venv/bin/pip" install -r requirements.txt; then
        echo "FAIL $(date '+%F %T') pip install gagal (service TIDAK di-restart, kode lama tetap jalan) — log: $LOG" > "$STATUS"
        exit 1
      fi
    fi
    # ── [2026-08-13] PENYAPU LOG: pasang dari repo + periksa hasilnya ────────────────────────
    # Sebab langkah ini ada: aturan pemangkas log dulu HANYA hidup di server (ditulis 24-Apr, era
    # v1). Saat proyek pindah ke v2 (17-Jun) aturannya tertinggal menunjuk folder lama, dan selama
    # DUA BULAN melapor "does not exist -- skipping" tanpa satu pun telinga mendengar. Berkasnya di
    # luar repo → tak terversikan, tak terperiksa, tak terlihat saat melenceng.
    # Sekarang: ikut terkirim tiap deploy (selamat dari pembangunan ulang server) DAN hasilnya
    # diperiksa. Gagal di sini TIDAK menggagalkan deploy — tapi WAJIB kelihatan, bukan diam.
    LOGROTATE_SRC="$BE_ROOT/scripts/logrotate-viral-machine.conf"
    LOGROTATE_DST="/etc/logrotate.d/viral-machine"
    if [ -f "$LOGROTATE_SRC" ]; then
      if ! sudo cmp -s "$LOGROTATE_SRC" "$LOGROTATE_DST" 2>/dev/null; then
        echo "[deploy_be] aturan pemangkas log berubah → memasang"
        sudo install -o root -g root -m 644 "$LOGROTATE_SRC" "$LOGROTATE_DST" \
          && sudo logrotate -d "$LOGROTATE_DST" >/dev/null 2>&1 \
          && echo "[deploy_be] aturan pemangkas log terpasang & lolos jalan-kering" \
          || echo "[deploy_be] PERINGATAN: aturan pemangkas log GAGAL dipasang/diuji"
      fi
    else
      echo "[deploy_be] PERINGATAN: $LOGROTATE_SRC tidak ada di repo"
    fi
    # Alarm ukuran: kalau pemangkas diam-diam berhenti bekerja lagi, INI yang menyalakan lampunya.
    WORKER_LOG="$BE_ROOT/worker.log"
    LOG_MAX_MB="${DEPLOY_LOG_MAX_MB:-200}"
    if [ -f "$WORKER_LOG" ]; then
      LOG_MB=$(( $(stat -c %s "$WORKER_LOG") / 1048576 ))
      if [ "$LOG_MB" -gt "$LOG_MAX_MB" ]; then
        echo "[deploy_be] PERINGATAN: worker.log ${LOG_MB}MB (> ${LOG_MAX_MB}MB) — pemangkas log kemungkinan tidak bekerja"
      fi
    fi

    sudo systemctl restart mv-worker mv-webhook
    sleep 8
    W="$(systemctl is-active mv-worker || true)"
    H="$(systemctl is-active mv-webhook || true)"
    HC="$(curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL" || echo ERR)"
    if [ "$W" = "active" ] && [ "$H" = "active" ] && [ "$HC" = "200" ]; then
      echo "OK $(date '+%F %T') mv-worker=$W mv-webhook=$H health=$HC commit=$(git rev-parse --short HEAD)" > "$STATUS"
    else
      echo "FAIL $(date '+%F %T') mv-worker=$W mv-webhook=$H health=$HC — periksa journalctl" > "$STATUS"
      journalctl -u mv-worker -u mv-webhook -n 15 --no-pager 2>/dev/null || true
    fi
    ;;

  status)
    if [ ! -f "$STATUS" ]; then
      echo "Belum pernah dijalankan di mesin ini."
      exit 0
    fi
    cat "$STATUS"
    if grep -q '^DEPLOYING' "$STATUS" && ! pgrep -f "deploy_be.sh _deploy" >/dev/null 2>&1; then
      echo "PERINGATAN: status DEPLOYING tapi proses deploy tidak ada — kemungkinan mati di tengah. Log terakhir:"
      tail -10 "$LOG" 2>/dev/null || true
    fi
    if grep -q '^FAIL' "$STATUS"; then
      echo "--- 20 baris terakhir log ---"
      tail -20 "$LOG" 2>/dev/null || true
    fi
    ;;

  *)
    echo "Pakai: $0 start [--force] | status"
    exit 1
    ;;
esac
