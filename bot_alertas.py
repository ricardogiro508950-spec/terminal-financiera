import os
import time
import threading
import requests
import pandas as pd
import yfinance as yf
from flask import Flask
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE TELEGRAM
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Activos reales a vigilar
ACTIVOS = {
    "Bitcoin": "BTC-USD",
    "Euro / Dólar": "EURUSD=X",
    "Euro / Libra": "EURGBP=X",
    "Dólar / Yen": "USDJPY=X",
    "Oro": "GC=F"
}

# ==========================================
# SERVIDOR WEB (Para mantener vivo en Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Algoritmo 4 Capas — Operando y registrando Logs internos."

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# FUNCIÓN DE TELEGRAM
# ==========================================
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
# INDICADORES MATEMÁTICOS
# ==========================================
def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -1 * delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def calcular_estocastico(df, k_period=14, d_period=3):
    low_min = df['Low'].rolling(window=k_period).min()
    high_max = df['High'].rolling(window=k_period).max()
    df['Stoch_K'] = 100 * ((df['Close'] - low_min) / (high_max - low_min + 1e-10))
    df['Stoch_D'] = df['Stoch_K'].rolling(window=d_period).mean()
    return df

def calcular_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

# ==========================================
# EL MOTOR DEL ALGORITMO
# ==========================================
def analizar_mercado(nombre, ticker):
    try:
        df = yf.Ticker(ticker).history(period="5d", interval="5m")
        if df.empty or len(df) < 200:
            print(f"[{nombre}] ⚠️ Datos insuficientes en Yahoo Finance.")
            return None

        # --- CÁLCULO DE VARIABLES ---
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        df['RSI'] = calcular_rsi(df['Close'])
        df = calcular_estocastico(df)
        df['ATR'] = calcular_atr(df)
        df['ATR_SMA'] = df['ATR'].rolling(window=14).mean()
        
        sma_20 = df['Close'].rolling(window=20).mean()
        std_20 = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = sma_20 + (2 * std_20)
        df['BB_Lower'] = sma_20 - (2 * std_20)

        vela = df.iloc[-2]
        c = vela['Close']
        o = vela['Open']
        h = vela['High']
        l = vela['Low']
        
        cuerpo = abs(c - o)
        mecha_sup = h - max(c, o)
        mecha_inf = min(c, o) - l

        # ==========================================
        # DIAGNÓSTICO INTERNO (LOGS EN RENDER)
        # ==========================================
        volatilidad_estado = "📈 ALTA (Ok)" if vela['ATR'] > vela['ATR_SMA'] else "📉 BAJA"
        tendencia_estado = "ALCISTA" if c > vela['EMA_50'] else "BAJISTA"
        print(f"[{nombre}] Precio: ${c:,.4f} | Tendencia: {tendencia_estado} | RSI: {vela['RSI']:.1f} | Volatilidad: {volatilidad_estado}")

        # ==========================================
        # EVALUACIÓN 4 CAPAS (COMPRA)
        # ==========================================
        c1_compra = c > vela['EMA_50'] and vela['EMA_50'] > vela['EMA_200']
        c2_compra = vela['RSI'] < 40 and vela['Stoch_K'] > vela['Stoch_D'] and vela['Stoch_K'] < 30
        c3_compra = l <= vela['BB_Lower'] and vela['ATR'] > vela['ATR_SMA']
        c4_compra = mecha_inf > (2 * cuerpo) and mecha_sup < cuerpo

        if c1_compra and c2_compra and c3_compra and c4_compra:
            print(f"⭐⭐⭐ ¡SEÑAL DE COMPRA ENCONTRADA EN {nombre}! ⭐⭐⭐")
            return {"señal": "🟢 OPORTUNIDAD DE COMPRA (Sube)", "precio": c, "rsi": vela['RSI']}

        # ==========================================
        # EVALUACIÓN 4 CAPAS (VENTA)
        # ==========================================
        c1_venta = c < vela['EMA_50'] and vela['EMA_50'] < vela['EMA_200']
        c2_venta = vela['RSI'] > 60 and vela['Stoch_K'] < vela['Stoch_D'] and vela['Stoch_K'] > 70
        c3_venta = h >= vela['BB_Upper'] and vela['ATR'] > vela['ATR_SMA']
        c4_venta = mecha_sup > (2 * cuerpo) and mecha_inf < cuerpo

        if c1_venta and c2_venta and c3_venta and c4_venta:
            print(f"⭐⭐⭐ ¡SEÑAL DE VENTA ENCONTRADA EN {nombre}! ⭐⭐⭐")
            return {"señal": "🔴 OPORTUNIDAD DE VENTA (Baja)", "precio": c, "rsi": vela['RSI']}

        return None

    except Exception as e:
        print(f"Error analizando {ticker}: {e}")
        return None

# ==========================================
# CICLO PRINCIPAL
# ==========================================
def ciclo_principal():
    while True:
        try:
            ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print("\n" + "="*50)
            print(f"🔄 INICIANDO ESCANEO DE MERCADO - {ahora}")
            print("="*50)

            for nombre, ticker in ACTIVOS.items():
                resultado = analizar_mercado(nombre, ticker)
                
                if resultado:
                    msj = (
                        f"⚡ *ALERTA 4 CAPAS DETECTADA*\n\n"
                        f"🌐 *Activo:* {nombre}\n"
                        f"📊 *Acción:* {resultado['señal']}\n"
                        f"💵 *Precio Cierre:* ${resultado['precio']:,.4f}\n"
                        f"📐 *RSI:* {resultado['rsi']:.1f}\n\n"
                        f"⚠️ _Todas las condiciones alineadas a 5 min._"
                    )
                    enviar_alerta(msj)
            
            print("⏳ Escaneo finalizado. Esperando 5 minutos...")
        except Exception as e:
            print(f"Error en ciclo: {e}")
        
        time.sleep(300)

if __name__ == "__main__":
    t = threading.Thread(target=mantener_vivo)
    t.daemon = True
    t.start()
    enviar_alerta("✅ *SISTEMA ACTIVO:* Radar de 5 activos encendido. Logs internos funcionando.")
    ciclo_principal()
