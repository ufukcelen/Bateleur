import json
import time
from typing import List, Dict, Any
from config import Config

class CommentModerator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Gemini API anahtarı (GEMINI_API_KEY) tanımlanmamış!")

        from google import genai
        self.client = genai.Client(api_key=self.api_key)
        self.primary_model = "gemini-3.5-flash"
        self.fallback_model = "gemini-3.5-flash-lite"

    def analyze_comments(self, comments: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Gelen yorum listesini 10'arlı paketler halinde Gemini ile analiz eder.
        """
        if not comments:
            return []

        all_results = []
        for i in range(0, len(comments), batch_size):
            chunk = comments[i:i + batch_size]
            print(f"[Gemini] {i+1}-{i+len(chunk)} arasındaki yorumlar analiz ediliyor...")
            chunk_results = self._analyze_chunk(chunk)
            all_results.extend(chunk_results)

        return all_results

    def _analyze_chunk(self, chunk: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        input_data = [
            {"id": c["comment_id"], "text": c["text"], "author": c["author_name"]}
            for c in chunk
        ]

        # Kullanıcının tanımladığı özel kurallar dosyası varsa yükle
        custom_rules = ""
        try:
            with open("moderation_rules.txt", "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                custom_rules = "\n".join(lines)
        except Exception:
            pass

        default_rules = (
            "1. HEDEF AYRIMI:\n"
            "Videodaki futbolculara, hakeme veya teknik direktöre yönelik sitemleri/küfürleri görmezden gel; "
            "yalnızca kanal sahibine/ekibimize edilen hakaretleri yakala.\n\n"
            "2. EŞİK DEĞERİ (TOLERANS):\n"
            "Hafif alay, iğneleme veya günlük argoları tolere et; yalnızca ağır şahsi küfür ve tehditleri bildir.\n\n"
            "3. ELEŞTİRİLER:\n"
            "Görüş ayrılıkları, beğenmeme veya sert sitemler kesinlikle hakaret değildir (is_offensive: false yap)."
        )

        base_instruction = (
            "Sen bir YouTube kanalının topluluk uzmanısın. "
            "Sana kanalın son videolarına gelen yorumlar verilecek.\n"
        )
        active_rules = custom_rules if custom_rules else default_rules
        system_instruction = f"{base_instruction}\nUyman gereken kurallar:\n{active_rules}\n\nSadece geçerli bir JSON listesi döndür."

        prompt = f"""
Aşağıdaki yorumları incele ve her biri için JSON listesi döndür:
{json.dumps(input_data, ensure_ascii=False)}

Format:
[
  {{"id": "...", "is_offensive": true/false, "severity": "none/low/medium/high", "category": "clean/insult/profanity", "explanation": "kısa açıklama"}}
]
"""

        # Önce primary model, hata verirse fallback model ile dene
        for model in [self.primary_model, self.fallback_model]:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "system_instruction": system_instruction,
                        "response_mime_type": "application/json",
                        "http_options": {"timeout": 15000}
                    }
                )

                raw_text = response.text.strip()
                evaluations = json.loads(raw_text)
                eval_map = {item["id"]: item for item in evaluations if "id" in item}

                chunk_results = []
                for c in chunk:
                    eval_result = eval_map.get(c["comment_id"], {
                        "is_offensive": False,
                        "severity": "none",
                        "category": "clean",
                        "explanation": "Normal yorum"
                    })
                    chunk_results.append({**c, **eval_result})

                return chunk_results

            except Exception as e:
                print(f"[Gemini {model} Hatası]: {e}. Yedek modele geçiliyor...")
                time.sleep(1)

        # İki model de yanıt vermezse temiz işaretle
        return [{**c, "is_offensive": False, "severity": "none", "category": "clean", "explanation": "Zaman aşımı"} for c in chunk]
