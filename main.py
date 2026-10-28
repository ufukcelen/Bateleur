import sys
from typing import Dict, Any

from config import Config
from database import get_storage
from youtube_client import YouTubeClient
from moderator import CommentModerator
from notifier import Notifier

def run_moderation_cycle() -> Dict[str, Any]:
    """
    Tek bir tarama döngüsünü çalıştırır:
    Her kanalı (@uykusuztosba, @radiomocas vb.) tek tek tarar,
    son 3 içeriğindeki yeni yorumları Gemini ile analiz eder.
    """
    print("=" * 60)
    print("🚀 Yorum Avcısı - Saatlik Moderasyon Döngüsü Başlatıldı")
    print(f"🎯 Hedef Kanallar: {', '.join(Config.YOUTUBE_CHANNELS)}")
    print(f"🎬 Kanal Başına Son İçerik: {Config.RECENT_VIDEOS_COUNT}")
    print("=" * 60)

    # 1. Servisleri başlat
    storage = get_storage()
    youtube = YouTubeClient()
    moderator = CommentModerator()
    notifier = Notifier()

    # 2. Daha önce işlenmiş ID'leri hafızadan çek
    processed_ids = storage.get_processed_ids()
    print(f"[Durum] Sistemde kayıtlı işlenmiş yorum sayısı: {len(processed_ids)}")

    # 3. Tüm kanallardan yorumları topla
    all_recent_comments = []
    for channel_id in Config.YOUTUBE_CHANNELS:
        try:
            ch_comments = youtube.get_comments_for_channel(channel_id, video_count=Config.RECENT_VIDEOS_COUNT)
            all_recent_comments.extend(ch_comments)
        except Exception as e:
            print(f"[HATA] {channel_id} yorumları çekilirken hata oluştu: {e}")

    print(f"\n[YouTube] Toplam {len(all_recent_comments)} adet yorum toplandı.")

    # 4. Sadece yeni olanları filtrele
    new_comments = [c for c in all_recent_comments if c["comment_id"] not in processed_ids]
    if not new_comments:
        print("✅ İncelenecek YENİ yorum bulunamadı. Tüm yorumlar daha önce taranmış.")
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

    # 7. İncelenen yorumları veritabanına kaydet
    new_ids = [c["comment_id"] for c in new_comments]
    storage.mark_as_processed(new_ids)
    print(f"💾 {len(new_ids)} adet yeni yorum işlendi olarak kaydedildi.")

    summary = {
        "status": "success",
        "processed_comments": len(new_comments),
        "offensive_count": offensive_count
    }
    print(f"🏁 Döngü tamamlandı. Toplam İncelenen: {len(new_comments)}, Hakaret Sayısı: {offensive_count}")
    return summary

def handle_cloud_function(request):
    """
    Google Cloud Functions HTTP tetikleyici fonksiyonu.
    GCP Cloud Scheduler saatte 1 kez bu adrese istek atar.
    """
    try:
        result = run_moderation_cycle()
        return (result, 200, {"Content-Type": "application/json"})
    except Exception as e:
        print(f"[HATA]: {e}")
        return ({"status": "error", "message": str(e)}, 500, {"Content-Type": "application/json"})

if __name__ == "__main__":
    try:
        run_moderation_cycle()
    except KeyboardInterrupt:
        print("\nİşlem kullanıcı tarafından durduruldu.")
    except Exception as exc:
        print(f"\n❌ Bir hata oluştu: {exc}")
        sys.exit(1)
