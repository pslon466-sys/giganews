import os
import sqlite3
import requests
import feedparser
import urllib3
from pathlib import Path

# Отключаем предупреждения о сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RSS_FEED_URL = os.getenv("RSS_FEED_URL", "https://habr.com/ru/rss/articles/")
DB_PATH = Path(__file__).resolve().parent / "news.db"

def get_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': f'Basic {os.getenv("GIGACHAT_CREDENTIALS")}'
    }
    payload = {'scope': 'GIGACHAT_API_PERS'}
    res = requests.post(url, headers=headers, data=payload, verify=False)
    return res.json()['access_token']

def summarize(text):
    token = get_token()
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": "Ты — технология для пересказа новостей. Кратко, четко, только суть."},
            {"role": "user", "content": text[:5000]}
        ]
    }
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.post(url, headers=headers, json=payload, verify=False)
    return res.json()['choices'][0]['message']['content']

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS sent (url TEXT PRIMARY KEY)")
    
    feed = feedparser.parse(RSS_FEED_URL)
    for entry in feed.entries[:3]:
        if not conn.execute("SELECT 1 FROM sent WHERE url = ?", (entry.link,)).fetchone():
            try:
                summary = summarize(f"{entry.title}\n\n{entry.get('summary', '')}")
                msg = f"<b>{entry.title}</b>\n\n{summary}\n\n🔗 {entry.link}"
                
                requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/sendMessage", 
                             json={"chat_id": os.getenv("TELEGRAM_CHAT_ID"), "text": msg, "parse_mode": "HTML"})
                
                conn.execute("INSERT INTO sent VALUES (?)", (entry.link,))
                conn.commit()
                print(f"Готово: {entry.title}")
            except Exception as e:
                print(f"Ошибка: {e}")
    conn.close()

if __name__ == "__main__":
    main()
