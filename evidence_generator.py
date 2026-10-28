import os
from datetime import datetime
from typing import Dict, Any

class EvidenceGenerator:
    """
    Savcılık ve adli makamlara sunulabilecek nitelikte
    Dijital Delil Tespit Tutanağı (HTML / Yazdırılabilir PDF formatı) üretir.
    """
    def __init__(self, output_dir: str = "deliller"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_html_card(self, comment_data: Dict[str, Any]) -> str:
        comment_id = comment_data.get("comment_id", "bilinmeyen")
        author_name = comment_data.get("author_name", "Bilinmeyen")
        author_img = comment_data.get("author_profile_image", "")
        author_channel_id = comment_data.get("author_channel_id", "Tespit Edilemedi")
        author_channel_url = comment_data.get("author_channel_url", "")
        
        channel_name = comment_data.get("channel_name", "")
        video_title = comment_data.get("video_title", "")
        video_url = comment_data.get("video_url", "")
        comment_url = comment_data.get("comment_url", "")
        
        text = comment_data.get("text", "")
        published_at = comment_data.get("published_at", "")
        category = comment_data.get("category", "").upper()
        severity = comment_data.get("severity", "").upper()
        explanation = comment_data.get("explanation", "")
        
        detection_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <title>Dijital Delil Tespit Tutanağı - {author_name}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: #f8fafc;
      color: #1e293b;
      margin: 0;
      padding: 30px;
    }}
    .container {{
      max-width: 750px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 30px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    .header {{
      border-bottom: 2px solid #ef4444;
      padding-bottom: 15px;
      margin-bottom: 25px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .header h1 {{
      font-size: 20px;
      color: #dc2626;
      margin: 0;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .badge {{
      background: #fee2e2;
      color: #991b1b;
      padding: 4px 10px;
      border-radius: 6px;
      font-weight: bold;
      font-size: 13px;
    }}
    .profile-card {{
      display: flex;
      gap: 20px;
      background: #f1f5f9;
      padding: 16px;
      border-radius: 8px;
      margin-bottom: 20px;
      align-items: center;
    }}
    .avatar {{
      width: 70px;
      height: 70px;
      border-radius: 50%;
      border: 2px solid #cbd5e1;
      object-fit: cover;
      background: #e2e8f0;
    }}
    .profile-info {{
      font-size: 14px;
      line-height: 1.6;
    }}
    .profile-info strong {{
      color: #0f172a;
    }}
    .comment-box {{
      background: #fff1f2;
      border-left: 4px solid #f43f5e;
      padding: 16px 20px;
      border-radius: 6px;
      margin: 20px 0;
      font-size: 16px;
      font-weight: 500;
      color: #881337;
      word-break: break-word;
    }}
    .section-title {{
      font-size: 14px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      margin-top: 20px;
      margin-bottom: 8px;
    }}
    .meta-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      margin-top: 10px;
    }}
    .meta-table td {{
      padding: 8px 10px;
      border-bottom: 1px solid #f1f5f9;
    }}
    .meta-table td:first-child {{
      width: 32%;
      color: #64748b;
      font-weight: 600;
    }}
    .meta-table td:last-child {{
      word-break: break-all;
    }}
    .footer {{
      margin-top: 30px;
      padding-top: 15px;
      border-top: 1px solid #e2e8f0;
      font-size: 12px;
      color: #94a3b8;
      text-align: center;
    }}
    @media print {{
      body {{ background: white; padding: 0; }}
      .container {{ border: none; box-shadow: none; padding: 0; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🦅 Bateleur - Dijital Delil Tespit Tutanağı</h1>
      <span class="badge">HUKUKİ DELİL / {severity}</span>
    </div>

    <div class="section-title">Şüpheli / Hesap Bilgileri</div>
    <div class="profile-card">
      <img src="{author_img}" alt="Profil Fotoğrafı" class="avatar" onerror="this.src='https://dummyimage.com/70x70/cbd5e1/475569.png&text=YOK'">
      <div class="profile-info">
        <div><strong>Kullanıcı Adı:</strong> {author_name}</div>
        <div><strong>Kalıcı Kanal ID:</strong> <code>{author_channel_id}</code></div>
        <div><strong>Profil Bağlantısı:</strong> <a href="{author_channel_url}" target="_blank">{author_channel_url}</a></div>
      </div>
    </div>

    <div class="section-title">İlgili Hakaret İçerikli Yorum</div>
    <div class="comment-box">
      "{text}"
    </div>

    <div class="section-title">Teknik ve Hukuki Detaylar</div>
    <table class="meta-table">
      <tr>
        <td>Mağdur Kanal</td>
        <td><strong>{channel_name}</strong></td>
      </tr>
      <tr>
        <td>İlgili Video</td>
        <td><a href="{video_url}" target="_blank">{video_title}</a></td>
      </tr>
      <tr>
        <td>Yorum Doğrudan URL (Kalıcı Link)</td>
        <td><a href="{comment_url}" target="_blank">{comment_url}</a></td>
      </tr>
      <tr>
        <td>Yorum Paylaşım Tarihi</td>
        <td>{published_at} (UTC)</td>
      </tr>
      <tr>
        <td>Tespit ve Kayıt Tarihi</td>
        <td>{detection_time} (TSİ)</td>
      </tr>
      <tr>
        <td>Hukuki Sınıflandırma</td>
        <td><strong>{category}</strong> ({explanation})</td>
      </tr>
    </table>

    <div class="footer">
      Bu tutanak, <strong>Bateleur</strong> YouTube Delil Takip ve Siber Suç Tespiti Altyapısı tarafından otomatik oluşturulmuştur.<br>
      Kalıcı Kanal ID ve Yorum URL'si doğrudan Google sunucularındaki kayıtla eşleşmektedir.
    </div>
  </div>
</body>
</html>
"""
        file_path = os.path.join(self.output_dir, f"delil_{comment_id}.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return file_path

