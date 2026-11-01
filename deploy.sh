#!/bin/bash
set -e

# ==================================================
# 🦅 Bateleur Google Cloud Functions Dağıtım Betiği
# ==================================================

FUNCTION_NAME="bateleur"
PROJECT_ID="bateleur-513014"
REGION="europe-west3" # Frankfurt
RUNTIME="python311"
ENTRY_POINT="handle_cloud_function"

# Ortam Değişkenleri (Değerler yoksa tanımlı varsayılanlar kullanılır)
YOUTUBE_API_KEY="${YOUTUBE_API_KEY:-AIzaSyAKKGKoQnLuyS6piv9HfLV3OCHJ37o7Oec}"
GEMINI_API_KEY="${GEMINI_API_KEY:-AQ.Ab8RN6Iaw_U-PnuYb10OlnknGs9GKlhfk8Nk8HsouOsALmLiVA}"
YOUTUBE_CHANNELS="${YOUTUBE_CHANNELS:-@uykusuztosba,@radiomocas}"
APIFY_API_TOKEN="${APIFY_API_TOKEN:-apify_api_mptmqC4Jjl1pg96xBp4FuB82cjKbDR14IjR0}"
INSTAGRAM_PROFILES="${INSTAGRAM_PROFILES:-uykusuztosba,radiomocas}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-9075674369:AAGBSA36v5rol4SIYxFdKpShe7rdf4-kUow}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:--5505248203}"

echo "=================================================="
echo " 🦅 Bateleur Google Cloud Functions Dağıtımı"
echo " Proje: $PROJECT_ID"
echo " Fonksiyon: $FUNCTION_NAME"
echo " Bölge: $REGION"
echo "=================================================="

# 1. Gerekli Google Cloud API'lerini etkinleştir
echo "⚙️ [1/4] Google Cloud servisleri etkinleştiriliyor..."
gcloud services enable \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  firestore.googleapis.com \
  --project=$PROJECT_ID

# 2. Firestore Veritabanı Hazırlığı (Yoksa oluşturur)
echo "🗄️ [2/4] Firestore veritabanı kontrol ediliyor..."
gcloud firestore databases describe --project=$PROJECT_ID >/dev/null 2>&1 || \
gcloud firestore databases create --location=$REGION --project=$PROJECT_ID >/dev/null 2>&1 || true

# 3. Google Cloud Function Dağıtımı
echo "🚀 [3/4] Cloud Function dağıtılıyor..."
gcloud functions deploy $FUNCTION_NAME \
  --project=$PROJECT_ID \
  --gen2 \
  --runtime=$RUNTIME \
  --region=$REGION \
  --source=. \
  --entry-point=$ENTRY_POINT \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars="YOUTUBE_API_KEY=$YOUTUBE_API_KEY,GEMINI_API_KEY=$GEMINI_API_KEY,YOUTUBE_CHANNELS=$YOUTUBE_CHANNELS,APIFY_API_TOKEN=$APIFY_API_TOKEN,INSTAGRAM_PROFILES=$INSTAGRAM_PROFILES,TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN,TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID,USE_LOCAL_DB=false,GCP_PROJECT_ID=$PROJECT_ID" \
  --memory=256Mi \
  --timeout=120s

# Fonksiyon URL'sini al
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --gen2 --region=$REGION --project=$PROJECT_ID --format="value(serviceConfig.uri)")
echo "🔗 Fonksiyon URL: $FUNCTION_URL"

# 4. Telegram Webhook ve Cloud Scheduler Kurulumu
echo "🤖 [4/4] Telegram Webhook ve 15 dakikalık Cloud Scheduler kuruluyor..."

# Telegram Webhook bağla (/check komutunu anında karşılaması için)
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$FUNCTION_URL\"}" > /dev/null

echo "✅ Telegram Webhook bağlandı: Gruba /check yazdığınızda anında tetiklenecektir."

# Cloud Scheduler Görevi Oluştur (Her 15 dakikada bir otomatik çalışma)
gcloud scheduler jobs create http bateleur-patrol \
  --project=$PROJECT_ID \
  --location=$REGION \
  --schedule="*/15 * * * *" \
  --uri="$FUNCTION_URL" \
  --http-method=POST \
  --message-body='{}' >/dev/null 2>&1 || \
gcloud scheduler jobs update http bateleur-patrol \
  --project=$PROJECT_ID \
  --location=$REGION \
  --schedule="*/15 * * * *" \
  --uri="$FUNCTION_URL" \
  --http-method=POST \
  --message-body='{}' >/dev/null 2>&1 || true

echo "✅ Cloud Scheduler görevi hazır: Her 15 dakikada bir otomatik tarama yapacak."

echo ""
echo "=================================================="
echo "🎉 TEBRİKLER! Bateleur Google Cloud'da yayında!"
echo "📡 Canlı URL: $FUNCTION_URL"
echo "⏰ Otomatik Çalışma: 15 dakikada bir"
echo "💬 Manuel Tetikleme: Telegram'a /check yazabilirsiniz"
echo "=================================================="
