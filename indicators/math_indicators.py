# indicators/math_indicators.py
import pandas as pd

def calculate_rsi(series, period=14):
    """Calcula el Índice de Fuerza Relativa (RSI) para medir el momento."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_atr(high, low, close, period=14):
    """Calcula el Rango Verdadero Promedio (ATR) para medir la volatilidad real."""
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr
