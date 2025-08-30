# test_telegram.py
import requests
from bot.config import settings

url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
payload = {
    "chat_id": settings.telegram_chat_id,
    "text": "🚀 ¡Prueba corregida! Si ves esto, funcionó.",
    "parse_mode": "Markdown"
}

response = requests.post(url, data=payload)
print("Respuesta de Telegram:", response.status_code)
print("Contenido:", response.json())