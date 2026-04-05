#!/bin/bash
# Compute channel insights mingguan — Senin 07:00 UTC
# Cron: 0 7 * * 1 /home/rad4vm/viral-machine/scripts/compute_insights.sh
cd /home/rad4vm/viral-machine
/usr/bin/python3.11 -c "
from src.analytics.performance_analyzer import PerformanceAnalyzer
result = PerformanceAnalyzer().compute_and_store('ryan_andrian')
print(result)
" >> logs/insights_$(date +%Y%m%d).log 2>&1
