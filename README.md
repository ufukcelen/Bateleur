# 🦅 Bateleur (v0.0.2)

> **YouTube İçerik Üreticileri ve Ekipleri İçin Yapay Zeka Destekli Hakaret Tespit ve Adli Delil Toplama Sistemi**

[![Version](https://img.shields.io/badge/version-0.0.2-blue.svg)](https://github.com/ufukcelen/Bateleur)
[![Python](https://img.shields.io/badge/python-3.11-brightgreen.svg)](https://www.python.org/)
[![AI Engine](https://img.shields.io/badge/AI-Google%20Gemini%20Flash-orange.svg)](https://aistudio.google.com/)
[![Platform](https://img.shields.io/badge/cloud-GitHub%20Actions%20Cron-black.svg)](https://github.com/features/actions)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📖 Bateleur Nedir?

Adını gökyüzünde kesintisiz devriye gezen ve hedefini gözden kaçırmayan efsanevi Cambaz Kartalı'ndan alan **Bateleur**; YouTube kanallarının videolarına ve Shorts içeriklerine gelen yorumları 7/24 otomatik denetleyen, argo/kinaye ve küfürleri **Google Gemini AI** ile bağlamsal olarak analiz eden ve tespit edilen hakaretleri **savcılık ve adli makamlar için resmi dijital delil tutanağına** dönüştüren bulut tabanlı bir siber moderasyon sistemidir.

Tamamen **sunucusuz (serverless)** mimaride çalışan Bateleur; kredi kartı, sunucu faturası veya açık bir bilgisayar gerektirmeden arka planda sessizce devriye gezer.

---

## ✨ Temel Özellikler

* 🦅 **Çoklu Kanal Desteği:** Tek bir kurulumla birden fazla YouTube kanalını (ör. `@uykusuztosba`, `@radiomocas`) eş zamanlı takip eder.
* ⏱️ **Saatlik Akıllı Devriye:** Her saat başı kanalların en son 3 içeriğini (Video/Shorts/Canlı Yayın) otomatik inceler.
* 🧠 **Gelişmiş AI Moderasyonu (Gemini):**
  * **Hedef Ayrımı:** Videodaki konuklara, futbolculara, takımlara veya hakemlere yönelik genel eleştirileri/sitemleri temiz sayar; **yalnızca kanal sahibine ve ekibine yönelik şahsi saldırıları** yakalar.
  * **Tolerans Eşiği:** Hafif alay ve günlük argoları tolere eder; yalnızca ağır şahsi küfür ve tehditleri bildirir.
* ⚖️ **Adli Delil Toplama (TCK Madde 125 Uyumlu):**
  * Şahsın güncel **profil fotoğrafını** çeker.
  * Kullanıcı adını değiştirse bile emniyet ve savcılığın IP tespiti için kullandığı **Kalıcı YouTube Kanal ID'sini (`UC...`)** kayda alır.
  * Yorumun doğrudan kalıcı linkini (`&lc=...`) ve kesin UTC/TSİ zaman damgasını belgeler.
  * Savcılık dosyasına eklenebilecek standartta tek sayfalık **HTML Dijital Delil Tutanağı** üretir.
* 👥 **Telegram Ekip Bildirimi (`Bateleur.app`):** Tespit edilen hakaretler ekip grubuna şahsın profil fotoğrafı, hakaret metni, gerekçesi ve direkt silme/inceleme linkiyle iletilir.
* 🤫 **Sessiz Çalışma:** Her saat rapor atıp ekibi rahatsız etmez; yalnızca yeni bir hakaret yakalandığında bildirim gönderir.
* 💾 **Mükerrer Analiz Koruması:** İncelenen yorumlar `processed_comments.json` dosyasında hafızada tutulur; daha önce bakılan bir yorum asla tekrar taranmaz veya raporlanmaz.
* 📂 **Google Drive Entegrasyonu:** Delil tutanaklarını Google Drive'daki `BateleurFiles` klasörüne otomatik olarak yedekleyebilir.
* 🆓 **%100 Ücretsiz Bulut Mimarisi:** GitHub Actions üzerinde kart bilgisi veya fatura olmadan 7/24 ömür boyu ücretsiz çalışır.

---

## 🏗️ Mimari ve Çalışma Prensibi

```
[GitHub Actions Bulut Cron] (Her saat başı: 0 * * * *)
            │
            ▼
    [Bateleur Engine]
            │
            ├──► 1. YouTube Data API v3 ──► Kanalların son 3 içeriğini & yorumları çeker
            │
            ├──► 2. Bellek (processed_comments.json) ──► Yeni gelen yorumları filtreler
            │
            ├──► 3. Google Gemini 3.5 Flash ──► Hedef ve tolerans kurallarına göre analiz eder
            │
            └──► 4. Aksiyon (Yalnızca Hakaret Varsa):
                      ├─► Hukuki Delil Tutanağı (HTML) oluşturur
                      ├─► Google Drive (BateleurFiles) klasörüne yedekler
                      └─► Telegram (Bateleur.app) grubuna fotoğraflı delil kartı iletir
```

---

## 🚀 Manuel Komut: `/check`

Ekip grubunda herhangi bir üye dilediği an:
* Telegram grubuna `/check` yazarak veya
* GitHub Actions sekmesinden **Run workflow** butonuna basarak

kanalları anlık olarak taratabilir. Yeni bir hakaret yoksa bile grup bilgilendirilir.

---

## 🛠️ Kurulum ve Ortam Değişkenleri

GitHub Deponuzun **Settings > Secrets and variables > Actions** alanında tanımlanan anahtarlar:

| Değişken Adı | Açıklama |
| :--- | :--- |
| `YOUTUBE_API_KEY` | YouTube Data API v3 Erişim Anahtarı |
| `GEMINI_API_KEY` | Google AI Studio Gemini API Anahtarı |
| `YOUTUBE_CHANNELS` | Takip edilecek kanallar (örn: `@uykusuztosba,@radiomocas`) |
| `TELEGRAM_BOT_TOKEN` | `@BotFather` tarafından verilen bot token'ı |
| `TELEGRAM_CHAT_ID` | Bildirimlerin gideceği `Bateleur.app` grup kimliği |

---

## 📂 Proje Dizin Yapısı

```
Bateleur/
├── .github/workflows/
│   └── bateleur_patrol.yml     # Saatlik bulut zamanlayıcı iş akışı
├── config.py                   # Proje ayarları ve ortam değişkenleri
├── youtube_client.py           # YouTube API veri çekme ve profil çıkarıcı
├── moderator.py                # Gemini AI bağlamsal hakaret analiz motoru
├── moderation_rules.txt        # Özelleştirilebilir Türkçe moderasyon kuralları
├── evidence_generator.py       # Resmi Dijital Delil Tespit Tutanağı üretici
├── notifier.py                 # Telegram HTML/Fotoğraflı bildirim servisi
├── drive_service.py            # Google Drive (BateleurFiles) yedekleme
├── database.py                 # JSON tabanlı bellek yöneticisi
├── processed_comments.json     # Taranmış yorum kimlikleri hafızası
├── main.py                     # Ana yürütücü orkestrasyon dosyası
├── requirements.txt            # Python kütüphaneleri
└── README.md                   # Dokümantasyon
```

---

## 📄 Sürüm Geçmişi

* **v0.0.2 (Güncel):**
  * Bateleur marka kimliği ve logo entegrasyonu.
  * GitHub Actions ile %100 kredi kartsız sunucusuz saatlik bulut devriyesi.
  * `Bateleur.app` Telegram grubu ve fotoğraflı adli delil kartları.
  * TCK 125 uyumlu Kalıcı YouTube Kanal ID ve avatar yakalama desteği.
  * Google Drive `BateleurFiles` otomatik arşivleme altyapısı.
* **v0.0.1:**
  * İlk prototip, YouTube API ve Gemini entegrasyonu.

---

## ⚖️ Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında korunmaktadır.
