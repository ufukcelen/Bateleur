import sqlite3
import os
from typing import Set, List
from config import Config

class BaseStorage:
    def get_processed_ids(self) -> Set[str]:
        raise NotImplementedError
    
    def mark_as_processed(self, comment_ids: List[str]) -> None:
        raise NotImplementedError

class SQLiteStorage(BaseStorage):
    """Yerel geliştirme ve testler için SQLite tabanlı depolama."""
    def __init__(self, db_path: str = "processed_comments.sqlite3"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_comments (
                    comment_id TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def get_processed_ids(self) -> Set[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT comment_id FROM processed_comments")
            return {row[0] for row in cursor.fetchall()}

    def mark_as_processed(self, comment_ids: List[str]) -> None:
        if not comment_ids:
            return
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT OR IGNORE INTO processed_comments (comment_id) VALUES (?)",
                [(cid,) for cid in comment_ids]
            )
            conn.commit()

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
        # Performans için son 2000 işlenmiş ID'yi getir
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
            # Firestore batch sınırı 500'dür
            if count >= 450:
                batch.commit()
                batch = self.client.batch()
                count = 0

        if count > 0:
            batch.commit()

def get_storage() -> BaseStorage:
    """Konfigürasyona göre uygun depolama motorunu döndürür."""
    if Config.USE_LOCAL_DB:
        print("[Storage] Yerel SQLite depolama kullanılıyor.")
        return SQLiteStorage()

    try:
        print("[Storage] Google Cloud Firestore'a bağlanılıyor...")
        return FirestoreStorage(Config.GCP_PROJECT_ID, Config.FIRESTORE_COLLECTION)
    except Exception as e:
        print(f"[Storage UYARI] Firestore bağlantısı kurulamadı ({e}). Yerel SQLite depolamaya geçiliyor.")
        return SQLiteStorage()

