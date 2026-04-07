#!/bin/bash
# Compute adaptive viral score weights bulanan — setiap tanggal 1, 08:00 UTC
# Cron: 0 8 1 * * /home/rad4vm/viral-machine/scripts/compute_viral_weights.sh
cd /home/rad4vm/viral-machine
/usr/bin/python3.11 scripts/compute_viral_weights.py >> logs/viral_weights_$(date +%Y%m%d).log 2>&1
