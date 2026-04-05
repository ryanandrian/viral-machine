#!/bin/bash
# VPS Snapshot — jalankan di VPS, paste hasilnya ke Claude
# Usage: bash scripts/vps_snapshot.sh

echo "========================================"
echo "VPS SNAPSHOT — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "========================================"

echo ""
echo "--- OS & PYTHON ---"
uname -a
python3 --version
python3.11 --version 2>/dev/null || echo "python3.11: not found"
which python3
which python3.11 2>/dev/null || echo "python3.11 path: not found"

echo ""
echo "--- PIP PACKAGES (installed) ---"
pip3 freeze 2>/dev/null || pip freeze

echo ""
echo "--- CRONTAB ---"
crontab -l 2>/dev/null || echo "(no crontab)"

echo ""
echo "--- .ENV KEYS (nilai disembunyikan) ---"
if [ -f /home/rad4vm/viral-machine/.env ]; then
    grep -v '^#' /home/rad4vm/viral-machine/.env | grep '=' | sed 's/=.*/=***/' | sort
else
    echo ".env tidak ditemukan di /home/rad4vm/viral-machine/"
fi

echo ""
echo "--- DISK USAGE ---"
df -h /
du -sh /home/rad4vm/viral-machine/logs/ 2>/dev/null || echo "logs/ tidak ditemukan"

echo ""
echo "--- GIT STATUS ---"
cd /home/rad4vm/viral-machine && git log --oneline -5
echo "---"
git status --short

echo ""
echo "========================================"
echo "SNAPSHOT SELESAI"
echo "========================================"
