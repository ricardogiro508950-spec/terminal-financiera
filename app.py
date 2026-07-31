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
    page_title="Oculoos Trading v5.40", page_icon="👁️", layout="wide", initial_sidebar_state="expanded"
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
    if "15 Minutos" in interval_type: period, yf_interval = "5d", "15m"
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

# MOTOR DE LA ESTRATEGIA: PRIMERA VELA (9:30 AM NY)
def get_orb_levels(asset_name):
    try:
        ticker = "BTC-USD" if asset_name == "Bitcoin" else "GC=F"
        df = yf.Ticker(ticker).history(period="5d", interval="15m")
        if df.empty: return None, None
        
        # Estandarizar a hora de Nueva York
        if df.index.tz is None: df.index = df.index.tz_localize('UTC')
        df.index = df.index.tz_convert('America/New_York')
        
        # Buscar las velas de las 9:30 AM
        df_open = df[(df.index.hour == 9) & (df.index.minute == 30)]
        if not df_open.empty:
            last_open = df_open.iloc[-1]
            return last_open['High'], last_open['Low']
        return None, None
    except: return None, None

market_data_init, _ = load_data("1 Día (1D)")

# ==========================================
# MENÚ LATERAL (SIDEBAR)
# ==========================================
st.sidebar.image("https://img.icons8.com/color/96/000000/bullish.png", width=60)
st.sidebar.title("Menú Oculoos")
modo_app = st.sidebar.radio("Selecciona tu área de trabajo:", [
    "📊 Terminal Principal (Operación Real)", 
    "🎮 Simulador Completo (Práctica)"
])
st.sidebar.markdown("---")
st.sidebar.caption("Oculoos Trading v5.40 | Módulo Primera Vela")

# =====================================================================
# MODO 1: TERMINAL PRINCIPAL
# =====================================================================
if modo_app == "📊 Terminal Principal (Operación Real)":
    
    st.title("👁️ Oculoos Trading v5.40 | Terminal de Operación")
    st.caption("Flujo Institucional, Gestión de Riesgo, y Radar de Primera Vela")
    st.markdown("---")

    # PASO 1: GESTIÓN DE RIESGO
    st.subheader("🛡️ PASO 1: Auditoría de Capital y Gestión de Riesgo")
    st.caption("Regla Institucional: Define tu pérdida máxima antes de mirar los gráficos.")
    ac_col1, ac_col2, ac_col3 = st.columns(3)
    
    with ac_col1: capital = st.number_input("Capital Total (USD)", min_value=10.0, step=100.0, key="audit_cap", on_change=update_monto_term)
    with ac_col2: riesgo_pct = st.slider("Riesgo por Operación (%)", 0.5, 5.0, step=0.1, key="audit_rsk", on_change=update_monto_term)
    with ac_col3: stop_loss_pct = st.number_input("Stop-Loss Distancia (%)", min_value=0.1, step=0.5, key="audit_sl", on_change=update_monto_term)

    riesgo_usd = capital * (riesgo_pct / 100)
    r_col1, r_col2 = st.columns(2)
    with r_col1: st.error(f"**Pérdida Máxima Aceptada:** ${riesgo_usd:.2f} USD")
    with r_col2: tamano_posicion = st.number_input("✅ Compra Máxima Permitida (Inversión USD) [Manual]:", min_value=1.0, step=10.0, key="monto_inv_term")
        
    st.markdown("---")

    st.subheader("🎛️ Configuración de Simulaciones de Entrada")
    sim_cfg1, sim_cfg2 = st.columns(2)
    with sim_cfg1: activo_sim = st.selectbox("Selecciona Activo:", ["Bitcoin", "Oro"], key="sim_ast")
    with sim_cfg2: direccion_sim = st.selectbox("Dirección:", ["Compra (Long)", "Venta (Short)"], key="sim_dir")

    precio_vivo_sim = market_data_init.get(activo_sim, {}).get('price', 60000.0)
    if precio_vivo_sim == 0: precio_vivo_sim = 60000.0 if activo_sim == "Bitcoin" else 2000.0
    st.info(f"⚡ **Precio Actual en Vivo de {activo_sim}:** `${precio_vivo_sim:,.2f} USD`")

    # Simulaciones (OCO y Manual)
    if "Compra" in direccion_sim:
        sl_calc = precio_vivo_sim * (1 - (stop_loss_pct / 100))
        dist = precio_vivo_sim - sl_calc
        m1r, m2r = precio_vivo_sim + dist, precio_vivo_sim + (dist * 2)
    else:
        sl_calc = precio_vivo_sim * (1 + (stop_loss_pct / 100))
        dist = sl_calc - precio_vivo_sim
        m1r, m2r = precio_vivo_sim - dist, precio_vivo_sim - (dist * 2)

    with st.expander("📊 Simulación 1: Orden Automática (OCO) - Piso y Techo", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("Monto", f"${tamano_posicion:,.2f}")
        c2.metric("Stop Loss", f"${sl_calc:,.2f}")
        c3.metric("Take Profit", f"${m2r:,.2f}")

    with st.expander("🏆 Simulación 2: Estrategia Manual (Break-Even)", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("Inversión", f"${tamano_posicion:,.2f}")
        c2.metric("Meta 1 (Vender 50%)", f"${m1r:,.2f}")
        c3.metric("Meta 2 (Trailing)", f"${m2r:,.2f}")

    st.markdown("---")

    # FRAGMENTO EN VIVO
    @st.fragment(run_every=1)
    def render_live_market_main():
        st.subheader("⚙️ Configuración del Radar Institucional")
        c_ctrl1, c_ctrl2, c_ctrl3 = st.columns(3)
        with c_ctrl1: asset_choice = st.selectbox("Activo a analizar:", ["Bitcoin", "Oro"], key="live_asset")
        with c_ctrl2: selected_timeframe = st.selectbox("Intervalo:", ["15 Minutos", "1 Hora", "4 Horas", "1 Día (1D)"], key="live_tf")
        with c_ctrl3: 
            st.markdown("<br>", unsafe_allow_html=True)
            usar_orb = st.checkbox("🎯 Activar Radar 'Primera Vela' (NY 9:30 AM)")

        market_data, market_history = load_data(selected_timeframe)
        c_close = market_data.get(asset_choice, {}).get('price', 0.0)

        # MÓDULO ESTRATÉGICO: PRIMERA VELA (ORB)
        if usar_orb:
            orb_high, orb_low = get_orb_levels(asset_choice)
            if orb_high and orb_low:
                st.markdown("### 🎯 Estrategia de la Primera Vela (Rango de Apertura NY)")
                
                estado_orb = "⏳ Dentro del Rango (Esperando)"
                color_orb = "#6b7280" # Gris
                if c_close > orb_high:
                    estado_orb = "🟢 RUPTURA ALCISTA CONFIRMADA (Buscando Compras)"
                    color_orb = "#10b981"
                elif c_close < orb_low:
                    estado_orb = "🔴 RUPTURA BAJISTA CONFIRMADA (Buscando Ventas)"
                    color_orb = "#ef4444"

                st.markdown(f"""
                <div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px solid {color_orb};">
                    <h4 style="color: {color_orb}; margin-top:0;">{estado_orb}</h4>
                    <p style="color: #d1d5db; margin-bottom: 5px;">Precio Actual: <b>${c_close:,.2f}</b></p>
                    <ul style="color: #9ca3af; font-size: 14px;">
                        <li><b>Techo (Resistencia):</b> ${orb_high:,.2f}</li>
                        <li><b>Piso (Soporte):</b> ${orb_low:,.2f}</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("No se encontraron datos de la apertura de Nueva York de hoy todavía.")

        # PASO 4: GRAFICO
        st.subheader(f"📈 PASO 4: Gráfico Cuantitativo [{selected_timeframe}]")
        if asset_choice in market_history:
            df = market_history[asset_choice].copy()
            df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
            df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean() if len(df) >= 200 else df["Close"].ewm(span=len(df), adjust=False).mean()
            
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Precio"))
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA_50"], line=dict(color="orange", width=1.5), name="EMA 50"))
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA_200"], line=dict(color="blue", width=1.5), name="EMA 200"))
            
            # Dibujar líneas de Primera Vela si está activo
            if usar_orb and orb_high and orb_low:
                fig.add_hline(y=orb_high, line_dash="dash", line_color="green", annotation_text="Techo 1ra Vela")
                fig.add_hline(y=orb_low, line_dash="dash", line_color="red", annotation_text="Piso 1ra Vela")

            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

    render_live_market_main()

# =====================================================================
# MODO 2: SIMULADOR DE PRÁCTICA COMPLETO
# =====================================================================
elif modo_app == "🎮 Simulador Completo (Práctica)":
    
    st.title("🎮 Simulador de Operaciones en Vivo")
    st.caption("Practica estrategias con precios y gráficos reales del mercado sin arriesgar un centavo.")
    st.markdown("---")

    # Panel de Saldo
    st.markdown(f"### 💰 Saldo de Práctica: **${st.session_state.sim_balance:,.2f} USD**")
    st.markdown(f"Ganancia/Pérdida Acumulada: **${st.session_state.sim_pnl_historico:,.2f} USD**")
    st.markdown("---")

    if st.session_state.sim_estado == 'CERRADO_OCO':
        st.success(st.session_state.get('sim_mensaje_oco', 'Orden ejecutada.'))
        if st.button("🔄 Volver al simulador"):
            st.session_state.sim_estado = 'INACTIVO'
            st.rerun()

    elif st.session_state.sim_estado == 'INACTIVO':
        st.subheader("1️⃣ Configurar Posición Virtual")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: s_asset = st.selectbox("Activo:", ["Bitcoin", "Oro"])
        with c2: s_dir = st.selectbox("Dirección:", ["Compra (Long)", "Venta (Short)"])
        with c3: s_riesgo_pct = st.number_input("Riesgo sobre Saldo (%)", min_value=0.1, step=0.1, key="sim_rsk_pct", on_change=update_monto_sim)
        with c4: s_sl_pct = st.number_input("Distancia de SL (%):", min_value=0.1, step=0.5, key="sim_sl_pct", on_change=update_monto_sim)

        precio_actual = market_data_init.get(s_asset, {}).get('price', 60000.0)
        if precio_actual == 0: precio_actual = 60000.0
        
        st.info(f"💡 Precio actual de **{s_asset}**: **${precio_actual:,.2f}**")
        s_monto = st.number_input("💸 Inversión a Ejecutar ($ USD) [Modificable]:", min_value=1.0, step=50.0, key="monto_inv_sim")

        st.markdown("### Selecciona tu Estrategia a Simular")
        s_estrategia = st.radio("Método de Operación:", [
            "✋ Estrategia Manual (Botones de Cierre Parcial)",
            "🤖 Estrategia Automática (Orden OCO)",
            "🎯 Estrategia 'Primera Vela' (Se usarán los niveles de la apertura NY)"
        ])

        s_tp, s_sl = 0.0, 0.0

        if "Primera Vela" in s_estrategia:
            orb_high, orb_low = get_orb_levels(s_asset)
            if orb_high and orb_low:
                st.success(f"Niveles detectados: Techo **${orb_high:,.2f}** | Piso **${orb_low:,.2f}**")
                if "Compra" in s_dir: s_tp, s_sl = orb_high + (orb_high-orb_low), orb_low
                else: s_tp, s_sl = orb_low - (orb_high-orb_low), orb_high
                st.caption(f"OCO configurado automáticamente en: TP ${s_tp:,.2f} y SL ${s_sl:,.2f}")
            else:
                st.error("No se pudo detectar la primera vela. Selecciona otra estrategia.")
                s_estrategia = "✋ Estrategia Manual (Botones de Cierre Parcial)"

        elif "Automática" in s_estrategia:
            if "Compra" in s_dir: sl_c = precio_actual * (1-(s_sl_pct/100)); tp_c = precio_actual + ((precio_actual - sl_c)*2)
            else: sl_c = precio_actual * (1+(s_sl_pct/100)); tp_c = precio_actual - ((sl_c - precio_actual)*2)
            col_oco1, col_oco2 = st.columns(2)
            with col_oco1: s_tp = st.number_input("Techo (TP $):", value=tp_c)
            with col_oco2: s_sl = st.number_input("Piso (SL $):", value=sl_c)

        if st.button("🚀 Ejecutar Operación"):
            st.session_state.sim_estado = 'ABIERTO'
            st.session_state.sim_activo = s_asset
            st.session_state.sim_dir = s_dir
            st.session_state.sim_monto_actual = s_monto
            st.session_state.sim_precio_entrada = precio_actual
            st.session_state.sim_estrategia = s_estrategia
            st.session_state.sim_tp = s_tp
            st.session_state.sim_sl = s_sl
            st.rerun()

    else:
        st.subheader("2️⃣ Vigilancia de Operación Activa y Gráfico")
        
        @st.fragment(run_every=1)
        def ejecutar_simulador_vivo():
            if st.session_state.get('sim_estado', 'INACTIVO') not in ['ABIERTO', 'FASE1_COMPLETADA']: st.rerun()

            s_asset = st.session_state.get('sim_activo', 'Bitcoin')
            m_data, m_history = load_data("15 Minutos")
            precio_actual = m_data.get(s_asset, {}).get('price', 60000.0)
            if precio_actual == 0: precio_actual = 60000.0

            p_ent = st.session_state.get('sim_precio_entrada', 60000.0)
            monto_v = st.session_state.get('sim_monto_actual', 0.0)
            dir_s = st.session_state.get('sim_dir', 'Compra (Long)')
            estrat = st.session_state.get('sim_estrategia', 'Manual')
            est_act = st.session_state.get('sim_estado', 'ABIERTO')

            # MOTOR OCO O PRIMERA VELA
            if "Automática" in estrat or "Primera Vela" in estrat:
                tp = st.session_state.get('sim_tp', 0.0)
                sl = st.session_state.get('sim_sl', 0.0)
                auto_c, raz, p_cierre = False, "", 0.0

                if "Compra" in dir_s:
                    if precio_actual >= tp: auto_c, raz, p_cierre = True, "Take Profit", tp
                    elif precio_actual <= sl: auto_c, raz, p_cierre = True, "Stop Loss", sl
                else: 
                    if precio_actual <= tp: auto_c, raz, p_cierre = True, "Take Profit", tp
                    elif precio_actual >= sl: auto_c, raz, p_cierre = True, "Stop Loss", sl

                if auto_c:
                    pnl_pct = ((p_cierre - p_ent)/p_ent)*100 if "Compra" in dir_s else ((p_ent - p_cierre)/p_ent)*100
                    pnl_usd = monto_v * (pnl_pct / 100)
                    st.session_state.sim_balance += pnl_usd
                    st.session_state.sim_pnl_historico += pnl_usd
                    st.session_state.sim_mensaje_oco = f"🤖 **ORDEN AUTOMÁTICA:** Cierre por **{raz}**. PnL: **${pnl_usd:,.2f} USD**."
                    st.session_state.sim_estado = 'CERRADO_OCO'
                    st.rerun()

            pnl_pct = ((precio_actual - p_ent)/p_ent)*100 if "Compra" in dir_s else ((p_ent - precio_actual)/p_ent)*100
            pnl_usd = monto_v * (pnl_pct / 100)

            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Activo", s_asset, dir_s)
            d2.metric("Entrada", f"${p_ent:,.2f}")
            d3.metric("Actual", f"${precio_actual:,.2f}")
            d4.metric("PnL Vivo", f"${pnl_usd:,.2f}", f"{pnl_pct:.2f}%")

            # GRAFICO
            if s_asset in m_history:
                df_sim = m_history[s_asset].tail(80) 
                fig_s = go.Figure(data=[go.Candlestick(x=df_sim.index, open=df_sim["Open"], high=df_sim["High"], low=df_sim["Low"], close=df_sim["Close"], name="Precio")])
                fig_s.add_hline(y=p_ent, line_dash="dot", line_color="white", annotation_text="Entrada")
                
                if "Automática" in estrat or "Primera Vela" in estrat:
                    fig_s.add_hline(y=st.session_state.get('sim_tp', 0.0), line_dash="dash", line_color="green", annotation_text="TP")
                    fig_s.add_hline(y=st.session_state.get('sim_sl', 0.0), line_dash="dash", line_color="red", annotation_text="SL")
                
                fig_s.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=10, b=10))
                st.plotly_chart(fig_s, use_container_width=True)

            st.markdown("---")
            c_ac1, c_ac2 = st.columns(2)
            with c_ac1:
                if "Manual" in estrat and est_act == 'ABIERTO':
                    if st.button("✅ Vender 50% y Mover a Break-Even"):
                        p_mitad = pnl_usd / 2
                        st.session_state.sim_monto_actual = monto_v / 2
                        st.session_state.sim_balance += p_mitad
                        st.session_state.sim_pnl_historico += p_mitad
                        st.session_state.sim_estado = 'FASE1_COMPLETADA'
                        st.rerun()
                elif "Manual" in estrat: st.info("✅ 50% asegurado. Persigue el resto.")
                else: st.caption("Botones manuales desactivados (Modo Automático).")
            
            with c_ac2:
                if st.button("🛑 Cerrar Totalmente y Salir"):
                    st.session_state.sim_balance += pnl_usd
                    st.session_state.sim_pnl_historico += pnl_usd
                    st.session_state.sim_estado = 'INACTIVO'
                    st.rerun()

        ejecutar_simulador_vivo()
