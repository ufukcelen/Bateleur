#!/bin/bash
set -e

# Google Cloud Function Deploy Betiği
# Bu betik projeyi Google Cloud Functions (2. Nesil) olarak deploy eder.

FUNCTION_NAME="youtube-comment-hunter"
REGION="europe-west3" # Frankfurt veya europe-west1 (Belçika)
RUNTIME="python311"
ENTRY_POINT="handle_cloud_function"

echo "=================================================="
echo " Google Cloud Functions Dağıtımı Başlatılıyor"
echo " Fonksiyon Adı: $FUNCTION_NAME"
echo " Bölge: $REGION"
echo "=================================================="

# .env dosyasından ortam değişkenlerini oku
if [ ! -f .env ]; then
  echo "HATA: .env dosyası bulunamadı. Lütfen .env.example dosyasını .env olarak kopyalayıp doldurun."
  exit 1
fi

gcloud functions deploy $FUNCTION_NAME \
  --gen2 \
  --runtime=$RUNTIME \
  --region=$REGION \
  --source=. \
  --entry-point=$ENTRY_POINT \
  --trigger-http \
  --allow-unauthenticated \
  --env-vars-file=.env.yaml \
  --memory=256Mi \
  --timeout=120s

echo ""
echo "✅ Fonksiyon başarıyla dağıtıldı!"
echo "Şimdi Google Cloud Scheduler üzerinden 15 dakikada bir çalışacak zamanlayıcıyı kurabilirsiniz."

