#!/bin/bash
# Fetch YouTube analytics harian — dijalankan sebelum produksi pertama
# Cron: 0 6 * * * /home/rad4vm/viral-machine/scripts/fetch_analytics.sh
cd /home/rad4vm/viral-machine
/usr/bin/python3.11 -c "
from src.analytics.channel_analytics import ChannelAnalytics
result = ChannelAnalytics(tenant_id='ryan_andrian').fetch_and_store('ryan_andrian')
print(result)
" >> logs/analytics_$(date +%Y%m%d).log 2>&1
