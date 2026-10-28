import os
import requests
from typing import Dict, Any
from config import Config
from evidence_generator import EvidenceGenerator

class Notifier:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or Config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or Config.TELEGRAM_CHAT_ID
        self.evidence_gen = EvidenceGenerator()

    def send_alert(self, offensive_comment: Dict[str, Any]) -> bool:
        """
        Tespit edilen hakaret için delil kartı üretir ve Telegram'a fotoğraflı bildirim atar.
        """
        # 1. Yazdırılabilir HTML Delil Tutanak Kartını oluştur
        html_file = self.evidence_gen.generate_html_card(offensive_comment)
        
        channel = offensive_comment.get("channel_name", "")
        author = offensive_comment.get("author_name", "Bilinmeyen")
        author_img = offensive_comment.get("author_profile_image", "")
        author_channel_id = offensive_comment.get("author_channel_id", "Yok")
        text = offensive_comment.get("text", "")
        category = offensive_comment.get("category", "Bilinmiyor").upper()
        severity = offensive_comment.get("severity", "medium").upper()
        explanation = offensive_comment.get("explanation", "")
        comment_url = offensive_comment.get("comment_url", "")
        video_title = offensive_comment.get("video_title", "")

        console_msg = (
            f"\n🚨 [HUKUKİ DELİL TESPİT EDİLDİ - {severity} Seviye]\n"
            f"📁 Delil Kartı: {html_file}\n"
            f"📺 Kanal: {channel}\n"
            f"🎬 Video: {video_title}\n"
            f"👤 Şüpheli: {author} (Kanal ID: {author_channel_id})\n"
            f"💬 Yorum: \"{text}\"\n"
            f"🏷️ Kategori: {category}\n"
            f"📝 Gerekçe: {explanation}\n"
            f"🔗 Kalıcı Link: {comment_url}\n"
        )
        print(console_msg)

        if not self.bot_token or not self.chat_id:
            print("[Notifier] Telegram ayarlanmadığı için bildirim konsola ve delil kartına yazıldı.")
            return True

        # Telegram Mesajı
        caption = (
            f"🚨 *HUKUKİ DELİL TESPİTİ* ({severity})\n\n"
            f"📺 *Kanal:* `{channel}`\n"
            f"🎬 *Video:* {video_title[:45]}...\n"
            f"👤 *Şahıs:* `{author}`\n"
            f"🆔 *Kalıcı Kanal ID:* `{author_channel_id}`\n\n"
            f"💬 *Yorum:*\n\"{text}\"\n\n"
            f"⚖️ *Hukuki Gerekçe:* _{explanation}_\n\n"
            f"👉 [Yorumu YouTube'da Gör / Doğrula]({comment_url})\n"
            f"📁 _Delil tutanağı otomatik oluşturuldu: {os.path.basename(html_file)}_"
        )

        # Şahsın profil fotoğrafı varsa fotoğraflı bildirim gönder
        if author_img:
            photo_url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            payload = {
                "chat_id": self.chat_id,
                "photo": author_img,
                "caption": caption,
                "parse_mode": "Markdown"
            }
            try:
                res = requests.post(photo_url, json=payload, timeout=10)
                if res.status_code == 200:
                    print(f"[Notifier] Fotoğraflı Telegram delil bildirimi iletildi ({author}).")
                    return True
            except Exception as e:
                print(f"[Notifier] Fotoğraf gönderilemedi, metin deneniyor: {e}")

        # Fotoğraf yoksa veya hata verdiyse normal metin gönder
        msg_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": caption,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        try:
            res = requests.post(msg_url, json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            print(f"[Notifier Hatası]: {e}")
            return False
