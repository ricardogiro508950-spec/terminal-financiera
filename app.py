import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Configuración de la página
st.set_page_config(
    page_title="Terminal Financiera Institucional v3.0", page_icon="📊", layout="wide"
)

st.title("📊 Terminal Financiera Institucional v3.0")
st.caption("Panel Avanzado | Aprendizaje Integrado y Auditoría de Capital")
st.markdown("---")

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

@st.cache_data(ttl=600)
def load_data():
    tickers = {
        "Bitcoin": "BTC-USD",
        "Oro": "GC=F",
        "DXY (Dólar)": "DX-Y.NYB",
        "Bonos 10Y": "^TNX",
    }
    data = {}
    history = {}
    for name, ticker in tickers.items():
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="6mo")
            if not df.empty:
                history[name] = df
                current_price = df["Close"].iloc[-1]
                prev_price = df["Close"].iloc[-2] if len(df) >= 2 else current_price
                change = ((current_price - prev_price) / prev_price) * 100
                data[name] = {"price": current_price, "change": change}
            else:
                data[name] = {"price": 0.0, "change": 0.0}
        except Exception:
            data[name] = {"price": 0.0, "change": 0.0}
    return data, history

market_data, market_history = load_data()

# ==========================================
# BARRA LATERAL: AUDITORÍA Y GESTIÓN DE RIESGO
# ==========================================
st.sidebar.header("🛡️ Auditoría de Capital")
st.sidebar.write("Calcula tu exposición exacta antes de operar.")

capital = st.sidebar.number_input("Capital Total Disponible (USD)", min_value=10.0, value=1000.0, step=100.0, help="El patrimonio total de tu cuenta.")
riesgo_pct = st.sidebar.slider("Riesgo por Operación (%)", 0.5, 5.0, 1.0, 0.5, help="Regla de oro: No arriesgar más del 1% al 2% por operación para preservar liquidez.")
stop_loss_pct = st.sidebar.number_input("Stop-Loss: Distancia de pérdida (%)", min_value=0.1, value=5.0, step=0.5, help="Si el mercado cae este porcentaje, asumes la pérdida y te retiras.")

# Cálculos financieros corporativos
riesgo_usd = capital * (riesgo_pct / 100)
tamano_posicion = riesgo_usd / (stop_loss_pct / 100)

st.sidebar.markdown("### 📊 Flujo de Caja Proyectado (Trade)")
st.sidebar.error(f"**Pérdida Máxima Aceptada:** ${riesgo_usd:.2f} USD")
st.sidebar.success(f"**Compra Máxima Permitida:** ${tamano_posicion:.2f} USD")
st.sidebar.caption("Al igual que en un balance general, nunca comprometas liquidez sin medir el impacto de una pérdida en el patrimonio total.")

# ==========================================
# 1. PANEL MACROECONÓMICO
# ==========================================
st.subheader("🌐 Panel Intermercados y Macroeconomía")

with st.expander("🎓 ¿Cómo interpretar la Macroeconomía? (Haz clic para leer)"):
    st.write("- **Índice Dólar (DXY):** Actúa como un pasivo pesado. Si sube, encarece el capital global y hace caer al Bitcoin y al Oro. Si baja, da alivio y empuja los precios al alza.")
    st.write("- **Bonos (US10Y):** Reflejan el costo de financiarse. Si las tasas superan el 4.5%, hay presión en el mercado porque el dinero seguro rinde bien sin necesidad de arriesgar en cripto.")

col1, col2, col3, col4 = st.columns(4)

btc_info = market_data.get("Bitcoin", {"price": 0, "change": 0})
gold_info = market_data.get("Oro", {"price": 0, "change": 0})
dxy_info = market_data.get("DXY (Dólar)", {"price": 0, "change": 0})
bond_info = market_data.get("Bonos 10Y", {"price": 0, "change": 0})

col1.metric("Bitcoin (BTC/USD)", f"${btc_info['price']:,.2f}", f"{btc_info['change']:.2f}%", help="El activo de mayor riesgo y crecimiento.")
col2.metric("Oro (XAU/USD)", f"${gold_info['price']:,.2f}", f"{gold_info['change']:.2f}%", help="Cobertura histórica contra inflación.")
col3.metric("Índice Dólar (DXY)", f"{dxy_info['price']:,.2f}", f"{dxy_info['change']:.2f}%", help="Fuerza del billete verde frente al mundo.")
col4.metric("Bono 10 Años (US10Y)", f"{bond_info['price']:,.2f}", f"{bond_info['change']:.2f}%", help="Tasa de rendimiento libre de riesgo.")

st.markdown("---")

# ==========================================
# 2. MOTOR TÉCNICO Y GRÁFICOS
# ==========================================
st.subheader("📈 Análisis Cuantitativo & Gráficos Interactivos")

with st.expander("🎓 ¿Cómo leer el Gráfico y los Indicadores?"):
    st.write("- **EMA 200 (Línea Azul):** Es la auditoría de largo plazo. Si el precio está arriba, es territorio de compras (tendencia alcista). Si está abajo, los institucionales están vendiendo (bajista).")
    st.write("- **EMA 50 (Línea Naranja):** Marca el ritmo de mediano plazo.")
    st.write("- **RSI:** Es como el flujo de caja del mercado. Mayor a 70 = Sobrecomprado (caro, a punto de caer). Menor a 30 = Sobrevendido (barato, posible rebote).")

asset_choice = st.selectbox("Seleccione activo para análisis técnico detallado:", ["Bitcoin", "Oro"])

if asset_choice in market_history:
    df_asset = market_history[asset_choice].copy()
    df_asset["EMA_50"] = df_asset["Close"].ewm(span=50, adjust=False).mean()
    df_asset["EMA_200"] = df_asset["Close"].ewm(span=200, adjust=False).mean() if len(df_asset) >= 200 else df_asset["Close"].ewm(span=len(df_asset), adjust=False).mean()
    df_asset["RSI"] = calculate_rsi(df_asset["Close"])

    current_close = df_asset["Close"].iloc[-1]
    current_ema50 = df_asset["EMA_50"].iloc[-1]
    current_ema200 = df_asset["EMA_200"].iloc[-1]
    current_rsi = df_asset["RSI"].iloc[-1]

    t_col1, t_col2, t_col3 = st.columns(3)
    estado_rsi = "Sobrecompra (>70)" if current_rsi > 70 else ("Sobreventa (<30)" if current_rsi < 30 else "Zona Neutral")
    t_col1.metric("RSI (14 períodos)", f"{current_rsi:.2f}", estado_rsi)
    t_col2.metric("EMA 50", f"${current_ema50:,.2f}")
    t_col3.metric("EMA 200", f"${current_ema200:,.2f}")

    # Gráfico de Velas con Plotly
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_asset.index, open=df_asset["Open"], high=df_asset["High"], low=df_asset["Low"], close=df_asset["Close"], name="Precio"))
    fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_50"], line=dict(color="orange", width=1.5), name="EMA 50"))
    fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_200"], line=dict(color="blue", width=1.5), name="EMA 200"))
    
    fig.update_layout(title=f"Acción del Precio e Indicadores - {asset_choice}", yaxis_title="Precio (USD)", xaxis_title="Fecha", template="plotly_white", height=500, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ==========================================
# 3. ALGORITMO DE DECISIÓN (EL VEREDICTO)
# ==========================================
st.subheader("🧠 Algoritmo de Confluencia (El Veredicto)")

with st.expander("🎓 ¿Cómo usar este Veredicto?"):
    st.write("El algoritmo suma los factores técnicos y macroeconómicos. No es una orden de compra infalible, es un **cálculo de probabilidad estadística**. Úsalo como semáforo para autorizar o denegar el uso de tu liquidez calculada en la barra lateral.")

score = 0
reasons = []

if "Bitcoin" in market_history and len(market_history["Bitcoin"]) > 0:
    btc_df = market_history["Bitcoin"]
    btc_close = btc_df["Close"].iloc[-1]
    ema_50_val = btc_df["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
    rsi_val = calculate_rsi(btc_df["Close"]).iloc[-1]

    if btc_close > ema_50_val:
        score += 1
        reasons.append("✔ Precio sobre la EMA de 50 (Estructura favorable)")
    else:
        score -= 1
        reasons.append("✖ Precio bajo la EMA de 50 (Estructura débil)")

    if 40 <= rsi_val <= 60:
        score += 1
        reasons.append("✔ RSI en rango neutral (Saludable)")
    elif rsi_val > 70:
        score -= 1
        reasons.append("⚠ RSI Sobrecomprado (Riesgo de caída)")
    elif rsi_val < 30:
        score += 1
        reasons.append("✔ RSI Sobrevendido (Posible oportunidad)")

dxy_change = dxy_info["change"]
if dxy_change < 0:
    score += 1
    reasons.append("✔ Dólar a la baja (Macro a favor)")
else:
    score -= 1
    reasons.append("✖ Dólar al alza (Macro en contra)")

st.markdown(f"**Puntuación:** `{score}/3`")
for r in reasons:
    st.write(r)

if score >= 2:
    st.success("🟢 **ESTADO VERDE:** Probabilidad a favor. Revisa la barra lateral para calcular tu posición y autorizar despliegue de capital.")
elif score == 1:
    st.warning("🟡 **ESTADO AMARILLO:** Señales mixtas. Evita la exposición riesgosa y mantén la mayor parte de tu patrimonio en reserva (USDT).")
else:
    st.error("🔴 **ESTADO ROJO:** Probabilidades en contra. Cierre de operaciones especulativas; priorizar defensa del balance general.")
