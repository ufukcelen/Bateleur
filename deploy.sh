#!/bin/bash
set -e

# Google Cloud Function Deploy Betiği
# Bu betik projeyi Google Cloud Functions (2. Nesil) olarak deploy eder.

FUNCTION_NAME="bateleur"
PROJECT_ID="bateleur-513014"
REGION="europe-west3" # Frankfurt
RUNTIME="python311"
ENTRY_POINT="handle_cloud_function"

echo "=================================================="
echo " 🦅 Bateleur Google Cloud Functions Dağıtımı"
echo " Proje: $PROJECT_ID"
echo " Fonksiyon: $FUNCTION_NAME"
echo " Bölge: $REGION"
echo "=================================================="

gcloud functions deploy $FUNCTION_NAME \
  --project=$PROJECT_ID \
  --gen2 \
  --runtime=$RUNTIME \
  --region=$REGION \
  --source=. \
  --entry-point=$ENTRY_POINT \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars="YOUTUBE_API_KEY=$YOUTUBE_API_KEY,GEMINI_API_KEY=$GEMINI_API_KEY,YOUTUBE_CHANNELS=$YOUTUBE_CHANNELS,TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN,TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID,USE_LOCAL_DB=false,GCP_PROJECT_ID=$PROJECT_ID" \
  --memory=256Mi \
  --timeout=120s

echo ""
echo "✅ Fonksiyon başarıyla dağıtıldı!"
echo "Şimdi Google Cloud Scheduler üzerinden 15 dakikada bir çalışacak zamanlayıcıyı kurabilirsiniz."

