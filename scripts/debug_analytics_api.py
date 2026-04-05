"""Debug: cek exact error dari YouTube Analytics API."""
import sys, json, os
sys.path.insert(0, '/home/rad4vm/viral-machine')
from dotenv import load_dotenv
load_dotenv()

from src.analytics.channel_analytics import ChannelAnalytics

ca = ChannelAnalytics(tenant_id='ryan_andrian')

# Print scopes yang ada di token
print("Scopes di token:")
for s in (ca._creds.scopes or []):
    print(f"  {s}")

# Coba query Analytics API langsung dan print full error
try:
    from datetime import datetime, timezone
    response = (
        ca._analytics.reports()
        .query(
            ids       = "channel==MINE",
            startDate = "2026-01-01",
            endDate   = datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            metrics   = "views,estimatedMinutesWatched,averageViewPercentage",
            dimensions = "video",
            maxResults = 1,
        )
        .execute()
    )
    print("\nAnalytics API OK:", response)
except Exception as e:
    print(f"\nAnalytics API ERROR: {type(e).__name__}")
    print(f"Detail: {e}")
    # Coba print response body jika ada
    if hasattr(e, 'content'):
        try:
            print("Response body:", json.loads(e.content))
        except Exception:
            print("Response body (raw):", e.content)
