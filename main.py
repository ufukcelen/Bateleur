import sys
import requests
from typing import Dict, Any

from config import Config
from database import get_storage
from youtube_client import YouTubeClient
from moderator import CommentModerator
from notifier import Notifier

def run_moderation_cycle(is_manual: bool = False) -> Dict[str, Any]:
    """
    Tek bir tarama döngüsünü çalıştırır:
    - Son 3 içerikteki yeni yorumları tarar.
    - Sadece hakaret varsa delil oluşturup Telegram'a bildirir.
    - is_manual=True ise (/check komutu ile çağrıldıysa) temiz olsa dahi gruba özet bilgi döner.
    """
    print("=" * 60)
    print("🚀 Yorum Avcısı - Moderasyon Döngüsü Başlatıldı" + (" (MANUEL: /check)" if is_manual else ""))
    print(f"🎯 Hedef Kanallar: {', '.join(Config.YOUTUBE_CHANNELS)}")
    print(f"🎬 Kanal Başına Son İçerik: {Config.RECENT_VIDEOS_COUNT}")
    print("=" * 60)

    # 1. Servisleri başlat
    storage = get_storage()
    youtube = YouTubeClient()
    moderator = CommentModerator()
    notifier = Notifier()

    # 2. Kayıtlı işlenmiş ID'leri al
    processed_ids = storage.get_processed_ids()
    print(f"[Durum] Sistemde kayıtlı işlenmiş yorum sayısı: {len(processed_ids)}")

    # 3. Yorumları çek
    all_recent_comments = []
    for channel_id in Config.YOUTUBE_CHANNELS:
        try:
            ch_comments = youtube.get_comments_for_channel(channel_id, video_count=Config.RECENT_VIDEOS_COUNT)
            all_recent_comments.extend(ch_comments)
        except Exception as e:
            print(f"[HATA] {channel_id} yorumları çekilemedi: {e}")

    print(f"\n[YouTube] Toplam {len(all_recent_comments)} adet yorum toplandı.")

    # 4. Sadece yeni olanları filtrele
    new_comments = [c for c in all_recent_comments if c["comment_id"] not in processed_ids]
    if not new_comments:
        print("✅ İncelenecek YENİ yorum bulunamadı.")
        if is_manual and Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID:
            msg = (
                "✅ <b>Manuel Tarama Tamamlandı (/check)</b>\n\n"
                f"📺 <i>{', '.join(Config.YOUTUBE_CHANNELS)}</i> kanallarının son içerikleri incelendi.\n"
                "✨ <b>Tüm yorumlar temiz.</b> Yeni bir hakaret veya tehdit bulunamadı."
            )
            requests.post(
                f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": Config.TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
            )
        return {"status": "success", "new_comments_count": 0, "offensive_count": 0}

    print(f"🔍 İncelenecek YENİ yorum sayısı: {len(new_comments)}")

    # 5. Gemini ile analiz et
    analyzed_comments = moderator.analyze_comments(new_comments)

    # 6. Hakaret içerenleri bildir
    offensive_count = 0
    for comment in analyzed_comments:
        if comment.get("is_offensive", False):
            offensive_count += 1
            notifier.send_alert(comment)

    # 7. İncelenen yorumları kaydet
    new_ids = [c["comment_id"] for c in new_comments]
    storage.mark_as_processed(new_ids)
    print(f"💾 {len(new_ids)} adet yeni yorum işlendi olarak kaydedildi.")

    if is_manual and offensive_count == 0 and Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID:
        msg = (
            "✅ <b>Manuel Tarama Tamamlandı (/check)</b>\n\n"
            f"🔍 <b>{len(new_comments)}</b> yeni yorum incelendi.\n"
            "✨ <b>Tüm yorumlar temiz.</b> Yeni bir hakaret tespit edilmedi."
        )
        requests.post(
            f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": Config.TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
        )

    summary = {
        "status": "success",
        "processed_comments": len(new_comments),
        "offensive_count": offensive_count
    }
    print(f"🏁 Döngü tamamlandı. Yeni İncelenen: {len(new_comments)}, Hakaret: {offensive_count}")
    return summary

def handle_cloud_function(request):
    """
    Google Cloud Functions HTTP Giriş Noktası.
    Hem Cloud Scheduler periyodik çağrılarını hem de Telegram'dan gelen /check Webhook isteklerini karşılar.
    """
    try:
        is_manual = False
        request_json = request.get_json(silent=True) or {}
        
        # Telegram Webhook isteği mi kontrol et
        if "message" in request_json:
            msg_text = request_json["message"].get("text", "").strip()
            if msg_text.startswith("/check"):
                is_manual = True

        result = run_moderation_cycle(is_manual=is_manual)
        return (result, 200, {"Content-Type": "application/json"})
    except Exception as e:
        print(f"[HATA]: {e}")
        return ({"status": "error", "message": str(e)}, 500, {"Content-Type": "application/json"})

if __name__ == "__main__":
    is_check = "--check" in sys.argv
    try:
        run_moderation_cycle(is_manual=is_check)
    except KeyboardInterrupt:
        print("\nİşlem durduruldu.")
    except Exception as exc:
        print(f"\n❌ Bir hata oluştu: {exc}")
        sys.exit(1)
