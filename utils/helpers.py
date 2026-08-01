# utils/helpers.py
import datetime
from zoneinfo import ZoneInfo

def format_currency(value):
    """Formatea cualquier cantidad numérica a formato de divisa USD."""
    try:
        return f"${value:,.2f}"
    except:
        return "$0.00"

def get_market_session_status():
    """Valida el estado actual de la sesión de Nueva York en tiempo real."""
    try:
        ny_now = datetime.datetime.now(ZoneInfo("America/New_York"))
        is_open = (ny_now.weekday() < 5) and (9 <= ny_now.hour < 16 or (ny_now.hour == 9 and ny_now.minute >= 30))
        time_str = ny_now.strftime("%I:%M:%S %p")
        status_str = "🟢 SESIÓN NY ABIERTA" if is_open else "🔴 SESIÓN NY CERRADA"
        return time_str, status_str
    except:
        return "Sincronizando...", "⏳ Verificando..."
