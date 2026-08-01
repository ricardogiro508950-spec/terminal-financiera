# core/alert_engine.py
import requests
from utils.logger import log

def send_telegram_alert(bot_token, chat_id, message):
    """
    Envía notificaciones push en tiempo real a un canal o chat privado de Telegram.
    Ideal para alertas de ruptura ORB, señales de IA y gestión de riesgo.
    """
    if not bot_token or not chat_id:
        log.warning("Token de Telegram o Chat ID no configurados.")
        return False, "Credenciales de Telegram faltantes."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            log.info("Alerta de Telegram enviada exitosamente.")
            return True, "Alerta enviada con éxito."
        else:
            log.error(f"Error al enviar Telegram: {response.text}")
            return False, f"Error del servidor Telegram: {response.status_code}"
    except Exception as e:
        log.error(f"Excepción conectando con la API de Telegram: {e}")
        return False, f"Excepción de red: {str(e)}"
