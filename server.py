import os
import threading
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
        "description": "YouTube & Instagram Moderasyon ve Siber Delil Takip Sistemi",
        "version": "v0.0.3"
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

@app.route("/check", methods=["GET", "POST"])
def manual_check_endpoint():
    """Doğrudan manuel tarama uç noktası."""
    print("[Render] /check çağrıldı, manuel tarama arka planda başlatılıyor...")
    threading.Thread(target=run_moderation_cycle, kwargs={"is_manual": True}).start()
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

        if "message" in data:
            msg = data["message"]
            msg_text = (msg.get("text") or "").strip()
            # Gruptan veya özelden geldiyse o chat'e yanıt ver
            if "chat" in msg and "id" in msg["chat"]:
                chat_id = msg["chat"]["id"]

            if msg_text.startswith("/check") or msg_text.startswith("/tara"):
                is_manual = True

        if is_manual:
            # Gruba anında "Tarama Başlatıldı" ön bilgisi gönder
            ack_text = "⏳ <b>Tarama Başlatıldı...</b>\nYouTube ve Instagram hesapları taranıyor, lütfen bekleyin."
            try:
                requests.post(
                    f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": ack_text, "parse_mode": "HTML"},
                    timeout=5
                )
            except Exception as e:
                print(f"[Webhook Ack Hatası]: {e}")

            # Taramayı arka planda başlat
            threading.Thread(target=run_moderation_cycle, kwargs={"is_manual": True}).start()
        else:
            # Diğer Telegram mesajları veya güncellemeleri için sessizce arka planda çalıştır
            if "message" in data:
                threading.Thread(target=run_moderation_cycle, kwargs={"is_manual": False}).start()

        # Telegram'a milisaniyeler içinde 200 OK dön (asla 502 vermez)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"[Render Webhook Hatası]: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
