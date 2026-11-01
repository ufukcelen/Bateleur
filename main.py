import sys
import html
import requests
from typing import Dict, Any

from config import Config
from database import get_storage
from youtube_client import YouTubeClient
from instagram_client import InstagramClient
from moderator import CommentModerator
from notifier import Notifier

def run_moderation_cycle(is_manual: bool = False) -> Dict[str, Any]:
    """
    Tek bir tarama döngüsünü çalıştırır:
    - YouTube ve Instagram'daki son içeriklerin yeni yorumlarını tarar.
    - Sadece hakaret varsa delil oluşturup Telegram'a bildirir.
    - is_manual=True ise (/check komutu ile çağrıldıysa) temiz olsa dahi gruba özet bilgi döner.
    """
    print("=" * 60)
    print("🦅 Bateleur - Sosyal Medya Moderasyon & Delil Takip Döngüsü" + (" (MANUEL: /check)" if is_manual else ""))
    if Config.YOUTUBE_CHANNELS:
        print(f"📺 Hedef YouTube Kanalları: {', '.join(Config.YOUTUBE_CHANNELS)} (Son {Config.RECENT_VIDEOS_COUNT} içerik)")
    if Config.INSTAGRAM_PROFILES:
        print(f"📸 Hedef Instagram Profilleri: {', '.join(Config.INSTAGRAM_PROFILES)} (Son {Config.RECENT_INSTAGRAM_POSTS_COUNT} içerik)")
    print("=" * 60)

    # 1. Servisleri başlat
    storage = get_storage()
    moderator = CommentModerator()
    notifier = Notifier()

    # 2. Kayıtlı işlenmiş ID'leri al
    processed_ids = storage.get_processed_ids()
    print(f"[Durum] Sistemde kayıtlı işlenmiş yorum sayısı: {len(processed_ids)}")

    # 3. Yorumları çek
    all_recent_comments = []
    scanned_yt = []
    scanned_ig = []

    # 3a. YouTube yorumları
    if Config.YOUTUBE_API_KEY and Config.YOUTUBE_CHANNELS:
        try:
            youtube = YouTubeClient()
            yt_count = 0
            for channel_id in Config.YOUTUBE_CHANNELS:
                try:
                    ch_comments = youtube.get_comments_for_channel(channel_id, video_count=Config.RECENT_VIDEOS_COUNT)
                    all_recent_comments.extend(ch_comments)
                    yt_count += len(ch_comments)
                except Exception as e:
                    print(f"[HATA] YouTube ({channel_id}) yorumları çekilemedi: {e}")
            scanned_yt = getattr(youtube, "scanned_videos", [])
            print(f"[YouTube] Toplam {yt_count} adet yorum toplandı.")
        except Exception as e:
            print(f"[YouTube Başlatma Hatası]: {e}")
    else:
        print("[YouTube] YOUTUBE_API_KEY veya kanal listesi tanımlı değil, atlanıyor.")

    # 3b. Instagram yorumları (Meta API ve login gerektirmez - Apify Scraper)
    if Config.APIFY_API_TOKEN and Config.INSTAGRAM_PROFILES:
        try:
            instagram = InstagramClient()
            ig_count = 0
            for profile in Config.INSTAGRAM_PROFILES:
                try:
                    ig_comments = instagram.get_comments_for_profile(
                        profile,
                        post_count=Config.RECENT_INSTAGRAM_POSTS_COUNT,
                        max_comments_per_post=Config.MAX_COMMENTS_PER_INSTAGRAM_POST
                    )
                    all_recent_comments.extend(ig_comments)
                    ig_count += len(ig_comments)
                except Exception as e:
                    print(f"[HATA] Instagram (@{profile}) yorumları çekilemedi: {e}")
            scanned_ig = getattr(instagram, "scanned_posts", [])
            print(f"[Instagram] Toplam {ig_count} adet yorum toplandı.")
        except Exception as e:
            print(f"[Instagram Başlatma Hatası]: {e}")
    else:
        if not Config.APIFY_API_TOKEN and Config.INSTAGRAM_PROFILES:
            print("[Instagram] UYARI: INSTAGRAM_PROFILES tanımlı ancak APIFY_API_TOKEN girilmemiş. Instagram atlandı.")

    print(f"\n[Havuz] Toplam {len(all_recent_comments)} adet yorum toplandı.")

    # Hedef özet metni (Manuel tarama Telegram raporu için)
    sources_summary = []
    if Config.YOUTUBE_CHANNELS and Config.YOUTUBE_API_KEY:
        sources_summary.append(f"📺 <b>YouTube:</b> <i>{', '.join(Config.YOUTUBE_CHANNELS)}</i>")
    if Config.INSTAGRAM_PROFILES and Config.APIFY_API_TOKEN:
        sources_summary.append(f"📸 <b>Instagram:</b> <i>{', '.join(Config.INSTAGRAM_PROFILES)}</i>")
    sources_text = "\n".join(sources_summary) if sources_summary else "<i>Sosyal medya hesapları</i>"

    # 4. Sadece yeni olanları filtrele
    new_comments = [c for c in all_recent_comments if c["comment_id"] not in processed_ids]
    
    # Sayım özetleri
    yt_comments_count = len([c for c in all_recent_comments if c.get("platform") == "YouTube"])
    ig_comments_count = len([c for c in all_recent_comments if c.get("platform") == "Instagram"])

    # Tarih formatlayıcı (Örn: 2026-10-31T... -> 31 Eki)
    def _format_date(iso_str: str) -> str:
        if not iso_str:
            return ""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            months = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
            return f"{dt.day} {months[dt.month]}"
        except Exception:
            return ""

    # Aynı URL'lerin mükerrer listelenmesini önle
    seen_urls = set()
    unique_yt = []
    for v in scanned_yt:
        u = v.get("url", "")
        if u and u not in seen_urls:
            seen_urls.add(u)
            unique_yt.append(v)

    unique_ig = []
    for p in scanned_ig:
        u = p.get("url", "")
        if u and u not in seen_urls:
            seen_urls.add(u)
            unique_ig.append(p)

    # Kontrol edilen içeriklerin tıklanabilir link listesi
    links_lines = []
    if unique_yt:
        links_lines.append("📺 <b>YouTube Videoları:</b>")
        for v in unique_yt:
            v_title = html.escape(v.get("title", "Video")[:45])
            d_str = _format_date(v.get("published_at", ""))
            date_badge = f" [<code>{d_str}</code>]" if d_str else ""
            links_lines.append(f"• <a href=\"{v['url']}\">{v_title}</a>{date_badge} ({html.escape(v.get('channel', ''))})")

    if unique_ig:
        if links_lines:
            links_lines.append("")
        links_lines.append("📸 <b>Instagram Gönderileri:</b>")
        for p in unique_ig:
            p_title = html.escape(p.get("title", "Gönderi")[:45])
            d_str = _format_date(p.get("published_at", ""))
            date_badge = f" [<code>{d_str}</code>]" if d_str else ""
            links_lines.append(f"• <a href=\"{p['url']}\">{p_title}</a>{date_badge} ({html.escape(p.get('channel', ''))})")

    links_block = "\n".join(links_lines)
    links_section = f"\n\n🔗 <b>Kontrol Edilen İçerik Linkleri:</b>\n{links_block}" if links_block else ""

    if not new_comments:
        print("✅ İncelenecek YENİ yorum bulunamadı.")
        if is_manual and Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID:
            msg = (
                "✅ <b>Bateleur Taraması Tamamlandı (Manuel)</b>\n\n"
                f"{sources_text}\n\n"
                f"📊 <b>İncelenen Yorum Sayıları:</b>\n"
                f"• YouTube: {yt_comments_count} yorum kontrol edildi\n"
                f"• Instagram: {ig_comments_count} yorum kontrol edildi"
                f"{links_section}\n\n"
                "✨ <b>Tüm yorumlar temiz.</b> Yeni bir hakaret veya tehdit tespit edilmedi."
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
            "✅ <b>Bateleur Taraması Tamamlandı (Manuel)</b>\n\n"
            f"{sources_text}\n\n"
            f"🔍 <b>{len(new_comments)}</b> yeni yorum Gemini AI ile analiz edildi.\n"
            f"• YouTube: {yt_comments_count} yorum\n"
            f"• Instagram: {ig_comments_count} yorum"
            f"{links_section}\n\n"
            "✨ <b>Tüm yorumlar temiz!</b> Yeni bir hakaret veya tehdit tespit edilmedi."
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
    import os
    is_check = "--check" in sys.argv or os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
    try:
        run_moderation_cycle(is_manual=is_check)
    except KeyboardInterrupt:
        print("\nİşlem durduruldu.")
    except Exception as exc:
        print(f"\n❌ Bir hata oluştu: {exc}")
        sys.exit(1)
