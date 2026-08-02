import requests
import time
import csv
import os
import json
import threading
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from flask import Flask

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8807352507:AAEI5mhH0Ao-heGHrsBtJVpM6geGtlMTAUo")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8260761627")

ACTIVOS = {"Oro": "GC=F", "Bitcoin": "BTC-USD"}
INTERVALO_SCAN_SEG = 300  # 5 minutos

# ==========================================
# LAS 3 VERSIONES CON SU CAPITAL DE PAPEL
# ==========================================
VERSIONES = {
    "V1 - PDF Original (Gann+Fibo)": {"capital": 5000.0, "tiempo_eval": 24, "filtros": "ninguno"},
    "V2 - Mejorada (Velas + Volumen)": {"capital": 5000.0, "tiempo_eval": 12, "filtros": "geometria"},
    "V3 - Agresiva (Scalper 3R)": {"capital": 5000.0, "tiempo_eval": 4, "filtros": "ninguno"}
}

ARCHIVO_CSV = "simulacion_triple_real.csv"
ARCHIVO_CAPITAL = "capital_triple_real.json"

# ==========================================
# SERVIDOR WEB (PARA MANTENER RENDER VIVO)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Simulación Real con Velas Activa. Fuente: YAHOO"

# ==========================================
# UTILIDADES
# ==========================================
def enviar_alerta(mensaje):
    if not TOKEN: return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def obtener_historico(ticker, period="1mo", interval="1h"):
    try: 
        return yf.Ticker(ticker).history(period=period, interval=interval)
    except: return None

def precio_actual(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1d", interval="5m")
        return float(df["Close"].iloc[-1]) if not df.empty else None
    except: return None

# ==========================================
# GESTIÓN DE CAPITAL (Para cuando se activen las operaciones)
# ==========================================
def cargar_capital():
    if os.path.exists(ARCHIVO_CAPITAL):
        try:
            with open(ARCHIVO_CAPITAL, "r") as f: return json.load(f)
        except: pass
    return {v: data["capital"] for v, data in VERSIONES.items()}

def guardar_capital(capital):
    with open(ARCHIVO_CAPITAL, "w") as f: json.dump(capital, f)

def calcular_resultado(version, activo, precio_entrada, precio_salida, señal, es_v3=False):
    capital = cargar_capital()
    balance_actual = capital.get(version, 5000.0)
    riesgo_1R = balance_actual * 0.01 
    valor_pip = 10.0 if activo == "Oro" else 1.0
    lote = 0.10
    
    puntos_movimiento = (precio_salida - precio_entrada)
    es_compra = "COMPRAR" in señal
    ganancia_usd = (puntos_movimiento / 0.01) * valor_pip * lote if es_compra else (-puntos_movimiento / 0.01) * valor_pip * lote
    
    r_multiplo = round(ganancia_usd / (riesgo_1R * 0.5 if es_v3 else riesgo_1R), 2) if riesgo_1R > 0 else 0.0
    nuevo_balance = round(balance_actual + ganancia_usd, 2)
    capital[version] = nuevo_balance
    guardar_capital(capital)
    return ganancia_usd, r_multiplo, nuevo_balance

# ==========================================
# MOTOR DE ANÁLISIS
# ==========================================
def analizar_mercado(ticker, precio_actual):
    # 1. Gann y Fibonacci
    df_daily = yf.Ticker(ticker).history(period="3mo", interval="1d")
    if df_daily is None or len(df_daily) < 20: return None
    
    high = df_daily["High"].tail(50).max()
    low = df_daily["Low"].tail(50).min()
    rango = high - low
    close = df_daily["Close"].iloc[-1]
    
    gann_50 = low + 0.5 * rango
    fib_95 = low + 0.95 * rango
    tolerancia = rango * 0.02
    confluencia = abs(close - gann_50) <= tolerancia and abs(close - fib_95) <= tolerancia
    
    # 2. Geometría de Velas y Volumen
    df_hour = yf.Ticker(ticker).history(period="1mo", interval="1h")
    patron_detectado = False
    volumen_alto = False
    
    if df_hour is not None and len(df_hour) > 3:
        v2 = df_hour.iloc[-2]
        v3 = df_hour.iloc[-1]
        
        cuerpo3 = abs(v3['Close'] - v3['Open'])
        rango3 = v3['High'] - v3['Low']
        mecha_inf3 = min(v3['Open'], v3['Close']) - v3['Low']
        mecha_sup3 = v3['High'] - max(v3['Open'], v3['Close'])
        
        if rango3 > 0 and mecha_inf3 >= (2 * cuerpo3) and mecha_sup3 < (0.2 * cuerpo3):
            patron_detectado = "🟢 Martillo (Compra)"
        elif v2['Close'] < v2['Open'] and v3['Close'] > v3['Open'] and v3['Open'] < v2['Close'] and v3['Close'] > v2['Open']:
            patron_detectado = "🟢 Envolvente Alcista (Compra)"
        elif v2['Close'] > v2['Open'] and abs(v3['Close'] - v3['Open']) < (0.3 * rango3) and v3['Close'] < v3['Open']:
            patron_detectado = "🔴 Estrella Tarde (Venta)"
        elif v2['Close'] > v2['Open'] and v3['Close'] < v3['Open'] and v3['Open'] > v2['Close'] and v3['Close'] < v2['Open']:
            patron_detectado = "🔴 Envolvente Bajista (Venta)"

        vol_actual = v3['Volume']
        vol_promedio = df_hour['Volume'].tail(20).mean()
        if vol_actual > (vol_promedio * 1.8):
            volumen_alto = True

    return {
        "confluencia": confluencia,
        "precio": close,
        "patron": patron_detectado,
        "volumen_alto": volumen_alto
    }

# ==========================================
# CICLO PRINCIPAL (MODO REPORTERO EN VIVO)
# ==========================================
def ejecutar_ciclo():
    informe = "📊 *OCULOOS REPORTE EN VIVO*\n\n"
    
    for activo, ticker in ACTIVOS.items():
        precio = precio_actual(ticker)
        if not precio: 
            informe += f"⚠️ {activo}: Sin datos actuales\n\n"
            continue
        
        analisis = analizar_mercado(ticker, precio)
        if not analisis:
            informe += f"🌐 {activo}: ${precio:,.2f}\n❌ Sin análisis.\n\n"
            continue
            
        precio_entrada = analisis["precio"]
        patron = analisis["patron"]
        volumen_alto = analisis["volumen_alto"]
        confluencia = analisis["confluencia"]
        
        informe += f"🌐 *{activo}*\n"
        informe += f"💵 Precio Actual: ${precio_entrada:,.2f}\n"
        
        if confluencia:
            informe += f"✅ *CONFLUENCIA DETECTADA* (Gann 0.5 + Fib 95%)\n"
            if patron:
                informe += f"🕯️ {patron}\n"
            else:
                informe += f"🕯️ Sin patrón de velas.\n"
            informe += f"📈 Volumen: {'ALTO' if volumen_alto else 'Normal'}\n"
            
            entraron = []
            if confluencia: entraron.append("V1 (PDF)")
            if patron and volumen_alto: entraron.append("V2 (Velas)")
            if confluencia: entraron.append("V3 (Scalper)")
            informe += f"🚀 Entrarían: {', '.join(entraron)}\n"
        else:
            informe += f"⏳ Sin confluencia (fuera de zona)\n"
        
        informe += "\n"

    # Enviar el informe a Telegram
    enviar_alerta(informe)

# ==========================================
# EJECUCIÓN EN HILOS
# ==========================================
if __name__ == '__main__':
    guardar_capital(cargar_capital())
    enviar_alerta("🚀 *BOT EN MODO REPORTERO*\nTe llegarán informes cada 5 minutos con el análisis en vivo del mercado.")
    
    def ciclo_principal():
        while True:
            try:
                ejecutar_ciclo()
                print(f"✅ Informe enviado a las {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                print(f"Error crítico en ciclo: {e}")
            time.sleep(INTERVALO_SCAN_SEG)
            
    hilo_bot = threading.Thread(target=ciclo_principal)
    hilo_bot.start()
    
    # Render web server
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)