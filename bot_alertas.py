import os
import time
import threading
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from flask import Flask
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE TELEGRAM Y ACTIVOS
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

ACTIVOS = {
    "ORO": "GC=F",
    "BITCOIN": "BTC-USD",
    "NETFLIX": "NFLX",
    "AMAZON": "AMZN",
    "EUR/USD": "EURUSD=X"
}

# Diccionario de control de tiempos para evitar spam (1800 seg = 30 min por activo)
ultimas_alertas = {ticker: 0 for ticker in ACTIVOS.values()}

# ==========================================
# SIMULADOR ANTI-MARTINGALA & RIESGO
# ==========================================
saldo_actual = 58.20
saldo_maximo = 58.20
drawdown_maximo = 0.0
inversion_base = 10.00
racha_ganadora = 0

# ==========================================
# SERVIDOR WEB (Para Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "⚡ Terminal Institucional - Sistema Loaiza Activo"

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
# MOTOR MATEMÁTICO: RSI + FIBONACCI (NIVELES LOAIZA)
# ==========================================
def calcular_rsi(df, periodos=14):
    """Calcula el RSI puro con protección contra división por cero"""
    delta = df['Close'].diff()
    ganancia = (delta.where(delta > 0, 0)).rolling(window=periodos).mean()
    perdida = (-delta.where(delta < 0, 0)).rolling(window=periodos).mean()
    
    perdida = perdida.replace(0, np.nan)
    rs = ganancia / perdida
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100)

def simular_operacion():
    """Ejecuta la lógica del simulador Anti-Martingala sobre el saldo"""
    global saldo_actual, racha_ganadora
    victoria = np.random.rand() > 0.45 
    
    if victoria:
        ganancia = inversion_base * 0.85
        saldo_actual += ganancia
        racha_ganadora += 1
    else:
        saldo_actual -= inversion_base
        racha_ganadora = 0

def actualizar_drawdown():
    """Calcula el riesgo máximo al que ha estado expuesta la cuenta"""
    global saldo_actual, saldo_maximo, drawdown_maximo
    if saldo_actual > saldo_maximo:
        saldo_maximo = saldo_actual
    
    caida_actual = ((saldo_maximo - saldo_actual) / saldo_maximo) * 100
    if caida_actual > drawdown_maximo:
        drawdown_maximo = caida_actual

def analizar_mercado():
    global saldo_actual
    
    while True:
        try:
            for nombre, ticker in ACTIVOS.items():
                if time.time() - ultimas_alertas[ticker] < 1800:
                    continue

                data = yf.download(ticker, period="5d", interval="5m", progress=False)
                if data.empty or len(data) < 20:
                    continue
                
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                
                data['RSI'] = calcular_rsi(data)
                
                ultimo_cierre = float(data['Close'].iloc[-1])
                maximo_reciente = float(data['High'].max())
                minimo_reciente = float(data['Low'].min())
                rsi_actual = float(data['RSI'].iloc[-1])
                
                rango = maximo_reciente - minimo_reciente
                if rango == 0:
                    continue
                
                fibo_posicion = ((ultimo_cierre - minimo_reciente) / rango) * 100
                
                senal = None
                tipo_alerta = ""
                
                # ===================================================
                # LÓGICA DE NIVELES INSTITUCIONALES (85% y 95%)
                # ===================================================
                
                # ZONA DE REVERSIÓN EXTREMA (Nivel 95% + RSI de Agotamiento)[span_2](start_span)[span_2](end_span)
                if fibo_posicion >= 95 and rsi_actual >= 75:
                    senal = "🔴 VENTA / SHORT (ZONA 95%)"
                    tipo_alerta = "EJECUCIÓN INSTITUCIONAL"
                elif fibo_posicion <= 5 and rsi_actual <= 25:
                    senal = "🟢 COMPRA / LONG (ZONA 5%)"
                    tipo_alerta = "EJECUCIÓN INSTITUCIONAL"
                
                # ZONA DE INTERÉS TEMPRANA (Nivel 85% - Preparación)[span_3](start_span)[span_3](end_span)
                elif 85 <= fibo_posicion < 95 and rsi_actual >= 70:
                    senal = "⚠️ ALERTA TEMPRANA: Posible Venta"
                    tipo_alerta = "ZONA DE INTERÉS (85%)"
                elif 5 < fibo_posicion <= 15 and rsi_actual <= 30:
                    senal = "⚠️ ALERTA TEMPRANA: Posible Compra"
                    tipo_alerta = "ZONA DE INTERÉS (15%)"
                
                if senal:
                    # Si es ejecución final, simulamos operación y riesgo
                    if "EJECUCIÓN" in tipo_alerta:
                        simular_operacion()
                        actualizar_drawdown()
                    
                    mensaje = (
                        f"⚡ **{tipo_alerta}** ⚡\n\n"
                        f"🌍 **Activo:** {nombre}\n"
                        f"📊 **Señal:** {senal}\n\n"
                        f"📈 **Métricas de Confluencia:**\n"
                        f"• Fibonacci (Nivel): {fibo_posicion:.1f}%\n"
                        f"• RSI (Agotamiento): {rsi_actual:.1f}\n\n"
                        f"💰 **Gestión de Riesgo:**\n"
                        f"• Saldo Actual: ${saldo_actual:.2f}\n"
                        f"• Drawdown Máx: {drawdown_maximo:.2f}%\n"
                        f"• Inversión Aplicada: ${inversion_base:.2f}"
                    )
                    enviar_alerta(mensaje)
                    
                    # Registrar timestamp para cooldown de este activo
                    ultimas_alertas[ticker] = time.time()
            
            time.sleep(60)
            
        except Exception as e:
            print(f"Error analizando: {e}")
            time.sleep(60)

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    t = threading.Thread(target=mantener_vivo)
    t.daemon = True
    t.start()
    
    mensaje_inicio = (
        "✅ **TERMINAL INSTITUCIONAL - SISTEMA LOAIZA**\n\n"
        "Niveles de control integrados:\n"
        "• Zona de Interés Temprana (85% / 15%)\n"
        "• Zona de Reversión Extrema (95% / 5%)\n"
        "• Filtro RSI de Agotamiento\n\n"
        f"💵 Saldo Inicial: ${saldo_actual:.2f}\n"
        "Radar escaneando: Oro, Bitcoin, Netflix, Amazon y EUR/USD."
    )
    enviar_alerta(mensaje_inicio)
    
    analizar_mercado()
