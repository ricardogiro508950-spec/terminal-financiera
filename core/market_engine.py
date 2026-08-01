# core/market_engine.py
import pandas as pd
import yfinance as yf
import streamlit as st
from utils.config import TICKER_MAP
from utils.logger import log

@st.cache_data(ttl=15)
def load_data(interval_type):
    """Descarga los datos del mercado en tiempo real según la temporalidad."""
    log.info(f"Descargando datos para el intervalo: {interval_type}")
    
    if "5 Minutos" in interval_type: period, yf_interval = "5d", "5m"
    elif "15 Minutos" in interval_type: period, yf_interval = "5d", "15m"
    elif "1 Hora" in interval_type: period, yf_interval = "1mo", "1h"
    elif "4 Horas" in interval_type: period, yf_interval = "2mo", "1h"
    elif "1 Semana" in interval_type: period, yf_interval = "1y", "1wk"
    elif "1 Mes" in interval_type: period, yf_interval = "2y", "1mo"
    else: period, yf_interval = "6mo", "1d"

    data, history = {}, {}
    for name, ticker in TICKER_MAP.items():
        try:
            df = yf.Ticker(ticker).history(period=period, interval=yf_interval)
            if not df.empty:
                if "4 Horas" in interval_type:
                    df = df.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                history[name] = df
                current_price = df["Close"].iloc[-1]
                prev_price = df["Close"].iloc[-2] if len(df) >= 2 else current_price
                change = ((current_price - prev_price) / prev_price) * 100
                low_period, high_period = df["Low"].min(), df["High"].max()
                volume_latest = df["Volume"].iloc[-1] if "Volume" in df.columns else 0
                
                data[name] = {
                    "price": current_price, "change": change, 
                    "low": low_period, "high": high_period, "volume": volume_latest
                }
            else:
                data[name] = {"price": 0.0, "change": 0.0, "low": 0.0, "high": 0.0, "volume": 0.0}
        except Exception as e:
            log.error(f"Error cargando {name}: {e}")
            data[name] = {"price": 0.0, "change": 0.0, "low": 0.0, "high": 0.0, "volume": 0.0}
            
    return data, history

@st.cache_data(ttl=15)
def load_mtf_data(asset_name):
    """Carga los datos Multi-Temporalidad para la Matriz Institucional (ICT)."""
    ticker = TICKER_MAP.get(asset_name, "BTC-USD")
    try:
        df_1d = yf.Ticker(ticker).history(period="3mo", interval="1d")
        df_1h = yf.Ticker(ticker).history(period="1mo", interval="1h")
        df_4h = df_1h.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        return {"1D": df_1d, "4H": df_4h, "1H": df_1h}
    except Exception as e:
        log.error(f"Error en MTF Data para {asset_name}: {e}")
        return None

@st.cache_data(ttl=60)
def get_orb_levels(asset_name):
    """Calcula los niveles de la Primera Vela (Opening Range Breakout)."""
    try:
        ticker = TICKER_MAP.get(asset_name, "BTC-USD")
        df = yf.Ticker(ticker).history(period="5d", interval="15m")
        if df.empty: return None, None, None

        if asset_name in ["Oro", "Petróleo"]:
            if df.index.tz is None: df.index = df.index.tz_localize('UTC')
            df.index = df.index.tz_convert('America/New_York')
            df_open = df[(df.index.hour == 9) & (df.index.minute == 30)]
            origen = "Apertura NY (9:30 AM EST)"
        else:
            if df.index.tz is not None: df.index = df.index.tz_convert('UTC')
            else: df.index = df.index.tz_localize('UTC')
            df_open = df[(df.index.hour == 0) & (df.index.minute == 0)]
            origen = "Apertura Diaria Global (00:00 UTC)"

        if not df_open.empty:
            last_open = df_open.iloc[-1]
            return last_open['High'], last_open['Low'], origen
        return None, None, None
    except Exception as e:
        log.error(f"Error calculando ORB para {asset_name}: {e}")
        return None, None, None
