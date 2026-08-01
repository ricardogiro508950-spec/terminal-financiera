# core/pattern_engine.py
import pandas as pd

def detect_candlestick_patterns(df):
    """
    Analiza las últimas velas del DataFrame para detectar patrones clásicos 
    de acción del precio (Martillo, Envolvente, Estrella Fugaz, etc.).
    """
    if df is None or len(df) < 5:
        return "Datos insuficientes para análisis de patrones"

    # Tomamos las últimas 2 o 3 velas para análisis
    c_last = df.iloc[-1]
    c_prev = df.iloc[-2]
    
    body_last = abs(c_last["Close"] - c_last["Open"])
    range_last = c_last["High"] - c_last["Low"]
    upper_wick_last = c_last["High"] - max(c_last["Close"], c_last["Open"])
    lower_wick_last = min(c_last["Close"], c_last["Open"]) - c_last["Low"]

    patrones_detectados = []

    # 1. Detección de Martillo (Hammer) / Pin Bar alcista
    if range_last > 0 and (lower_wick_last >= 2 * body_last) and (upper_wick_last < body_last * 0.5):
        if c_last["Close"] > c_last["Open"]:
            patrones_detectados.append("🟢 Martillo Alcista (Pin Bar de Compra)")
        else:
            patrones_detectados.append("🔴 Hombre Colgado / Pin Bar Bajista")

    # 2. Detección de Estrella Fugaz (Shooting Star)
    if range_last > 0 and (upper_wick_last >= 2 * body_last) and (lower_wick_last < body_last * 0.5):
        patrones_detectados.append("🔴 Estrella Fugaz (Rechazo bajista en zona alta)")

    # 3. Detección de Envolvente (Engulfing)
    prev_body = abs(c_prev["Close"] - c_prev["Open"])
    if c_prev["Close"] < c_prev["Open"] and c_last["Close"] > c_last["Open"]: # Anterior roja, actual verde
        if c_last["Close"] >= c_prev["Open"] and c_last["Open"] <= c_prev["Close"]:
            patrones_detectados.append("🟢 Envolvente Alcista Institucional")
    elif c_prev["Close"] > c_prev["Open"] and c_last["Close"] < c_last["Open"]: # Anterior verde, actual roja
        if c_last["Close"] <= c_prev["Open"] and c_last["Open"] >= c_prev["Close"]:
            patrones_detectados.append("🔴 Envolvente Bajista Institucional")

    if not patrones_detectados:
        return "⚪ Sin patrones de giro críticos en la última vela (Mercado en desarrollo estructural)."
    
 | join(" | ")
