import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Configuración de la página
st.set_page_config(
    page_title="Terminal Financiera Institucional v4.0", page_icon="📊", layout="wide"
)

st.title("📊 Terminal Financiera Institucional v4.0")
st.caption("Panel Avanzado | Aprendizaje, Auditoría y Gestión de Portafolio en Vivo")
st.markdown("---")

# ==========================================
# INICIALIZAR MEMORIA DEL PORTAFOLIO
# ==========================================
if 'trades' not in st.session_state:
    st.session_state.trades = pd.DataFrame(columns=["Activo", "Tipo", "Cantidad", "Precio_Entrada", "Inversion_Inicial_USD"])

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

    # Gráfico
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_asset.index, open=df_asset["Open"], high=df_asset["High"], low=df_asset["Low"], close=df_asset["Close"], name="Precio"))
    fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_50"], line=dict(color="orange", width=1.5), name="EMA 50"))
    fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_200"], line=dict(color="blue", width=1.5), name="EMA 200"))
    
    fig.update_layout(title=f"Acción del Precio e Indicadores - {asset_choice}", yaxis_title="Precio (USD)", xaxis_title="Fecha", template="plotly_white", height=500, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ==========================================
# 3. TRADUCTOR DEL MERCADO EN VIVO
# ==========================================
st.subheader("📝 Traductor del Mercado en Vivo")

dxy_change = dxy_info["change"]
if dxy_change < 0:
    st.markdown(f"*   🟢 **El Viento a Favor (Macro):** El Índice Dólar cae (`{dxy_change:.2f}%`). **BUENO**. Inyecta liquidez a los activos de riesgo.")
else:
    st.markdown(f"*   🔴 **El Viento en Contra (Macro):** El Índice Dólar sube (`+{dxy_change:.2f}%`). **MALO**. Encarece el capital.")

bond_change = bond_info["change"]
if bond_change < 0:
    st.markdown(f"*   🟢 **Tasas de Interés:** El Bono a 10 Años cae (`{bond_change:.2f}%`). **BUENO** para los activos especulativos.")
else:
    st.markdown(f"*   🔴 **Tasas de Interés:** El Bono a 10 Años sube (`+{bond_change:.2f}%`). **MALO** para el riesgo.")

if current_rsi > 70:
    st.markdown(f"*   🔴 **Salud del Movimiento:** RSI en `{current_rsi:.2f}`. **PELIGRO**. Sobrecomprado, posible corrección.")
elif current_rsi < 30:
    st.markdown(f"*   🟢 **Salud del Movimiento:** RSI en `{current_rsi:.2f}`. **OPORTUNIDAD**. Sobrevendido, posible rebote.")
else:
    st.markdown(f"*   🟡 **Salud del Movimiento:** RSI en `{current_rsi:.2f}`. **SANO**. Subiendo o bajando de forma orgánica.")

if current_close > current_ema50:
    st.markdown(f"*   🟢 **Batalla Técnica:** Precio arriba de la EMA 50. **BUENO**. Fuerza alcista.")
else:
    st.markdown(f"*   🔴 **Batalla Técnica:** Precio atrapado debajo de la EMA 50. **PRECAUCIÓN**. Resistencia activa.")

st.markdown("---")

# ==========================================
# 4. ALGORITMO DE DECISIÓN (EL VEREDICTO)
# ==========================================
st.subheader("🧠 Algoritmo de Confluencia")

score = 0
if current_close > current_ema50: score += 1
else: score -= 1
if 40 <= current_rsi <= 60: score += 1
elif current_rsi > 70: score -= 1
elif current_rsi < 30: score += 1
if dxy_change < 0: score += 1
else: score -= 1

if score >= 2:
    st.success("🟢 **ESTADO VERDE:** Probabilidades a favor. Mercado propicio.")
elif score == 1:
    st.warning("🟡 **ESTADO AMARILLO:** Señales divididas. Mercado dudoso, mantén liquidez.")
else:
    st.error("🔴 **ESTADO ROJO:** Riesgo extremo. Probabilidades en contra. No operar.")

st.markdown("---")

# ==========================================
# 5. BITÁCORA DE OPERACIONES Y PORTAFOLIO EN VIVO
# ==========================================
st.subheader("💼 Mi Portafolio y Bitácora de Trading")
st.write("Registra tus compras aquí. El sistema cruzará tus datos con el mercado en vivo para calcular tus ganancias o pérdidas reales.")

# Formulario para registrar una nueva operación
with st.form("registro_operacion", clear_on_submit=True):
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        nuevo_activo = st.selectbox("Activo", ["Bitcoin", "Oro"])
    with col_b:
        nuevo_tipo = st.selectbox("Tipo", ["Compra"]) # Simplificado a compras por ahora
    with col_c:
        nueva_cantidad = st.number_input("Cantidad de monedas/onzas", min_value=0.00001, format="%.5f")
    with col_d:
        precio_actual = btc_info['price'] if nuevo_activo == "Bitcoin" else gold_info['price']
        nuevo_precio = st.number_input("Precio de Compra (USD)", value=float(precio_actual), min_value=0.1)
    
    submit_trade = st.form_submit_button("➕ Registrar Operación")
    
    if submit_trade and nueva_cantidad > 0:
        inversion = nueva_cantidad * nuevo_precio
        nueva_fila = pd.DataFrame([{
            "Activo": nuevo_activo, 
            "Tipo": nuevo_tipo, 
            "Cantidad": nueva_cantidad, 
            "Precio_Entrada": nuevo_precio, 
            "Inversion_Inicial_USD": inversion
        }])
        st.session_state.trades = pd.concat([st.session_state.trades, nueva_fila], ignore_index=True)
        st.success(f"✅ Operación registrada: Compraste {nueva_cantidad} de {nuevo_activo} por ${inversion:.2f} USD.")

# Mostrar Estadísticas del Portafolio si hay operaciones
if not st.session_state.trades.empty:
    df_trades = st.session_state.trades.copy()
    
    # Calcular precios actuales cruzando con datos en vivo
    precios_actuales = {"Bitcoin": btc_info['price'], "Oro": gold_info['price']}
    df_trades['Precio_Actual_Mercado'] = df_trades['Activo'].map(precios_actuales)
    
    # Calcular valorizaciones
    df_trades['Valor_Actual_USD'] = df_trades['Cantidad'] * df_trades['Precio_Actual_Mercado']
    df_trades['Ganancia/Perdida_USD'] = df_trades['Valor_Actual_USD'] - df_trades['Inversion_Inicial_USD']
    df_trades['Rendimiento_%'] = (df_trades['Ganancia/Perdida_USD'] / df_trades['Inversion_Inicial_USD']) * 100
    
    # Resumen Total
    inversion_total = df_trades['Inversion_Inicial_USD'].sum()
    valor_actual_total = df_trades['Valor_Actual_USD'].sum()
    ganancia_neta = valor_actual_total - inversion_total
    rendimiento_total = (ganancia_neta / inversion_total) * 100 if inversion_total > 0 else 0
    
    st.markdown("### 📊 Rendimiento de mi Portafolio")
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("Inversión Total (USD)", f"${inversion_total:,.2f}")
    res_col2.metric("Valor Actual (USD)", f"${valor_actual_total:,.2f}", f"{ganancia_neta:,.2f} USD")
    res_col3.metric("Rendimiento Neto (%)", f"{rendimiento_total:.2f}%")
    
    st.markdown("**Historial de Transacciones Cruzadas con el Mercado:**")
    st.dataframe(df_trades.style.format({
        "Cantidad": "{:.5f}",
        "Precio_Entrada": "${:,.2f}",
        "Inversion_Inicial_USD": "${:,.2f}",
        "Precio_Actual_Mercado": "${:,.2f}",
        "Valor_Actual_USD": "${:,.2f}",
        "Ganancia/Perdida_USD": "${:,.2f}",
        "Rendimiento_%": "{:.2f}%"
    }), use_container_width=True)

else:
    st.info("No tienes operaciones registradas. Ingresa una compra en el formulario de arriba para iniciar la simulación en vivo.")
