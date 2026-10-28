from typing import List, Dict, Any
from googleapiclient.discovery import build
from config import Config

KNOWN_CHANNEL_IDS = {
    "@uykusuztosba": "UCDiEYYSdms_e3C3bqusOltw",
    "uykusuztosba": "UCDiEYYSdms_e3C3bqusOltw",
    "@radiomocas": "UC1zagOy2h5yUmdJ4ZOQ8EPg",
    "radiomocas": "UC1zagOy2h5yUmdJ4ZOQ8EPg",
    "youtube.com/radiomocas": "UC1zagOy2h5yUmdJ4ZOQ8EPg",
}

class YouTubeClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.YOUTUBE_API_KEY
        if not self.api_key:
            raise ValueError("YouTube API anahtarı (YOUTUBE_API_KEY) tanımlanmamış!")
        self.youtube = build("youtube", "v3", developerKey=self.api_key)

    def resolve_channel_id(self, identifier: str) -> str:
        """
        Kanal handle veya ID'sini doğrular ve UC... ID'sini döndürür.
        """
        identifier = identifier.strip()
        if identifier.lower() in KNOWN_CHANNEL_IDS:
            return KNOWN_CHANNEL_IDS[identifier.lower()]

        if identifier.startswith("UC") and len(identifier) == 24:
            return identifier

        handle = identifier if identifier.startswith("@") else f"@{identifier}"
        try:
            request = self.youtube.channels().list(part="id", forHandle=handle)
            response = request.execute()
            items = response.get("items", [])
            if items:
                return items[0]["id"]
        except Exception as e:
            print(f"[Kanal Handle Çözümleme Hatası]: {e}")

        try:
            search_req = self.youtube.search().list(part="snippet", q=identifier, type="channel", maxResults=1)
            search_res = search_req.execute()
            items = search_res.get("items", [])
            if items:
                return items[0]["snippet"]["channelId"]
        except Exception as e:
            print(f"[Kanal Arama Hatası]: {e}")

        raise ValueError(f"'{identifier}' için geçerli bir YouTube Kanal ID bulunamadı.")

    def get_latest_videos(self, channel_id: str, count: int = 3) -> List[Dict[str, str]]:
        """
        Kanalın en son yüklenen N adet içeriğini getirir.
        """
        ch_resp = self.youtube.channels().list(part="contentDetails", id=channel_id).execute()
        items = ch_resp.get("items", [])
        if not items:
            return []

        uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        pl_resp = self.youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=count
        ).execute()

        videos = []
        for pl_item in pl_resp.get("items", []):
            snippet = pl_item["snippet"]
            video_id = snippet["resourceId"]["videoId"]
            title = snippet.get("title", "")
            videos.append({
                "video_id": video_id,
                "title": title,
                "published_at": snippet.get("publishedAt", "")
            })

        return videos

    def get_comments_for_video(self, video_id: str, video_title: str = "", channel_name: str = "", max_comments: int = 100) -> List[Dict[str, Any]]:
        """
        Hukuki delil niteliği taşıyacak tüm kullanıcı ve yorum üstverilerini eksiksiz çeker.
        """
        comments = []
        next_page_token = None

        while True:
            try:
                request = self.youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=min(max_comments - len(comments), 100),
                    textFormat="plainText",
                    pageToken=next_page_token,
                    order="time"
                )
                response = request.execute()
            except Exception as e:
                print(f"[Video Yorumları Çekilemedi - {video_id}]: {e}")
                break

            for item in response.get("items", []):
                top_level = item["snippet"]["topLevelComment"]["snippet"]
                comment_id = item["id"]

                # Yazar kalıcı kanal ID'si (Hukuki soruşturmalar için en kritik veri)
                author_channel_id_obj = top_level.get("authorChannelId", {})
                author_channel_id = author_channel_id_obj.get("value", "") if isinstance(author_channel_id_obj, dict) else ""

                comments.append({
                    "comment_id": comment_id,
                    "channel_name": channel_name,
                    "video_id": video_id,
                    "video_title": video_title,
                    "video_url": f"https://www.youtube.com/watch?v={video_id}",
                    "comment_url": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
                    "author_name": top_level.get("authorDisplayName", "Bilinmeyen Kullanıcı"),
                    "author_channel_url": top_level.get("authorChannelUrl", ""),
                    "author_channel_id": author_channel_id,
                    "author_profile_image": top_level.get("authorProfileImageUrl", ""),
                    "text": top_level.get("textOriginal") or top_level.get("textDisplay", ""),
                    "published_at": top_level.get("publishedAt", ""),
                    "updated_at": top_level.get("updatedAt", ""),
                    "like_count": top_level.get("likeCount", 0),
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token or len(comments) >= max_comments:
                break

        return comments

    def get_comments_for_channel(self, channel_identifier: str, video_count: int = 3) -> List[Dict[str, Any]]:
        """
        Kanalın son N içeriğindeki yorumları toplar.
        """
        channel_id = self.resolve_channel_id(channel_identifier)
        latest_videos = self.get_latest_videos(channel_id, count=video_count)
        
        all_comments = []
        for v in latest_videos:
            comments = self.get_comments_for_video(
                v["video_id"],
                video_title=v["title"],
                channel_name=channel_identifier,
                max_comments=Config.MAX_COMMENTS_PER_VIDEO
            )
            all_comments.extend(comments)

        return all_comments
