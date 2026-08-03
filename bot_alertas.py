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
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

ARCHIVO_CSV = "historial_senales_reales.csv"
ARCHIVO_ESTADO = "ultimo_estado.json"
ARCHIVO_CAPITAL = "capital_por_estrategia.json"

CAPITAL_INICIAL_POR_ESTRATEGIA = 1000.0   # dinero de PAPEL, no real
MONTO_POR_SEÑAL = 100.0                    # monto simulado que "invierte" en cada señal

ACTIVOS = {"Bitcoin": "BTC-USD", "Oro": "GC=F", "Petróleo": "CL=F"}
ESTRATEGIAS = [
    "Confluencia Clásica", "Primera Vela (ORB)", "Cazador de Pullbacks",
    "Confluencia Gann + Fibonacci", "Confluencia Profesional (Velas+Estructura+Fibo)",
]

# 5 minutos es el máximo detalle real que tiene sentido: revisar "cada segundo" no sirve
# porque Yahoo Finance no actualiza tan rápido y además bloquea por exceso de peticiones.
INTERVALO_CICLO_SEG = 300
UMBRAL_PULLBACK_PCT = 0.35

# Cada estrategia opera en una temporalidad distinta, así que cada una necesita
# su propio tiempo de espera antes de evaluar si la señal acertó:
HORAS_EVALUACION_POR_ESTRATEGIA = {
    "Primera Vela (ORB)": 2,                                     # velas de 15 min -> se resuelve rápido
    "Cazador de Pullbacks": 6,                                   # velas de 1 hora -> tiempo intermedio
    "Confluencia Clásica": 72,                                   # velas de 1 día -> necesita varios días
    "Confluencia Gann + Fibonacci": 72,                          # rango de velas diarias
    "Confluencia Profesional (Velas+Estructura+Fibo)": 72,       # rango de velas diarias
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
# ANÁLISIS 4: CONFLUENCIA GANN + FIBONACCI
# ==========================================
def analizar_gann_fibonacci(ticker):
    """
    Divide el rango de las últimas 50 velas diarias en niveles de Gann (0/0.5/1)
    y Fibonacci (0/0.5/0.618/0.85/0.95/1). El nivel 0.5 coincide en ambos sistemas
    (mayor peso según el material de referencia). La zona 85-95% de Fibonacci es
    la otra zona de reversión que se marca en el documento.

    NOTA HONESTA: no se detecta "Order Block" (mencionado en el material original)
    porque no tiene una regla matemática precisa y verificable — en su lugar se usa
    RSI en zona extrema como confirmación real.
    """
    df = obtener_historico(ticker, period="3mo", interval="1d")
    if df is None or len(df) < 30:
        return None

    ventana = df.tail(50)
    high = ventana["High"].max()
    low = ventana["Low"].min()
    rango = high - low
    if rango <= 0:
        return None

    close = df["Close"].iloc[-1]
    rsi = calculate_rsi(df["Close"]).iloc[-1]

    nivel_05 = low + 0.5 * rango                 # Gann 0.5 = Fibonacci 0.5 (coinciden)
    zona_fib_85 = low + 0.85 * rango
    zona_fib_95 = low + 0.95 * rango

    tolerancia = rango * 0.02  # 2% del rango como margen de "cerca del nivel"
    cerca_del_medio = abs(close - nivel_05) <= tolerancia
    en_zona_85_95 = zona_fib_85 <= close <= zona_fib_95 + tolerancia

    if en_zona_85_95 and rsi > 70:
        señal = "🔴 VENDER (zona de reversión 85-95% Fibonacci + RSI sobrecomprado)"
    elif cerca_del_medio and rsi < 35:
        señal = "🟢 COMPRAR (zona de interés 0.5 Gann/Fibonacci + RSI sobrevendido)"
    else:
        señal = "🟡 ESPERAR (sin confluencia clara en este momento)"

    return {
        "señal": señal, "precio": close, "rsi": rsi,
        "ema50": nivel_05, "ema200": None,
    }


# ==========================================
# ANÁLISIS 5: CONFLUENCIA PROFESIONAL (Velas + Estructura + Fibonacci + Volumen)
# Basado en el material de referencia: estructura de mercado, niveles psicológicos,
# Fibonacci clásico, patrones de velas japonesas y confirmación de volumen simple.
# ==========================================

def calcular_estructura(df, ventana=30):
    """Detecta si los últimos pivotes forman máximos/mínimos crecientes (alcista),
    decrecientes (bajista), o ninguno claro (lateral)."""
    sub = df.tail(ventana)
    highs = sub["High"].values
    lows = sub["Low"].values
    pivot_highs, pivot_lows = [], []

    for i in range(2, len(highs) - 2):
        if highs[i] == max(highs[i - 2:i + 3]):
            pivot_highs.append(highs[i])
        if lows[i] == min(lows[i - 2:i + 3]):
            pivot_lows.append(lows[i])

    if len(pivot_highs) >= 2 and len(pivot_lows) >= 2:
        hh = pivot_highs[-1] > pivot_highs[-2]
        hl = pivot_lows[-1] > pivot_lows[-2]
        lh = pivot_highs[-1] < pivot_highs[-2]
        ll = pivot_lows[-1] < pivot_lows[-2]
        if hh and hl:
            return "Alcista (HH/HL)"
        elif lh and ll:
            return "Bajista (LH/LL)"
    return "Lateral/Mixta"

def nivel_psicologico_cercano(precio):
    """Redondea al nivel psicológico (número 'redondo') más cercano y calcula la distancia %."""
    if precio <= 0:
        return 0, 999
    magnitud = 10 ** (len(str(int(precio))) - 1)
    paso = magnitud / 2 if magnitud >= 10 else 1
    nivel = round(precio / paso) * paso
    distancia_pct = abs(precio - nivel) / precio * 100
    return nivel, distancia_pct

def calcular_fibonacci_clasico(df, ventana=50):
    """Niveles clásicos 38.2% / 50% / 61.8% sobre el rango de las últimas N velas."""
    sub = df.tail(ventana)
    high, low = sub["High"].max(), sub["Low"].min()
    rango = high - low
    if rango <= 0:
        return None
    niveles = {
        "38.2%": high - 0.382 * rango,
        "50%": high - 0.5 * rango,
        "61.8%": high - 0.618 * rango,
    }
    return niveles, high, low

def detectar_patron_vela(df):
    """Reconoce 6 patrones de vela con reglas geométricas reales (cuerpo/mecha/contexto).
    Devuelve (nombre_patron, direccion) donde direccion es Compra/Venta/Neutral."""
    if len(df) < 6:
        return "Datos insuficientes", "Neutral"

    def datos(v):
        o, c, h, l = v["Open"], v["Close"], v["High"], v["Low"]
        cuerpo = abs(c - o)
        rango = (h - l) if (h - l) > 0 else 0.0001
        mecha_sup = h - max(o, c)
        mecha_inf = min(o, c) - l
        return o, c, cuerpo, rango, mecha_sup, mecha_inf

    v0, v1, v2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
    o0, c0, cuerpo0, rango0, mecha_sup0, mecha_inf0 = datos(v0)
    o1, c1, cuerpo1, rango1, _, _ = datos(v1)

    tendencia_previa = "alcista" if df["Close"].iloc[-2] > df["Close"].iloc[-6] else "bajista"

    if cuerpo0 <= rango0 * 0.05:
        return "Doji", "Neutral"

    if cuerpo0 <= rango0 * 0.3 and mecha_inf0 >= cuerpo0 * 2 and mecha_sup0 <= rango0 * 0.1:
        return ("Martillo", "Compra") if tendencia_previa == "bajista" else ("Hombre Colgado", "Venta")

    if cuerpo0 <= rango0 * 0.3 and mecha_sup0 >= cuerpo0 * 2 and mecha_inf0 <= rango0 * 0.1:
        return ("Estrella Fugaz", "Venta") if tendencia_previa == "alcista" else ("Martillo Invertido", "Compra")

    vela0_verde, vela0_roja = c0 > o0, c0 < o0
    vela1_roja, vela1_verde = c1 < o1, c1 > o1

    if vela0_verde and vela1_roja and o0 <= c1 and c0 >= o1:
        return "Envolvente Alcista", "Compra"
    if vela0_roja and vela1_verde and o0 >= c1 and c0 <= o1:
        return "Envolvente Bajista", "Venta"

    o2, c2, cuerpo2, rango2, _, _ = datos(v2)
    punto_medio2 = (o2 + c2) / 2
    if c2 < o2 and cuerpo1 <= rango1 * 0.3 and vela0_verde and c0 > punto_medio2:
        return "Estrella de la Mañana", "Compra"
    if c2 > o2 and cuerpo1 <= rango1 * 0.3 and vela0_roja and c0 < punto_medio2:
        return "Estrella de la Tarde", "Venta"

    return "Sin patrón claro", "Neutral"

def volumen_confirmado(df):
    """Confirmación simple de volumen (NO es el Perfil de Volumen completo — eso
    requiere datos de tick que no tenemos disponibles honestamente)."""
    if "Volume" not in df.columns or len(df) < 20:
        return False
    vol_actual = df["Volume"].iloc[-1]
    vol_prom = df["Volume"].tail(20).mean()
    return bool(vol_prom and vol_actual > vol_prom * 1.1)

def analizar_confluencia_profesional(ticker):
    df = obtener_historico(ticker, period="6mo", interval="1d")
    if df is None or len(df) < 60:
        return None

    close = df["Close"].iloc[-1]
    estructura = calcular_estructura(df)
    nivel_psico, dist_psico_pct = nivel_psicologico_cercano(close)
    fib_resultado = calcular_fibonacci_clasico(df)
    patron, direccion_patron = detectar_patron_vela(df)
    vol_ok = volumen_confirmado(df)

    puntos_alcista, puntos_bajista = 0, 0
    detalles = []

    if "Alcista" in estructura:
        puntos_alcista += 1
        detalles.append("Estructura alcista (HH/HL)")
    elif "Bajista" in estructura:
        puntos_bajista += 1
        detalles.append("Estructura bajista (LH/LL)")

    if dist_psico_pct <= 1.0:
        detalles.append(f"Cerca de nivel psicológico ${nivel_psico:,.2f}")

    if fib_resultado:
        niveles, hi, lo = fib_resultado
        punto_medio_rango = (hi + lo) / 2
        for nombre, valor in niveles.items():
            if abs(close - valor) <= (hi - lo) * 0.02:
                detalles.append(f"Cerca de Fibonacci {nombre}")
                # Nota: esta dirección es una interpretación propia (no una regla literal
                # del material) — retroceso en la mitad superior del rango = sesgo bajista,
                # en la mitad inferior = sesgo alcista.
                if close > punto_medio_rango:
                    puntos_bajista += 1
                else:
                    puntos_alcista += 1

    if direccion_patron == "Compra":
        puntos_alcista += 1
        detalles.append(f"Patrón de vela: {patron}")
    elif direccion_patron == "Venta":
        puntos_bajista += 1
        detalles.append(f"Patrón de vela: {patron}")

    if vol_ok:
        detalles.append("Volumen por encima del promedio")
        if puntos_alcista > puntos_bajista:
            puntos_alcista += 1
        elif puntos_bajista > puntos_alcista:
            puntos_bajista += 1

    score_texto = f"{puntos_alcista} a favor / {puntos_bajista} en contra"

    if puntos_alcista >= 3 and puntos_alcista > puntos_bajista:
        señal = f"🟢 COMPRAR (confluencia profesional: {score_texto})"
    elif puntos_bajista >= 3 and puntos_bajista > puntos_alcista:
        señal = f"🔴 VENDER (confluencia profesional: {score_texto})"
    else:
        señal = f"🟡 ESPERAR (sin confluencia suficiente: {score_texto})"

    return {"señal": señal, "precio": close, "rsi": None, "ema50": nivel_psico, "ema200": None}


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
    capital = cargar_capital()

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

        # Ganancia/pérdida en $ de PAPEL: % de variación real aplicado a un monto fijo.
        # Esto funciona igual de bien para Bitcoin, Oro o Petróleo porque usa % real,
        # no una fórmula de "pips" que solo tiene sentido en forex.
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
            f"Resultado: {emoji_res} {resultado_final}\n"
            f"💵 Ganancia/Pérdida (papel): `{ganancia_usd:+.2f} USD`"
        )

    if cambios:
        df.to_csv(ARCHIVO_CSV, index=False)
        guardar_capital(capital)

def enviar_resumen_capital():
    """Envía cada ciclo un resumen del capital de papel por estrategia."""
    capital = cargar_capital()
    capital_inicial_total = CAPITAL_INICIAL_POR_ESTRATEGIA * len(ESTRATEGIAS)
    capital_actual_total = sum(capital.get(est, CAPITAL_INICIAL_POR_ESTRATEGIA) for est in ESTRATEGIAS)
    ganancia_total = capital_actual_total - capital_inicial_total

    lineas = ["📊 *RESUMEN DE CAPITAL (PAPEL, NO REAL)*", ""]
    for est in ESTRATEGIAS:
        actual = capital.get(est, CAPITAL_INICIAL_POR_ESTRATEGIA)
        diferencia = actual - CAPITAL_INICIAL_POR_ESTRATEGIA
        pct = (diferencia / CAPITAL_INICIAL_POR_ESTRATEGIA) * 100
        emoji = "🟢" if diferencia > 0 else ("🔴" if diferencia < 0 else "⚪")
        lineas.append(f"{emoji} {est}: `${actual:,.2f}` ({diferencia:+.2f} | {pct:+.1f}%)")

    lineas.append("")
    lineas.append(f"💰 Capital inicial total: `${capital_inicial_total:,.2f}`")
    lineas.append(f"💰 Capital actual total: `${capital_actual_total:,.2f}`")
    lineas.append(f"📈 Ganancia/Pérdida total: `{ganancia_total:+.2f} USD`")
    lineas.append("")
    lineas.append("⚠️ Esto es dinero SIMULADO para comparar estrategias — no es tu dinero real.")

    enviar_alerta("\n".join(lineas))

# ==========================================
# CICLO PRINCIPAL
# ==========================================
def iniciar_bot():
    inicializar_csv()
    estado_anterior = cargar_estado()
    guardar_capital(cargar_capital())  # crea el archivo de capital si no existe

    enviar_alerta(
        "🚀 *Oculoos Bot de Señales Reales — Iniciado*\n"
        "Calcula 5 estrategias con datos verdaderos de mercado (sin aleatoriedad).\n"
        "Solo avisa cuando una señal CAMBIA. Cada estrategia se evalúa a su propio ritmo:\n"
        "🌅 ORB: 2h | 🧲 Pullbacks: 6h | 📊 Confluencia Clásica: 72h | 📐 Gann+Fibonacci: 72h | "
        "🕯️ Confluencia Profesional: 72h\n\n"
        f"💰 Cada estrategia arranca con ${CAPITAL_INICIAL_POR_ESTRATEGIA:,.2f} de papel. "
        "Recibirás un resumen de capital cada 5 minutos."
    )

    while True:
        for activo, ticker in ACTIVOS.items():
            resultados_por_estrategia = {
                "Confluencia Clásica": analizar_confluencia_clasica(ticker),
                "Primera Vela (ORB)": analizar_orb(ticker),
                "Cazador de Pullbacks": analizar_pullback(ticker),
                "Confluencia Gann + Fibonacci": analizar_gann_fibonacci(ticker),
                "Confluencia Profesional (Velas+Estructura+Fibo)": analizar_confluencia_profesional(ticker),
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
        enviar_resumen_capital()
        time.sleep(INTERVALO_CICLO_SEG)

if __name__ == '__main__':
    hilo_bot = threading.Thread(target=iniciar_bot)
    hilo_bot.start()
    mantener_vivo()
