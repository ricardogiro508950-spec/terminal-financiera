import requests
import time
import csv
import os
import json
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import yfinance as yf
from flask import Flask

# ==========================================
# CONFIGURACIÓN
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

ARCHIVO_CSV = "historial_senales_reales.csv"
ARCHIVO_ESTADO = "ultimo_estado.json"

ACTIVOS = {"Bitcoin": "BTC-USD", "Oro": "GC=F", "Petróleo": "CL=F"}
ESTRATEGIAS = [
    "Confluencia Clásica", "Primera Vela (ORB)", "Cazador de Pullbacks",
    "Confluencia Gann + Fibonacci", "Confluencia Profesional (Velas+Estructura+Fibo)",
]

INTERVALO_CICLO_SEG = 300
UMBRAL_PULLBACK_PCT = 0.35

HORAS_EVALUACION_POR_ESTRATEGIA = {
    "Primera Vela (ORB)": 2,
    "Cazador de Pullbacks": 6,
    "Confluencia Clásica": 72,
    "Confluencia Gann + Fibonacci": 72,
    "Confluencia Profesional (Velas+Estructura+Fibo)": 72,
}

# ==========================================
# SERVIDOR WEB (para mantener vivo en Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Oculoos Bot de Señales Reales — Activo."

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# UTILIDADES DE ARCHIVO
# ==========================================
def inicializar_csv():
    if not os.path.exists(ARCHIVO_CSV):
        with open(ARCHIVO_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Fecha_Señal", "Activo", "Estrategia", "Señal",
                "Precio_Señal", "RSI", "EMA50", "EMA200",
                "Fecha_Evaluacion", "Precio_Evaluacion", "Variacion_Pct", "Resultado"
            ])

def cargar_estado():
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_estado(estado):
    with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f)

def enviar_alerta(mensaje):
    if not TOKEN:
        print("⚠️ No hay TOKEN configurado:", mensaje)
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=datos, timeout=10)
    except Exception as e:
        print(f"Error enviando alerta: {e}")

# ==========================================
# MATEMÁTICA Y ANÁLISIS
# ==========================================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def obtener_historico(ticker, period="1mo", interval="1h"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        return df if not df.empty else None
    except Exception as e:
        print(f"Error descargando {ticker}: {e}")
        return None

def precio_actual(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1d", interval="5m")
        if df.empty:
            return None
        return float(df["Close"].iloc[-1])
    except Exception:
        return None

def analizar_confluencia_clasica(ticker):
    df = obtener_historico(ticker, period="6mo", interval="1d")
    if df is None or len(df) < 200:
        return None
    ema50 = df["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
    ema200 = df["Close"].ewm(span=200, adjust=False).mean().iloc[-1]
    rsi = calculate_rsi(df["Close"]).iloc[-1]
    close = df["Close"].iloc[-1]
    if close > ema50 and rsi < 70 and ema50 > ema200:
        señal = "🟢 COMPRAR (Confluencia alcista)"
    elif close < ema50 and rsi > 30:
        señal = "🟡 ESPERAR (consolidación/duda)"
    else:
        señal = "🔴 EVITAR (riesgo técnico)"
    return {"señal": señal, "precio": close, "rsi": rsi, "ema50": ema50, "ema200": ema200}

def analizar_pullback(ticker):
    df = obtener_historico(ticker, period="1mo", interval="1h")
    if df is None or len(df) < 200:
        return None
    ema50 = df["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
    ema200 = df["Close"].ewm(span=200, adjust=False).mean().iloc[-1]
    rsi = calculate_rsi(df["Close"]).iloc[-1]
    close = df["Close"].iloc[-1]
    dist_pct = abs(close - ema50) / ema50 * 100 if ema50 else 999
    if close > ema50:
        señal = "🟢 COMPRAR (pullback a la EMA50, RSI sano)" if dist_pct <= UMBRAL_PULLBACK_PCT and rsi < 75 else "🟡 ESPERAR (lejos de EMA o RSI alto)"
    else:
        señal = "🔴 VENDER (rebote a la EMA50, RSI sano)" if dist_pct <= UMBRAL_PULLBACK_PCT and rsi > 25 else "🟡 ESPERAR (lejos de EMA o RSI bajo)"
    return {"señal": señal, "precio": close, "rsi": rsi, "ema50": ema50, "ema200": ema200}

def analizar_orb(ticker):
    try:
        df = yf.Ticker(ticker).history(period="5d", interval="15m")
        if df.empty:
            return None
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        df.index = df.index.tz_convert('America/New_York')
        df_open = df[(df.index.hour == 9) & (df.index.minute == 30)]
        if df_open.empty:
            return None
        vela = df_open.iloc[-1]
        orb_high, orb_low = vela['High'], vela['Low']
        close = df["Close"].iloc[-1]
        if close > orb_high:
            señal = "🟢 COMPRAR (ruptura alcista del rango de apertura)"
        elif close < orb_low:
            señal = "🔴 VENDER (ruptura bajista del rango de apertura)"
        else:
            señal = "🟡 ESPERAR (dentro del rango)"
        return {"señal": señal, "precio": close, "rsi": None, "ema50": orb_high, "ema200": orb_low}
    except Exception:
        return None

def analizar_gann_fibonacci(ticker):
    df = obtener_historico(ticker, period="3mo", interval="1d")
    if df is None or len(df) < 30:
        return None
    ventana = df.tail(50)
    high, low = ventana["High"].max(), ventana["Low"].min()
    rango = high - low
    if rango <= 0:
        return None
    close = df["Close"].iloc[-1]
    rsi = calculate_rsi(df["Close"]).iloc[-1]
    nivel_05 = low + 0.5 * rango
    zona_fib_85 = low + 0.85 * rango
    zona_fib_95 = low + 0.95 * rango
    tolerancia = rango * 0.02
    if zona_fib_85 <= close <= zona_fib_95 + tolerancia and rsi > 70:
        señal = "🔴 VENDER (zona 85-95% Fibo + RSI alto)"
    elif abs(close - nivel_05) <= tolerancia and rsi < 35:
        señal = "🟢 COMPRAR (zona 0.5 Gann/Fibo + RSI bajo)"
    else:
        señal = "🟡 ESPERAR"
    return {"señal": señal, "precio": close, "rsi": rsi, "ema50": nivel_05, "ema200": None}

def calcular_estructura(df, ventana=30):
    sub = df.tail(ventana)
    highs, lows = sub["High"].values, sub["Low"].values
    pivot_highs, pivot_lows = [], []
    for i in range(2, len(highs) - 2):
        if highs[i] == max(highs[i - 2:i + 3]):
            pivot_highs.append(highs[i])
        if lows[i] == min(lows[i - 2:i + 3]):
            pivot_lows.append(lows[i])
    if len(pivot_highs) >= 2 and len(pivot_lows) >= 2:
        if pivot_highs[-1] > pivot_highs[-2] and pivot_lows[-1] > pivot_lows[-2]:
            return "Alcista (HH/HL)"
        elif pivot_highs[-1] < pivot_highs[-2] and pivot_lows[-1] < pivot_lows[-2]:
            return "Bajista (LH/LL)"
    return "Lateral/Mixta"

def nivel_psicologico_cercano(precio):
    if precio <= 0:
        return 0, 999
    magnitud = 10 ** (len(str(int(precio))) - 1)
    paso = magnitud / 2 if magnitud >= 10 else 1
    nivel = round(precio / paso) * paso
    return nivel, abs(precio - nivel) / precio * 100

def calcular_fibonacci_clasico(df, ventana=50):
    sub = df.tail(ventana)
    high, low = sub["High"].max(), sub["Low"].min()
    rango = high - low
    if rango <= 0:
        return None
    return {"38.2%": high - 0.382 * rango, "50%": high - 0.5 * rango, "61.8%": high - 0.618 * rango}, high, low

def detectar_patron_vela(df):
    if len(df) < 6:
        return "Datos insuficientes", "Neutral"
    v0, v1 = df.iloc[-1], df.iloc[-2]
    o0, c0, h0, l0 = v0["Open"], v0["Close"], v0["High"], v0["Low"]
    cuerpo0 = abs(c0 - o0)
    rango0 = (h0 - l0) if (h0 - l0) > 0 else 0.0001
    if cuerpo0 <= rango0 * 0.05:
        return "Doji", "Neutral"
    if c0 > o0 and c0 >= v1["Open"] and o0 <= v1["Close"]:
        return "Envolvente Alcista", "Compra"
    if c0 < o0 and c0 <= v1["Open"] and o0 >= v1["Close"]:
        return "Envolvente Bajista", "Venta"
    return "Sin patrón claro", "Neutral"

def volumen_confirmado(df):
    if "Volume" not in df.columns or len(df) < 20:
        return False
    return bool(df["Volume"].iloc[-1] > df["Volume"].tail(20).mean() * 1.1)

def analizar_confluencia_profesional(ticker):
    df = obtener_historico(ticker, period="6mo", interval="1d")
    if df is None or len(df) < 60:
        return None
    close = df["Close"].iloc[-1]
    estructura = calcular_estructura(df)
    nivel_psico, dist_psico_pct = nivel_psicologico_cercano(close)
    patron, dir_patron = detectar_patron_vela(df)
    
    puntos_alc, puntos_baj = 0, 0
    if "Alcista" in estructura: puntos_alc += 1
    elif "Bajista" in estructura: puntos_baj += 1
    if dir_patron == "Compra": puntos_alc += 1
    elif dir_patron == "Venta": puntos_baj += 1
    if volumen_confirmado(df):
        if puntos_alc > puntos_baj: puntos_alc += 1
        elif puntos_baj > puntos_alc: puntos_baj += 1

    score = f"{puntos_alc} a favor / {puntos_baj} en contra"
    if puntos_alc >= 3 and puntos_alc > puntos_baj:
        señal = f"🟢 COMPRAR (confluencia profesional: {score})"
    elif puntos_baj >= 3 and puntos_baj > puntos_alc:
        señal = f"🔴 VENDER (confluencia profesional: {score})"
    else:
        señal = f"🟡 ESPERAR (sin confluencia: {score})"
    return {"señal": señal, "precio": close, "rsi": None, "ema50": nivel_psico, "ema200": None}

def registrar_señal(activo, estrategia, resultado):
    inicializar_csv()
    id_unico = f"{activo}_{estrategia}_{int(time.time())}"
    with open(ARCHIVO_CSV, mode='a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([
            id_unico, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), activo, estrategia, resultado["señal"],
            round(resultado["precio"], 2),
            round(resultado["rsi"], 2) if resultado["rsi"] is not None else "",
            round(resultado["ema50"], 2) if resultado["ema50"] is not None else "",
            round(resultado["ema200"], 2) if resultado["ema200"] is not None else "",
            "", "", "", "Pendiente"
        ])
    return id_unico

def evaluar_señales_pendientes():
    if not os.path.exists(ARCHIVO_CSV): return
    try:
        df = pd.read_csv(ARCHIVO_CSV)
    except Exception:
        return
    if df.empty or "Resultado" not in df.columns: return

    cambios = False
    ahora = datetime.now()
    for idx, fila in df[df["Resultado"] == "Pendiente"].iterrows():
        try:
            f_señal = datetime.strptime(fila["Fecha_Señal"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        espera = HORAS_EVALUACION_POR_ESTRATEGIA.get(fila["Estrategia"], 4)
        if (ahora - f_señal) < timedelta(hours=espera): continue
        
        ticker = ACTIVOS.get(fila["Activo"])
        if not ticker: continue
        p_hoy = precio_actual(ticker)
        if p_hoy is None: continue
        
        p_señal = float(fila["Precio_Señal"])
        var_pct = ((p_hoy - p_señal) / p_señal) * 100
        
        if "COMPRAR" in str(fila["Señal"]):
            res = "✅ Acierto" if var_pct > 0 else "❌ Fallo"
        elif "VENDER" in str(fila["Señal"]):
            res = "✅ Acierto" if var_pct < 0 else "❌ Fallo"
        else:
            res = "N/A"
            
        df.at[idx, "Resultado"] = res
        cambios = True
        enviar_alerta(f"📋 *EVALUACIÓN*\n{fila['Activo']} - {fila['Estrategia']}\nVariación: `{var_pct:+.2f}%` -> {res}")
    if cambios:
        df.to_csv(ARCHIVO_CSV, index=False)

# ==========================================
# CICLO PRINCIPAL DEL BOT
# ==========================================
def iniciar_bot():
    inicializar_csv()
    enviar_alerta("🚀 *Oculoos Bot de Señales Reales — Iniciado*\nMonitoreando mercados activamente.")
    
    while True:
        try:
            evaluar_señales_pendientes()
            for activo, ticker in ACTIVOS.items():
                estrategias_funcs = [
                    (ESTRATEGIAS[0], analizar_confluencia_clasica),
                    (ESTRATEGIAS[1], analizar_orb),
                    (ESTRATEGIAS[2], analizar_pullback),
                    (ESTRATEGIAS[3], analizar_gann_fibonacci),
                    (ESTRATEGIAS[4], analizar_confluencia_profesional),
                ]
                for nombre_est, func in estrategias_funcs:
                    res = func(ticker)
                    if res and ("COMPRAR" in res["señal"] or "VENDER" in res["señal"]):
                        registrar_señal(activo, nombre_est, res)
                        enviar_alerta(f"📊 *NUEVA SEÑAL*\nActivo: {activo}\nEstrategia: {nombre_est}\nSeñal: {res['señal']}\nPrecio: `${res['precio']:,.2f}`")
                    time.sleep(2)
        except Exception as e:
            print(f"Error en ciclo: {e}")
        time.sleep(INTERVALO_CICLO_SEG)

if __name__ == "__main__":
    hilo_bot = threading.Thread(target=iniciar_bot, daemon=True)
    hilo_bot.start()
    mantener_vivo()
