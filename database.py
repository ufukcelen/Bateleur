import json
import os
from typing import Set, List
from config import Config

class BaseStorage:
    def get_processed_ids(self) -> Set[str]:
        raise NotImplementedError
    
    def mark_as_processed(self, comment_ids: List[str]) -> None:
        raise NotImplementedError

class JSONStorage(BaseStorage):
    """
    GitHub Actions ve yerel ortam için JSON tabanlı kalıcı depolama.
    Veritabanı kurulumu veya kart bilgisi gerektirmez; dosya git ile senkronize kalır.
    """
    def __init__(self, file_path: str = "processed_comments.json"):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def get_processed_ids(self) -> Set[str]:
        try:
            if not os.path.exists(self.file_path):
                return set()
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data)
        except Exception as e:
            print(f"[JSONStorage Okuma]: {e}")
            return set()

    def mark_as_processed(self, comment_ids: List[str]) -> None:
        if not comment_ids:
            return
        current = self.get_processed_ids()
        current.update(comment_ids)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(sorted(list(current)), f, indent=2, ensure_ascii=False)

class FirestoreStorage(BaseStorage):
    """Google Cloud Firestore tabanlı sunucusuz depolama."""
    def __init__(self, project_id: str, collection_name: str = "processed_comments"):
        from google.cloud import firestore
        if project_id:
            self.client = firestore.Client(project=project_id)
        else:
            self.client = firestore.Client()
        self.collection = self.client.collection(collection_name)

    def get_processed_ids(self) -> Set[str]:
        docs = self.collection.order_by("processed_at", direction="DESCENDING").limit(2000).stream()
        return {doc.id for doc in docs}

    def mark_as_processed(self, comment_ids: List[str]) -> None:
        from google.cloud import firestore
        batch = self.client.batch()
        count = 0
        now = firestore.SERVER_TIMESTAMP

        for cid in comment_ids:
            doc_ref = self.collection.document(cid)
            batch.set(doc_ref, {"processed_at": now})
            count += 1
            if count >= 450:
                batch.commit()
                batch = self.client.batch()
                count = 0

        if count > 0:
            batch.commit()

def get_storage() -> BaseStorage:
    """Konfigürasyona göre uygun depolama motorunu döndürür."""
    if Config.USE_LOCAL_DB or not Config.GCP_PROJECT_ID:
        return JSONStorage()

    try:
        return FirestoreStorage(Config.GCP_PROJECT_ID, Config.FIRESTORE_COLLECTION)
    except Exception as e:
        print(f"[Storage UYARI] Firestore bağlantısı kurulamadı ({e}). JSON depolamaya geçiliyor.")
        return JSONStorage()
