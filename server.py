import os
from flask import Flask, request, jsonify
from main import run_moderation_cycle

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health_check():
    """Canlılık ve sağlık kontrolü."""
    return jsonify({
        "status": "online",
        "app": "Bateleur",
        "description": "YouTube & Instagram Moderasyon ve Siber Delil Takip Sistemi",
        "version": "v0.0.3"
    }), 200

@app.route("/cron", methods=["GET", "POST"])
def cron_endpoint():
    """
    Periyodik tarama uç noktası.
    cron-job.org veya harici zamanlayıcılar tarafından tetiklenebilir.
    """
    print("[Render] /cron tetiklendi, periyodik tarama başlatılıyor...")
    result = run_moderation_cycle(is_manual=False)
    return jsonify(result), 200

@app.route("/check", methods=["GET", "POST"])
def manual_check_endpoint():
    """Doğrudan manuel tarama uç noktası (özet raporu Telegram'a iletir)."""
    print("[Render] /check tetiklendi, manuel tarama başlatılıyor...")
    result = run_moderation_cycle(is_manual=True)
    return jsonify(result), 200

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """
    Telegram Webhook Giriş Noktası.
    Telegram grubundan bota gelen mesajları (/check) dinler.
    """
    try:
        data = request.get_json(silent=True) or {}
        is_manual = False
        if "message" in data:
            msg_text = (data["message"].get("text") or "").strip()
            if msg_text.startswith("/check"):
                is_manual = True

        result = run_moderation_cycle(is_manual=is_manual)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Render Webhook Hatası]: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
