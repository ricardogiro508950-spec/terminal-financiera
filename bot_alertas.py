import requests
import time
import csv
import os
import json
import threading
from datetime import datetime, timedelta
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
ARCHIVO_CAPITAL = "capital_por_estrategia.json"

CAPITAL_INICIAL_POR_ESTRATEGIA = 1000.0   
MONTO_POR_SEÑAL = 100.0                    

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
# SERVIDOR WEB (para mantener vivo)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Oculoos Bot de Señales Reales — Activo."

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# UTILIDADES
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

def cargar_capital():
    if os.path.exists(ARCHIVO_CAPITAL):
        try:
            with open(ARCHIVO_CAPITAL, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {est: CAPITAL_INICIAL_POR_ESTRATEGIA for est in ESTRATEGIAS}

def guardar_capital(capital):
    with open(ARCHIVO_CAPITAL, "w", encoding="utf-8") as f:
        json.dump(capital, f)

def enviar_alerta(mensaje):
    if not TOKEN or "PON_TU_TOKEN" in TOKEN:
        print("⚠️ No hay TOKEN configurado, no se envía a Telegram.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=datos, timeout=10)
    except Exception as e:
        print(f"Error enviando alerta: {e}")

# ==========================================
# MATEMÁTICA Y ESTRATEGIAS
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
    except Exception:
        return None

def precio_actual(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1d", interval="5m")
        if df.empty: return None
        return float(df["Close"].iloc[-1])
    except Exception:
        return None

def analizar_confluencia_clasica(ticker):
    df = obtener_historico(ticker, period="6mo", interval="1d")
    if df is None or len(df) < 200: return None
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
    if df is None or len(df) < 200: return None
    ema50 = df["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
    rsi = calculate_rsi(df["Close"]).iloc[-1]
    close = df["Close"].iloc[-1]
    dist_pct = abs(close - ema50) / ema50 * 100 if ema50 else 999

    if close > ema50:
        señal = "🟢 COMPRAR (pullback a la EMA50, RSI sano)" if dist_pct <= UMBRAL_PULLBACK_PCT and rsi < 75 else "🟡 ESPERAR (todavía lejos de la EMA o RSI alto)"
    else:
        señal = "🔴 VENDER (rebote a la EMA50, RSI sano)" if dist_pct <= UMBRAL_PULLBACK_PCT and rsi > 25 else "🟡 ESPERAR (todavía lejos de la EMA o RSI bajo)"
    return {"señal": señal, "precio": close, "rsi": rsi, "ema50": ema50, "ema200": None}

def analizar_orb(ticker):
    try:
        df = yf.Ticker(ticker).history(period="5d", interval="15m")
        if df.empty: return None
        if df.index.tz is None: df.index = df.index.tz_localize('UTC')
        df.index = df.index.tz_convert('America/New_York')
        df_open = df[(df.index.hour == 9) & (df.index.minute == 30)]
        if df_open.empty: return None
        vela = df_open.iloc[-1]
        orb_high, orb_low = vela['High'], vela['Low']
        close = df["Close"].iloc[-1]

        if close > orb_high: señal = "🟢 COMPRAR (ruptura alcista del rango de apertura)"
        elif close < orb_low: señal = "🔴 VENDER (ruptura bajista del rango de apertura)"
        else: señal = "🟡 ESPERAR (dentro del rango, sin ruptura)"
        return {"señal": señal, "precio": close, "rsi": None, "ema50": orb_high, "ema200": orb_low}
    except Exception:
        return None

def analizar_gann_fibonacci(ticker):
    df = obtener_historico(ticker, period="3mo", interval="1d")
    if df is None or len(df) < 30: return None
    ventana = df.tail(50)
    high, low = ventana["High"].max(), ventana["Low"].min()
    rango = high - low
    if rango <= 0: return None
    close = df["Close"].iloc[-1]
    rsi = calculate_rsi(df["Close"]).iloc[-1]

    nivel_05 = low + 0.5 * rango
    zona_fib_85, zona_fib_95 = low + 0.85 * rango, low + 0.95 * rango
    tolerancia = rango * 0.02

    if (zona_fib_85 <= close <= zona_fib_95 + tolerancia) and rsi > 70:
        señal = "🔴 VENDER (zona de reversión 85-95% Fibonacci + RSI sobrecomprado)"
    elif (abs(close - nivel_05) <= tolerancia) and rsi < 35:
        señal = "🟢 COMPRAR (zona de interés 0.5 Gann/Fibonacci + RSI sobrevendido)"
    else:
        señal = "🟡 ESPERAR (sin confluencia clara en este momento)"
    return {"señal": señal, "precio": close, "rsi": rsi, "ema50": nivel_05, "ema200": None}

def analizar_confluencia_profesional(ticker):
    return {"señal": "🟡 ESPERAR (buscando estructura del mercado)", "precio": precio_actual(ticker) or 0, "rsi": None, "ema50": None, "ema200": None}

# ==========================================
# REGISTRO Y EVALUACIÓN
# ==========================================
def registrar_señal(activo, estrategia, resultado):
    inicializar_csv()
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    id_unico = f"{activo}_{estrategia}_{int(time.time())}"
    with open(ARCHIVO_CSV, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            id_unico, fecha_hora, activo, estrategia, resultado["señal"],
            round(resultado["precio"], 2),
            round(resultado["rsi"], 2) if resultado["rsi"] is not None else "",
            round(resultado["ema50"], 2) if resultado["ema50"] is not None else "",
            "", "", "", "", "Pendiente"
        ])

def es_señal_accionable(texto_señal):
    return "COMPRAR" in texto_señal or "VENDER" in texto_señal

def evaluar_señales_pendientes():
    if not os.path.exists(ARCHIVO_CSV): return
    try:
        df = pd.read_csv(ARCHIVO_CSV)
    except Exception: return

    if df.empty or "Resultado" not in df.columns: return

    cambios = False
    ahora = datetime.now()
    capital = cargar_capital()

    for idx, fila in df[df["Resultado"] == "Pendiente"].iterrows():
        try:
            fecha_señal = datetime.strptime(fila["Fecha_Señal"], "%Y-%m-%d %H:%M:%S")
        except Exception: continue

        horas_espera = HORAS_EVALUACION_POR_ESTRATEGIA.get(fila["Estrategia"], 4)
        if (ahora - fecha_señal) < timedelta(hours=horas_espera): continue

        ticker = ACTIVOS.get(fila["Activo"])
        if not ticker: continue
        precio_hoy = precio_actual(ticker)
        if precio_hoy is None: continue

        precio_señal = float(fila["Precio_Señal"])
        variacion_pct = ((precio_hoy - precio_señal) / precio_señal) * 100

        es_compra = "COMPRAR" in str(fila["Señal"])
        es_venta = "VENDER" in str(fila["Señal"])

        if es_compra:
            resultado_final = "✅ Acierto" if variacion_pct > 0 else "❌ Fallo"
            ganancia_usd = MONTO_POR_SEÑAL * (variacion_pct / 100)
        elif es_venta:
            resultado_final = "✅ Acierto" if variacion_pct < 0 else "❌ Fallo"
            ganancia_usd = MONTO_POR_SEÑAL * (-variacion_pct / 100)
        else:
            resultado_final = "N/A"
            ganancia_usd = 0.0

        estrategia_fila = fila["Estrategia"]
        capital[estrategia_fila] = round(capital.get(estrategia_fila, CAPITAL_INICIAL_POR_ESTRATEGIA) + ganancia_usd, 2)
        
        df.at[idx, "Resultado"] = resultado_final
        df.at[idx, "Fecha_Evaluacion"] = ahora.strftime("%Y-%m-%d %H:%M:%S")
        df.at[idx, "Precio_Evaluacion"] = round(precio_hoy, 2)
        df.at[idx, "Variacion_Pct"] = round(variacion_pct, 2)
        cambios = True

    if cambios:
        df.to_csv(ARCHIVO_CSV, index=False)
        guardar_capital(capital)

# ==========================================
# CICLO PRINCIPAL
# ==========================================
def ciclo_principal():
    inicializar_csv()
    estado = cargar_estado()

    while True:
        try:
            evaluar_señales_pendientes()

            for nombre_activo, ticker in ACTIVOS.items():
                resultados = {
                    "Confluencia Clásica": analizar_confluencia_clasica(ticker),
                    "Cazador de Pullbacks": analizar_pullback(ticker),
                    "Primera Vela (ORB)": analizar_orb(ticker),
                    "Confluencia Gann + Fibonacci": analizar_gann_fibonacci(ticker),
                    "Confluencia Profesional (Velas+Estructura+Fibo)": analizar_confluencia_profesional(ticker)
                }

                for estrategia, res in resultados.items():
                    if res and es_señal_accionable(res["señal"]):
                        clave_estado = f"{ticker}_{estrategia}"
                        ultimo_estado = estado.get(clave_estado, "")

                        if res["señal"] != ultimo_estado:
                            registrar_señal(nombre_activo, estrategia, res)
                            estado[clave_estado] = res["señal"]
                            horas_eval = HORAS_EVALUACION_POR_ESTRATEGIA.get(estrategia, 4)
                            
                            msj = (
                                f"📊 *NUEVA SEÑAL DETECTADA*\n\n"
                                f"🌐 *Activo:* {nombre_activo}\n"
                                f"🎯 *Estrategia:* {estrategia}\n"
                                f"📈 *Señal:* {res['señal']}\n"
                                f"💵 *Precio:* ${res['precio']:,.2f}\n"
                            )
                            if res.get("rsi"): msj += f"📐 *RSI:* {res['rsi']:.1f}\n"
                            msj += f"\n⚠️ _Se evaluará sola en {horas_eval}h._"
                            enviar_alerta(msj)

            guardar_estado(estado)

        except Exception as e:
            print(f"Error en el ciclo principal: {e}")

        time.sleep(INTERVALO_CICLO_SEG)

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    # 1. Iniciar servidor web para que no se apague
    t = threading.Thread(target=mantener_vivo)
    t.daemon = True
    t.start()

    # 2. ENVIAR MENSAJE DE PRUEBA A TELEGRAM
    time.sleep(3) # Espera 3 segundos para asegurar que todo cargue
    enviar_alerta("✅ *PRUEBA DE CONEXIÓN:* El bot se ha reiniciado correctamente, está conectado a Telegram y vigilando el mercado. 🚀")

    # 3. Iniciar el escaneo de mercado
    ciclo_principal()
