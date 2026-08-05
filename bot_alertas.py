import os
import time
import threading
import requests
import pandas as pd
import yfinance as yf
from flask import Flask
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE TELEGRAM Y ACTIVOS
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Los "Pesos Pesados" inspirados en los flujos institucionales
ACTIVOS = {
    "ORO": "GC=F",
    "BITCOIN": "BTC-USD",
    "NETFLIX": "NFLX",
    "AMAZON": "AMZN",
    "EUR/USD": "EURUSD=X"
}

# ==========================================
# SIMULADOR ANTI-MARTINGALA & RIESGO
# ==========================================
saldo_actual = 58.20
saldo_maximo = 58.20  # Para calcular el peor momento (Drawdown)
drawdown_maximo = 0.0
inversion_base = 10.00
racha_ganadora = 0

# ==========================================
# SERVIDOR WEB (Para Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "⚡ Terminal Financiera Pro - Fibo + RSI Activo"

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def enviar_alerta(mensaje):
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=datos, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")

# ==========================================
# MOTOR MATEMÁTICO: RSI + FIBONACCI
# ==========================================
def calcular_rsi(df, periodos=14):
    """Calcula el RSI puro usando Pandas para medir el agotamiento"""
    delta = df['Close'].diff()
    ganancia = (delta.where(delta > 0, 0)).rolling(window=periodos).mean()
    perdida = (-delta.where(delta < 0, 0)).rolling(window=periodos).mean()
    
    rs = ganancia / perdida
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analizar_mercado():
    global saldo_actual, saldo_maximo, drawdown_maximo
    
    while True:
        try:
            for nombre, ticker in ACTIVOS.items():
                # Descargamos los últimos 5 días en velas de 5 minutos
                data = yf.download(ticker, period="5d", interval="5m", progress=False)
                if data.empty or len(data) < 20:
                    continue
                
                # Inyectamos el RSI a la tabla de datos
                data['RSI'] = calcular_rsi(data)
                
                # Extraemos los datos de la última vela cerrada
                ultimo_cierre = data['Close'].iloc[-1]
                maximo_reciente = data['High'].max()
                minimo_reciente = data['Low'].min()
                rsi_actual = data['RSI'].iloc[-1]
                
                # Filtro de seguridad (evitar errores de división si no hay movimiento)
                rango = maximo_reciente - minimo_reciente
                if rango == 0:
                    continue
                
                # Calculamos en qué porcentaje de Fibonacci está el precio
                fibo_posicion = ((ultimo_cierre - minimo_reciente) / rango) * 100
                
                # ===================================================
                # LA CONFLUENCIA LOGICA "Y" (Precio + Agotamiento)
                # ===================================================
                senal = Ninguna
                
                # VENTA: Precio en el techo (Fibo > 95%) Y mercado sobrecomprado (RSI > 75)
                if fibo_posicion >= 95 and rsi_actual >= 75:
                    senal = "🔴 VENTA / SHORT"
                    zona = "Techo Institucional"
                    
                # COMPRA: Precio en el piso (Fibo < 5%) Y mercado sobrevendido (RSI < 25)
                elif fibo_posicion <= 5 and rsi_actual <= 25:
                    senal = "🟢 COMPRA / LONG"
                    zona = "Soporte Extremo"
                
                if senal:
                    # Actualizar métricas de riesgo
                    actualizar_drawdown()
                    hora_texto = datetime.now().strftime("%I:%M %p")
                    
                    mensaje = (
                        f"⚡ **ALERTA DE ALTA PRECISIÓN** ⚡\n\n"
                        f"🌍 **Activo:** {nombre}\n"
                        f"📊 **Operación:** {senal}\n"
                        f"🎯 **Zona:** {zona}\n\n"
                        f"📈 **Confirmaciones Matemáticas:**\n"
                        f"• Fibonacci (Nivel): {fibo_posicion:.1f}%\n"
                        f"• RSI (Agotamiento): {rsi_actual:.1f}\n\n"
                        f"💰 **Gestión de Riesgo:**\n"
                        f"• Saldo Actual: ${saldo_actual:.2f}\n"
                        f"• Drawdown Máx: {drawdown_maximo:.2f}%\n"
                        f"• Inversión Sugerida: ${inversion_base:.2f}"
                    )
                    enviar_alerta(mensaje)
                    print(f"Alerta enviada para {nombre}")
                    
                    # Pausa de 30 minutos para este par y evitar spam en la misma zona
                    time.sleep(1800) 
            
            # El bot respira 1 minuto antes de volver a escanear todo
            time.sleep(60)
            
        except Exception as e:
            print(f"Error analizando: {e}")
            time.sleep(60)

def actualizar_drawdown():
    """Calcula el riesgo máximo al que ha estado expuesta la cuenta"""
    global saldo_actual, saldo_maximo, drawdown_maximo
    if saldo_actual > saldo_maximo:
        saldo_maximo = saldo_actual
    
    caida_actual = ((saldo_maximo - saldo_actual) / saldo_maximo) * 100
    if caida_actual > drawdown_maximo:
        drawdown_maximo = caida_actual

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    t = threading.Thread(target=mantener_vivo)
    t.daemon = True
    t.start()
    
    mensaje_inicio = (
        "✅ **TERMINAL INSTITUCIONAL ACTUALIZADA**\n\n"
        "Filtros activos:\n"
        "• Fibonacci (Zonas Extremas)\n"
        "• RSI (Agotamiento de Fuerza)\n\n"
        f"💵 Saldo Inicial: ${saldo_actual:.2f}\n"
        "Radar escaneando: Oro, Bitcoin, Netflix, Amazon y EUR/USD."
    )
    enviar_alerta(mensaje_inicio)
    
    analizar_mercado()
