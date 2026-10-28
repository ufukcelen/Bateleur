# 🎯 Yorum Avcısı (YouTube Hakaret Tespit Sistemi)

Tamamen **Google Cloud** üzerinde, **%100 ücretsiz kotalarla** çalışan; kendi YouTube kanalınızın videolarına gelen yeni yorumları otomatik okuyan, **Google Gemini AI** ile hakaret/küfür tespiti yapan ve Telegram üzerinden anlık bildirim gönderen bulut tabanlı bir sistemdir.

---

## 🏗️ Mimari ve Çalışma Prensibi

1. **Google Cloud Scheduler (Zamanlayıcı):** Her 15 dakikada bir Cloud Function'ı tetikler.
2. **YouTube Data API v3:** Kanalın son yorumlarını çeker.
3. **Google Firestore (Veritabanı):** Önceden incelenmiş yorumları hafızada tutarak mükerrer incelemeyi ve kota harcamasını engeller.
4. **Google Gemini 2.5/1.5 Flash:** Yeni yorumların bağlamını, argo, kinaye ve şahsa yönelik hakaret durumunu Türkçe analiz eder.
5. **Telegram Bildirimi:** Hakaret tespit edildiğinde yorum sahibini, yorum metnini, şiddet derecesini ve doğrudan yoruma giden linki telefonunuza iletir.

---

## 🆓 Neden %100 Ücretsiz?

| Servis | Ücretsiz Kota Limiti | Bizim Kullanımımız |
| :--- | :--- | :--- |
| **Cloud Functions** | Ayda 2.000.000 çağrı | ~2.900 çağrı/ay (her 15 dk bir) |
| **Cloud Firestore** | Günde 50.000 okuma / 20.000 yazma | Günde ~200 işlem |
| **Cloud Scheduler** | 3 adet cron işi ömür boyu ücretsiz | 1 adet cron işi |
| **YouTube Data API** | Günde 10.000 kota birimi | Günde ~100 kota birimi |
| **Gemini AI API** | Günde 1.500 istek / dakikada 15 istek | Günde ~50 istek |
| **Telegram Botu** | Sınırsız / Tamamen Ücretsiz | Bildirim başı 1 istek |

---

## ⚙️ 1. Adım: Gerekli API Anahtarlarını Alma

### A. YouTube Data API v3 Anahtarı
1. [Google Cloud Console](https://console.cloud.google.com/) adresine gidin ve yeni bir proje oluşturun (örn: `yorum-avcisi`).
2. **APIs & Services > Library** sayfasına girin.
3. **YouTube Data API v3** servisini aratıp **Enable (Etkinleştir)** butonuna basın.
4. **APIs & Services > Credentials** sayfasına gelin, **Create Credentials > API Key** seçin.
5. Oluşan anahtarı kopyalayın (`YOUTUBE_API_KEY`).

### B. YouTube Kanal ID'nizi Bulma
1. YouTube Studio'ya girin: [studio.youtube.com](https://studio.youtube.com/)
2. Sol menüden **Ayarlar (Settings) > Kanal (Channel) > Gelişmiş Ayarlar (Advanced Settings)** yolunu izleyin.
3. Sayfanın en altındaki **Kanal Kimliği (Channel ID)** değerini kopyalayın (`UC...` ile başlar).

### C. Google Gemini API Anahtarı
1. [Google AI Studio](https://aistudio.google.com/app/apikey) adresine gidin.
2. Google hesabınızla giriş yapıp **Get API key** butonuna tıklayarak ücretsiz anahtarınızı alın (`GEMINI_API_KEY`).

### D. Telegram Botu (Anlık Mobil Bildirim İçin)
1. Telegram uygulamasında `@BotFather` kullanıcısını bulun.
2. `/newbot` komutunu gönderin ve botunuza bir isim verin.
3. BotFather size bir **HTTP API Token** verecektir (`TELEGRAM_BOT_TOKEN`).
4. Telefonunuza bildirim gelebilmesi için, yeni oluşturduğunuz bota Telegram'dan `/start` mesajı gönderin.
5. Telegram Chat ID'nizi öğrenmek için Telegram'da `@userinfobot` botunu başlatın; size `Id` numaranızı verecektir (`TELEGRAM_CHAT_ID`).

---

## 💻 2. Adım: Yerel Ortamda Test Etme

1. Proje dizininde sanal ortam oluşturup paketleri kurun:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. `.env.example` dosyasını `.env` olarak kopyalayın ve anahtarlarınızı girin:
   ```bash
   cp .env.example .env
   ```
   *(Yerel test yaparken `USE_LOCAL_DB=true` bırakabilirsiniz, böylece Firestore yerine yerel SQLite veritabanı kullanılır).*

3. Programı çalıştırıp test edin:
   ```bash
   python3 main.py
   ```

---

## ☁️ 3. Adım: Tamamen Google Cloud'a Yükleme (Sunucusuz)

İki yöntemle buluta yükleyebilirsiniz:

### Yöntem A: Google Cloud Console Arayüzü Üzerinden (Kodlama/Terminal Gerektirmez)

1. [Google Cloud Console > Cloud Functions](https://console.cloud.google.com/functions) sayfasına gidin.
2. **Create Function** butonuna tıklayın:
   - **Environment:** 2nd gen
   - **Function name:** `youtube-comment-hunter`
   - **Region:** `europe-west3` (Frankfurt) veya `europe-west1` (Belçika)
   - **Trigger:** HTTPS
   - **Runtime:** Python 3.11
   - **Entry point:** `handle_cloud_function`
3. Proje dosyalarını (`main.py`, `config.py`, `database.py`, `moderator.py`, `notifier.py`, `youtube_client.py`, `requirements.txt`) tarayıcıdaki kod editörüne yükleyin.
4. **Environment Variables** bölümüne `.env` içindeki değişkenlerinizi ekleyin (`USE_LOCAL_DB=false`).
5. **Deploy** butonuna basın.

### Yöntem B: Cloud Scheduler ile Otomatik Tetikleme Ayarlama

Fonksiyon kurulduktan sonra size bir URL verecektir (ör: `https://europe-west3-...cloudfunctions.net/youtube-comment-hunter`).

1. [Google Cloud Scheduler](https://console.cloud.google.com/cloudscheduler) sayfasına gidin.
2. **Create Job** butonuna tıklayın:
   - **Name:** `youtube-comment-cron`
   - **Region:** Fonksiyonunuzla aynı bölge (örn. `europe-west3`)
   - **Frequency (Sıklık):** `*/15 * * * *` (Her 15 dakikada bir çalışır)
   - **Timezone:** Turkey (Europe/Istanbul)
   - **Target type:** HTTP
   - **URL:** Cloud Function'ınızın HTTPS tetikleyici URL'si
   - **HTTP method:** GET veya POST
3. **Create** butonuna basarak tamamlayın.

Artık sistem 7/24 tamamen arka planda Google Cloud üzerinde çalışacak ve kanalınıza küfür veya hakaret geldiğinde telefonunuza anında bildirim düşecektir!

