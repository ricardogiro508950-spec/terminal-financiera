import os
import time
import threading
import requests
import pandas as pd
import yfinance as yf
from flask import Flask

# ==========================================
# CONFIGURACIÓN DE TELEGRAM
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Activos reales a vigilar (Yahoo Finance)
ACTIVOS = {
    "Bitcoin": "BTC-USD",
    "Euro / Dólar": "EURUSD=X"
}

# ==========================================
# SERVIDOR WEB (Para mantener vivo el bot en Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Algoritmo Cuantitativo 4 Capas — Activo y vigilando."

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# FUNCIÓN DE TELEGRAM
# ==========================================
def enviar_alerta(mensaje):
    if not TOKEN or not CHAT_ID:
        print("⚠️ Faltan credenciales de Telegram.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=datos, timeout=10)
        print("Mensaje enviado a Telegram con éxito.")
    except Exception as e:
        print(f"Error enviando alerta: {e}")

# ==========================================
# INDICADORES MATEMÁTICOS
# ==========================================
def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -1 * delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / (loss + 1e-10) # Evitar división por cero
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
# EL MOTOR DEL ALGORITMO (4 CAPAS)
# ==========================================
def analizar_mercado(ticker):
    try:
        # Descargamos velas de 5 minutos
        df = yf.Ticker(ticker).history(period="5d", interval="5m")
        if df.empty or len(df) < 200:
            return None

        # --- CÁLCULO DE VARIABLES ---
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        df['RSI'] = calcular_rsi(df['Close'])
        df = calcular_estocastico(df)
        df['ATR'] = calcular_atr(df)
        df['ATR_SMA'] = df['ATR'].rolling(window=14).mean() # Promedio de volatilidad
        
        # Bandas de Bollinger
        sma_20 = df['Close'].rolling(window=20).mean()
        std_20 = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = sma_20 + (2 * std_20)
        df['BB_Lower'] = sma_20 - (2 * std_20)

        # Tomamos los datos de la última vela cerrada
        vela = df.iloc[-2] # Usamos -2 para asegurar que la vela esté 100% cerrada
        
        c = vela['Close']
        o = vela['Open']
        h = vela['High']
        l = vela['Low']
        
        # Anatomía de la vela
        cuerpo = abs(c - o)
        mecha_sup = h - max(c, o)
        mecha_inf = min(c, o) - l

        # ==========================================
        # EVALUACIÓN LÓGICA (COMPRAS)
        # ==========================================
        # Capa 1: Tendencia Alcista
        c1_compra = c > vela['EMA_50'] and vela['EMA_50'] > vela['EMA_200']
        
        # Capa 2: Momento Sobrevendido
        c2_compra = vela['RSI'] < 40 and vela['Stoch_K'] > vela['Stoch_D'] and vela['Stoch_K'] < 30
        
        # Capa 3: Volatilidad (Rebote en banda inferior con volumen)
        c3_compra = l <= vela['BB_Lower'] and vela['ATR'] > vela['ATR_SMA']
        
        # Capa 4: Gatillo (Pin Bar Alcista / Martillo)
        c4_compra = mecha_inf > (2 * cuerpo) and mecha_sup < cuerpo

        if c1_compra and c2_compra and c3_compra and c4_compra:
            return {"señal": "🟢 OPORTUNIDAD DE COMPRA (Sube)", "precio": c, "rsi": vela['RSI']}

        # ==========================================
        # EVALUACIÓN LÓGICA (VENTAS)
        # ==========================================
        # Capa 1: Tendencia Bajista
        c1_venta = c < vela['EMA_50'] and vela['EMA_50'] < vela['EMA_200']
        
        # Capa 2: Momento Sobrecomprado
        c2_venta = vela['RSI'] > 60 and vela['Stoch_K'] < vela['Stoch_D'] and vela['Stoch_K'] > 70
        
        # Capa 3: Volatilidad (Rebote en banda superior con volumen)
        c3_venta = h >= vela['BB_Upper'] and vela['ATR'] > vela['ATR_SMA']
        
        # Capa 4: Gatillo (Pin Bar Bajista / Estrella fugaz)
        c4_venta = mecha_sup > (2 * cuerpo) and mecha_inf < cuerpo

        if c1_venta and c2_venta and c3_venta and c4_venta:
            return {"señal": "🔴 OPORTUNIDAD DE VENTA (Baja)", "precio": c, "rsi": vela['RSI']}

        return None # Si no se cumplen las 4 capas exactas, se queda en silencio

    except Exception as e:
        print(f"Error analizando {ticker}: {e}")
        return None

# ==========================================
# CICLO PRINCIPAL (Cada 5 Minutos)
# ==========================================
def ciclo_principal():
    while True:
        try:
            for nombre, ticker in ACTIVOS.items():
                resultado = analizar_mercado(ticker)
                
                if resultado:
                    msj = (
                        f"⚡ *ALERTA 4 CAPAS DETECTADA*\n\n"
                        f"🌐 *Activo:* {nombre}\n"
                        f"📊 *Acción:* {resultado['señal']}\n"
                        f"💵 *Precio Cierre:* ${resultado['precio']:,.4f}\n"
                        f"📐 *RSI:* {resultado['rsi']:.1f}\n\n"
                        f"⚠️ _Todas las condiciones matemáticas alineadas a 5 min._"
                    )
                    enviar_alerta(msj)
                    
        except Exception as e:
            print(f"Error en ciclo: {e}")
        
        # Pausa de 300 segundos (5 minutos) antes del próximo escaneo
        time.sleep(300)

# ==========================================
# EJECUCIÓN DEL SCRIPT
# ==========================================
if __name__ == "__main__":
    t = threading.Thread(target=mantener_vivo)
    t.daemon = True
    t.start()

    time.sleep(2)
    enviar_alerta("✅ *SISTEMA ACTIVO:* El algoritmo de 4 Capas Cuantitativas ha iniciado. Vigilando el mercado cada 5 minutos. Recibirás un mensaje solo cuando se confirme una oportunidad clara.")
    
    ciclo_principal()
