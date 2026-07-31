import json
import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuración de la página
st.set_page_config(
    page_title="Oculoos Trading v5.42", page_icon="👁️", layout="wide", initial_sidebar_state="expanded"
)

# ==========================================
# INICIALIZACIÓN DE VARIABLES (BLINDAJE DE ERRORES)
# ==========================================
if 'audit_cap' not in st.session_state: st.session_state.audit_cap = 1000.0
if 'audit_rsk' not in st.session_state: st.session_state.audit_rsk = 1.0
if 'audit_sl' not in st.session_state: st.session_state.audit_sl = 5.0
if 'monto_inv_term' not in st.session_state: st.session_state.monto_inv_term = 200.0

if 'sim_estado' not in st.session_state: st.session_state.sim_estado = 'INACTIVO'
if 'sim_balance' not in st.session_state: st.session_state.sim_balance = 10000.0 
if 'sim_pnl_historico' not in st.session_state: st.session_state.sim_pnl_historico = 0.0
if 'sim_rsk_pct' not in st.session_state: st.session_state.sim_rsk_pct = 1.0
if 'sim_sl_pct' not in st.session_state: st.session_state.sim_sl_pct = 5.0
if 'monto_inv_sim' not in st.session_state: st.session_state.monto_inv_sim = 2000.0 

# Funciones de reacción (Callbacks)
def update_monto_term():
    cap = st.session_state.audit_cap
    rsk = st.session_state.audit_rsk
    sl = st.session_state.audit_sl
    if sl > 0: st.session_state.monto_inv_term = (cap * (rsk / 100)) / (sl / 100)

def update_monto_sim():
    bal = st.session_state.sim_balance
    rsk = st.session_state.sim_rsk_pct
    sl = st.session_state.sim_sl_pct
    if sl > 0: st.session_state.monto_inv_sim = (bal * (rsk / 100)) / (sl / 100)

# ==========================================
# FUNCIONES MATEMÁTICAS Y DE DATOS
# ==========================================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=15)
def load_data(interval_type):
    if "5 Minutos" in interval_type: period, yf_interval = "5d", "5m"
    elif "15 Minutos" in interval_type: period, yf_interval = "5d", "15m"
    elif "1 Hora" in interval_type: period, yf_interval = "1mo", "1h"
    elif "4 Horas" in interval_type: period, yf_interval = "2mo", "1h"
    elif "1 Semana" in interval_type: period, yf_interval = "1y", "1wk"
    elif "1 Mes" in interval_type: period, yf_interval = "2y", "1mo"
    else: period, yf_interval = "6mo", "1d"

    tickers = {"Bitcoin": "BTC-USD", "Oro": "GC=F", "DXY (Dólar)": "DX-Y.NYB", "Bonos 10Y": "^TNX"}
    data, history = {}, {}
    for name, ticker in tickers.items():
        try:
            df = yf.Ticker(ticker).history(period=period, interval=yf_interval)
            if not df.empty:
                if "4 Horas" in interval_type:
                    df = df.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                history[name] = df
                current_price = df["Close"].iloc[-1]
                prev_price = df["Close"].iloc[-2] if len(df) >= 2 else current_price
                change = ((current_price - prev_price) / prev_price) * 100
                data[name] = {"price": current_price, "change": change, "low": df["Low"].min(), "high": df["High"].max()}
            else: data[name] = {"price": 0.0, "change": 0.0, "low": 0.0, "high": 0.0}
        except: data[name] = {"price": 0.0, "change": 0.0, "low": 0.0, "high": 0.0}
    return data, history

@st.cache_data(ttl=15)
def load_mtf_data(asset_name):
    ticker = "BTC-USD" if asset_name == "Bitcoin" else "GC=F"
    try:
        df_1d = yf.Ticker(ticker).history(period="3mo", interval="1d")
        df_1h = yf.Ticker(ticker).history(period="1mo", interval="1h")
        df_4h = df_1h.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        return {"1D": df_1d, "4H": df_4h, "1H": df_1h}
    except: return None

# MOTOR DE LA PRIMERA VELA (ORB) - Vela de las 9:30 NY
@st.cache_data(ttl=60)
def get
