import os
import threading
from typing import Any
import requests
from flask import Flask, request, jsonify
from config import Config
from main import run_moderation_cycle

app = Flask(__name__)

@app.route("/", methods=["GET"])
@app.route("/healthz", methods=["GET"])
def health_check():
    """Canlılık ve sağlık kontrolü (Render Health Check)."""
    return jsonify({
        "status": "online",
        "healthy": True,
        "app": "Bateleur",
        "env_check": {
            "telegram_token_set": bool(Config.TELEGRAM_BOT_TOKEN),
            "telegram_chat_set": bool(Config.TELEGRAM_CHAT_ID),
            "gemini_key_set": bool(Config.GEMINI_API_KEY),
            "youtube_key_set": bool(Config.YOUTUBE_API_KEY),
            "apify_token_set": bool(Config.APIFY_API_TOKEN),
            "tiktok_profiles_count": len(Config.TIKTOK_PROFILES),
            "use_local_db": Config.USE_LOCAL_DB
        },
        "description": "YouTube, Instagram & TikTok Moderasyon ve Siber Delil Takip Sistemi",
        "version": "v0.0.6"
    }), 200

@app.route("/cron", methods=["GET", "POST"])
def cron_endpoint():
    """
    Periyodik tarama uç noktası (cron-job.org veya harici servisler için).
    Arka planda çalıştırıp hemen 200 döner.
    """
    print("[Render] /cron çağrıldı, tarama arka planda başlatılıyor...")
    threading.Thread(target=run_moderation_cycle, kwargs={"is_manual": False}).start()
    return jsonify({"status": "accepted", "message": "Periyodik tarama başlatıldı."}), 200

IS_SCANNING = False
SCAN_LOCK = threading.Lock()

def _safe_run_scan(is_manual: bool, chat_id: Any = None):
    global IS_SCANNING
    with SCAN_LOCK:
        if IS_SCANNING:
            if is_manual and chat_id and Config.TELEGRAM_BOT_TOKEN:
                busy_msg = "⚠️ <b>Tarama Devam Ediyor...</b>\nHalihazırda yürütülen bir tarama işlemi var. Lütfen tamamlanmasını bekleyin."
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage",
                        json={"chat_id": chat_id, "text": busy_msg, "parse_mode": "HTML"},
                        timeout=5
                    )
                except Exception:
                    pass
            return
        IS_SCANNING = True

    try:
        if is_manual and chat_id and Config.TELEGRAM_BOT_TOKEN:
            ack_text = "⏳ <b>Tarama Başlatıldı...</b>\nYouTube, Instagram ve TikTok hesapları taranıyor, lütfen bekleyin (yaklaşık 30-40 sn)..."
            try:
                requests.post(
                    f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": ack_text, "parse_mode": "HTML"},
                    timeout=5
                )
            except Exception as e:
                print(f"[Webhook Ack Hatası]: {e}")

        run_moderation_cycle(is_manual=is_manual)
    except Exception as e:
        print(f"[Tarama Hatası]: {e}")
    finally:
        with SCAN_LOCK:
            IS_SCANNING = False

@app.route("/check", methods=["GET", "POST"])
def manual_check_endpoint():
    """Doğrudan manuel tarama uç noktası."""
    print("[Render] /check çağrıldı, manuel tarama arka planda başlatılıyor...")
    threading.Thread(target=_safe_run_scan, args=(True, Config.TELEGRAM_CHAT_ID)).start()
    return jsonify({"status": "accepted", "message": "Manuel tarama başlatıldı."}), 200

@app.route("/webhook", methods=["GET", "POST"])
def telegram_webhook():
    """
    Telegram Webhook Giriş Noktası.
    Telegram grubundan bota gelen mesajları (/check) karşılar.
    Telegram'ın 502/zaman aşımına uğramaması için hemen 200 döner,
    taramayı arka planda yürütür.
    """
    if request.method == "GET":
        return jsonify({"status": "ok", "message": "Telegram Webhook aktif ve hazır."}), 200
    try:
        data = request.get_json(silent=True) or {}
        is_manual = False
        chat_id = Config.TELEGRAM_CHAT_ID

        # Mesaj nesnesini kontrol et (doğrudan mesaj veya gruptan mesaj)
        msg = data.get("message") or data.get("edited_message") or {}
        if msg:
            msg_text = (msg.get("text") or "").strip().lower()
            if "chat" in msg and "id" in msg["chat"]:
                chat_id = msg["chat"]["id"]

            # /check, /check@bot, /tara, check, tara komutlarını yakala
            if msg_text.startswith(("/check", "/tara", "check", "tara")):
                is_manual = True

        if is_manual:
            threading.Thread(target=_safe_run_scan, args=(True, chat_id)).start()

        # Telegram'a milisaniyeler içinde 200 OK dön (asla 502 vermez)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"[Render Webhook Hatası]: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
