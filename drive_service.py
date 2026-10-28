import os
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import Config

class DriveService:
    """
    Oluşturulan delil tutanaklarını kullanıcının Google Drive'ındaki
    'YorumHunterFiles' klasörüne otomatik yükler.
    """
    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        self.service = None
        self._init_service()

    def _init_service(self):
        try:
            # 1. Ortamda veya GCP'de varsayılan kimlik bilgileri varsa
            if self.credentials_path and os.path.exists(self.credentials_path):
                from google.oauth2 import service_account
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=["https://www.googleapis.com/auth/drive"]
                )
                self.service = build("drive", "v3", credentials=creds)
            else:
                # GCP Cloud Function üzerinde çalışırken default SA kullanılır
                import google.auth
                creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
                self.service = build("drive", "v3", credentials=creds)
        except Exception as e:
            # Yerel testte henüz Drive hesabı bağlanmadıysa sessizce uyar
            print(f"[Google Drive Başlatma]: Drive kimliği henüz yapılandırılmadı ({e}). Dosyalar yerel olarak 'deliller/' klasöründe saklanıyor.")
            self.service = None

    def get_or_create_folder(self, folder_name: str = "YorumHunterFiles") -> Optional[str]:
        """
        'YorumHunterFiles' klasörünü bulur, yoksa otomatik oluşturur ve ID'sini döner.
        """
        if not self.service:
            return None

        try:
            # Klasör var mı diye ara
            query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
            files = results.get("files", [])
            if files:
                return files[0]["id"]

            # Yoksa oluştur
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            folder = self.service.files().create(body=folder_metadata, fields="id").execute()
            print(f"[Google Drive] '{folder_name}' klasörü otomatik oluşturuldu (ID: {folder.get('id')})")
            return folder.get("id")
        except Exception as e:
            print(f"[Google Drive Klasör Hatası]: {e}")
            return None

    def upload_file(self, file_path: str, folder_name: str = "YorumHunterFiles") -> Optional[str]:
        """
        Delil dosyasını Drive'daki ilgili klasöre yükler ve dosya linkini döner.
        """
        if not self.service or not os.path.exists(file_path):
            return None

        try:
            folder_id = self.get_or_create_folder(folder_name)
            file_name = os.path.basename(file_path)

            file_metadata = {"name": file_name}
            if folder_id:
                file_metadata["parents"] = [folder_id]

            media = MediaFileUpload(file_path, mimetype="text/html", resumable=True)
            uploaded_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink"
            ).execute()

            web_link = uploaded_file.get("webViewLink")
            print(f"[Google Drive] Delil dosyası başarıyla yüklendi: {file_name}")
            return web_link

        except Exception as e:
            print(f"[Google Drive Yükleme Hatası]: {e}")
            return None
