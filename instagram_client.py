from typing import List, Dict, Any
from apify_client import ApifyClient
from config import Config

class InstagramClient:
    """
    Apify kullanarak Meta API ve giriş (login) gerektirmeden
    kamuya açık Instagram profillerinin son gönderilerindeki yorumları toplar.
    """
    def __init__(self, api_token: str = None):
        self.api_token = api_token or Config.APIFY_API_TOKEN
        if not self.api_token:
            raise ValueError("Apify API anahtarı (APIFY_API_TOKEN) tanımlanmamış!")
        self.client = ApifyClient(self.api_token)
        self.scanned_posts: List[Dict[str, str]] = []

    @staticmethod
    def _get_dataset_id(run) -> str:
        if hasattr(run, "default_dataset_id"):
            return str(run.default_dataset_id)
        if isinstance(run, dict):
            return str(run.get("defaultDatasetId") or run.get("default_dataset_id") or "")
        return str(getattr(run, "defaultDatasetId", ""))

    @staticmethod
    def clean_username(identifier: str) -> str:
        clean = identifier.strip().rstrip("/")
        if "instagram.com/" in clean:
            clean = clean.split("instagram.com/")[-1].split("/")[0]
        return clean.lstrip("@").strip()

    def get_latest_posts(self, profile_identifier: str, count: int = 3) -> List[Dict[str, Any]]:
        """
        Kullanıcı profilinin son N adet gönderisini çeker.
        """
        username = self.clean_username(profile_identifier)
        profile_url = f"https://www.instagram.com/{username}/"
        print(f"[Instagram] @{username} profilinin son {count} gönderisi sorgulanıyor...")

        run_input = {
            "directUrls": [profile_url],
            "resultsType": "posts",
            "resultsLimit": count,
        }

        posts = []
        try:
            run = self.client.actor("apify/instagram-scraper").call(run_input=run_input)
            dataset_id = self._get_dataset_id(run)
            for item in self.client.dataset(dataset_id).iterate_items():
                shortcode = item.get("shortCode") or item.get("code") or ""
                post_url = item.get("url") or (f"https://www.instagram.com/p/{shortcode}/" if shortcode else "")
                caption = item.get("caption") or ""
                post_id = item.get("id") or shortcode

                posts.append({
                    "id": post_id,
                    "shortcode": shortcode,
                    "url": post_url,
                    "caption": caption,
                    "timestamp": item.get("timestamp", ""),
                })
        except Exception as e:
            print(f"[Instagram Hata] @{username} gönderileri çekilemedi: {e}")

        # İstenen adet kadar sınırla
        return posts[:count]

    def get_comments_for_profile(self, profile_identifier: str, post_count: int = 3, max_comments_per_post: int = 50) -> List[Dict[str, Any]]:
        """
        Hedef Instagram profilinin son N gönderisindeki yorumları toplar.
        Bateleur standart formatında döndürür.
        """
        username = self.clean_username(profile_identifier)
        posts = self.get_latest_posts(username, count=post_count)
        if not posts:
            print(f"[Instagram] @{username} için incelenecek gönderi bulunamadı.")
            return []

        for p in posts:
            cap = p.get("caption", "").strip()
            self.scanned_posts.append({
                "channel": f"@{username}",
                "title": (cap[:45] + "...") if cap else "Instagram Gönderisi",
                "url": p.get("url", ""),
                "published_at": p.get("timestamp", ""),
            })

        post_urls = [p["url"] for p in posts if p.get("url")]
        if not post_urls:
            print(f"[Instagram] @{username} gönderilerinin doğrudan URL'leri alınamadı.")
            return []

        print(f"[Instagram] @{username} için {len(post_urls)} gönderinin yorumları toplanıyor...")

        # URL üzerinden post detaylarına eşleştirme haritası
        post_map = {}
        for p in posts:
            clean_url = p["url"].rstrip("/")
            post_map[clean_url] = p
            if p.get("shortcode"):
                post_map[p["shortcode"]] = p

        run_input = {
            "directUrls": post_urls,
            "resultsLimit": max_comments_per_post,
        }

        all_comments = []
        try:
            run = self.client.actor("apify/instagram-comment-scraper").call(run_input=run_input)
            dataset_id = self._get_dataset_id(run)
            for item in self.client.dataset(dataset_id).iterate_items():
                raw_id = str(item.get("id", "")).strip()
                if not raw_id:
                    continue

                comment_id = f"ig_{raw_id}"

                author_name = (
                    item.get("ownerUsername") or 
                    (item.get("owner", {}).get("username") if isinstance(item.get("owner"), dict) else "") or
                    "instagram_user"
                )

                author_img = (
                    item.get("ownerProfilePicUrl") or
                    (item.get("owner", {}).get("profilePicUrl") if isinstance(item.get("owner"), dict) else "") or
                    ""
                )

                author_id = str(
                    item.get("ownerId") or 
                    (item.get("owner", {}).get("id") if isinstance(item.get("owner"), dict) else "") or
                    author_name
                )

                input_url = (item.get("inputUrl") or "").rstrip("/")
                post_data = post_map.get(input_url, {})
                caption = post_data.get("caption", "").strip()
                post_title = (caption[:80] + "...") if caption else "Instagram Gönderisi"
                video_url = post_data.get("url") or input_url

                all_comments.append({
                    "comment_id": comment_id,
                    "platform": "Instagram",
                    "channel_name": f"@{username}",
                    "video_id": post_data.get("shortcode") or "ig_post",
                    "video_title": post_title,
                    "video_url": video_url,
                    "comment_url": video_url,
                    "author_name": f"@{author_name.lstrip('@')}",
                    "author_channel_url": f"https://www.instagram.com/{author_name.lstrip('@')}/",
                    "author_channel_id": author_id,
                    "author_profile_image": author_img,
                    "text": item.get("text", "") or "",
                    "published_at": item.get("timestamp", ""),
                    "updated_at": item.get("timestamp", ""),
                    "like_count": item.get("likesCount", 0),
                })
        except Exception as e:
            print(f"[Instagram Yorum Çekme Hatası]: {e}")

        print(f"[Instagram] @{username} profilinden toplam {len(all_comments)} yorum toplandı.")
        return all_comments

