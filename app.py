import json
import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuración de la página
st.set_page_config(
    page_title="Terminal Financiera Institucional v5.3", page_icon="📊", layout="wide"
)

st.title("📊 Terminal Financiera Institucional v5.3")
st.caption("Panel Cuantitativo Avanzado | Auditoría Visible, Móvil y Nube")
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
# 1. AUDITORÍA DE CAPITAL Y GESTIÓN DE RIESGO (VISIBLE EN PANTALLA PRINCIPAL)
# ==========================================
st.subheader("🛡️ Auditoría de Capital y Gestión de Riesgo")
ac_col1, ac_col2, ac_col3 = st.columns(3)
with ac_col1:
    capital = st.number_input("Capital Total (USD)", min_value=10.0, value=1000.0, step=100.0)
with ac_col2:
    riesgo_pct = st.slider("Riesgo por Operación (%)", 0.5, 5.0, 1.0, 0.5)
with ac_col3:
    stop_loss_pct = st.number_input("Stop-Loss Distancia (%)", min_value=0.1, value=5.0, step=0.5)

riesgo_usd = capital * (riesgo_pct / 100)
tamano_posicion = riesgo_usd / (stop_loss_pct / 100) if stop_loss_pct > 0 else 0

r_col1, r_col2 = st.columns(2)
with r_col1:
    st.error(f"**Pérdida Máxima Aceptada:** ${riesgo_usd:.2f} USD")
with r_col2:
    st.success(f"**Compra Máxima Permitida:** ${tamano_posicion:.2f} USD")

st.caption("Regla institucional: Nunca comprometas liquidez sin medir el impacto de una pérdida en el patrimonio total.")
st.markdown("---")

# ==========================================
# 2. PANEL MACROECONÓMICO E INTERMERCADOS (MÓVIL OPTIMIZADO)
# ==========================================
st.subheader("🌐 Panel Intermercados y Macroeconomía")

col1, col2, col3, col4 = st.columns(4)
btc_info = market_data.get("Bitcoin", {"price": 0, "change": 0})
gold_info = market_data.get("Oro", {"price": 0, "change": 0})
dxy_info = market_data.get("DXY (Dólar)", {"price": 0, "change": 0})
bond_info = market_data.get("Bonos 10Y", {"price": 0, "change": 0})

def render_mobile_card(col, title, price, change, is_currency=True):
    p_str = f"${price:,.2f}" if is_currency else f"{price:,.2f}"
    color = "#28a745" if change >= 0 else "#dc3545"
    sign = "+" if change >= 0 else ""
    col.markdown(f"""
    <div style="background-color: #111827; padding: 6px; border-radius: 6px; border: 1px solid #1f2937; text-align: center;">
        <div style="font-size: 10px; color: #9ca3af; margin-bottom: 2px;">{title}</div>
        <div style="font-size: 11px; font-weight: bold; color: #f3f4f6; white-space: nowrap;">{p_str}</div>
        <div style="font-size: 9px; color: {color}; font-weight: 600;">{sign}{change:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col1:
    render_mobile_card(col1, "Bitcoin", btc_info['price'], btc_info['change'])
with col2:
    render_mobile_card(col2, "Oro", gold_info['price'], gold_info['change'])
with col3:
    render_mobile_card(col3, "DXY", dxy_info['price'], dxy_info['change'], is_currency=False)
with col4:
    render_mobile_card(col4, "Bono 10Y", bond_info['price'], bond_info['change'], is_currency=False)

st.markdown("---")

# ==========================================
# 3. MOTOR TÉCNICO Y GRÁFICOS INTERACTIVOS
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

    m1, m2, m3 = st.columns(3)
    m1.metric("RSI (14)", f"{current_rsi:.2f}")
    m2.metric("EMA 50", f"${current_ema50:,.2f}")
    m3.metric("EMA 200", f"${current_ema200:,.2f}")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_asset.index, open=df_asset["Open"], high=df_asset["High"], low=df_asset["Low"], close=df_asset["Close"], name="Precio"))
    fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_50"], line=dict(color="orange", width=1.5), name="EMA 50"))
    fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_200"], line=dict(color="blue", width=1.5), name="EMA 200"))
    fig.update_layout(title=f"Acción del Precio e Indicadores - {asset_choice}", yaxis_title="Precio (USD)", template="plotly_dark", height=450, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ==========================================
# 4. TRADUCTOR DEL MERCADO EN VIVO
# ==========================================
st.subheader("📝 Traductor del Mercado en Vivo")

dxy_chg = dxy_info['change']
bond_chg = bond_info['change']

dxy_status = "BUENO. Inyecta liquidez a los activos de riesgo." if dxy_chg < 0 else "PRECAUCIÓN. Fortaleza del dólar ejerce presión bajista."
bond_status = "MALO para el riesgo." if bond_chg > 0 else "FAVORABLE para los activos de riesgo."
rsi_status = "SOBRECOMPRADO (>70). Alerta de posible corrección." if current_rsi > 70 else ("SOBREVENDIDO (<30). Posible zona de rebote." if current_rsi < 30 else "SANO. Subiendo o bajando de forma orgánica.")
ema_status = "Precio operando por encima de la EMA 50. Tendencia alcista activa." if current_close > current_ema50 else "Precio atrapado debajo de la EMA 50. PRECAUCIÓN. Resistencia activa."

st.markdown(f"* **El Viento a Favor (Macro):** El Dólar varía ({dxy_chg:.2f}%). {dxy_status}")
st.markdown(f"* **Tasas de Interés:** El Bono a 10 Años varía ({bond_chg:.2f}%). {bond_status}")
st.markdown(f"* **Salud del Movimiento:** RSI en `{current_rsi:.2f}`. {rsi_status}")
st.markdown(f"* **Batalla Técnica:** {ema_status}")

st.markdown("---")

# ==========================================
# 5. ALGORITMO DE CONFLUENCIA
# ==========================================
if current_close > current_ema50 and current_rsi < 70:
    st.success("🟢 **ESTADO VERDE:** Alta confluencia alcista. Condiciones técnicas favorables para operar.")
elif current_close < current_ema50 and current_rsi > 30:
    st.warning("🟡 **ESTADO AMARILLO:** Señales divididas. Mercado dudoso, mantén liquidez.")
else:
    st.error("🔴 **ESTADO ROJO:** Alta volatilidad o zona de extremidad técnica. Riesgo elevado.")

st.markdown("---")

# ==========================================
# 6. BITÁCORA DE TRADING Y PORTAFOLIO (NUBE)
# ==========================================
st.subheader("💼 Mi Portafolio y Bitácora de Trading")
st.caption("Registra tus compras aquí. El sistema cruzará tus datos con el mercado en vivo para calcular tus ganancias o pérdidas reales.")

@st.cache_resource(ttl=60)
def get_sheet_data():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = json.loads(st.secrets["google_credentials_json"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1k-H50JiL6U41E6ne8qcmHeSvaoC8HCTe9DqWIQlP-Xo/edit").sheet1
        registros = sheet.get_all_records()
        return sheet, pd.DataFrame(registros)
    except Exception as e:
        return None, pd.DataFrame()

worksheet, df_trades = get_sheet_data()

if worksheet is None:
    st.error("⚠️ No se pudo conectar a Google Sheets. Verifica los Secretos en Streamlit.")

with st.form("registro_operacion", clear_on_submit=True):
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        nuevo_activo = st.selectbox("Activo", ["Bitcoin", "Oro"])
    with col_b:
        nuevo_tipo = st.selectbox("Tipo", ["Compra"])
    with col_c:
        nueva_cantidad = st.number_input("Cantidad", min_value=0.00001, format="%.5f")
    with col_d:
        raw_precio = btc_info['price'] if nuevo_activo == "Bitcoin" else gold_info['price']
        precio_seguro = float(raw_precio) if raw_precio > 0 else (60000.0 if nuevo_activo == "Bitcoin" else 2000.0)
        nuevo_precio = st.number_input("Precio Compra ($)", value=precio_seguro, min_value=0.1, format="%.2f")
    
    submit_trade = st.form_submit_button("➕ Registrar Operación")
    
    if submit_trade and nueva_cantidad > 0 and worksheet is not None:
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        inversion = nueva_cantidad * nuevo_precio
        nueva_fila = [fecha_actual, nuevo_activo, nuevo_tipo, float(nueva_cantidad), float(nuevo_precio), float(inversion)]
        
        try:
            worksheet.append_row(nueva_fila)
            st.success("✅ ¡Operación registrada en la nube!")
            st.rerun()
        except Exception as e:
            st.error(f"Error al escribir: {e}")

if not df_trades.empty and 'Activo' in df_trades.columns:
    df_trades['Cantidad'] = pd.to_numeric(df_trades['Cantidad'], errors='coerce')
    df_trades['Precio_Entrada'] = pd.to_numeric(df_trades['Precio_Entrada'], errors='coerce')
    df_trades['Inversion_Inicial_USD'] = pd.to_numeric(df_trades['Inversion_Inicial_USD'], errors='coerce')
    
    precios_actuales = {"Bitcoin": btc_info['price'], "Oro": gold_info['price']}
    df_trades['Precio_Actual_Mercado'] = df_trades['Activo'].map(precios_actuales)
    df_trades['Valor_Actual_USD'] = df_trades['Cantidad'] * df_trades['Precio_Actual_Mercado']
    df_trades['Ganancia/Perdida_USD'] = df_trades['Valor_Actual_USD'] - df_trades['Inversion_Inicial_USD']
    
    inversion_total = df_trades['Inversion_Inicial_USD'].sum()
    valor_actual_total = df_trades['Valor_Actual_USD'].sum()
    ganancia_neta = valor_actual_total - inversion_total
    rendimiento_total = (ganancia_neta / inversion_total) * 100 if inversion_total > 0 else 0
    
    st.markdown("### 📊 Rendimiento del Portafolio en Vivo")
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("Inversión Total", f"${inversion_total:,.2f}")
    res_col2.metric("Valor Actual", f"${valor_actual_total:,.2f}", f"{ganancia_neta:,.2f} USD")
    res_col3.metric("Rendimiento Neto", f"{rendimiento_total:.2f}%")
    
    st.dataframe(df_trades.style.format({
        "Cantidad": "{:.5f}",
        "Precio_Entrada": "${:,.2f}",
        "Inversion_Inicial_USD": "${:,.2f}",
        "Precio_Actual_Mercado": "${:,.2f}",
        "Valor_Actual_USD": "${:,.2f}",
        "Ganancia/Perdida_USD": "${:,.2f}"
    }), use_container_width=True)
else:
    st.info("No tienes operaciones registradas. Ingresa una compra en el formulario de arriba.")
