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
    page_title="Oculoos Trading v5.52", page_icon="👁️", layout="wide"
)

# ==========================================
# INYECCIÓN DE CSS PARA AUMENTAR TAMAÑOS
# ==========================================
st.markdown("""
<style>
/* Aumentar tamaño de métricas (números principales) */
[data-testid="stMetricValue"] {
    font-size: 2.5rem !important;
}
[data-testid="stMetricLabel"] {
    font-size: 1.2rem !important;
}
/* Aumentar texto general y listas */
p, li, span {
    font-size: 1.15rem !important;
}
/* Aumentar Subtítulos */
h2 {
    font-size: 2.2rem !important;
}
h3 {
    font-size: 1.8rem !important;
}
</style>
""", unsafe_allow_html=True)

st.title("👁️ Oculoos Trading v5.52 (Visual Pro)")
st.caption("Filtro de Volumen, ATR Dinámico, Gráficos Interactivos con Dibujo y Blindaje de Memoria")
st.markdown("---")

ACTIVOS_DISPONIBLES = ["Bitcoin", "Oro", "Petróleo"]
TICKER_MAP = {"Bitcoin": "BTC-USD", "Oro": "GC=F", "Petróleo": "CL=F"}
PRECIO_DEFECTO = {"Bitcoin": 60000.0, "Oro": 2000.0, "Petróleo": 75.0}
FEE_BINANCE = 0.001 # 0.1% comisión estándar de Binance

# CONFIGURACIÓN INTERACTIVA DE GRÁFICOS (PC Y MÓVIL) + HERRAMIENTAS DE DIBUJO
PLOTLY_CONFIG = {
    'scrollZoom': True,
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToAdd': ['drawline', 'drawrect', 'eraseshape'],
    'modeBarButtonsToRemove': ['lasso2d', 'select2d']
}

# ESTILO PERSONALIZADO PARA LOS DIBUJOS DEL USUARIO (CELESTE NEÓN)
USER_DRAWING_STYLE = dict(line_color="#00FFFF", fillcolor="rgba(0, 255, 255, 0.15)", line_width=2)

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
if 'sim_fees_pagados' not in st.session_state: st.session_state.sim_fees_pagados = 0.0

# Funciones de reacción seguras
def update_monto_term():
    cap = st.session_state.get('audit_cap', 1000.0)
    rsk = st.session_state.get('audit_rsk', 1.0)
    sl = st.session_state.get('audit_sl', 5.0)
    if sl > 0: st.session_state.monto_inv_term = (cap * (rsk / 100)) / (sl / 100)

def update_monto_sim():
    bal = st.session_state.get('sim_balance', 10000.0)
    rsk = st.session_state.get('sim_rsk_pct', 1.0)
    sl = st.session_state.get('sim_sl_pct', 5.0)
    if sl > 0: st.session_state.monto_inv_sim = (bal * (rsk / 100)) / (sl / 100)

# ==========================================
# FUNCIONES MATEMÁTICAS AVANZADAS
# ==========================================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Calculadora de Volatilidad (ATR)
def calculate_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

@st.cache_data(ttl=15)
def load_data(interval_type):
    if "5 Minutos" in interval_type: period, yf_interval = "5d", "5m"
    elif "15 Minutos" in interval_type: period, yf_interval = "5d", "15m"
    elif "1 Hora" in interval_type: period, yf_interval = "1mo", "1h"
    elif "4 Horas" in interval_type: period, yf_interval = "2mo", "1h"
    elif "1 Semana" in interval_type: period, yf_interval = "1y", "1wk"
    elif "1 Mes" in interval_type: period, yf_interval = "2y", "1mo"
    else: period, yf_interval = "6mo", "1d"

    tickers = {
        "Bitcoin": "BTC-USD", "Oro": "GC=F", "Petróleo": "CL=F",
        "DXY (Dólar)": "DX-Y.NYB", "Bonos 10Y": "^TNX"
    }
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
        except Exception:
            data[name] = {"price": 0.0, "change": 0.0, "low": 0.0, "high": 0.0, "volume": 0.0}
    return data, history

@st.cache_data(ttl=15)
def load_mtf_data(asset_name):
    ticker = TICKER_MAP.get(asset_name, "BTC-USD")
    try:
        df_1d = yf.Ticker(ticker).history(period="3mo", interval="1d")
        df_1h = yf.Ticker(ticker).history(period="1mo", interval="1h")
        df_4h = df_1h.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        return {"1D": df_1d, "4H": df_4h, "1H": df_1h}
    except Exception:
        return None

# MOTOR MEJORADO DE LA PRIMERA VELA
@st.cache_data(ttl=60)
def get_orb_levels(asset_name):
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
    except Exception:
        return None, None, None

market_data_init, market_history_init = load_data("1 Hora")

# ==========================================
# PASO 1: GESTIÓN DE RIESGO Y AUDITORÍA
# ==========================================
st.subheader("🛡️ PASO 1: Auditoría de Capital y Riesgo Dinámico")
st.caption("Define tu pérdida máxima. El sistema calculará tu límite seguro de compra.")
ac_col1, ac_col2, ac_col3 = st.columns(3)
with ac_col1: capital = st.number_input("Capital Total (USD)", min_value=10.0, value=1000.0, step=100.0, key="audit_capital", on_change=update_monto_term)
with ac_col2: riesgo_pct = st.slider("Riesgo Máximo por Operación (%)", 0.5, 5.0, 1.0, 0.5, key="audit_risk", on_change=update_monto_term)
with ac_col3:
    activo_riesgo = st.selectbox("Activo a operar:", ACTIVOS_DISPONIBLES, key="risk_asset")
    
    sugerencia_sl_pct = 5.0
    if activo_riesgo in market_history_init:
        df_atr = market_history_init[activo_riesgo]
        if not df_atr.empty and len(df_atr) > 14:
            atr = calculate_atr(df_atr['High'], df_atr['Low'], df_atr['Close']).iloc[-1]
            precio_actual = df_atr['Close'].iloc[-1]
            sugerencia_sl_pct = (atr / precio_actual) * 100 * 1.5 
            
    st.info(f"💡 **Sugerencia de Stop Loss (ATR):** `{sugerencia_sl_pct:.2f}%`")
    stop_loss_pct = st.number_input("Tu Stop-Loss Distancia (%)", min_value=0.1, value=float(f"{sugerencia_sl_pct:.2f}"), step=0.1, key="audit_sl_pct", on_change=update_monto_term)

riesgo_usd = capital * (riesgo_pct / 100)
tamano_posicion = riesgo_usd / (stop_loss_pct / 100) if stop_loss_pct > 0 else 0

r_col1, r_col2 = st.columns(2)
with r_col1: st.error(f"**Pérdida Máxima Aceptada (Riesgo):** ${riesgo_usd:.2f} USD")
with r_col2: st.success(f"**Límite de Inversión Seguro:** ${tamano_posicion:.2f} USD")
st.markdown("---")

# ==========================================
# SECCIÓN EN VIVO (ACTUALIZACIÓN CADA 5 SEG)
# ==========================================
@st.fragment(run_every=5)
def render_live_market():
    try:
        ny_now = datetime.datetime.now(ZoneInfo("America/New_York"))
        ny_time_str = ny_now.strftime("%I:%M:%S %p")
        market_hour, market_minute = ny_now.hour, ny_now.minute
        is_market_open = (ny_now.weekday() < 5) and (9 <= market_hour < 16 or (market_hour == 9 and market_minute >= 30))
        session_status = "🟢 SESIÓN NY ABIERTA (Alta Liquidez)" if is_market_open else "🔴 SESIÓN NY CERRADA"
    except Exception:
        ny_time_str, session_status = "Sincronizando...", "⏳ Verificando..."

    col_reloj1, col_reloj2 = st.columns([2, 1])
    with col_reloj1: st.markdown(f"🕒 **Hora NY:** `{ny_time_str}`")
    with col_reloj2: st.markdown(f"**Estado General:** {session_status}")
    st.markdown("---")

    # ================= SELECTOR DINÁMICO DE ESTRATEGIA =================
    st.subheader("⚙️ Configuración del Radar Multi-Estrategia")
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)

    with col_ctrl1:
        asset_choice = st.selectbox("Activo en Radar:", ACTIVOS_DISPONIBLES, key="asset_live_choice")

    with col_ctrl2:
        estrategia = st.selectbox("🎯 Motor Estratégico:", [
            "📊 Confluencia Clásica (Tendencia + RSI)",
            "🌅 Primera Vela (Ruptura ORB Institucional)",
            "🧲 Cazador de Pullbacks (Rebote EMA 50)"
        ], key="strat_selector")

    with col_ctrl3:
        if "Primera Vela" in estrategia:
            selected_timeframe = st.selectbox("Temporalidad:", ["15 Minutos (15m)", "5 Minutos (5m)"], key="global_timeframe_orb")
            st.caption("🔒 Rango fijado para confirmar rupturas ORB.")
        elif "Pullbacks" in estrategia:
            selected_timeframe = st.selectbox("Temporalidad:", ["15 Minutos (15m)", "1 Hora (1h)"], key="global_timeframe_pull")
            st.caption("🔒 Temporalidad de alta precisión para rebotes.")
        else:
            selected_timeframe = st.selectbox("Temporalidad:", ["15 Minutos (15m)", "1 Hora (1h)", "4 Horas (4h)", "1 Día (1D)", "1 Semana (1W)", "1 Mes (1M)"], index=1, key="global_timeframe_clas")

    umbral_pullback_pct = 0.35
    if "Pullbacks" in estrategia:
        umbral_pullback_pct = st.slider("Precisión del Gatillo (% distancia a EMA 50):", 0.10, 1.00, 0.35, 0.05, key="pullback_threshold")

    market_data, market_history = load_data(selected_timeframe)

    if asset_choice == "Petróleo":
        st.caption("⚠️ Advertencia de Activo: El Petróleo (CL=F) no cotiza 24/7. Precio congelado fuera de horario NY.")

    st.markdown("---")

    # ================= PASO 2: MACRO Y MATRIZ =================
    st.subheader("🌐 PASO 2: Clima Macroeconómico")
    c1, c2, c3, c4 = st.columns(4)
    btc = market_data.get("Bitcoin", {})
    gold = market_data.get("Oro", {})
    dxy = market_data.get("DXY (Dólar)", {})
    bond = market_data.get("Bonos 10Y", {})

    def render_mc(col, title, info, is_currency=True):
        p, chg = info.get('price', 0), info.get('change', 0)
        p_str = f"${p:,.2f}" if is_currency else f"{p:,.2f}"
        color = "#28a745" if chg >= 0 else "#dc3545"
        sign = "+" if chg >= 0 else ""
        col.markdown(f"""
        <div style="background-color: #111827; padding: 10px; border-radius: 6px; border: 1px solid #1f2937; text-align: center;">
            <div style="font-size: 14px; color: #9ca3af;">{title}</div>
            <div style="font-size: 28px; font-weight: bold; color: #f3f4f6;">{p_str}</div>
            <div style="font-size: 14px; color: {color}; font-weight: 600;">{sign}{chg:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    render_mc(c1, "Bitcoin", btc)
    render_mc(c2, "Oro", gold)
    render_mc(c3, "DXY", dxy, False)
    render_mc(c4, "Bono 10Y", bond, False)

    # ================= MÓDULO INTELIGENTE ORB =================
    orb_high, orb_low = None, None
    c_close_actual = market_data.get(asset_choice, {}).get('price', 0.0)

    if "Primera Vela" in estrategia:
        orb_high, orb_low, origen_orb = get_orb_levels(asset_choice)
        if orb_high and orb_low:
            st.markdown(f"### 🎯 Radar Institucional ORB: {asset_choice}")
            st.caption(f"Calculado sobre: **{origen_orb}**")
            
            estado_orb = "⏳ Mercado comprimido en Rango (Esperando Volumen Institucional)"
            color_orb = "#6b7280"

            if c_close_actual > orb_high:
                estado_orb = "🟢 RUPTURA ALCISTA (Evalúa Largo/Compra tras validación de volumen)"
                color_orb = "#10b981"
            elif c_close_actual > 0 and c_close_actual < orb_low:
                estado_orb = "🔴 RUPTURA BAJISTA (Evalúa Corto/Venta tras validación de volumen)"
                color_orb = "#ef4444"

            st.markdown(f"""
            <div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px solid {color_orb}; margin-top: 10px;">
                <h4 style="color: {color_orb}; font-size: 1.5rem; margin-top:0;">{estado_orb}</h4>
                <p style="color: #d1d5db; font-size: 1.2rem; margin-bottom: 5px;">Precio Actual: <b>${c_close_actual:,.2f}</b></p>
                <ul style="color: #9ca3af; font-size: 1.1rem; margin-bottom: 0;">
                    <li><b>Techo del Rango:</b> ${orb_high:,.2f}</li>
                    <li><b>Piso del Rango:</b> ${orb_low:,.2f}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"No hay datos de apertura de sesión suficientes hoy para {asset_choice}.")

    # ================= PASO 3 Y 4: GRÁFICO Y ALGORITMO =================
    st.markdown("---")
    st.subheader(f"📈 Gráfico Cuantitativo Expandido [{selected_timeframe}]")

    if asset_choice in market_history:
        df_asset = market_history[asset_choice].copy()
        df_asset["EMA_50"] = df_asset["Close"].ewm(span=50, adjust=False).mean()
        df_asset["EMA_200"] = df_asset["Close"].ewm(span=200, adjust=False).mean() if len(df_asset) >= 200 else df_asset["Close"].ewm(span=len(df_asset), adjust=False).mean()
        df_asset["RSI"] = calculate_rsi(df_asset["Close"])
        
        df_asset["Vol_SMA_20"] = df_asset["Volume"].rolling(20).mean()

        current_close = df_asset["Close"].iloc[-1]
        current_ema50 = df_asset["EMA_50"].iloc[-1]
        current_ema200 = df_asset["EMA_200"].iloc[-1]
        current_rsi = df_asset["RSI"].iloc[-1]
        current_vol = df_asset["Volume"].iloc[-1]
        avg_vol = df_asset["Vol_SMA_20"].iloc[-1] if not pd.isna(df_asset["Vol_SMA_20"].iloc[-1]) else current_vol

        rvol = (current_vol / avg_vol) if avg_vol > 0 else 1.0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("RSI (Momento)", f"{current_rsi:.2f}")
        m2.metric("EMA 50 (Soporte)", f"${current_ema50:,.2f}")
        
        rvol_color = "normal" if rvol >= 1.2 else "off"
        m3.metric("Filtro Volumen (RVOL)", f"{rvol:.2f}x", delta="Buen Volumen" if rvol >= 1.2 else "Volumen Bajo", delta_color=rvol_color)
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_asset.index, open=df_asset["Open"], high=df_asset["High"], low=df_asset["Low"], close=df_asset["Close"], name="Precio"))

        if "Pullbacks" in estrategia:
            fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_50"], line=dict(color="#fbbf24", width=3.5), name="EMA 50 (Gatillo)"))
            fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_200"], line=dict(color="blue", width=1.0), opacity=0.4, name="EMA 200"))
        else:
            fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_50"], line=dict(color="orange", width=1.5), name="EMA 50"))
            fig.add_trace(go.Scatter(x=df_asset.index, y=df_asset["EMA_200"], line=dict(color="blue", width=1.5), name="EMA 200"))

        if "Primera Vela" in estrategia and orb_high and orb_low:
            fig.add_hline(y=orb_high, line_dash="dash", line_color="#10b981", annotation_text="Techo ORB")
            fig.add_hline(y=orb_low, line_dash="dash", line_color="#ef4444", annotation_text="Piso ORB")

        # ALTURA AUMENTADA, ZOOM CONFIGURADO Y COLOR NEÓN PARA DIBUJOS
        fig.update_layout(
            template="plotly_dark", 
            height=650, 
            margin=dict(l=20, r=20, t=40, b=20),
            dragmode='zoom',
            xaxis=dict(rangeslider=dict(visible=False)),
            newshape=USER_DRAWING_STYLE
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        st.markdown("### 🤖 Auditoría de Algoritmo (Confirmación de Entrada):")
        
        volumen_valido = rvol >= 1.1

        if "Clásica" in estrategia:
            if current_close > current_ema50 and current_rsi < 70 and current_ema50 > current_ema200:
                if volumen_valido:
                    st.success("🟢 **ESTADO VERDE:** Confluencia Alcista CONFIRMADA con buen volumen. Autorizado para buscar compras.")
                else:
                    st.warning("🟡 **ADVERTENCIA:** Hay tendencia alcista, pero el VOLUMEN ES DÉBIL. Alta probabilidad de trampa institucional. Cuidado.")
            elif current_close < current_ema50 and current_rsi > 30:
                st.warning("🟡 **ESTADO AMARILLO:** Mercado en consolidación. No operar.")
            else:
                st.error("🔴 **ESTADO ROJO:** Riesgo técnico severo.")

        elif "Primera Vela" in estrategia:
            if current_close > orb_high:
                if volumen_valido: st.success("🟢 **RUPTURA LEGÍTIMA:** Ruptura alcista avalada por entrada de volumen. Busca el pullback para comprar.")
                else: st.error("🚨 **TRAMPA DETECTADA:** Ruptura alcista SIN VOLUMEN. Posible 'Caza de Stop Loss' de los bancos. No compres.")
            elif current_close > 0 and current_close < orb_low:
                if volumen_valido: st.error("🔴 **RUPTURA LEGÍTIMA:** Ruptura bajista con volumen. Busca el pullback para vender (Short).")
                else: st.warning("🚨 **TRAMPA DETECTADA:** Ruptura bajista SIN VOLUMEN. No caigas en el engaño.")
            else:
                st.info("⏳ Esperando ruptura direccional.")

        elif "Pullbacks" in estrategia:
            dist_pct = abs(current_close - current_ema50) / current_ema50 * 100 if current_ema50 else 0
            if current_close > current_ema50:
                if dist_pct <= umbral_pullback_pct:
                    st.success(f"🟢 **GATILLO DE PULLBACK LISTO:** El precio está sobre el soporte dinámico (EMA 50).")
                else:
                    st.warning(f"⏳ **ESPERANDO:** Precio lejos de la EMA 50. No persigas, espera a que caiga.")
            else:
                if dist_pct <= umbral_pullback_pct:
                    st.error(f"🔴 **GATILLO DE PULLBACK (SHORT):** El precio tocó la resistencia (EMA 50).")
                else:
                    st.warning(f"⏳ **ESPERANDO REBOTE:** Tendencia bajista, espera que el precio suba a la línea amarilla.")

render_live_market()
st.markdown("---")

# =====================================================================
# SIMULADOR COMPLETO (CON COMISIONES REALES Y USO SEGURO DE ESTADO)
# =====================================================================
st.subheader("🎮 Simulador de Mercado Abierto")
st.caption("Integrado con comisiones Maker/Taker de Binance (0.1%) para un PnL 100% realista.")

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1: s_asset = st.selectbox("Activo a Simular:", ACTIVOS_DISPONIBLES, key="sim_asset")
with col_s2: s_dir = st.selectbox("Posición:", ["Compra (Long)", "Venta (Short)"])
with col_s3: s_monto = st.number_input("Inversión ($ USD):", min_value=10.0, value=500.0, step=50.0)
with col_s4: st_sl_pct = st.number_input("Riesgo (SL %):", min_value=0.1, value=5.0, step=0.5)

precio_mercado = market_data_init.get(s_asset, {}).get('price', 60000.0)
if precio_mercado == 0: precio_mercado = PRECIO_DEFECTO.get(s_asset, 100.0)

if st.button("🚀 Abrir Posición en Simulador"):
    st.session_state.sim_estado = 'ABIERTO'
    st.session_state.sim_activo = s_asset
    st.session_state.sim_dir = s_dir
    st.session_state.sim_monto_inicial = s_monto
    st.session_state.sim_precio_entrada = precio_mercado
    
    # Comisión de apertura
    fee_entrada = s_monto * FEE_BINANCE
    st.session_state.sim_fees_pagados = fee_entrada
    st.success(f"Posición abierta. Comisión de Binance pagada al entrar: ${fee_entrada:.2f} USD.")
    st.rerun()

# USO DE .GET() PARA EVITAR ATTRIBUTEERROR
if st.session_state.get('sim_estado', 'INACTIVO') == 'ABIERTO':
    @st.fragment(run_every=2)
    def motor_simulador_vivo():
        if st.session_state.get('sim_estado', 'INACTIVO') != 'ABIERTO': st.rerun()
        
        asset = st.session_state.get('sim_activo', 'Bitcoin')
        m_data, m_history = load_data("1 Hora")
        p_actual = m_data.get(asset, {}).get('price', 60000.0)
        p_entrada = st.session_state.get('sim_precio_entrada', 60000.0)
        monto = st.session_state.get('sim_monto_inicial', 500.0)
        direccion = st.session_state.get('sim_dir', 'Compra (Long)')
        fees_pagados = st.session_state.get('sim_fees_pagados', 0.0)
        
        if "Compra" in direccion: pnl_bruto_pct = ((p_actual - p_entrada) / p_entrada) * 100
        else: pnl_bruto_pct = ((p_entrada - p_actual) / p_entrada) * 100
        
        pnl_bruto_usd = monto * (pnl_bruto_pct / 100)
        fee_salida = monto * FEE_BINANCE
        pnl_neto_usd = pnl_bruto_usd - fees_pagados - fee_salida
        
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Activo", asset, direccion)
        d2.metric("Precio de Entrada", f"${p_entrada:,.2f}")
        d3.metric("Precio Actual", f"${p_actual:,.2f}")
        d4.metric("PnL NETO (Rebajando Fees)", f"${pnl_neto_usd:,.2f}", f"{(pnl_neto_usd/monto)*100:.2f}%")
        
        st.caption(f"Para quedar en Break-Even (ganancia cero), debes cubrir las comisiones de entrada y salida (Total fees: ${(fees_pagados + fee_salida):.2f}).")

        # Gráfico del simulador aumentado, zoom y dibujo
        if asset in m_history:
            df_sim = m_history[asset].tail(80)
            fig_sim = go.Figure(data=[go.Candlestick(x=df_sim.index, open=df_sim["Open"], high=df_sim["High"], low=df_sim["Low"], close=df_sim["Close"], name="Precio")])
            fig_sim.add_hline(y=p_entrada, line_dash="dot", line_color="white", annotation_text="Tu Entrada")
            fig_sim.update_layout(
                template="plotly_dark", 
                height=600, 
                margin=dict(l=20, r=20, t=10, b=10),
                dragmode='zoom',
                xaxis=dict(rangeslider=dict(visible=False)),
                newshape=USER_DRAWING_STYLE
            )
            st.plotly_chart(fig_sim, use_container_width=True, config=PLOTLY_CONFIG)

        if st.button("🛑 CERRAR POSICIÓN"):
            st.session_state.sim_balance += pnl_neto_usd
            st.session_state.sim_estado = 'INACTIVO'
            st.rerun()
            
    motor_simulador_vivo()

st.markdown("---")

# ==========================================
# PASO 5: BITÁCORA Y NUBE
# ==========================================
st.subheader("💼 PASO 5: Registro de Operaciones y Bitácora")

@st.cache_resource(ttl=60)
def get_sheet_data():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = json.loads(st.secrets["google_credentials_json"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1k-H50JiL6U41E6ne8qcmHeSvaoC8HCTe9DqWIQlP-Xo/edit").sheet1
        return sheet, pd.DataFrame(sheet.get_all_records())
    except Exception: return None, pd.DataFrame()

worksheet, df_trades = get_sheet_data()
if worksheet is None: st.error("⚠️ No se pudo conectar a Google Sheets.")

with st.form("registro_operacion", clear_on_submit=True):
    col_a, col_b, col_c = st.columns(3)
    with col_a: reg_activo = st.selectbox("Activo", ACTIVOS_DISPONIBLES)
    with col_b: reg_tipo_mov = st.selectbox("Movimiento", ["Apertura (Compra)", "Cierre Parcial", "Cierre Total"])
    with col_c: reg_cantidad = st.number_input("Cantidad", min_value=0.00001, format="%.5f")

    col_d, col_e = st.columns(2)
    with col_d: reg_precio = st.number_input("Precio ($)", value=PRECIO_DEFECTO.get(reg_activo, 100.0), format="%.2f")
    with col_e: reg_precio_ref = st.number_input("Precio Entrada Ref. (Solo Cierres)", value=PRECIO_DEFECTO.get(reg_activo, 100.0), format="%.2f")

    if st.form_submit_button("➕ Registrar") and reg_cantidad > 0 and worksheet:
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        es_cierre = "Cierre" in reg_tipo_mov
        pnl_bruto = (reg_precio - reg_precio_ref) * reg_cantidad if es_cierre else 0
        fees = (reg_precio * reg_cantidad * FEE_BINANCE) * (2 if es_cierre else 1)
        pnl_neto = pnl_bruto - fees if es_cierre else 0

        worksheet.append_row([fecha, reg_activo, reg_tipo_mov, float(reg_cantidad), float(reg_precio), float(reg_precio_ref) if es_cierre else "", float(pnl_neto) if es_cierre else ""])
        st.success("✅ Guardado en nube.")
        st.rerun()

if not df_trades.empty and 'Tipo_Movimiento' in df_trades.columns:
    df_trades['Ganancia_Realizada_USD'] = pd.to_numeric(df_trades.get('Ganancia_Realizada_USD', pd.Series(dtype=float)), errors='coerce').fillna(0)
    cierres = df_trades[df_trades['Tipo_Movimiento'].str.contains("Cierre", na=False)]
    
    st.markdown("### 📊 Rendimiento Realizado (Cierres Netos)")
    c1, c2 = st.columns(2)
    c1.metric("Ganancia Neta (Post-Fees)", f"${cierres['Ganancia_Realizada_USD'].sum():,.2f}")
    c2.metric("Operaciones Cerradas", f"{len(cierres)}")
    st.dataframe(df_trades, use_container_width=True)
