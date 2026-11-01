import os
from typing import List
from dotenv import load_dotenv

# .env dosyası varsa yükle
load_dotenv()

class Config:
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    
    # Çoklu kanal desteği: Virgülle ayrılmış kanal kullanıcı adları veya ID'leri
    _raw_channels = os.getenv("YOUTUBE_CHANNELS", "") or os.getenv("YOUTUBE_CHANNEL_ID", "@uykusuztosba,@radiomocas")
    YOUTUBE_CHANNELS: List[str] = [ch.strip() for ch in _raw_channels.split(",") if ch.strip()]

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Telegram Bildirim Ayarları
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # GCP / Firestore Ayarları
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    FIRESTORE_COLLECTION: str = os.getenv("FIRESTORE_COLLECTION", "processed_comments")
    
    # Yerel geliştirme bayrağı
    USE_LOCAL_DB: bool = os.getenv("USE_LOCAL_DB", "false").lower() in ("true", "1", "yes")

    # Taranacak son video/içerik adedi (kanal başına)
    RECENT_VIDEOS_COUNT: int = int(os.getenv("RECENT_VIDEOS_COUNT", "3"))

    # Her video için maksimum yorum sınırı
    MAX_COMMENTS_PER_VIDEO: int = int(os.getenv("MAX_COMMENTS_PER_VIDEO", "100"))

    # Instagram & Apify Ayarları
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    _raw_ig_profiles = os.getenv("INSTAGRAM_PROFILES", "") or "uykusuztosba,radiomocas"
    INSTAGRAM_PROFILES: List[str] = [p.strip().lstrip("@") for p in _raw_ig_profiles.split(",") if p.strip()]
    RECENT_INSTAGRAM_POSTS_COUNT: int = int(os.getenv("RECENT_INSTAGRAM_POSTS_COUNT", "3"))
    MAX_COMMENTS_PER_INSTAGRAM_POST: int = int(os.getenv("MAX_COMMENTS_PER_INSTAGRAM_POST", "50"))
