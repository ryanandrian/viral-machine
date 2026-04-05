"""
Re-authorize YouTube token untuk tambah scope yt-analytics.readonly.

Jalankan SEKALI secara interaktif (butuh browser):
    python3.11 scripts/reauth_youtube.py

Setelah selesai, token_youtube.json akan diupdate dengan scope baru.
Pipeline upload YouTube tidak terganggu — scope lama tetap ada.
"""

import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
    # Scope baru untuk YouTube Analytics API v2
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

TOKEN_PATH          = "token_youtube.json"
CLIENT_SECRET_PATH  = os.getenv("YOUTUBE_CLIENT_SECRET_PATH", "client_secret.json")


def main():
    print("=" * 60)
    print("YouTube Re-Authorization — Tambah yt-analytics scope")
    print("=" * 60)

    if not os.path.exists(CLIENT_SECRET_PATH):
        print(f"\nERROR: {CLIENT_SECRET_PATH} tidak ditemukan.")
        print("Download dari Google Cloud Console:")
        print("  APIs & Services → Credentials → OAuth 2.0 Client → Download JSON")
        print(f"  Simpan sebagai: {CLIENT_SECRET_PATH}")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("\nERROR: Package tidak tersedia.")
        print("Install: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    print(f"\nScopes yang akan diotorisasi:")
    for s in SCOPES:
        print(f"  - {s}")

    print(f"\nMembuka browser untuk otorisasi...")
    print("(Jika browser tidak terbuka, copy URL yang muncul ke browser manual)")

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
    creds = flow.run_local_server(port=0)

    # Baca token lama untuk preserve data yang ada
    old_data = {}
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            old_data = json.load(f)

    # Tulis token baru
    token_data = {
        **old_data,
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes),
    }

    with open(TOKEN_PATH, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\n✅ Token berhasil diupdate: {TOKEN_PATH}")
    print(f"Scopes aktif: {len(token_data['scopes'])}")
    for s in token_data["scopes"]:
        marker = "✅" if "yt-analytics" in s else "  "
        print(f"  {marker} {s}")

    print("\nSekarang jalankan:")
    print("  python3.11 -c \"from src.analytics.channel_analytics import ChannelAnalytics; "
          "print(ChannelAnalytics().fetch_and_store('ryan_andrian'))\"")


if __name__ == "__main__":
    main()
