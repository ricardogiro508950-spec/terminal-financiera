import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Configuración de la página
st.set_page_config(
    page_title="Terminal Financiera Institucional v3.1", page_icon="📊", layout="wide"
)

st.title("📊 Terminal Financiera Institucional v3.1")
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

capital = st.sidebar.number_input("Capital Total Disponible (USD)", min_value=10.0, value=1000.0, step=100.0)
riesgo_pct = st.sidebar.slider("Riesgo por Operación (%)", 0.5, 5.0, 1.0, 0.5)
stop_loss_pct = st.sidebar.number_input("Stop-Loss: Distancia de pérdida (%)", min_value=0.1, value=5.0, step=0.5)

riesgo_usd = capital * (riesgo_pct / 100)
tamano_posicion = riesgo_usd / (stop_loss_pct / 100) if stop_loss_pct > 0 else 0

st.sidebar.markdown("### 📊 Flujo de Caja Proyectado")
st.sidebar.error(f"**Pérdida Máxima Aceptada:** ${riesgo_usd:.2f} USD")
st.sidebar.success(f"**Compra Máxima Permitida:** ${tamano_posicion:.2f} USD")
st.sidebar.caption("Regla institucional: Nunca comprometas liquidez sin medir el impacto de una pérdida en el patrimonio total.")

# ==========================================
# 1. PANEL MACROECONÓMICO
# ==========================================
st.subheader("🌐 Panel Intermercados y Macroeconomía")

with st.expander("🎓 ¿Cómo interpretar la Macroeconomía? (Haz clic para leer)"):
    st.write("- **Índice Dólar (DXY):** Si sube, encarece el capital global y hace caer al Bitcoin. Si baja, empuja los precios al alza.")
    st.write("- **Bonos (US10Y):** Reflejan el costo de financiarse. Tasas altas son malas para el riesgo.")

col1, col2, col3, col4 = st.columns(4)

btc_info = market_data.get("Bitcoin", {"price": 0, "change": 0})
gold_info = market_data.get("Oro", {"price": 0, "change": 0})
dxy_info = market_data.get("DXY (Dólar)", {"price": 0, "change": 0})
bond_info = market_data.get("Bonos 10Y", {"price": 0, "change": 0})

col1.metric("Bitcoin (BTC/USD)", f"${btc_info['price']:,.2f}", f"{btc_info['change']:.2f}%")
col2.metric("Oro (XAU/USD)", f"${gold_info['price']:,.2f}", f"{gold_info['change']:.2f}%")
col3.metric("Índice Dólar (DXY)", f"{dxy_info['price']:,.2f}", f"{dxy_info['change']:.2f}%")
col4.metric("Bono 10 Años (US10Y)", f"{bond_info['price']:,.2f}", f"{bond_info['change']:.2f}%")

st.markdown("---")

# ==========================================
# 2. MOTOR TÉCNICO Y GRÁFICOS
# ==========================================
st.subheader("📈 Análisis Cuantitativo & Gráficos Interactivos")

asset_choice = st.selectbox("Seleccione activo para análisis técnico detallado:", ["Bitcoin", "Oro"])

current_close = 0
current_ema50 = 0
current_ema200 = 0
current_rsi = 50

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
# 3. TRADUCTOR DEL MERCADO EN VIVO (NUEVO)
# ==========================================
st.subheader("📝 Traductor del Mercado en Vivo")
st.write("¿Qué significan los números de arriba en este exacto momento?")

# Traducción del Dólar
dxy_change = dxy_info["change"]
if dxy_change < 0:
    st.markdown(f"*   🟢 **El Viento a Favor (Macro):** El Índice Dólar está cayendo (`{dxy_change:.2f}%`). Esto es **BUENO**. Inyecta liquidez y facilita que activos como Bitcoin y Oro suban de precio.")
else:
    st.markdown(f"*   🔴 **El Viento en Contra (Macro):** El Índice Dólar está subiendo (`+{dxy_change:.2f}%`). Esto es **MALO**. Encarece el capital y asfixia a los activos de riesgo.")

# Traducción de los Bonos
bond_change = bond_info["change"]
if bond_change < 0:
    st.markdown(f"*   🟢 **Tasas de Interés:** El Bono a 10 Años cae (`{bond_change:.2f}%`). **BUENO**. El dinero seguro rinde menos, lo que empuja a los grandes inversores a comprar cripto.")
else:
    st.markdown(f"*   🔴 **Tasas de Interés:** El Bono a 10 Años sube (`+{bond_change:.2f}%`). **MALO**. Hay presión en el mercado porque el dinero seguro está pagando bien sin riesgo.")

# Traducción del RSI
if current_rsi > 70:
    st.markdown(f"*   🔴 **Salud del Movimiento:** RSI en `{current_rsi:.2f}`. **PELIGRO**. El activo está sobrecomprado, la gente está eufórica y es muy probable una caída brusca.")
elif current_rsi < 30:
    st.markdown(f"*   🟢 **Salud del Movimiento:** RSI en `{current_rsi:.2f}`. **OPORTUNIDAD**. El activo está sobrevendido por pánico extremo. Podría rebotar pronto.")
else:
    st.markdown(f"*   🟡 **Salud del Movimiento:** RSI en `{current_rsi:.2f}`. **SANO**. Está subiendo/bajando de forma orgánica, sin euforia ni desesperación extrema.")

# Traducción de la Batalla Técnica (Precio vs EMA 50)
if current_close > current_ema50:
    st.markdown(f"*   🟢 **La Batalla en las Trincheras:** El precio (`${current_close:,.2f}`) ha superado la línea naranja EMA 50 (`${current_ema50:,.2f}`). **BUENO**. Demuestra fuerza alcista a corto plazo.")
else:
    st.markdown(f"*   🔴 **La Batalla en las Trincheras:** El precio (`${current_close:,.2f}`) está atrapado debajo de la línea naranja EMA 50 (`${current_ema50:,.2f}`). **PRECAUCIÓN**. La línea naranja funciona como un 'techo' de concreto que aún no puede romper.")

st.markdown("---")

# ==========================================
# 4. ALGORITMO DE DECISIÓN (EL VEREDICTO)
# ==========================================
st.subheader("🧠 Algoritmo de Confluencia (El Veredicto Final)")

score = 0
if current_close > current_ema50: score += 1
else: score -= 1

if 40 <= current_rsi <= 60: score += 1
elif current_rsi > 70: score -= 1
elif current_rsi < 30: score += 1

if dxy_change < 0: score += 1
else: score -= 1

st.markdown(f"**Puntuación:** `{score}/3`")

if score >= 2:
    st.success("🟢 **ESTADO VERDE:** Semáforo en verde. Tienes probabilidades estadísticas a tu favor. Si decides operar, revisa tu 'Compra Máxima Permitida' en la barra lateral.")
elif score == 1:
    st.warning("🟡 **ESTADO AMARILLO:** Señales divididas (mercado dudoso). Mejor esperar a que haya más fuerza o mantener el capital seguro en dólares (USDT).")
else:
    st.error("🔴 **ESTADO ROJO:** Riesgo extremo. Probabilidades en contra. Prohibido comprar. Priorizar la defensa del balance general.")
