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
# CONFIGURACIÓN — usa variables de entorno, no escribas el token aquí
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8807352507:AAEI5mhH0Ao-heGHrsBtJVpM6geGtlMTAUo")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8260761627")

ARCHIVO_CSV = "historial_senales_reales.csv"
ARCHIVO_ESTADO = "ultimo_estado.json"

ACTIVOS = {"Bitcoin": "BTC-USD", "Oro": "GC=F", "Petróleo": "CL=F"}
ESTRATEGIAS = ["Confluencia Clásica", "Primera Vela (ORB)", "Cazador de Pullbacks"]

INTERVALO_CICLO_SEG = 900       # revisa cada 15 minutos (no cada 45 seg — evita saturar la API)
UMBRAL_PULLBACK_PCT = 0.35

# Cada estrategia opera en una temporalidad distinta, así que cada una necesita
# su propio tiempo de espera antes de evaluar si la señal acertó:
HORAS_EVALUACION_POR_ESTRATEGIA = {
    "Primera Vela (ORB)": 2,          # usa velas de 15 min -> se resuelve rápido
    "Cazador de Pullbacks": 6,        # usa velas de 1 hora -> tiempo intermedio
    "Confluencia Clásica": 72,        # usa velas de 1 día -> necesita varios días
}

# ==========================================
# SERVIDOR WEB (para mantener vivo en Render/Railway/etc.)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Oculoos Bot de Señales Reales — Activo (sin aleatoriedad, cálculo genuino)."

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
    if not TOKEN or "PON_TU_TOKEN" in TOKEN:
        print("⚠️ No hay TOKEN configurado, no se envía a Telegram. Mensaje:", mensaje)
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=datos, timeout=10)
    except Exception as e:
        print(f"Error enviando alerta: {e}")

# ==========================================
# MATEMÁTICA REAL (idéntica a la de tu app Oculoos)
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

# ==========================================
# ANÁLISIS 1: CONFLUENCIA CLÁSICA (Tendencia + RSI)
# ==========================================
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

# ==========================================
# ANÁLISIS 2: CAZADOR DE PULLBACKS (Rebote EMA 50)
# ==========================================
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
        if dist_pct <= UMBRAL_PULLBACK_PCT and rsi < 75:
            señal = "🟢 COMPRAR (pullback a la EMA50, RSI sano)"
        else:
            señal = "🟡 ESPERAR (todavía lejos de la EMA o RSI alto)"
    else:
        if dist_pct <= UMBRAL_PULLBACK_PCT and rsi > 25:
            señal = "🔴 VENDER (rebote a la EMA50, RSI sano)"
        else:
            señal = "🟡 ESPERAR (todavía lejos de la EMA o RSI bajo)"

    return {"señal": señal, "precio": close, "rsi": rsi, "ema50": ema50, "ema200": ema200}

# ==========================================
# ANÁLISIS 3: PRIMERA VELA (ORB) — vela de 9:30 AM NY
# ==========================================
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
            señal = "🟡 ESPERAR (dentro del rango, sin ruptura)"

        return {"señal": señal, "precio": close, "rsi": None, "ema50": orb_high, "ema200": orb_low}
    except Exception as e:
        print(f"Error ORB {ticker}: {e}")
        return None

# ==========================================
# REGISTRO Y ALERTA
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
            round(resultado["ema200"], 2) if resultado["ema200"] is not None else "",
            "", "", "", "Pendiente"
        ])
    return id_unico

def es_señal_accionable(texto_señal):
    return "COMPRAR" in texto_señal or "VENDER" in texto_señal

# ==========================================
# EVALUACIÓN AUTOMÁTICA (backtesting hacia adelante real)
# ==========================================
def evaluar_señales_pendientes():
    if not os.path.exists(ARCHIVO_CSV):
        return
    try:
        df = pd.read_csv(ARCHIVO_CSV)
    except Exception:
        return

    if df.empty or "Resultado" not in df.columns:
        return

    cambios = False
    ahora = datetime.now()

    for idx, fila in df[df["Resultado"] == "Pendiente"].iterrows():
        try:
            fecha_señal = datetime.strptime(fila["Fecha_Señal"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

        horas_espera = HORAS_EVALUACION_POR_ESTRATEGIA.get(fila["Estrategia"], 4)
        if (ahora - fecha_señal) < timedelta(hours=horas_espera):
            continue  # todavía no ha pasado suficiente tiempo para ESTA estrategia

        ticker = ACTIVOS.get(fila["Activo"])
        if not ticker:
            continue
        precio_hoy = precio_actual(ticker)
        if precio_hoy is None:
            continue

        precio_señal = float(fila["Precio_Señal"])
        variacion_pct = ((precio_hoy - precio_señal) / precio_señal) * 100

        es_compra = "COMPRAR" in str(fila["Señal"])
        es_venta = "VENDER" in str(fila["Señal"])

        if es_compra:
            resultado_final = "✅ Acierto" if variacion_pct > 0 else "❌ Fallo"
        elif es_venta:
            resultado_final = "✅ Acierto" if variacion_pct < 0 else "❌ Fallo"
        else:
            resultado_final = "N/A"

        df.at[idx, "Fecha_Evaluacion"] = ahora.strftime("%Y-%m-%d %H:%M:%S")
        df.at[idx, "Precio_Evaluacion"] = round(precio_hoy, 2)
        df.at[idx, "Variacion_Pct"] = round(variacion_pct, 2)
        df.at[idx, "Resultado"] = resultado_final
        cambios = True

        emoji_res = "✅" if "Acierto" in resultado_final else "❌"
        enviar_alerta(
            f"📋 *EVALUACIÓN DE SEÑAL ({horas_espera}h después)*\n"
            f"🌐 {fila['Activo']} — {fila['Estrategia']}\n"
            f"Señal original: {fila['Señal']}\n"
            f"Precio señal: `${precio_señal:,.2f}` → Precio ahora: `${precio_hoy:,.2f}`\n"
            f"Variación: `{variacion_pct:+.2f}%`\n"
            f"Resultado: {emoji_res} {resultado_final}"
        )

    if cambios:
        df.to_csv(ARCHIVO_CSV, index=False)

# ==========================================
# CICLO PRINCIPAL
# ==========================================
def iniciar_bot():
    inicializar_csv()
    estado_anterior = cargar_estado()

    enviar_alerta(
        "🚀 *Oculoos Bot de Señales Reales — Iniciado*\n"
        "Calcula las 3 estrategias con datos verdaderos de mercado (sin aleatoriedad).\n"
        "Solo avisa cuando una señal CAMBIA. Cada estrategia se evalúa a su propio ritmo:\n"
        "🌅 ORB: 2h | 🧲 Pullbacks: 6h | 📊 Confluencia Clásica: 72h (3 días)"
    )

    while True:
        for activo, ticker in ACTIVOS.items():
            resultados_por_estrategia = {
                "Confluencia Clásica": analizar_confluencia_clasica(ticker),
                "Primera Vela (ORB)": analizar_orb(ticker),
                "Cazador de Pullbacks": analizar_pullback(ticker),
            }

            for estrategia, resultado in resultados_por_estrategia.items():
                if resultado is None:
                    continue

                clave = f"{activo}_{estrategia}"
                señal_actual = resultado["señal"]
                señal_previa = estado_anterior.get(clave)

                if señal_actual != señal_previa:
                    estado_anterior[clave] = señal_actual
                    guardar_estado(estado_anterior)

                    if es_señal_accionable(señal_actual):
                        registrar_señal(activo, estrategia, resultado)
                        rsi_txt = f"{resultado['rsi']:.1f}" if resultado["rsi"] is not None else "N/A"
                        horas_esta_estrategia = HORAS_EVALUACION_POR_ESTRATEGIA.get(estrategia, 4)
                        enviar_alerta(
                            f"📊 *NUEVA SEÑAL DETECTADA*\n\n"
                            f"🌐 *Activo:* {activo}\n"
                            f"🎯 *Estrategia:* {estrategia}\n"
                            f"📈 *Señal:* {señal_actual}\n"
                            f"💵 *Precio:* `${resultado['precio']:,.2f}`\n"
                            f"📐 *RSI:* `{rsi_txt}`\n\n"
                            f"⚠️ Esto es una SEÑAL, no una operación ejecutada. "
                            f"Se evaluará sola en {horas_esta_estrategia}h para ver si acertó."
                        )
                    else:
                        print(f"{clave}: cambió a '{señal_actual}' (no accionable, no se registra ni avisa)")

        evaluar_señales_pendientes()
        time.sleep(INTERVALO_CICLO_SEG)

if __name__ == '__main__':
    hilo_bot = threading.Thread(target=iniciar_bot)
    hilo_bot.start()
    mantener_vivo()
