import os
import time
import threading
import requests
import random
from flask import Flask
from datetime import datetime, timedelta

# ==========================================
# CONFIGURACIÓN DE TELEGRAM
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Los pares clásicos que usan en Opciones Binarias
PARES = ["EUR/USD", "EUR/JPY", "GBP/USD", "USD/JPY"]

# ==========================================
# SERVIDOR WEB (Para Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤡 Generador de Señales (Modo TikTok) - Activo"

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def enviar_alerta(mensaje):
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=datos, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")

# ==========================================
# EL "CEREBRO" DEL SOFTWARE (Probabilidad Ciega)
# ==========================================
def generar_senal_probabilistica():
    # 1. Elige un par al azar
    par_elegido = random.choice(PARES)
    
    # 2. Genera una probabilidad (50/50 o ajustada al 60% para simular "estrategia")
    probabilidad = random.random()
    
    if probabilidad > 0.5:
        accion = "COMPRAR / BUY"
        icono = "🟢"
    else:
        accion = "VENDER / SELL"
        icono = "🔴"
        
    return par_elegido, accion, icono

# ==========================================
# CICLO PRINCIPAL (El reloj suizo de 3 minutos)
# ==========================================
def ciclo_vendehumos():
    while True:
        try:
            # Obtiene la hora actual para el mensaje
            ahora = datetime.now()
            hora_texto = ahora.strftime("%I:%M %p")
            
            # Genera la señal inventada
            par, accion, icono = generar_senal_probabilistica()
            
            # Construye el mensaje con el formato exacto del TikTok
            mensaje = (
                f"⚙️ SOFTWARE PREMIUM ⚙️\n\n"
                f"{par} {hora_texto}\n"
                f"{icono} {accion}\n\n"
                f"⏳ Expiración: 3 a 5 minutos."
            )
            
            # Envía a Telegram
            enviar_alerta(mensaje)
            print(f"Señal falsa enviada: {par} - {accion}")
            
            # EL TRUCO: Se duerme exactamente 180 segundos (3 minutos)
            # Sin importar qué esté haciendo el mercado real.
            time.sleep(180) 
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    t = threading.Thread(target=mantener_vivo)
    t.daemon = True
    t.start()
    
    enviar_alerta("✅ *SOFTWARE INICIADO:* Recibirás una señal probabilística cada 3 minutos exactos, ignorando la acción del precio real.")
    
    # Inicia el bucle infinito
    ciclo_vendehumos()
