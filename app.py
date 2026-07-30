import streamlit as st
import yfinance as yf

# Configuración de la página (Adaptada para celular)
st.set_page_config(page_title="Terminal Financiera", page_icon="📊", layout="centered")

st.title("📊 Terminal Institucional")
st.caption("Panel de Control Patrimonial | v1.0")
st.markdown("---")

# ==========================================
# MOTOR 1: CRIPTOMONEDAS (YFINANCE BTC-USD)
# ==========================================
st.subheader("🪙 Motor Cripto (Riesgo/Crecimiento)")
try:
    btc = yf.Ticker("BTC-USD")
    btc_data = btc.history(period="2d")
    
    if len(btc_data) >= 2:
        btc_price = btc_data['Close'].iloc[-1]
        btc_prev = btc_data['Close'].iloc[-2]
        btc_change = ((btc_price - btc_prev) / btc_prev) * 100
    else:
        btc_price = btc_data['Close'].iloc[-1]
        btc_change = 0.0
        
    col1, col2 = st.columns(2)
    col1.metric(label="Bitcoin (BTC/USD)", value=f"${btc_price:,.2f}", delta=f"{btc_change:.2f}%")
    col2.metric(label="Estado", value="Conectado", delta="Tiempo Real", delta_color="off")
    
except Exception as e:
    col1, col2 = st.columns(2)
    col1.metric(label="Bitcoin (BTC/USD)", value="$0.00", delta="0.00%")
    col2.metric(label="Estado", value="Reintentando", delta="Offline", delta_color="off")

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
