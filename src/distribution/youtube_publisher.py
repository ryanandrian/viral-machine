import os
import json
import time
from loguru import logger
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.intelligence.config import TenantConfig, system_config
from src.exceptions import PublishError, ErrorClass

load_dotenv()


def _niche_default_hashtags(niche: str) -> list:
    """Lapis DEFAULT hashtag niche (niches.default_hashtags, diatur admin via Niche Studio).
    Dipakai sebagai fallback saat channel belum override (channels.niche_hashtags[niche] kosong).
    Fail-soft → []."""
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        r = sb.table("niches").select("default_hashtags").eq("niche_id", niche).limit(1).execute()
        dh = (r.data or [{}])[0].get("default_hashtags") or []
        return dh if isinstance(dh, list) else []
    except Exception as e:
        logger.warning(f"[YouTube] ambil default_hashtags niche {niche} gagal (non-fatal): {e}")
        return []


def _niche_video_tags(niche: str) -> list:
    """Tag video (snippet.tags = kata-kunci TERSEMBUNYI utk pencarian/rekomendasi YouTube; beda dari #hashtag).
    Sumber = `niches.keywords` (diatur admin via Niche Library / tenant via Niche Studio) — BUKAN lagi hardcode
    per-niche ryan. Niche tanpa keywords → [] (graceful; admin isi). Fail-soft → []."""
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        r = sb.table("niches").select("keywords").eq("niche_id", niche).limit(1).execute()
        kw = (r.data or [{}])[0].get("keywords") or []
        return kw if isinstance(kw, list) else []
    except Exception as e:
        logger.warning(f"[YouTube] ambil keywords niche {niche} gagal (non-fatal): {e}")
        return []


def _niche_category(niche: str) -> str:
    """categoryId YouTube per-niche dari `niches.youtube_category_id` (diatur admin via Niche Library /
    tenant via Niche Studio) — BUKAN lagi hardcode per-niche ryan. Fallback "27" (Education). Fail-soft."""
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        r = sb.table("niches").select("youtube_category_id").eq("niche_id", niche).limit(1).execute()
        cat = (r.data or [{}])[0].get("youtube_category_id")
        return str(cat) if cat else "27"
    except Exception as e:
        logger.warning(f"[YouTube] ambil category niche {niche} gagal (non-fatal): {e}")
        return "27"


class YouTubePublisher:
    """
    Auto-publish video ke YouTube Shorts menggunakan OAuth token tenant.
    Multi-tenant ready — setiap tenant punya token sendiri.
    """

    # B4: scope "kelola penuh" (.../auth/youtube) DIBUANG — dulu hanya dipakai update deskripsi channel
    # (hardcode, sudah dihapus). Sisa = upload (tulis judul+deskripsi video) + baca channel + analitik.
    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ]

    TOKEN_PATH = "token_youtube.json"  # backward compatible fallback

    def _get_credentials(self, tenant_config: TenantConfig, channel_id: str | None = None) -> Credentials:
        # OAuth Platform (model POOL 2026-06-25): kredensial dari tenant_youtube_accounts (via channels.youtube_account_id).
        # client_id/secret = app PLATFORM (.env GOOGLE_CLIENT_*). NO-FALLBACK file (fosil single-tenant dibuang).
        from src.utils.tenant_credentials import load_google_credentials, save_google_access_token
        ch_id      = channel_id or getattr(tenant_config, "channel_id", None)
        token_data = load_google_credentials(tenant_config.tenant_id, channel_id=ch_id)
        if not token_data:
            raise RuntimeError(
                f"OAuth YouTube belum tersambung utk tenant {tenant_config.tenant_id} — hubungkan di Kredensial (no-fallback)."
            )
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes") or self.SCOPES
        )
        if creds.expired and creds.refresh_token:
            logger.info("Refreshing expired YouTube token (pool)...")
            try:
                creds.refresh(Request())
            except RefreshError as e:
                # [B11] 3.2 — HANYA `invalid_grant` (refresh token dicabut/kedaluwarsa PERMANEN,
                # kode kanonik OAuth2 RFC 6749) = koneksi mati, mustahil sembuh dgn diulang → tandai
                # INVALID (rem produksi/publish seketika, hemat biaya) + gagal JUJUR ber-kelas
                # AUTH_INVALID. RefreshError LAIN (mis. 5xx endpoint token) = transien → re-raise apa
                # adanya (perilaku lama, retryable). HARAM tandai-invalid atas asumsi liar (§6 error-mgmt).
                if "invalid_grant" in str(e).lower():
                    from src.utils.tenant_credentials import mark_youtube_account_invalid
                    mark_youtube_account_invalid(tenant_config.tenant_id, ch_id, reason=str(e)[:200])
                    _label = getattr(tenant_config, "channel_name", "") or ch_id or ""
                    raise PublishError(
                        f"YouTube OAuth invalid_grant (koneksi channel {_label} dicabut/kedaluwarsa): {e}",
                        step="publish", error_class=ErrorClass.AUTH_INVALID,
                        human_message=(f"Koneksi YouTube channel '{_label}' terputus — sambungkan ulang "
                                       f"di menu Integrasi → Koneksi YouTube."),
                    ) from e
                raise
            save_google_access_token(tenant_config.tenant_id, creds.token, channel_id=ch_id)
            logger.info("Token refreshed successfully")
        return creds

    def _token_channel_id(self, youtube) -> str | None:
        """[B11] Identitas channel milik token aktif (channels.list mine=true). None = tak terbaca."""
        try:
            items = youtube.channels().list(part="id", mine=True).execute().get("items", [])
            return items[0]["id"] if items else None
        except Exception as e:
            logger.warning(f"[Publisher] baca identitas token gagal: {e}")
            return None

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
        cta        = self._resolve_cta(tenant_config)   # 5C: ikut channel cta_mode (Branded), bukan hardcode per-niche

        # ── s73: Hashtag strategy — topik + niche + universal ──
        try:
            from src.config.tenant_config import load_tenant_config
            rc = load_tenant_config(tenant_config.tenant_id, getattr(tenant_config, "channel_id", None), getattr(tenant_config, "niche", None))
            niche_tags = []
            if hasattr(rc, "niche_hashtags") and rc.niche_hashtags:
                niche_tags = rc.niche_hashtags.get(niche, []) or []
            if not niche_tags:
                # Channel belum override → fallback default hashtag niche (lapis niche, admin/Niche Studio).
                niche_tags = _niche_default_hashtags(niche)
        except Exception:
            niche_tags = []

        topic_tags = [h for h in hashtags if h.startswith("#")][:2]
        niche_tags = [h for h in niche_tags if h not in topic_tags][:2]
        universal  = ["#Shorts"]
        all_hashtags = topic_tags + niche_tags + universal
        seen = set()
        final_hashtags = []
        for h in all_hashtags:
            if h.lower() not in seen:
                seen.add(h.lower())
                final_hashtags.append(h)
        hashtag_str = " ".join(final_hashtags[:5])

        # ── Description footer — CTA (kalau ada, dari cta_mode channel) + hashtag ──
        # 5C: CTA kosong (implicit) → TANPA baris CTA (tak ada baris kosong nyangkut).
        _foot_parts = [p for p in [cta, hashtag_str] if p]
        footer     = ("\n" + "\n\n".join(_foot_parts)) if _foot_parts else ""
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

        # Branded Content (§6): sisipkan landing_link di deskripsi (top|bottom). Pinned comment
        # mustahil via API → pakai link deskripsi. cta soft-sell brand = di script (cta_mode).
        link = getattr(tenant_config, "landing_link", None)
        if link:
            pos = (getattr(tenant_config, "link_position", "bottom") or "bottom").lower()
            if pos == "top":
                description = f"{link}\n\n{description}"[:MAX_DESC]
            else:
                room = max(0, MAX_DESC - len(link) - 2)
                description = f"{description[:room]}\n\n{link}"
        # Bahasa konten channel → metadata YouTube. Subtag UTAMA BCP-47 ('id-ID'→'id'; 'en-US'→'en'
        # = byte-identik nilai lama utk channel English → nol regresi). Fosil hardcode "en" dibuang 2026-07-05.
        content_lang = ((getattr(tenant_config, "language", None) or "en-US").strip() or "en-US").split("-")[0].lower()
        tags = list(_niche_video_tags(niche))   # 5A: dari niches.keywords (DB), bukan hardcode
        for tag in hashtags:
            clean = tag.replace("#", "").strip().lower()
            if clean and clean not in tags:
                tags.append(clean)
        for word in [w.strip(".,!?").lower() for w in title.split() if len(w) > 4]:
            if word not in tags:
                tags.append(word)
        for t in ["shorts", "youtubeshorts", "viral"]:
            if t not in tags:
                tags.append(t)
        return {
            "snippet": {
                "title":                title,
                "description":          description,
                "tags":                 tags[:500],
                "categoryId":           _niche_category(niche),
                "defaultLanguage":      content_lang,
                "defaultAudioLanguage": content_lang,
            },
            "status": {
                # Config-driven (no-hardcode): default 'public'; override utk test/staging.
                # Sumber: tenant_config.publish_privacy → env YOUTUBE_PRIVACY_STATUS → 'public'.
                "privacyStatus":           self._privacy_status(tenant_config),
                "selfDeclaredMadeForKids": False,
                "madeForKids":             False,
                # Phase 6.3 (§9.2) — disclosure Altered/Synthetic content (field RESMI YouTube API,
                # sejak 2024-10-30; wajib kebijakan Mei 2025). Per-channel, default ON (compliance-first).
                "containsSyntheticMedia":  bool(getattr(tenant_config, "ai_disclosure", True)),
            }
        }


    @staticmethod
    def _resolve_cta(tenant_config) -> str:
        """CTA deskripsi (footer) = ikut Branded channel (`cta_mode`), BUKAN hardcode per-niche (5C).
        `implicit` → "" (TANPA baris CTA — selaras filosofi narasi yg melarang follow/subscribe);
        `soft_sell` → `brand_cta_text` channel (kosong → ""). CTA NARASI (beat) & mode di script_engine
        TIDAK disentuh — ini hanya footer deskripsi."""
        mode = (getattr(tenant_config, "cta_mode", "implicit") or "implicit").lower()
        if mode == "soft_sell":
            return (getattr(tenant_config, "brand_cta_text", None) or "").strip()
        return ""

    @staticmethod
    def _privacy_status(tenant_config) -> str:
        """privacyStatus config-driven: tenant_config.publish_privacy → env → 'public'.
        Hanya menerima nilai sah YouTube; selain itu fallback 'public' (fail-safe)."""
        # DEFAULT private (trial-safe): tenant uji config dulu, ubah ke public saat cocok.
        val = (getattr(tenant_config, "publish_privacy", None)
               or os.getenv("YOUTUBE_PRIVACY_STATUS")
               or "private")
        val = str(val).strip().lower()
        return val if val in ("public", "private", "unlisted") else "private"

    def publish(self, video_path: str, script: dict,
                tenant_config: TenantConfig,
                thumbnail_path: str = "",
                content_type: str = "short") -> dict:
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

            # ── [B11] Batch 1.4 — PAGAR SALAH-CHANNEL (multi-channel) ─────────────────
            # Upload YouTube SELALU jatuh ke channel milik token (API tak punya "pilih channel").
            # Maka: identitas token HARUS == channel tujuan (channels.platform_channel_id).
            # Selisih/tak terbaca → GAGAL JUJUR tanpa upload (no silent wrong-channel publish).
            expected = (getattr(tenant_config, "platform_channel_id", None) or "").strip()
            if expected:
                actual = self._token_channel_id(youtube)
                if not actual:
                    msg = ("Identitas channel token YouTube tak terbaca — upload DIBATALKAN "
                           "(pagar salah-channel; akan diulang otomatis).")
                    logger.error(f"[Publisher] {msg}")
                    return {"platform": "youtube", "status": "failed", "error": msg}
                if actual != expected:
                    msg = (f"PAGAR SALAH-CHANNEL: token = {actual}, channel tujuan = {expected}. "
                           f"Upload DIBATALKAN. Periksa 'Koneksi YouTube' channel ini di menu Channel.")
                    logger.error(f"[Publisher] {msg}")
                    return {"platform": "youtube", "status": "failed", "error": msg}
            # (expected kosong = channel tanpa target — jalur test/legacy; tak ada target utk dilindungi.)

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
                self._upload_thumbnail(youtube, video_id, thumbnail_path, content_type)

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
            # [B11] 3.2 — teruskan makna error (error_class/human_message) lewat dict hasil supaya
            # pemanggil (publisher decoupled) bisa bereaksi tepat (mis. AUTH_INVALID = jangan kirim
            # pesan 'akan diulang' yang menyesatkan). Aditif → nol regresi pemanggil lama.
            _ec = getattr(e, "error_class", None)
            return {"platform": "youtube", "status": "failed", "error": str(e),
                    "error_class": _ec.value if _ec else None,
                    "human_error": getattr(e, "human_message", None)}

    def _upload_thumbnail(self, youtube, video_id: str, thumbnail_path: str,
                          content_type: str = "short") -> bool:
        """
        s72/s92: Upload custom thumbnail via YouTube thumbnails.set().

        Dimensi berdasarkan content_type:
          short → 1080×1920 portrait (9:16) — Shorts, min width YouTube 640px terpenuhi
          long  → 1280×720  landscape (16:9) — regular video
        """
        import os
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            logger.warning(f"[YouTube] Thumbnail tidak ada: {thumbnail_path}")
            return False
        try:
            import subprocess as sp

            # Dimensi target berdasarkan content_type
            if content_type == "long":
                target_w, target_h = 1280, 720
            else:
                # short (default) — portrait 9:16
                target_w, target_h = 1080, 1920

            scale_filter = (
                f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
            )

            resized = thumbnail_path.replace(".jpg", "_yt.jpg")
            sp.run([
                "ffmpeg", "-y", "-i", thumbnail_path,
                "-vf", scale_filter,
                "-q:v", "3", resized
            ], capture_output=True)

            # Pakai resized jika berhasil dan < 2MB, fallback ke original
            if os.path.exists(resized) and os.path.getsize(resized) < 2097152:
                upload_path = resized
                logger.info(
                    f"[YouTube] Thumbnail resized → {target_w}×{target_h} "
                    f"({content_type}) | {os.path.getsize(resized)/1024:.0f}KB"
                )
            elif os.path.getsize(thumbnail_path) < 2097152:
                upload_path = thumbnail_path
                logger.warning("[YouTube] Thumbnail resize gagal — pakai original")
            else:
                logger.warning("[YouTube] Thumbnail terlalu besar, skip")
                return False

            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(
                upload_path, mimetype="image/jpeg", resumable=False
            )
            # E1: retry transient (read timeout dll) — samakan resiliensi dgn video upload
            # (videos.insert pakai retry 3×). num_retries = exponential backoff googleapiclient.
            youtube.thumbnails().set(
                videoId=video_id, media_body=media
            ).execute(num_retries=3)
            logger.info(f"[YouTube] Thumbnail uploaded OK: {video_id} ({content_type})")
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
