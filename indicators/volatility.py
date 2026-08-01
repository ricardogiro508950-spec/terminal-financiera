# indicators/volatility.py
import pandas as pd

def calculate_bollinger_bands(df, window=20, num_std=2.0):
    """Calcula las Bandas de Bollinger para medir la expansión y contracción de la volatilidad."""
    middle_band = df["Close"].rolling(window=window).mean()
    std_dev = df["Close"].rolling(window=window).std()
    upper_band = middle_band + (std_dev * num_std)
    lower_band = middle_band - (std_dev * num_std)
    return upper_band, middle_band, lower_band
