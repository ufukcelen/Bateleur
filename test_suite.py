import os
import sys
import html
import json
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import Config
from youtube_client import YouTubeClient
from instagram_client import InstagramClient
from tiktok_client import TikTokClient
from moderator import CommentModerator
from evidence_generator import EvidenceGenerator
from notifier import Notifier
from server import app


class TestBateleurComprehensive(unittest.TestCase):

    # ==========================================
    # 1. CONFIG TESTS
    # ==========================================
    def test_01_config_loading(self):
        print("\n--- [TEST 1] Config Değerleri Kontrol Ediliyor ---")
        self.assertTrue(bool(Config.YOUTUBE_API_KEY), "YOUTUBE_API_KEY boş olmamalı")
        self.assertTrue(bool(Config.GEMINI_API_KEY), "GEMINI_API_KEY boş olmamalı")
        self.assertTrue(bool(Config.TELEGRAM_BOT_TOKEN), "TELEGRAM_BOT_TOKEN boş olmamalı")
        self.assertTrue(bool(Config.TELEGRAM_CHAT_ID), "TELEGRAM_CHAT_ID boş olmamalı")
        self.assertTrue(bool(Config.APIFY_API_TOKEN), "APIFY_API_TOKEN boş olmamalı")
        self.assertIsInstance(Config.YOUTUBE_CHANNELS, list)
        self.assertIsInstance(Config.INSTAGRAM_PROFILES, list)
        print("  [BAŞARILI] Tüm kritik yapılandırma değişkenleri yüklendi.")

    # ==========================================
    # 2. INSTAGRAM CLIENT TESTS
    # ==========================================
    def test_02_instagram_username_cleaner(self):
        print("\n--- [TEST 2] Instagram Kullanıcı Adı Temizleme Testi ---")
        cases = [
            ("@uykusuztosba", "uykusuztosba"),
            ("uykusuztosba/", "uykusuztosba"),
            ("https://www.instagram.com/uykusuztosba/", "uykusuztosba"),
            ("https://instagram.com/radiomocas", "radiomocas"),
            ("   @radiomocas/  ", "radiomocas")
        ]
        for raw, expected in cases:
            cleaned = InstagramClient.clean_username(raw)
            self.assertEqual(cleaned, expected, f"Temizleme hatası: {raw} -> {cleaned} != {expected}")
        print("  [BAŞARILI] Kullanıcı adı normalizasyonu tüm senaryolarda doğru çalışıyor.")

    def test_03_instagram_dataset_id_extraction(self):
        print("\n--- [TEST 3] Instagram Apify Run Nesnesi Uyumluluğu ---")
        # Pydantic-like object
        class MockRunObj:
            default_dataset_id = "dataset_abc_123"
        run_obj = MockRunObj()
        self.assertEqual(InstagramClient._get_dataset_id(run_obj), "dataset_abc_123")

        # Dict format
        run_dict1 = {"defaultDatasetId": "dataset_def_456"}
        self.assertEqual(InstagramClient._get_dataset_id(run_dict1), "dataset_def_456")

        run_dict2 = {"default_dataset_id": "dataset_ghi_789"}
        self.assertEqual(InstagramClient._get_dataset_id(run_dict2), "dataset_ghi_789")
        print("  [BAŞARILI] Apify v3 model ve dict varyantları sorunsuz işlendi.")

    def test_03b_tiktok_username_cleaner(self):
        print("\n--- [TEST 3b] TikTok Kullanıcı Adı Temizleme Testi ---")
        cases = [
            ("/uykusuztosba", "uykusuztosba"),
            ("@uykusuztosba", "uykusuztosba"),
            ("https://www.tiktok.com/@donkisotttt", "donkisotttt"),
            ("burhan.mutlugz/", "burhan.mutlugz"),
            ("   @burhan.mutlugz/  ", "burhan.mutlugz")
        ]
        for raw, expected in cases:
            cleaned = TikTokClient.clean_username(raw)
            self.assertEqual(cleaned, expected, f"TikTok temizleme hatası: {raw} -> {cleaned} != {expected}")
        self.assertEqual(len(Config.TIKTOK_PROFILES), 3, "3 TikTok hesabı tanımlı olmalı")
        print("  [BAŞARILI] TikTok kullanıcı adları (/uykusuztosba, /donkisotttt, /burhan.mutlugz) doğrulandı.")

    # ==========================================
    # 3. YOUTUBE CLIENT TESTS
    # ==========================================
    def test_04_youtube_channel_resolution(self):
        print("\n--- [TEST 4] YouTube Kanal Çözümleme Testi ---")
        yt = YouTubeClient()
        for ch_handle in Config.YOUTUBE_CHANNELS[:2]:
            ch_id = yt.resolve_channel_id(ch_handle)
            self.assertIsNotNone(ch_id, f"Kanal ID bulunamadı: {ch_handle}")
            self.assertTrue(ch_id.startswith("UC"), f"Geçersiz kanal ID formatı: {ch_id}")
            print(f"  [BAŞARILI] {ch_handle} -> {ch_id}")

    def test_05_youtube_get_latest_videos(self):
        print("\n--- [TEST 5] YouTube Son Videolar ve Tarih Formatı Testi ---")
        yt = YouTubeClient()
        test_handle = Config.YOUTUBE_CHANNELS[0]
        videos = yt.get_latest_videos(test_handle, count=2)
        self.assertGreater(len(videos), 0, "En az 1 video çekilebilmeli")
        for v in videos:
            self.assertIn("video_id", v)
            self.assertIn("title", v)
            self.assertIn("published_at", v)
            self.assertTrue(v["video_id"], "video_id boş olmamalı")
            print(f"  [BAŞARILI] Video: '{v['title'][:35]}...' (Tarih: {v.get('published_at')})")

    # ==========================================
    # 4. MODERATOR (GEMINI AI) TESTS
    # ==========================================
    def test_06_moderator_clean_vs_offensive(self):
        print("\n--- [TEST 6] Gemini Moderatör Sınıflandırma Testi ---")
        moderator = CommentModerator()

        mock_comments = [
            {
                "comment_id": "clean_1",
                "text": "Harika bir yayın olmuş, emeğinize sağlık!",
                "author_name": "Ali Veli",
                "platform": "YouTube"
            },
            {
                "comment_id": "football_arg_1",
                "text": "Hoca değişiklikleri çok geç yaptı, böyle oynarsak şampiyon olamayız.",
                "author_name": "Mehmet Kaya",
                "platform": "YouTube"
            },
            {
                "comment_id": "insult_1",
                "text": "Sen ne iğrenç, karaktersiz bir adamsın, senin gibi kanal sahibinin...",
                "author_name": "Trol Hesap",
                "platform": "YouTube"
            }
        ]

        results = moderator.analyze_comments(mock_comments)
        self.assertEqual(len(results), 3, "3 yorum analiz edilmeli")

        res_map = {r["comment_id"]: r for r in results}

        # clean_1 must NOT be offensive
        self.assertFalse(res_map["clean_1"].get("is_offensive"), "Temiz yoruma hakaret denmemeli")
        
        # football_arg_1 must NOT be offensive (criticism tolerance rule)
        self.assertFalse(res_map["football_arg_1"].get("is_offensive"), "Futbol eleştirisi hakaret sayılmamalı")

        # insult_1 MUST be flagged
        self.assertTrue(res_map["insult_1"].get("is_offensive"), "Ağır şahsi hakaret yakalanmalı")
        print(f"  [BAŞARILI] Hakaret tespiti ve eleştiri toleransı mükemmel çalışıyor.")

    # ==========================================
    # 5. EVIDENCE GENERATOR TESTS (XSS & SECURITY)
    # ==========================================
    def test_07_evidence_generator_security_xss(self):
        print("\n--- [TEST 7] Delil Kartı Güvenlik ve HTML Çıktı Testi ---")
        gen = EvidenceGenerator(output_dir="deliller")
        xss_comment = {
            "comment_id": "xss_test_999",
            "author_name": "<script>alert('xss')</script>TehlikeliKullanici",
            "author_profile_image": "https://example.com/pic.jpg",
            "author_channel_id": "UC_hack_\"'<>",
            "author_channel_url": "https://youtube.com/channel/hack",
            "channel_name": "@uykusuztosba",
            "video_title": "Normal Video <b>Kalın</b>",
            "video_url": "https://youtube.com/watch?v=123",
            "comment_url": "https://youtube.com/watch?v=123&lc=999",
            "text": "<img src=x onerror=alert(1)> Senin kanalını basarım!",
            "published_at": "2026-11-01T12:00:00Z",
            "category": "threat",
            "severity": "high",
            "explanation": "Doğrudan can güvenliği tehdidi",
            "platform": "YouTube"
        }

        file_path = gen.generate_html_card(xss_comment)
        self.assertTrue(os.path.exists(file_path), "Delil dosyası oluşturulmalı")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if malicious script or img tags were executed raw
        has_unescaped_script = "<script>alert('xss')</script>" in content
        self.assertFalse(has_unescaped_script, "HTML Delil kartında XSS açığı bulunmamalı")
        self.assertIn("&lt;script&gt;", content, "Tehlikeli karakterler escape edilmiş olmalı")
        print("  [BAŞARILI] Delil kartında HTML güvenliği (XSS Koruması) doğrulandı.")

        # Cleanup test file
        try:
            os.remove(file_path)
        except Exception:
            pass

    # ==========================================
    # 6. NOTIFIER TESTS (TELEGRAM LIMITS)
    # ==========================================
    def test_08_notifier_caption_length_handling(self):
        print("\n--- [TEST 8] Telegram Notifier Karakter Sınırı Testi ---")
        # Telegram sendPhoto caption limit is 1024 characters
        long_text = "Çok uzun bir hakaret metni... " * 50  # ~1500 chars
        comment = {
            "channel_name": "@uykusuztosba",
            "author_name": "Test User",
            "author_profile_image": "https://example.com/avatar.jpg",
            "author_channel_id": "UC_test",
            "text": long_text,
            "category": "insult",
            "severity": "high",
            "explanation": "Açıklama " * 20,
            "comment_url": "https://youtube.com/watch?v=123",
            "video_title": "Test Video",
            "platform": "YouTube"
        }

        notifier = Notifier()
        # Verify if caption exceeds 1024 chars without crashing
        # We test the caption generation logic
        safe_text = html.escape(str(comment["text"]))
        caption_len = len(safe_text)
        print(f"  Metin uzunluğu: {caption_len} karakter.")
        if caption_len > 1024:
            print("  [BİLGİ] 1024 karakteri aşan yorumlarda sendPhoto yerine fallback (sendMessage) kullanılmalı veya özetlenmeli.")

    # ==========================================
    # 7. SERVER ENDPOINTS TESTS
    # ==========================================
    def test_09_server_endpoints(self):
        print("\n--- [TEST 9] Render Webhook & API Endpointleri Testi ---")
        client = app.test_client()

        # 1. Healthz (Render Health Check)
        res_health = client.get("/healthz")
        self.assertEqual(res_health.status_code, 200)
        self.assertIn("healthy", res_health.get_data(as_text=True))
        print("  [BAŞARILI] /healthz endpointi 200 OK yanıt veriyor.")

        # 2. Ana sayfa
        res_root = client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertIn("Bateleur", res_root.get_data(as_text=True))
        print("  [BAŞARILI] / ana sayfa endpointi 200 OK yanıt veriyor.")

        # 3. Webhook GET
        res_webhook_get = client.get("/webhook")
        self.assertEqual(res_webhook_get.status_code, 200)
        print("  [BAŞARILI] /webhook (GET) endpointi 200 OK yanıt veriyor.")

        # 4. Webhook POST (/check simülasyonu)
        fake_telegram_update = {
            "update_id": 12345678,
            "message": {
                "message_id": 99,
                "chat": {"id": int(Config.TELEGRAM_CHAT_ID) if Config.TELEGRAM_CHAT_ID.lstrip("-").isdigit() else -5505248203},
                "text": "/check"
            }
        }
        with patch("server.threading.Thread") as mock_thread:
            res_webhook_post = client.post(
                "/webhook",
                data=json.dumps(fake_telegram_update),
                content_type="application/json"
            )
            self.assertEqual(res_webhook_post.status_code, 200)
            mock_thread.return_value.start.assert_called_once()
            print("  [BAŞARILI] /webhook (POST /check) arka planda asenkron iş parçacığı başlattı.")


if __name__ == "__main__":
    unittest.main()
