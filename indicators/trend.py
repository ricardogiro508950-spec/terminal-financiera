# indicators/trend.py
import pandas as pd

def calculate_emas(df, short_span=50, long_span=200):
    """Calcula las Medias Móviles Exponenciales (EMA) para el análisis de tendencia."""
    ema_short = df["Close"].ewm(span=short_span, adjust=False).mean()
    ema_long = df["Close"].ewm(span=long_span, adjust=False).mean()
    return ema_short, ema_long
