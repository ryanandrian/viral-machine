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

    # Category ID per niche
    NICHE_CATEGORY = {
        "universe_mysteries": "28",
        "dark_history":       "27",
        "ocean_mysteries":    "28",
        "fun_facts":          "27",
    }

    NICHE_BASE_TAGS = {
        "universe_mysteries": ["universe","space","NASA","astronomy","cosmos","space facts","galaxy","black hole","universe mysteries","space shorts"],
        "dark_history":       ["history","dark history","historical facts","history shorts","ancient history","world history","untold history","shocking history"],
        "ocean_mysteries":    ["ocean","deep sea","ocean mysteries","marine life","underwater","sea creatures","ocean facts","deep ocean","sea mystery"],
        "fun_facts":          ["fun facts","did you know","amazing facts","mind blowing","interesting facts","science facts","random facts","cool facts"],
    }

    NICHE_CTA = {
        "universe_mysteries": "Follow for more mind-blowing universe mysteries every day!",
        "dark_history":       "Follow for more shocking history facts you were never taught!",
        "ocean_mysteries":    "Follow for more terrifying ocean mysteries from the deep!",
        "fun_facts":          "Follow for more amazing facts that will blow your mind!",
    }

    def _build_metadata(self, script: dict, tenant_config: TenantConfig) -> dict:
        niche    = tenant_config.niche
        title    = script.get("title", script.get("topic", "Amazing Facts"))
        if len(title) > 100:
            title = title[:97] + "..."
        hook       = script.get("hook", "")
        mystery    = script.get("mystery_drop", "")
        build_up   = script.get("build_up", "")
        core_facts = script.get("core_facts", "")
        climax     = script.get("climax", "")
        hashtags   = script.get("hashtags", [])
        cta        = self.NICHE_CTA.get(niche, self.NICHE_CTA["fun_facts"])

        # ── s73: Hashtag strategy — topik + niche + universal ──
        try:
            from src.config.tenant_config import load_tenant_config
            rc = load_tenant_config(tenant_config.tenant_id)
            niche_tags = []
            if hasattr(rc, "niche_hashtags") and rc.niche_hashtags:
                niche_tags = rc.niche_hashtags.get(niche, [])
        except Exception:
            niche_tags = []

        topic_tags = [h for h in hashtags if h.startswith("#")][:5]
        niche_tags = [h for h in niche_tags if h not in topic_tags][:7]
        universal  = ["#shorts", "#viral", "#facts"]
        all_hashtags = topic_tags + niche_tags + universal
        seen = set()
        final_hashtags = []
        for h in all_hashtags:
            if h.lower() not in seen:
                seen.add(h.lower())
                final_hashtags.append(h)
        hashtag_str = " ".join(final_hashtags[:15])

        # ── s73: Description — CTA + hashtag dijamin masuk ──
        footer     = f"\n{cta}\n\n{hashtag_str}"
        MAX_DESC   = 4500
        hook_block = f"{hook}\n\n" if hook else ""
        budget     = MAX_DESC - len(footer) - len(hook_block)

        preview_full = " ".join(filter(None, [mystery, build_up, core_facts, climax]))
        if len(preview_full) > budget and budget > 0:
            preview_cut = preview_full[:budget]
            last_dot = max(
                preview_cut.rfind("."),
                preview_cut.rfind("!"),
                preview_cut.rfind("?")
            )
            if last_dot > budget // 2:
                preview_full = preview_cut[:last_dot + 1]
            else:
                preview_full = preview_cut.rsplit(" ", 1)[0]

        if preview_full.strip():
            description = f"{hook_block}{preview_full.strip()}{footer}"
        else:
            description = f"{hook_block.strip()}{footer}"
        description = description[:MAX_DESC]
        tags = list(self.NICHE_BASE_TAGS.get(niche, []))
        for tag in hashtags:
            clean = tag.replace("#", "").strip().lower()
            if clean and clean not in tags:
                tags.append(clean)
        for word in [w.strip(".,!?").lower() for w in title.split() if len(w) > 4]:
            if word not in tags:
                tags.append(word)
        for t in ["shorts", "youtubeshorts", "viral", "facts"]:
            if t not in tags:
                tags.append(t)
        return {
            "snippet": {
                "title":                title,
                "description":          description,
                "tags":                 tags[:500],
                "categoryId":           self.NICHE_CATEGORY.get(niche, "28"),
                "defaultLanguage":      "en",
                "defaultAudioLanguage": "en"
            },
            "status": {
                "privacyStatus":           "public",
                "selfDeclaredMadeForKids": False,
                "madeForKids":             False
            }
        }


    def publish(self, video_path: str, script: dict,
                tenant_config: TenantConfig,
                thumbnail_path: str = "") -> dict:
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

            # ── s72: Upload custom thumbnail ──────────────────
            if thumbnail_path and video_id:
                self._upload_thumbnail(youtube, video_id, thumbnail_path)

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

    def _upload_thumbnail(self, youtube, video_id: str, thumbnail_path: str) -> bool:
        """s72: Upload custom thumbnail via YouTube thumbnails.set()."""
        import os
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            logger.warning(f"[YouTube] Thumbnail tidak ada: {thumbnail_path}")
            return False
        try:
            # Resize ke 1280x720, max 2MB (YouTube limit)
            import subprocess as sp
            resized = thumbnail_path.replace(".jpg", "_yt.jpg")
            sp.run([
                "ffmpeg", "-y", "-i", thumbnail_path,
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease",
                "-q:v", "4", resized
            ], capture_output=True)
            # Pakai resized jika berhasil dan < 2MB, fallback ke original
            if os.path.exists(resized) and os.path.getsize(resized) < 2097152:
                upload_path = resized
            elif os.path.getsize(thumbnail_path) < 2097152:
                upload_path = thumbnail_path
            else:
                logger.warning("[YouTube] Thumbnail terlalu besar, skip")
                return False
            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(
                upload_path, mimetype="image/jpeg", resumable=False
            )
            youtube.thumbnails().set(
                videoId=video_id, media_body=media
            ).execute()
            logger.info(f"[YouTube] s72 Thumbnail uploaded OK: {video_id}")
            return True
        except Exception as e:
            logger.warning(f"[YouTube] Thumbnail upload gagal (non-critical): {e}")
            return False

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
