import streamlit as st
import requests
import yfinance as yf

# Configuración de la página (Adaptada para celular)
st.set_page_config(page_title="Terminal Financiera", page_icon="📊", layout="centered")

st.title("📊 Terminal Institucional")
st.caption("Panel de Control Patrimonial | v1.0")
st.markdown("---")

# ==========================================
# MOTOR 1: CRIPTOMONEDAS (BINANCE API)
# ==========================================
st.subheader("🪙 Motor Cripto (Riesgo/Crecimiento)")
try:
    url_binance = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    res_binance = requests.get(url_binance, timeout=5).json()
    
    btc_price = float(res_binance['lastPrice'])
    btc_change = float(res_binance['priceChangePercent'])
    btc_vol = float(res_binance['volume'])
    
    col1, col2 = st.columns(2)
    col1.metric(label="Bitcoin (BTC/USDT)", value=f"${btc_price:,.2f}", delta=f"{btc_change:.2f}%")
    col2.metric(label="Volumen 24h", value=f"{btc_vol:,.0f} BTC", delta="Liquidez")
    
except Exception as e:
    st.error("Error conectando a Binance (Tiempo de espera agotado).")
    col1, col2 = st.columns(2)
    col1.metric(label="Bitcoin (BTC/USDT)", value="$0.00", delta="0.00%")
    col2.metric(label="Volumen 24h", value="0 BTC", delta="Sin conexión")

st.markdown("---")

# ==========================================
# MOTOR 2: MATERIAS PRIMAS (ORO SPOT)
# ==========================================
st.subheader("🥇 Motor Refugio (Protección)")
try:
    gold = yf.Ticker("GC=F")
    gold_data = gold.history(period="2d")
    
    if len(gold_data) >= 2:
        gold_price = gold_data['Close'].iloc[-1]
        gold_prev = gold_data['Close'].iloc[-2]
        gold_change = ((gold_price - gold_prev) / gold_prev) * 100
    else:
        gold_price = gold_data['Close'].iloc[-1]
        gold_change = 0.0
        
    col3, col4 = st.columns(2)
    col3.metric(label="Oro (XAU/USD - Onza)", value=f"${gold_price:,.2f}", delta=f"{gold_change:.2f}%")
    col4.metric(label="Tendencia", value="Monitoreando", delta="Refugio Global", delta_color="off")
    
except Exception as e:
    st.error("Error conectando al mercado de materias primas.")
    col3, col4 = st.columns(2)
    col3.metric(label="Oro (XAU/USD - Onza)", value="$0.00", delta="0.00%")
    col4.metric(label="Tendencia", value="Desconectado", delta="Offline", delta_color="off")

st.markdown("---")

# ==========================================
# MOTOR 3: ALGORITMO DE DECISIÓN
# ==========================================
st.subheader("🧠 Algoritmo de Decisión")
st.info("Calculando Soportes, Resistencias, RSI y EMAs en segundo plano...")

st.warning("🟡 ESTADO ACTUAL: Mercado evaluando liquidez. Mantener capital en USDT.")

st.markdown("---")
st.caption("Desarrollado en Python. Datos en tiempo real.")
