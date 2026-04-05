"""Validasi ChannelAnalytics — jalankan di VPS setelah git pull."""
import sys
sys.path.insert(0, '/home/rad4vm/viral-machine')

from src.analytics.channel_analytics import ChannelAnalytics

result = ChannelAnalytics(tenant_id='ryan_andrian').fetch_and_store('ryan_andrian')
print(result)
