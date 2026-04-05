"""
Force re-fetch analytics untuk semua video (reset fetched_at).
Gunakan setelah upgrade scope yt-analytics.readonly.
"""
import sys
import os
sys.path.insert(0, '/home/rad4vm/viral-machine')

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb  = create_client(url, key)

# Reset fetched_at supaya fetch_and_store mau re-fetch semua
result = sb.table("video_analytics").update({"fetched_at": "2000-01-01T00:00:00+00:00"}).eq("tenant_id", "ryan_andrian").execute()
print(f"Reset {len(result.data)} records fetched_at → force re-fetch aktif")

# Langsung jalankan fetch
from src.analytics.channel_analytics import ChannelAnalytics
out = ChannelAnalytics(tenant_id='ryan_andrian').fetch_and_store('ryan_andrian')
print(out)
