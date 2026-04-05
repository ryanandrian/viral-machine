"""
Re-authorize YouTube token untuk tambah scope yt-analytics.readonly.

Multi-channel ready: setiap channel punya token sendiri di tokens/{channel_id}.json

Jalankan SEKALI secara interaktif (butuh browser):
    python3.11 scripts/reauth_youtube.py --channel ryan_andrian

Setelah selesai:
- Token disimpan ke tokens/{channel_id}.json
- Pipeline upload dan analytics tidak terganggu — scope lama tetap ada
- Copy tokens/{channel_id}.json ke VPS (path yang sama)
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

TOKENS_DIR          = "tokens"
CLIENT_SECRET_PATH  = os.getenv("YOUTUBE_CLIENT_SECRET_PATH", "youtube_credentials.json")


def resolve_token_path(channel_id: str) -> str:
    """Konvensi: tokens/{channel_id}.json"""
    os.makedirs(TOKENS_DIR, exist_ok=True)
    return os.path.join(TOKENS_DIR, f"{channel_id}.json")


def main():
    parser = argparse.ArgumentParser(
        description="Re-authorize YouTube OAuth token per channel"
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Channel ID / tenant_id (contoh: ryan_andrian)",
    )
    args = parser.parse_args()
    channel_id = args.channel
    token_path = resolve_token_path(channel_id)

    print("=" * 60)
    print(f"YouTube Re-Authorization — Channel: {channel_id}")
    print("=" * 60)
    print(f"Token path  : {token_path}")
    print(f"Client file : {CLIENT_SECRET_PATH}")

    if not os.path.exists(CLIENT_SECRET_PATH):
        print(f"\nERROR: {CLIENT_SECRET_PATH} tidak ditemukan.")
        print("Download dari Google Cloud Console:")
        print("  APIs & Services → Credentials → OAuth 2.0 Client → Download JSON")
        print(f"  Simpan sebagai: {CLIENT_SECRET_PATH}")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("\nERROR: google-auth-oauthlib tidak terinstall.")
        print("Install: pip install google-auth-oauthlib")
        sys.exit(1)

    print(f"\nScopes yang akan diotorisasi:")
    for s in SCOPES:
        print(f"  - {s}")

    print(f"\nMembuka browser untuk otorisasi...")
    print("(Jika browser tidak terbuka, copy URL yang muncul ke browser manual)")

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
    creds = flow.run_local_server(port=0)

    # Preserve data token lama jika ada
    old_data = {}
    if os.path.exists(token_path):
        with open(token_path) as f:
            old_data = json.load(f)

    token_data = {
        **old_data,
        "channel_id":    channel_id,
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes),
    }

    with open(token_path, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\n✅ Token berhasil disimpan: {token_path}")
    print(f"Scopes aktif ({len(token_data['scopes'])}):")
    for s in token_data["scopes"]:
        marker = "✅" if "yt-analytics" in s else "  "
        print(f"  {marker} {s}")

    print(f"\nLangkah berikutnya:")
    print(f"1. Copy token ke VPS:")
    print(f"   scp {token_path} rad4vm@<IP_VPS>:/home/rad4vm/viral-machine/{token_path}")
    print(f"2. Verifikasi di VPS:")
    print(f"   python3.11 -c \"from src.analytics.channel_analytics import ChannelAnalytics; "
          f"print(ChannelAnalytics(tenant_id='{channel_id}').fetch_and_store('{channel_id}'))\"")


if __name__ == "__main__":
    main()
