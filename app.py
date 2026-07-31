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
    page_title="Oculoos Trading v5.30", page_icon="👁️", layout="wide"
)

st.title("👁️ Oculoos Trading v5.30")
st.caption("Terminal Cuantitativa Pro | Dos Simulaciones en Vivo, Gestión Institucional y Nube Completa")
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
    ticker = "BTC-USD" if asset_name == "Bitcoin" else "GC=F"
    try:
        df_1d = yf.Ticker(ticker).history(period="3mo", interval="1d")
        df_1h = yf.Ticker(ticker).history(period="1mo", interval="1h")
        df_4h = df_1h.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        return {"1D": df_1d, "4H": df_4h, "1H": df_1h}
    except:
        return None

# Carga inicial de precios en vivo
market_data_init, _ = load_data("1 Día (1D)")

# ==========================================
# PASO 1: GESTIÓN DE RIESGO Y AUDITORÍA
# ==========================================
st.subheader("🛡️ PASO 1: Auditoría de Capital y Gestión de Riesgo")
st.caption("Regla Institucional: Define tu pérdida máxima antes de mirar los gráficos.")
ac_col1, ac_col2, ac_col3 = st.columns(3)
with ac_col1: capital = st.number_input("Capital Total (USD)", min_value=10.0, value=1000.0, step=100.0, key="audit_capital")
with ac_col2: riesgo_pct = st.slider("Riesgo por Operación (%)", 0.5, 5.0, 1.0, 0.5, key="audit_risk")
with ac_col3: stop_loss_pct = st.number_input("Stop-Loss Distancia (%)", min_value=0.1, value=5.0, step=0.5, key="audit_sl_pct")

riesgo_usd = capital * (riesgo_pct / 100)
tamano_posicion = riesgo_usd / (stop_loss_pct / 100) if stop_loss_pct > 0 else 0

r_col1, r_col2 = st.columns(2)
with r_col1: st.error(f"**Pérdida Máxima Aceptada:** ${riesgo_usd:.2f} USD")
with r_col2: st.success(f"**Compra Máxima Permitida (Tamaño de Posición):** ${tamano_posicion:.2f} USD")
st.markdown("---")

# ==========================================
# SELECTOR GENERAL DE ACTIVO Y DIRECCIÓN PARA LAS SIMULACIONES
# ==========================================
st.subheader("🎛️ Configuración de Simulaciones en Vivo")
sim_cfg1, sim_cfg2 = st.columns(2)
with sim_cfg1:
    activo_sim = st.selectbox("Selecciona Activo:", ["Bitcoin", "Oro"], key="sim_asset_sel")
with sim_cfg2:
    direccion_sim = st.selectbox("Dirección de Operación:", ["Compra (Long - Hacia Arriba)", "Venta (Short - Hacia Abajo)"], key="sim_dir_sel")

precio_vivo_sim = market_data_init.get(activo_sim, {}).get('price', 60000.0)
if precio_vivo_sim == 0:
    precio_vivo_sim = 60000.0 if activo_sim == "Bitcoin" else 2000.0

st.info(f"⚡ **Precio Actual en Vivo de {activo_sim}:** `${precio_vivo_sim:,.2f} USD`")

# Cálculos matemáticos comunes
if "Compra" in direccion_sim:
    sl_calculado = precio_vivo_sim * (1 - (stop_loss_pct / 100))
    distancia_r = precio_vivo_sim - sl_calculado
    meta_1r = precio_vivo_sim + distancia_r
    meta_2r = precio_vivo_sim + (distancia_r * 2)
else:
    sl_calculado = precio_vivo_sim * (1 + (stop_loss_pct / 100))
    distancia_r = sl_calculado - precio_vivo_sim
    meta_1r = precio_vivo_sim - distancia_r
    meta_2r = precio_vivo_sim - (distancia_r * 2)

# ==========================================
# SIMULACIÓN 1: ORDEN ESTÁNDAR Y CONFIGURACIÓN OCO
# ==========================================
with st.expander("📊 Simulación 1: Orden Estándar de Riesgo y Órdenes OCO en Binance", expanded=True):
    st.markdown("Esta simulación calcula los datos exactos para entrar al mercado con un único objetivo de ganancia (Ratio 1:2) y protección total.")
    
    s1_c1, s1_c2, s1_c3 = st.columns(3)
    with s1_c1:
        st.metric("1️⃣ Monto a Comprar/Vender", f"${tamano_posicion:,.2f} USD")
        st.caption("Monto dictado por tu gestión de riesgo.")
    with s1_c2:
        st.metric("2️⃣ Stop Loss (Alarma OCO)", f"${sl_calculado:,.2f}")
        st.caption(f"Distancia del {stop_loss_pct}% para proteger tus ${riesgo_usd:.2f} de riesgo.")
    with s1_c3:
        st.metric("3️⃣ Take Profit (Meta OCO)", f"${meta_2r:,.2f}")
        st.caption("Objetivo de ganancia principal (Ratio 1:2).")

st.markdown("---")

# ==========================================
# SIMULACIÓN 2: ESTRATEGIA DE PERSECUCIÓN Y CIERRES PARCIALES (MÉTODO CAMISETAS)
# ==========================================
with st.expander("🏆 Simulación 2: Persecución Dinámica, Cierres Parciales y Break-Even (50% + 50%)", expanded=True):
    st.markdown("Aquí aplicamos la persecución del precio: vendes el 50% temprano para asegurar efectivo, subes tu base a riesgo cero, y persigues el resto.")
    
    s2_c1, s2_c2, s2_c3 = st.columns(3)
    with s2_c1:
        st.markdown(f"""
        <div style="background-color: #111827; padding: 12px; border-radius: 6px; border: 1px solid #374151;">
            <h4 style="color: #60a5fa; margin-top:0;">Inversión Inicial</h4>
            <h3 style="color: #ffffff;">${tamano_posicion:,.2f} USD</h3>
            <p style="font-size: 11px; color: #9ca3af;">Capital total asignado.</p>
        </div>
        """, unsafe_allow_html=True)
    with s2_c2:
        st.markdown(f"""
        <div style="background-color: #1e3a8a; padding: 12px; border-radius: 6px; border: 1px solid #3b82f6;">
            <h4 style="color: #93c5fd; margin-top:0;">Fase 1: Venta del 50%</h4>
            <h3 style="color: #ffffff;">${meta_1r:,.2f}</h3>
            <p style="font-size: 11px; color: #93c5fd;">✅ Vende la mitad (${tamano_posicion/2:,.2f}) y mueve tu Stop Loss a tu entrada (${precio_vivo_sim:,.2f}). ¡Riesgo $0!</p>
        </div>
        """, unsafe_allow_html=True)
    with s2_c3:
        st.markdown(f"""
        <div style="background-color: #064e3b; padding: 12px; border-radius: 6px; border: 1px solid #10b981;">
            <h4 style="color: #6ee7b7; margin-top:0;">Fase 2: Persecución / Meta 2</h4>
            <h3 style="color: #ffffff;">${meta_2r:,.2f}</h3>
            <p style="font-size: 11px; color: #6ee7b7;">🧲 Sigue persiguiendo el precio con el 50% restante o activa Trailing Stop (5%).</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# GUÍA PRÁCTICA: CÓMO OPERAR EN BINANCE
# ==========================================
with st.expander("📖 Guía Práctica de Órdenes en Binance (Paso a Paso)", expanded=False):
    st.markdown("""
    ### 1. La Compra Inicial en Spot
    * Ve a **Binance -> Trade -> Spot** y selecciona tu par (ej. `BTC/USDT`).
    * Selecciona el botón verde de **COMPRAR** (o rojo si es Short).
    * Cambia el tipo de orden a **Market (Mercado)** para ejecutar tu orden al instante con el precio en vivo.
    * Ingresa el **Monto exacto** indicado en tus tarjetas de simulación y dale clic a Comprar.
    
    ### 2. Configurar los Seguros Automáticos (Órdenes OCO)
    * Ve al botón de **VENDER** y selecciona la orden tipo **OCO** (*One Cancels the Other*).
    * **Precio (Take Profit):** Coloca tu meta final o parcial de ganancia calculada arriba.
    * **Stop (Alarma de Peligro):** Coloca tu precio de Stop Loss de protección.
    * **Límite (Venta de Emergencia):** Unos pocos dólares más allá de la alarma para asegurar la ejecución.
    * **Cantidad:** Desliza la barra al 100%.
    """)
st.markdown("---")

# ==========================================
# SECCIÓN EN VIVO (ACTUALIZACIÓN CADA 1 SEG)
# ==========================================
@st.fragment(run_every=1)
def render_live_market():
    # Reloj de Wall Street
    try:
        ny_now = datetime.datetime.now(ZoneInfo("America/New_York"))
        ny_time_str = ny_now.strftime("%I:%M:%S %p")
        ny_date_str = ny_now.strftime("%A, %d %B %Y")
        market_hour, market_minute = ny_now.hour, ny_now.minute
        is_market_open = (ny_now.weekday() < 5) and (9 <= market_hour < 16 or (market_hour == 9 and market_minute >= 30))
        session_status = "🟢 MERCADO ABIERTO" if is_market_open else "🔴 MERCADO CERRADO"
    except:
        ny_time_str, ny_date_str, session_status = "Sincronizando...", "", "⏳ Verificando..."

    col_reloj1, col_reloj2 = st.columns([2, 1])
    with col_reloj1: st.markdown(f"🕒 **Hora NY:** `{ny_time_str}` — *{ny_date_str}*")
    with col_reloj2: st.markdown(f"**Estado:** {session_status}")
    st.markdown("---")

    # Controles Generales
    st.subheader("⚙️ Configuración del Radar")
    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1: asset_choice = st.selectbox("Activo a analizar:", ["Bitcoin", "Oro"], key="asset_live_choice")
    with col_ctrl2: selected_timeframe = st.selectbox("Intervalo de Gráfico:", ["15 Minutos (15m)", "1 Hora (1h)", "4 Horas (4h)", "1 Día (1D)", "1 Semana (1W)", "1 Mes (1M)"], key="global_timeframe")

    market_data, market_history = load_data(selected_timeframe)

    # Alertas
    active_alerts = []
    for asset_name, info in market_data.items():
        chg = info['change']
        if chg >= 0.8: active_alerts.append(f"🚀 **CRECIMIENTO:** **{asset_name}** registra fuerte impulso alcista del `+{chg:.2f}%`.")
        elif chg <= -0.8: active_alerts.append(f"🔻 **CORRECCIÓN:** **{asset_name}** presenta presión bajista del `{chg:.2f}%`.")
    if active_alerts:
        for alert in active_alerts: st.warning(alert)
    else:
        st.info("ℹ️ **Monitoreo:** Mercados estables. Sin volatilidad extrema reciente.")
    st.markdown("---")

    # ================= PASO 2 =================
    st.subheader("🌐 PASO 2: Clima Macroeconómico")
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

    # ================= PASO 3 =================
    st.subheader(f"🧩 PASO 3: Matriz Institucional (ICT) - {asset_choice}")
    st.caption("Esta matriz busca de forma automática las trampas de liquidez en el mercado.")
    
    mtf_data = load_mtf_data(asset_choice)
    if mtf_data:
        def get_mtf_row(timeframe, role, df):
            if df is None or len(df) < 50: return f"| {timeframe} | {role} | Calculando... | Calculando... |"
            c = df['Close'].iloc[-1]
            e50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
            r = calculate_rsi(df['Close']).iloc[-1]
            trend = "Alcista 🟢" if c > e50 else "Bajista 🔴"
            if r > 70: liq = f"🔥 Sobrecomprado ({r:.1f}) - Posible trampa"
            elif r < 30: liq = f"🩸 Sobrevendido ({r:.1f}) - Caza de Stop Loss"
            else: liq = f"⚖️ Neutral ({r:.1f}) - Acumulación"
            return f"| {timeframe} | {role} | {trend} | {liq} |"

        table_md = "| Temporalidad | Rol (Smart Money) | Tendencia (EMA 50) | Estado de Liquidez (RSI) |\n"
        table_md += "|---|---|---|---|\n"
        table_md += get_mtf_row("📅 **1 Día (1D)**", "Estructura Principal", mtf_data['1D']) + "\n"
        table_md += get_mtf_row("⏳ **4 Horas (4H)**", "Estructura Interna", mtf_data['4H']) + "\n"
        table_md += get_mtf_row("⏱️ **1 Hora (1H)**", "Zona de Trampa", mtf_data['1H'])
        st.markdown(table_md)
    else:
        st.info("Cargando datos institucionales...")
    st.markdown("---")

    # ================= PASO 4 =================
    st.subheader(f"📈 PASO 4: Gráfico Cuantitativo y Traductor [{selected_timeframe}]")
    
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

        with st.expander(f"📊 Ver Estadísticas Avanzadas de {asset_choice}"):
            e_col1, e_col2, e_col3 = st.columns(3)
            e_col1.metric("Mínimo del Periodo", f"${p_low:,.2f}")
            e_col2.metric("Máximo del Periodo", f"${p_high:,.2f}")
            e_col3.metric("Volumen", f"${p_vol:,.0f}" if p_vol > 0 else "N/A")
            if asset_choice == "Bitcoin":
                st.markdown("* **Suministro Circulante:** `20.06M BTC` / Máximo: `21.00M BTC`")
                st.markdown("* **Dominancia de Mercado:** `~58.61%` | **Clasificación:** `#1`")

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_asset.index, open=df_asset["Open"], high=df_asset["High"], low=df_asset["Low"], close=df_asset["Close"], name="Precio"))
        fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_50"], line=dict(color="orange", width=1.5), name="EMA 50"))
        fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_200"], line=dict(color="blue", width=1.5), name="EMA 200"))
        fig.update_layout(title=f"Acción del Precio [{selected_timeframe}] - {asset_choice}", yaxis_title="Precio (USD)", template="plotly_dark", height=450, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # TEXTO DEL TRADUCTOR
        dxy_chg, bond_chg = dxy.get('change', 0), bond.get('change', 0)
        dxy_status = "BUENO para el riesgo." if dxy_chg < 0 else "PRECAUCIÓN. Presión bajista."
        bond_status = "DESFAVORABLE." if bond_chg > 0 else "FAVORABLE."
        
        if current_rsi > 70: rsi_context = f"SOBRECOMPRADO ({current_rsi:.2f}). Riesgo de corrección."
        elif current_rsi < 30: rsi_context = f"SOBREVENDIDO ({current_rsi:.2f}). Zona de rebote institucional."
        elif current_rsi > 50: rsi_context = f"NEUTRAL-ALCISTA ({current_rsi:.2f}). Impulso comprador."
        else: rsi_context = f"NEUTRAL-BAJISTA ({current_rsi:.2f}). Presión vendedora."

        ema_structure = "Alcista (EMA 50 > EMA 200)." if current_ema50 > current_ema200 else "Bajista (EMA 50 < EMA 200)."
        price_battle = "Precio sobre la EMA 50 (Soporte)." if current_close > current_ema50 else "Precio bajo la EMA 50 (Resistencia)."

        st.markdown(f"* **Macroeconomía:** Dólar ({dxy_chg:.2f}%). {dxy_status} | Bonos 10Y ({bond_chg:.2f}%). {bond_status}")
        st.markdown(f"* **Estructura Técnica:** Tendencia Macro {ema_structure} | {price_battle}")
        st.markdown(f"* **Momento (RSI & F&G):** {rsi_context} | Sentimiento en zona de {sentiment_label}.")

        # ALGORITMO FINAL
        if current_close > current_ema50 and current_rsi < 70 and current_ema50 > current_ema200:
            st.success("🟢 **ESTADO VERDE:** Confluencia Alcista. Buen escenario para operar a favor de la tendencia.")
        elif current_close < current_ema50 and current_rsi > 30:
            st.warning("🟡 **ESTADO AMARILLO:** Mercado en consolidación o duda. Máxima precaución.")
        else:
            st.error("🔴 **ESTADO ROJO:** Riesgo técnico severo. Evitar operar o usar stop loss ajustado.")

# Ejecutar el fragmento en vivo
render_live_market()

st.markdown("---")

# ==========================================
# PASO 5: BITÁCORA Y NUBE
# ==========================================
st.subheader("💼 PASO 5: Registro de Operaciones y Bitácora")
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
        nuevo_activo = st.selectbox("Activo", ["Bitcoin", "Oro"], key="reg_asset")
    with col_b:
        nuevo_tipo = st.selectbox("Tipo", ["Compra"], key="reg_type")
    with col_c:
        nueva_cantidad = st.number_input("Cantidad", min_value=0.00001, format="%.5f", key="reg_qty")
    with col_d:
        market_data_temp, _ = load_data("1 Día (1D)")
        raw_precio = market_data_temp.get(nuevo_activo, {}).get('price', 60000.0)
        precio_seguro = float(raw_precio) if raw_precio > 0 else (60000.0 if nuevo_activo == "Bitcoin" else 2000.0)
        nuevo_precio = st.number_input("Precio Compra ($)", value=precio_seguro, min_value=0.1, format="%.2f", key="reg_price")
    
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
    
    market_data_temp, _ = load_data("1 Día (1D)")
    precios_actuales = {"Bitcoin": market_data_temp.get("Bitcoin", {}).get('price', 0), "Oro": market_data_temp.get("Oro", {}).get('price', 0)}
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
