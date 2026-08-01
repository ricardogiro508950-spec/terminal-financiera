# indicators/momentum.py
import pandas as pd

def calculate_macd(df, fast=12, slow=26, signal=9):
    """Calcula el indicador de momento MACD y su línea de señal."""
    exp1 = df["Close"].ewm(span=fast, adjust=False).mean()
    exp2 = df["Close"].ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
