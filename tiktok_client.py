from typing import List, Dict, Any
from apify_client import ApifyClient
from config import Config

class TikTokClient:
    """
    Apify kullanarak resmi TikTok API veya kullanıcı girişi gerektirmeden
    kamuya açık TikTok profillerinin son videolarındaki yorumları toplar.
    """
    def __init__(self, api_token: str = None):
        self.api_token = api_token or Config.APIFY_API_TOKEN
        if not self.api_token:
            raise ValueError("Apify API anahtarı (APIFY_API_TOKEN) tanımlanmamış!")
        self.client = ApifyClient(self.api_token)
        self.scanned_videos: List[Dict[str, str]] = []

    @staticmethod
    def _get_dataset_id(run) -> str:
        if hasattr(run, "default_dataset_id"):
            return str(run.default_dataset_id)
        if isinstance(run, dict):
            return str(run.get("defaultDatasetId") or run.get("default_dataset_id") or "")
        return str(getattr(run, "defaultDatasetId", ""))

    @staticmethod
    def clean_username(identifier: str) -> str:
        """
        Gelen her türlü formatı (örn: /uykusuztosba, @uykusuztosba, tiktok.com/@uykusuztosba)
        temiz kullanıcı adına dönüştürür.
        """
        clean = identifier.strip().rstrip("/")
        if "tiktok.com/" in clean:
            clean = clean.split("tiktok.com/")[-1].split("/")[0]
        return clean.lstrip("@/").strip()

    def get_latest_videos_for_profiles(self, profiles: List[str], count: int = 3) -> List[Dict[str, Any]]:
        """
        Belirtilen TikTok profillerinin en son N adet videosunu tek bir Apify oturumunda çeker.
        """
        clean_profiles = [self.clean_username(p) for p in profiles if self.clean_username(p)]
        if not clean_profiles:
            return []

        print(f"[TikTok] {', '.join(clean_profiles)} profillerinin son {count} videosu sorgulanıyor...")

        run_input = {
            "profiles": clean_profiles,
            "resultsPerPage": count,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False
        }

        videos = []
        try:
            run = self.client.actor("clockworks/tiktok-scraper").call(run_input=run_input)
            dataset_id = self._get_dataset_id(run)
            for item in self.client.dataset(dataset_id).iterate_items():
                video_url = item.get("webVideoUrl") or ""
                video_id = str(item.get("id") or "")
                caption = (item.get("text") or "").strip()
                author_meta = item.get("authorMeta") or {}
                username = author_meta.get("name") or ""
                created_at = item.get("createTimeISO") or ""

                if not video_url and username and video_id:
                    video_url = f"https://www.tiktok.com/@{username}/video/{video_id}"

                if video_url:
                    video_info = {
                        "id": video_id,
                        "url": video_url,
                        "caption": caption,
                        "title": (caption[:45] + "...") if caption else "TikTok Videosu",
                        "username": username,
                        "channel": f"@{username}",
                        "published_at": created_at,
                    }
                    videos.append(video_info)
                    self.scanned_videos.append(video_info)

            print(f"[TikTok] Toplam {len(videos)} adet video bulundu.")
            return videos

        except Exception as e:
            print(f"[TikTok Video Çekme Hatası]: {e}")
            return []

    def get_comments_for_videos(self, videos: List[Dict[str, Any]], max_comments_per_video: int = 30) -> List[Dict[str, Any]]:
        """
        Verilen video URL'lerindeki yorumları çeker ve hukuki delil formatına dönüştürür.
        """
        if not videos:
            return []

        video_urls = [v["url"] for v in videos if v.get("url")]
        if not video_urls:
            return []

        print(f"[TikTok] {len(video_urls)} video için yorumlar toplanıyor (video başına maks {max_comments_per_video})...")

        # Video URL'lerini detaylarıyla eşleştiren harita
        video_map = {v["url"]: v for v in videos}

        run_input = {
            "postURLs": video_urls,
            "commentsPerPost": max_comments_per_video,
        }

        all_comments = []
        try:
            run = self.client.actor("clockworks/tiktok-comments-scraper").call(run_input=run_input)
            dataset_id = self._get_dataset_id(run)

            for item in self.client.dataset(dataset_id).iterate_items():
                raw_id = str(item.get("cid") or item.get("id") or "").strip()
                text = (item.get("text") or "").strip()
                if not raw_id or not text:
                    continue

                comment_id = f"tt_{raw_id}"
                user_handle = item.get("uniqueId") or "tiktok_user"
                user_id = str(item.get("uid") or user_handle)
                avatar = item.get("avatarThumbnail") or ""
                video_url = item.get("videoWebUrl") or item.get("submittedVideoUrl") or ""

                v_info = video_map.get(video_url, {})
                channel_name = v_info.get("channel", "")
                if not channel_name and video_url and "@" in video_url:
                    channel_name = "@" + video_url.split("@")[-1].split("/")[0]

                video_title = v_info.get("title") or "TikTok Videosu"
                comment_url = f"{video_url}?comment_id={raw_id}" if video_url else ""

                all_comments.append({
                    "comment_id": comment_id,
                    "platform": "TikTok",
                    "channel_name": channel_name,
                    "video_id": v_info.get("id") or raw_id,
                    "video_title": video_title,
                    "video_url": video_url,
                    "comment_url": comment_url,
                    "author_name": f"@{user_handle.lstrip('@')}",
                    "author_channel_url": f"https://www.tiktok.com/@{user_handle.lstrip('@')}",
                    "author_channel_id": user_id,
                    "author_profile_image": avatar,
                    "text": text,
                    "published_at": item.get("createTimeISO") or "",
                    "updated_at": item.get("createTimeISO") or "",
                    "like_count": item.get("diggCount", 0),
                })

            print(f"[TikTok] Toplam {len(all_comments)} adet yorum başarıyla toplandı.")
            return all_comments

        except Exception as e:
            print(f"[TikTok Yorum Çekme Hatası]: {e}")
            return []

    def get_comments_for_profiles(self, profiles: List[str], video_count: int = 3, max_comments_per_video: int = 30) -> List[Dict[str, Any]]:
        """
        Profillerin son videolarını bulur ve yorumlarını eksiksiz toplar.
        """
        videos = self.get_latest_videos_for_profiles(profiles, count=video_count)
        if not videos:
            return []
        return self.get_comments_for_videos(videos, max_comments_per_video=max_comments_per_video)
