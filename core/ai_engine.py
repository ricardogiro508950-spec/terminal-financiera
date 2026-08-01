# core/ai_engine.py
import pandas as pd
import numpy as np

def calculate_ai_score(df):
    """
    Calcula un puntaje de Inteligencia Artificial (0 a 100) basado en confluencias técnicas:
    RSI, Tendencia de EMAs, y Volumen Relativo (RVOL).
    """
    if df is None or len(df) < 50:
        return 50.0, "Datos insuficientes para análisis de IA", []

    score = 50.0  # Punto neutro base
    razones = []

    # 1. Análisis de Tendencia (EMA 50 vs EMA 200)
    ema_50 = df["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
    ema_200 = df["Close"].ewm(span=200, adjust=False).mean().iloc[-1]
    current_close = df["Close"].iloc[-1]

    if current_close > ema_50 and ema_50 > ema_200:
        score += 20
        razones.append("Tendencia alcista institucional sólida (Precio > EMA 50 > EMA 200).")
    elif current_close < ema_50 and ema_50 < ema_200:
        score -= 20
        razones.append("Tendencia bajista dominante (Precio < EMA 50 < EMA 200).")
    else:
        razones.append("Mercado en rango o transición de tendencia.")

    # 2. Análisis de Momento (RSI 14)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean().iloc[-1]
    avg_loss = loss.rolling(window=14).mean().iloc[-1]
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))

    if 40 <= rsi <= 65:
        score += 15
        razones.append(f"RSI saludable en zona neutral-alcista ({rsi:.1f}).")
    elif rsi > 70:
        score -= 15
        razones.append(f"RSI en zona de sobrecompra extrema ({rsi:.1f}), riesgo de corrección.")
    elif rsi < 30:
        score += 10
        razones.append(f"RSI en sobreventa ({rsi:.1f}), posible rebote técnico.")

    # 3. Análisis de Volumen Relativo (RVOL)
    vol_sma = df["Volume"].rolling(20).mean().iloc[-1]
    current_vol = df["Volume"].iloc[-1]
    rvol = current_vol / vol_sma if vol_sma > 0 else 1.0

    if rvol >= 1.3:
        score += 15
        razones.append(f"Alto volumen institucional detectado (RVOL {rvol:.2f}x).")
    else:
        razones.append(f"Volumen moderado o bajo (RVOL {rvol:.2f}x).")

    # Limitar el score entre 0 y 100 absoluto
    final_score = max(0.0, min(100.0, score))
    
    # Veredicto algorítmico de la IA
    if final_score >= 70:
        veredicto = "🟢 FUERTE COMPRA (Alta Confluencia)"
    elif final_score >= 55:
        veredicto = "🟡 COMPRA MODERADA / VIGILAR"
    elif final_score <= 30:
        veredicto = "🔴 FUERTE VENTA / PRECAUCIÓN"
    else:
        veredicto = "⚪ ZONA NEUTRAL (Esperar confirmación)"

    return round(final_score, 1), veredicto, razones
