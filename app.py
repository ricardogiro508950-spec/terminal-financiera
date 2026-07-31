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
    page_title="Oculoos Trading v5.21", page_icon="👁️", layout="wide"
)

st.title("👁️ Oculoos Trading v5.21")
st.caption("Terminal Cuantitativa Pro | Traductor en Vivo, Matriz ICT y Nube")
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

@st.cache_data(ttl=15)
def load_data(interval_type):
    if "15 Minutos" in interval_type:
        period, yf_interval = "5d", "15m"
    elif "1 Hora" in interval_type:
        period, yf_interval = "1mo", "1h"
    elif "4 Horas" in interval_type:
        period, yf_interval = "2mo", "1h"
    elif "1 Semana" in interval_type:
        period, yf_interval = "1y", "1wk"
    elif "1 Mes" in interval_type:
        period, yf_interval = "2y", "1mo"
    else:  # 1 Día (1D)
        period, yf_interval = "6mo", "1d"

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
                low_period, high_period = df["Low"].min(), df["High"].max()
                volume_latest = df["Volume"].iloc[-1] if "Volume" in df.columns else 0
                data[name] = {"price": current_price, "change": change, "low": low_period, "high": high_period, "volume": volume_latest}
            else:
                data[name] = {"price": 0.0, "change": 0.0, "low": 0.0, "high": 0.0, "volume": 0.0}
        except:
            data[name] = {"price": 0.0, "change": 0.0, "low": 0.0, "high": 0.0, "volume": 0.0}
    return data, history

@st.cache_data(ttl=15)
def load_mtf_data(asset_name):
    """Descarga datos de 3 temporalidades simultáneas para la matriz ICT"""
    ticker = "BTC-USD" if asset_name == "Bitcoin" else "GC=F"
    try:
        df_1d = yf.Ticker(ticker).history(period="3mo", interval="1d")
        df_1h = yf.Ticker(ticker).history(period="1mo", interval="1h")
        df_4h = df_1h.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        return {"1D": df_1d, "4H": df_4h, "1H": df_1h}
    except:
        return None

# ==========================================
# SECCIÓN EN VIVO (ACTUALIZACIÓN CADA 1 SEG)
# ==========================================
@st.fragment(run_every=1)
def render_live_market():
    # 1. Reloj de Wall Street
    try:
        ny_now = datetime.datetime.now(ZoneInfo("America/New_York"))
        ny_time_str = ny_now.strftime("%I:%M:%S %p")
        ny_date_str = ny_now.strftime("%A, %d %B %Y")
        market_hour, market_minute = ny_now.hour, ny_now.minute
        is_market_open = (ny_now.weekday() < 5) and (9 <= market_hour < 16 or (market_hour == 9 and market_minute >= 30))
        session_status = "🟢 MERCADO ABIERTO (Wall Street)" if is_market_open else "🔴 MERCADO CERRADO (Fuera de Sesión)"
    except:
        ny_time_str, ny_date_str, session_status = "Sincronizando...", "", "⏳ Verificando..."

    col_reloj1, col_reloj2 = st.columns([2, 1])
    with col_reloj1: st.markdown(f"🕒 **Hora Oficial NY:** `{ny_time_str}` — *{ny_date_str}*")
    with col_reloj2: st.markdown(f"**Estado:** {session_status}")
    st.markdown("---")

    # Selector y Carga de Datos
    st.subheader("⚙️ Selector de Intervalo para Gráfico")
    selected_timeframe = st.selectbox("Seleccione el intervalo de análisis visual:", ["15 Minutos (15m)", "1 Hora (1h)", "4 Horas (4h)", "1 Día (1D)", "1 Semana (1W)", "1 Mes (1M)"], key="global_timeframe")
    market_data, market_history = load_data(selected_timeframe)

    # 2. Panel Macro & Tarjetas
    st.subheader("🌐 Panel Intermercados y Macroeconomía")
    col1, col2, col3, col4 = st.columns(4)
    btc, gold, dxy, bond = market_data.get("Bitcoin", {}), market_data.get("Oro", {}), market_data.get("DXY (Dólar)", {}), market_data.get("Bonos 10Y", {})
    
    def render_mobile_card(col, title, info, is_currency=True):
        p, chg = info.get('price', 0), info.get('change', 0)
        p_str = f"${p:,.2f}" if is_currency else f"{p:,.2f}"
        color = "#28a745" if chg >= 0 else "#dc3545"
        sign = "+" if chg >= 0 else ""
        col.markdown(f"""
        <div style="background-color: #111827; padding: 10px; border-radius: 6px; border: 1px solid #1f2937; text-align: center;">
            <div style="font-size: 11px; color: #9ca3af; margin-bottom: 4px;">{title}</div>
            <div style="font-size: 24px; font-weight: bold; color: #f3f4f6; white-space: nowrap;">{p_str}</div>
            <div style="font-size: 11px; color: {color}; font-weight: 600; margin-top: 3px;">{sign}{chg:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    render_mobile_card(col1, "Bitcoin", btc)
    render_mobile_card(col2, "Oro", gold)
    render_mobile_card(col3, "DXY", dxy, False)
    render_mobile_card(col4, "Bono 10Y", bond, False)
    st.markdown("---")

    # 3. Gráficos Técnicos
    st.subheader(f"📈 Análisis Cuantitativo [{selected_timeframe}] & Gráficos")
    asset_choice = st.selectbox("Seleccione activo para análisis técnico detallado:", ["Bitcoin", "Oro"], key="asset_live_choice")

    current_close, current_ema50, current_ema200, current_rsi = 0, 0, 0, 50
    if asset_choice in market_history:
        df_asset = market_history[asset_choice].copy()
        df_asset["EMA_50"] = df_asset["Close"].ewm(span=50, adjust=False).mean()
        df_asset["EMA_200"] = df_asset["Close"].ewm(span=200, adjust=False).mean() if len(df_asset) >= 200 else df_asset["Close"].ewm(span=len(df_asset), adjust=False).mean()
        df_asset["RSI"] = calculate_rsi(df_asset["Close"])

        current_close = df_asset["Close"].iloc[-1]
        current_ema50 = df_asset["EMA_50"].iloc[-1]
        current_ema200 = df_asset["EMA_200"].iloc[-1]
        current_rsi = df_asset["RSI"].iloc[-1]
        
        selected_info = btc if asset_choice == "Bitcoin" else gold
        p_low, p_high, p_vol = selected_info.get("low", 0), selected_info.get("high", 0), selected_info.get("volume", 0)

        sentiment_score = int(np.clip(current_rsi * 1.2, 10, 90))
        sentiment_label = "Miedo Extremo" if sentiment_score < 25 else ("Miedo" if sentiment_score < 45 else ("Neutral" if sentiment_score < 55 else ("Codicia" if sentiment_score < 75 else "Codicia Extrema")))

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("RSI (14)", f"{current_rsi:.2f}")
        m2.metric("EMA 50", f"${current_ema50:,.2f}")
        m3.metric("EMA 200", f"${current_ema200:,.2f}")
        m4.metric("Sentimiento", f"{sentiment_score} ({sentiment_label})")

        with st.expander(f"📊 Ver Estadísticas Avanzadas y Datos de Mercado [{asset_choice}]"):
            e_col1, e_col2, e_col3 = st.columns(3)
            e_col1.metric("Mínimo del Periodo", f"${p_low:,.2f}")
            e_col2.metric("Máximo del Periodo", f"${p_high:,.2f}")
            e_col3.metric("Volumen del Periodo", f"${p_vol:,.0f}" if p_vol > 0 else "N/A")
            if asset_choice == "Bitcoin":
                st.markdown("* **Suministro Circulante:** `20.06M BTC` / Máximo: `21.00M BTC`")
                st.markdown("* **Dominancia de Mercado:** `~58.61%` | **Clasificación:** `#1`")

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_asset.index, open=df_asset["Open"], high=df_asset["High"], low=df_asset["Low"], close=df_asset["Close"], name="Precio"))
        fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_50"], line=dict(color="orange", width=1.5), name="EMA 50"))
        fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_200"], line=dict(color="blue", width=1.5), name="EMA 200"))
        fig.update_layout(title=f"Acción del Precio [{selected_timeframe}] - {asset_choice}", yaxis_title="Precio (USD)", template="plotly_dark", height=450, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 4. TRADUCTOR DEL MERCADO EN VIVO (RESTAURADO)
    st.subheader(f"📝 Traductor del Mercado — {asset_choice} ({selected_timeframe})")
    
    dxy_chg = dxy.get('change', 0)
    bond_chg = bond.get('change', 0)

    dxy_status = "BUENO. Inyecta liquidez institucional a los activos de riesgo." if dxy_chg < 0 else "PRECAUCIÓN. Fortaleza del Dólar ejerce presión bajista general."
    bond_status = "DESFAVORABLE para activos de riesgo." if bond_chg > 0 else "FAVORABLE para la valoración de activos."
    
    if current_rsi > 70: rsi_context = f"SOBRECOMPRADO (RSI en {current_rsi:.2f}). Alerta máxima de agotamiento alcista en escala {selected_timeframe}."
    elif current_rsi < 30: rsi_context = f"SOBREVENDIDO (RSI en {current_rsi:.2f}). Zona óptima de posible rebote técnico institucional."
    elif current_rsi > 50: rsi_context = f"NEUTRAL-ALCISTA (RSI en {current_rsi:.2f}). Impulso comprador dominante."
    else: rsi_context = f"NEUTRAL-BAJISTA (RSI en {current_rsi:.2f}). Presión vendedora controlada."

    if current_ema50 > current_ema200: ema_structure = "Tendencia Estructural Alcista (EMA 50 por encima de la EMA 200)."
    else: ema_structure = "Tendencia Estructural Bajista o de Acumulación (EMA 50 por debajo de la EMA 200)."

    if current_close > current_ema50: price_battle = f"Precio cotizando por encima de la EMA 50 (${current_ema50:,.2f}). Soporte dinámico activo."
    else: price_battle = f"Precio atrapado por debajo de la EMA 50 (${current_ema50:,.2f}). Resistencia activa."

    range_position = "cerca de los máximos del rango" if (p_high - p_low) > 0 and ((current_close - p_low) / (p_high - p_low)) > 0.7 else "en zona media o baja del rango"

    st.markdown(f"* **Macroeconomía (Dólar):** El Dólar varía un ({dxy_chg:.2f}%). {dxy_status}")
    st.markdown(f"* **Deuda Soberana (Bonos 10Y):** Rendimiento varía un ({bond_chg:.2f}%). {bond_status}")
    st.markdown(f"* **Inercia del Impulso (RSI 14):** {rsi_context}")
    st.markdown(f"* **Estructura de Medias Móviles:** {ema_structure}")
    st.markdown(f"* **Estadísticas de Rango [{selected_timeframe}]:** El activo cotiza **{range_position}** (Mínimo: `${p_low:,.2f}` | Máximo: `${p_high:,.2f}`).")
    st.markdown(f"* **Batalla Técnica del Precio:** {price_battle}")

    # Algoritmo de Confluencia
    if current_close > current_ema50 and current_rsi < 70 and current_ema50 > current_ema200:
        st.success("🟢 **ESTADO VERDE:** Alta confluencia alcista institucional. Alineación perfecta entre precio, medias y momentum.")
    elif current_close < current_ema50 and current_rsi > 30:
        st.warning("🟡 **ESTADO AMARILLO:** Señales divididas o mercado en rango. Mantén disciplina y gestión de riesgo.")
    else:
        st.error("🔴 **ESTADO ROJO:** Alta volatilidad o conflicto técnico severo. Riesgo elevado de trampa de mercado.")

    st.markdown("---")

    # 5. MATRIZ DE SINCRONIZACIÓN INSTITUCIONAL (SMART MONEY)
    st.subheader(f"🧩 Matriz de Sincronización Institucional (ICT) - {asset_choice}")
    st.caption("Esta matriz escanea múltiples temporalidades simultáneamente para detectar dónde están las trampas de liquidez.")
    
    mtf_data = load_mtf_data(asset_choice)
    if mtf_data:
        def get_mtf_row(timeframe, role, df):
            if df is None or len(df) < 50: return f"| {timeframe} | {role} | Calculando... | Calculando... |"
            c = df['Close'].iloc[-1]
            e50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
            r = calculate_rsi(df['Close']).iloc[-1]
            trend = "Alcista 🟢" if c > e50 else "Bajista 🔴"
            if r > 70: liq = f"🔥 Sobrecomprado ({r:.1f}) - Posible trampa alcista"
            elif r < 30: liq = f"🩸 Sobrevendido ({r:.1f}) - Caza de Stop Loss (Zona de Compra)"
            else: liq = f"⚖️ Neutral ({r:.1f}) - Acumulación de liquidez"
            return f"| {timeframe} | {role} | {trend} | {liq} |"

        table_md = "| Temporalidad | Rol en la Estrategia (ICT) | Tendencia (EMA 50) | Estado de Liquidez (RSI) |\n"
        table_md += "|---|---|---|---|\n"
        table_md += get_mtf_row("📅 **1 Día (1D)**", "Estructura Principal (Dirección)", mtf_data['1D']) + "\n"
        table_md += get_mtf_row("⏳ **4 Horas (4H)**", "Estructura Interna (Retrocesos)", mtf_data['4H']) + "\n"
        table_md += get_mtf_row("⏱️ **1 Hora (1H)**", "Zona de Liquidez / Trampa", mtf_data['1H'])
        
        st.markdown(table_md)
    else:
        st.info("Cargando datos institucionales...")

# Ejecutar el fragmento en vivo
render_live_market()

st.markdown("---")

# ==========================================
# SECCIÓN ESTÁTICA: AUDITORÍA DE CAPITAL Y BITÁCORA NUBE
# ==========================================
st.subheader("🛡️ Auditoría de Capital y Gestión de Riesgo")
ac_col1, ac_col2, ac_col3 = st.columns(3)
with ac_col1: capital = st.number_input("Capital Total (USD)", min_value=10.0, value=1000.0, step=100.0)
with ac_col2: riesgo_pct = st.slider("Riesgo por Operación (%)", 0.5, 5.0, 1.0, 0.5)
with ac_col3: stop_loss_pct = st.number_input("Stop-Loss Distancia (%)", min_value=0.1, value=5.0, step=0.5)

riesgo_usd = capital * (riesgo_pct / 100)
tamano_posicion = riesgo_usd / (stop_loss_pct / 100) if stop_loss_pct > 0 else 0

r_col1, r_col2 = st.columns(2)
with r_col1: st.error(f"**Pérdida Máxima Aceptada:** ${riesgo_usd:.2f} USD")
with r_col2: st.success(f"**Compra Máxima Permitida:** ${tamano_posicion:.2f} USD")

st.markdown("---")

st.subheader("💼 Mi Portafolio y Bitácora de Trading")
@st.cache_resource(ttl=60)
def get_sheet_data():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = json.loads(st.secrets["google_credentials_json"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1k-H50JiL6U41E6ne8qcmHeSvaoC8HCTe9DqWIQlP-Xo/edit").sheet1
        return sheet, pd.DataFrame(sheet.get_all_records())
    except:
        return None, pd.DataFrame()

worksheet, df_trades = get_sheet_data()

with st.form("registro_operacion", clear_on_submit=True):
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a: nuevo_activo = st.selectbox("Activo", ["Bitcoin", "Oro"])
    with col_b: nuevo_tipo = st.selectbox("Tipo", ["Compra"])
    with col_c: nueva_cantidad = st.number_input("Cantidad", min_value=0.00001, format="%.5f")
    with col_d: nuevo_precio = st.number_input("Precio Compra ($)", value=60000.0, min_value=0.1, format="%.2f")
    
    if st.form_submit_button("➕ Registrar Operación") and nueva_cantidad > 0 and worksheet is not None:
        try:
            worksheet.append_row([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nuevo_activo, nuevo_tipo, float(nueva_cantidad), float(nuevo_precio), float(nueva_cantidad * nuevo_precio)])
            st.success("✅ ¡Operación registrada en la nube!")
            st.rerun()
        except Exception as e:
            st.error(f"Error al escribir: {e}")

if not df_trades.empty and 'Activo' in df_trades.columns:
    df_trades['Cantidad'] = pd.to_numeric(df_trades['Cantidad'], errors='coerce')
    df_trades['Inversion_Inicial_USD'] = pd.to_numeric(df_trades['Inversion_Inicial_USD'], errors='coerce')
    
    market_data_temp, _ = load_data("1 Día (1D)")
    precios_actuales = {"Bitcoin": market_data_temp.get("Bitcoin", {}).get('price', 0), "Oro": market_data_temp.get("Oro", {}).get('price', 0)}
    df_trades['Precio_Actual_Mercado'] = df_trades['Activo'].map(precios_actuales)
    df_trades['Valor_Actual_USD'] = df_trades['Cantidad'] * df_trades['Precio_Actual_Mercado']
    df_trades['Ganancia/Perdida_USD'] = df_trades['Valor_Actual_USD'] - df_trades['Inversion_Inicial_USD']
    
    st.dataframe(df_trades.style.format({
        "Cantidad": "{:.5f}", "Precio_Entrada": "${:,.2f}", "Inversion_Inicial_USD": "${:,.2f}",
        "Precio_Actual_Mercado": "${:,.2f}", "Valor_Actual_USD": "${:,.2f}", "Ganancia/Perdida_USD": "${:,.2f}"
    }), use_container_width=True)
