import os
import json
import time
from loguru import logger
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.intelligence.config import TenantConfig, system_config

load_dotenv()

class YouTubePublisher:
    """
    Auto-publish video ke YouTube Shorts menggunakan OAuth token tenant.
    Multi-tenant ready — setiap tenant punya token sendiri.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.readonly"
    ]

    TOKEN_PATH = "token_youtube.json"

    def _get_credentials(self, tenant_config: TenantConfig) -> Credentials:
        token_path = getattr(tenant_config, 'youtube_token_path', self.TOKEN_PATH)
        if not os.path.exists(token_path):
            raise FileNotFoundError(f"YouTube token not found: {token_path}")

        with open(token_path) as f:
            token_data = json.load(f)

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", self.SCOPES)
        )

        if creds.expired and creds.refresh_token:
            logger.info("Refreshing expired YouTube token...")
            creds.refresh(Request())
            token_data["token"] = creds.token
            with open(token_path, "w") as f:
                json.dump(token_data, f)
            logger.info("Token refreshed successfully")

        return creds

    def _build_metadata(self, script: dict, tenant_config: TenantConfig) -> dict:
        title = script.get("title", script.get("topic", "Amazing Facts"))
        if len(title) > 100:
            title = title[:97] + "..."

        hook = script.get("hook", "")
        build_up = script.get("build_up", "")
        hashtags = script.get("hashtags", ["#shorts", "#facts", "#universe"])

        description_parts = [
            hook,
            "",
            build_up[:200] if build_up else "",
            "",
            "Follow for more mind-blowing facts about the universe!",
            "",
            " ".join(hashtags[:10])
        ]
        description = "\n".join(description_parts)[:5000]

        tags = []
        for tag in hashtags:
            clean = tag.replace("#", "").strip()
            if clean:
                tags.append(clean)
        tags.extend(["shorts", "facts", "universe", "space", "mindblowing"])

        return {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags[:500],
                "categoryId": "28",
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
                "madeForKids": False
            }
        }

    def publish(self, video_path: str, script: dict,
                tenant_config: TenantConfig) -> dict:
        """
        Upload video ke YouTube Shorts.
        Returns: dict berisi video_id dan URL jika berhasil.
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return {}

        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        logger.info(f"Uploading to YouTube: {video_path} ({file_size_mb:.1f} MB)")

        try:
            creds = self._get_credentials(tenant_config)
            youtube = build("youtube", "v3", credentials=creds)

            metadata = self._build_metadata(script, tenant_config)
            logger.info(f"Title: {metadata['snippet']['title']}")
            logger.info(f"Tags: {metadata['snippet']['tags'][:5]}")

            media = MediaFileUpload(
                video_path,
                mimetype="video/mp4",
                resumable=True,
                chunksize=1024 * 1024 * 5
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=metadata,
                media_body=media
            )

            response = None
            retry_count = 0
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info(f"Upload progress: {progress}%")
                except Exception as e:
                    retry_count += 1
                    if retry_count > 3:
                        raise e
                    logger.warning(f"Upload chunk failed, retrying ({retry_count}/3)...")
                    time.sleep(2 ** retry_count)

            video_id = response.get("id", "")
            video_url = f"https://www.youtube.com/shorts/{video_id}"

            logger.info(f"Upload complete!")
            logger.info(f"Video ID : {video_id}")
            logger.info(f"URL      : {video_url}")

            return {
                "platform": "youtube",
                "video_id": video_id,
                "url": video_url,
                "title": metadata["snippet"]["title"],
                "status": "published",
                "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            return {"platform": "youtube", "status": "failed", "error": str(e)}

    def get_channel_stats(self, tenant_config: TenantConfig) -> dict:
        try:
            creds = self._get_credentials(tenant_config)
            youtube = build("youtube", "v3", credentials=creds)
            response = youtube.channels().list(
                part="snippet,statistics",
                mine=True
            ).execute()

            if response.get("items"):
                item = response["items"][0]
                stats = item.get("statistics", {})
                return {
                    "channel_id": item["id"],
                    "title": item["snippet"]["title"],
                    "subscribers": int(stats.get("subscriberCount", 0)),
                    "total_views": int(stats.get("viewCount", 0)),
                    "video_count": int(stats.get("videoCount", 0))
                }
        except Exception as e:
            logger.error(f"Get channel stats error: {e}")
        return {}


if __name__ == "__main__":
    import glob

    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")
    publisher = YouTubePublisher()

    logger.info("Checking YouTube channel stats...")
    stats = publisher.get_channel_stats(tenant)
    if stats:
        print(f"\n{'='*60}")
        print(f"CHANNEL: {stats['title']}")
        print(f"{'='*60}")
        print(f"Subscribers : {stats['subscribers']:,}")
        print(f"Total Views : {stats['total_views']:,}")
        print(f"Videos      : {stats['video_count']}")
        print(f"{'='*60}")

    video_files = sorted(glob.glob("logs/video_ryan_andrian_*.mp4"))
    if not video_files:
        logger.error("No video found. Run video_renderer.py first.")
        exit(1)

    latest_video = video_files[-1]
    logger.info(f"Found video: {latest_video}")

    script_files = sorted(glob.glob("logs/optimized_ryan_andrian.json"))
    if not script_files:
        logger.error("No script found.")
        exit(1)

    with open(script_files[-1]) as f:
        scripts = json.load(f)
    script = scripts[0] if scripts else {}

    print(f"\nReady to upload:")
    print(f"Video : {latest_video} ({os.path.getsize(latest_video)/1024/1024:.1f} MB)")
    print(f"Title : {script.get('title', 'N/A')}")
    print(f"Hook  : {script.get('hook', 'N/A')}")

    confirm = input("\nUpload to YouTube Shorts? (yes/no): ").strip().lower()
    if confirm == "yes":
        result = publisher.publish(latest_video, script, tenant)
        if result.get("video_id"):
            print(f"\n{'='*60}")
            print(f"UPLOAD SUCCESSFUL!")
            print(f"{'='*60}")
            print(f"Video ID : {result['video_id']}")
            print(f"URL      : {result['url']}")
            print(f"Title    : {result['title']}")
            print(f"{'='*60}")
        else:
            print(f"\nUpload failed: {result.get('error', 'Unknown error')}")
    else:
        print("Upload cancelled.")
