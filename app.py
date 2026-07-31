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
    page_title="Oculoos Trading v5.34", page_icon="👁️", layout="wide", initial_sidebar_state="expanded"
)

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
st.sidebar.caption("Oculoos Trading v5.34")

# =====================================================================
# MODO 1: TERMINAL PRINCIPAL
# =====================================================================
if modo_app == "📊 Terminal Principal (Operación Real)":
    
    st.title("👁️ Oculoos Trading v5.34 | Terminal de Operación")
    st.caption("Flujo Institucional, Gestión de Riesgo y Registro en Nube")
    st.markdown("---")

    # PASO 1: GESTIÓN DE RIESGO
    st.subheader("🛡️ PASO 1: Auditoría de Capital y Gestión de Riesgo")
    st.caption("Regla Institucional: Define tu pérdida máxima antes de mirar los gráficos.")
    ac_col1, ac_col2, ac_col3 = st.columns(3)
    with ac_col1: capital = st.number_input("Capital Total (USD)", min_value=10.0, value=1000.0, step=100.0, key="audit_cap")
    with ac_col2: riesgo_pct = st.slider("Riesgo por Operación (%)", 0.5, 5.0, 1.0, 0.5, key="audit_rsk")
    with ac_col3: stop_loss_pct = st.number_input("Stop-Loss Distancia (%)", min_value=0.1, value=5.0, step=0.5, key="audit_sl")

    riesgo_usd = capital * (riesgo_pct / 100)
    tamano_posicion = riesgo_usd / (stop_loss_pct / 100) if stop_loss_pct > 0 else 0

    r_col1, r_col2 = st.columns(2)
    with r_col1: st.error(f"**Pérdida Máxima Aceptada:** ${riesgo_usd:.2f} USD")
    with r_col2: st.success(f"**Compra Máxima Permitida (Tamaño de Posición):** ${tamano_posicion:.2f} USD")
    st.markdown("---")

    st.subheader("🎛️ Configuración de Simulaciones de Entrada")
    sim_cfg1, sim_cfg2 = st.columns(2)
    with sim_cfg1: activo_sim = st.selectbox("Selecciona Activo:", ["Bitcoin", "Oro"], key="sim_ast")
    with sim_cfg2: direccion_sim = st.selectbox("Dirección:", ["Compra (Long)", "Venta (Short)"], key="sim_dir")

    precio_vivo_sim = market_data_init.get(activo_sim, {}).get('price', 60000.0)
    if precio_vivo_sim == 0: precio_vivo_sim = 60000.0 if activo_sim == "Bitcoin" else 2000.0

    st.info(f"⚡ **Precio Actual en Vivo de {activo_sim}:** `${precio_vivo_sim:,.2f} USD`")

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

    with st.expander("📊 Simulación 1: Orden Automática (OCO) - Piso y Techo", expanded=True):
        s1_c1, s1_c2, s1_c3 = st.columns(3)
        with s1_c1:
            st.metric("1️⃣ Monto de Operación", f"${tamano_posicion:,.2f} USD")
            st.caption("Tamaño dictado por tu riesgo.")
        with s1_c2:
            st.metric("2️⃣ Stop Loss (Alarma Piso)", f"${sl_calculado:,.2f}")
            st.caption(f"Límite de pérdida de ${riesgo_usd:.2f}.")
        with s1_c3:
            st.metric("3️⃣ Take Profit (Meta Techo)", f"${meta_2r:,.2f}")
            st.caption("Objetivo Ratio 1:2.")

    with st.expander("🏆 Simulación 2: Estrategia Manual (Persecución y Break-Even)", expanded=True):
        s2_c1, s2_c2, s2_c3 = st.columns(3)
        with s2_c1:
            st.markdown(f"""
            <div style="background-color: #111827; padding: 12px; border-radius: 6px; border: 1px solid #374151;">
                <h4 style="color: #60a5fa; margin-top:0;">Inversión Inicial</h4>
                <h3 style="color: #ffffff;">${tamano_posicion:,.2f} USD</h3>
            </div>
            """, unsafe_allow_html=True)
        with s2_c2:
            st.markdown(f"""
            <div style="background-color: #1e3a8a; padding: 12px; border-radius: 6px; border: 1px solid #3b82f6;">
                <h4 style="color: #93c5fd; margin-top:0;">Fase 1: Venta del 50%</h4>
                <h3 style="color: #ffffff;">${meta_1r:,.2f}</h3>
                <p style="font-size: 11px; color: #93c5fd;">✅ Vende la mitad y sube el Stop Loss a ${precio_vivo_sim:,.2f} (Riesgo $0).</p>
            </div>
            """, unsafe_allow_html=True)
        with s2_c3:
            st.markdown(f"""
            <div style="background-color: #064e3b; padding: 12px; border-radius: 6px; border: 1px solid #10b981;">
                <h4 style="color: #6ee7b7; margin-top:0;">Fase 2: Persecución</h4>
                <h3 style="color: #ffffff;">${meta_2r:,.2f}</h3>
                <p style="font-size: 11px; color: #6ee7b7;">🧲 Activa Trailing Stop del 5% o espera esta meta final.</p>
            </div>
            """, unsafe_allow_html=True)

    with st.expander("📖 Guía Práctica de Binance", expanded=False):
        st.markdown("""
        1. **Spot (Mercado):** Compra o vende el monto exacto de la simulación al precio de mercado.
        2. **Vender (OCO):** Coloca en "Precio" tu Take Profit (Techo) y en "Stop" tu nivel de Stop Loss (Piso).
        """)
    st.markdown("---")

    # FRAGMENTO EN VIVO PARA GRÁFICOS Y RELOJ
    @st.fragment(run_every=1)
    def render_live_market_main():
        try:
            ny_now = datetime.datetime.now(ZoneInfo("America/New_York"))
            ny_time_str = ny_now.strftime("%I:%M:%S %p")
            is_market_open = (ny_now.weekday() < 5) and (9 <= ny_now.hour < 16 or (ny_now.hour == 9 and ny_now.minute >= 30))
            session_status = "🟢 MERCADO ABIERTO" if is_market_open else "🔴 MERCADO CERRADO"
        except:
            ny_time_str, session_status = "Sincronizando...", "⏳ Verificando..."

        c_r1, c_r2 = st.columns([2, 1])
        with c_r1: st.markdown(f"🕒 **Hora NY:** `{ny_time_str}`")
        with c_r2: st.markdown(f"**Estado:** {session_status}")
        st.markdown("---")

        st.subheader("⚙️ Configuración del Radar Institucional")
        c_ctrl1, c_ctrl2 = st.columns(2)
        with c_ctrl1: asset_choice = st.selectbox("Activo a analizar:", ["Bitcoin", "Oro"], key="live_asset")
        with c_ctrl2: selected_timeframe = st.selectbox("Intervalo:", ["15 Minutos", "1 Hora", "4 Horas", "1 Día (1D)"], key="live_tf")

        market_data, market_history = load_data(selected_timeframe)

        # PASO 2: MACRO
        st.subheader("🌐 PASO 2: Clima Macroeconómico")
        c1, c2, c3, c4 = st.columns(4)
        btc, gold, dxy, bond = market_data.get("Bitcoin", {}), market_data.get("Oro", {}), market_data.get("DXY (Dólar)", {}), market_data.get("Bonos 10Y", {})
        
        def render_mc(col, title, info, is_curr=True):
            p, chg = info.get('price', 0), info.get('change', 0)
            p_str = f"${p:,.2f}" if is_curr else f"{p:,.2f}"
            c = "#28a745" if chg >= 0 else "#dc3545"
            s = "+" if chg >= 0 else ""
            col.markdown(f"""
            <div style="background-color: #111827; padding: 10px; border-radius: 6px; border: 1px solid #1f2937; text-align: center;">
                <div style="font-size: 11px; color: #9ca3af;">{title}</div>
                <div style="font-size: 20px; font-weight: bold; color: #f3f4f6;">{p_str}</div>
                <div style="font-size: 11px; color: {c};">{s}{chg:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
        render_mc(c1, "Bitcoin", btc)
        render_mc(c2, "Oro", gold)
        render_mc(c3, "DXY", dxy, False)
        render_mc(c4, "Bono 10Y", bond, False)
        st.markdown("---")

        # PASO 3: ICT
        st.subheader(f"🧩 PASO 3: Matriz Institucional - {asset_choice}")
        mtf_data = load_mtf_data(asset_choice)
        if mtf_data:
            def get_row(tf, r, df):
                if df is None or len(df) < 50: return f"| {tf} | {r} | Calculando... | Calculando... |"
                c = df['Close'].iloc[-1]
                e50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                rsi = calculate_rsi(df['Close']).iloc[-1]
                trend = "Alcista 🟢" if c > e50 else "Bajista 🔴"
                liq = f"🔥 Sobrecomprado ({rsi:.1f})" if rsi > 70 else (f"🩸 Sobrevendido ({rsi:.1f})" if rsi < 30 else f"⚖️ Neutral ({rsi:.1f})")
                return f"| {tf} | {r} | {trend} | {liq} |"
            t = "| Temporalidad | Rol | Tendencia | Liquidez (RSI) |\n|---|---|---|---|\n"
            t += get_row("📅 1D", "Estructura Mayor", mtf_data['1D']) + "\n"
            t += get_row("⏳ 4H", "Estructura Interna", mtf_data['4H']) + "\n"
            t += get_row("⏱️ 1H", "Zona Trampa", mtf_data['1H'])
            st.markdown(t)
        st.markdown("---")

        # PASO 4: GRAFICO
        st.subheader(f"📈 PASO 4: Gráfico y Traductor [{selected_timeframe}]")
        if asset_choice in market_history:
            df = market_history[asset_choice].copy()
            df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
            df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean() if len(df) >= 200 else df["Close"].ewm(span=len(df), adjust=False).mean()
            
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Precio"))
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA_50"], line=dict(color="orange", width=1.5), name="EMA 50"))
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA_200"], line=dict(color="blue", width=1.5), name="EMA 200"))
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

            c_close = df["Close"].iloc[-1]
            c_e50 = df["EMA_50"].iloc[-1]
            c_e200 = df["EMA_200"].iloc[-1]
            c_rsi = calculate_rsi(df["Close"]).iloc[-1]

            if c_close > c_e50 and c_rsi < 70 and c_e50 > c_e200:
                st.success("🟢 **ESTADO VERDE:** Confluencia Alcista. Buen escenario.")
            elif c_close < c_e50 and c_rsi > 30:
                st.warning("🟡 **ESTADO AMARILLO:** Consolidación. Precaución.")
            else:
                st.error("🔴 **ESTADO ROJO:** Riesgo técnico. Evitar operar.")
    
    render_live_market_main()
    st.markdown("---")

    # PASO 5: NUBE
    st.subheader("💼 PASO 5: Registro en la Nube")
    @st.cache_resource(ttl=60)
    def get_sheet_data():
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds_dict = json.loads(st.secrets["google_credentials_json"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            c = gspread.authorize(creds)
            s = c.open_by_url("https://docs.google.com/spreadsheets/d/1k-H50JiL6U41E6ne8qcmHeSvaoC8HCTe9DqWIQlP-Xo/edit").sheet1
            return s, pd.DataFrame(s.get_all_records())
        except: return None, pd.DataFrame()
    
    sheet, df_t = get_sheet_data()
    with st.form("reg"):
        ca, cb, cc, cd = st.columns(4)
        with ca: na = st.selectbox("Activo", ["Bitcoin", "Oro"])
        with cb: nt = st.selectbox("Tipo", ["Compra", "Venta"])
        with cc: nq = st.number_input("Cantidad", min_value=0.00001, format="%.5f")
        with cd: np = st.number_input("Precio ($)", value=60000.0, format="%.2f")
        if st.form_submit_button("Registrar") and nq > 0 and sheet:
            sheet.append_row([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), na, nt, float(nq), float(np), float(nq*np)])
            st.success("Guardado en Google Sheets.")
            st.rerun()

    if not df_t.empty and 'Activo' in df_t.columns:
        st.dataframe(df_t)


# =====================================================================
# MODO 2: SIMULADOR DE PRÁCTICA (ENTORNO SANDBOX COMPLETO Y OCO)
# =====================================================================
elif modo_app == "🎮 Simulador Completo (Práctica)":
    
    st.title("🎮 Simulador de Operaciones en Vivo")
    st.caption("Practica ambas estrategias con precios reales del mercado sin arriesgar un centavo.")
    st.markdown("---")

    # Inicialización de variables de estado del simulador
    if 'sim_estado' not in st.session_state:
        st.session_state.sim_estado = 'INACTIVO' # INACTIVO, ABIERTO, FASE1_COMPLETADA, CERRADO_OCO
    if 'sim_balance' not in st.session_state:
        st.session_state.sim_balance = 10000.0 
    if 'sim_pnl_historico' not in st.session_state:
        st.session_state.sim_pnl_historico = 0.0

    # Panel de Saldo
    st.markdown(f"### 💰 Saldo de Práctica: **${st.session_state.sim_balance:,.2f} USD**")
    st.markdown(f"Ganancia/Pérdida Acumulada: **${st.session_state.sim_pnl_historico:,.2f} USD**")
    st.markdown("---")

    # PANTALLA DE RESULTADO AUTOMÁTICO (OCO)
    if st.session_state.sim_estado == 'CERRADO_OCO':
        st.success(st.session_state.get('sim_mensaje_oco', 'Orden ejecutada automáticamente.'))
        if st.button("🔄 Entendido, volver al simulador"):
            st.session_state.sim_estado = 'INACTIVO'
            st.rerun()

    # Lógica cuando NO hay operación abierta
    elif st.session_state.sim_estado == 'INACTIVO':
        st.subheader("1️⃣ Configurar y Abrir Posición Virtual")
        c1, c2, c3 = st.columns(3)
        with c1: s_asset = st.selectbox("Activo:", ["Bitcoin", "Oro"])
        with c2: s_dir = st.selectbox("Dirección:", ["Compra (Long)", "Venta (Short)"])
        with c3: s_monto = st.number_input("Inversión ($ USD):", min_value=10.0, max_value=st.session_state.sim_balance, value=500.0, step=50.0)

        precio_actual = market_data_init.get(s_asset, {}).get('price', 60000.0)
        if precio_actual == 0: precio_actual = 60000.0
        
        st.info(f"El precio actual de **{s_asset}** en el mercado es de **${precio_actual:,.2f}**")

        st.markdown("### Selecciona tu Estrategia a Simular")
        s_estrategia = st.radio("Método de Operación:", [
            "✋ Estrategia Manual (Tú vigilarás el PnL y harás los Cierres Parciales con botones)",
            "🤖 Estrategia Automática (Orden OCO: Configuras el Piso y Techo y la App cierra sola)"
        ])

        s_tp, s_sl = 0.0, 0.0
        if "Automática" in s_estrategia:
            st.markdown("#### Define los límites automáticos de Binance:")
            col_oco1, col_oco2 = st.columns(2)
            with col_oco1: s_tp = st.number_input("Techo (Take Profit $):", value=precio_actual * 1.05)
            with col_oco2: s_sl = st.number_input("Piso (Stop Loss $):", value=precio_actual * 0.95)

        if st.button("🚀 Ejecutar Operación de Práctica"):
            st.session_state.sim_estado = 'ABIERTO'
            st.session_state.sim_activo = s_asset
            st.session_state.sim_dir = s_dir
            st.session_state.sim_monto_inicial = s_monto
            st.session_state.sim_monto_actual = s_monto
            st.session_state.sim_precio_entrada = precio_actual
            st.session_state.sim_pnl_realizado = 0.0
            st.session_state.sim_estrategia = s_estrategia
            st.session_state.sim_tp = s_tp
            st.session_state.sim_sl = s_sl
            st.rerun()

    # Lógica cuando SÍ hay una operación abierta (En vivo)
    else:
        st.subheader("2️⃣ Vigilancia de Operación Activa")
        
        @st.fragment(run_every=1) # Se actualiza solo cada segundo para vigilar la OCO y el PnL
        def ejecutar_simulador_vivo():
            if st.session_state.sim_estado not in ['ABIERTO', 'FASE1_COMPLETADA']:
                st.rerun()

            s_asset = st.session_state.sim_activo
            m_data, _ = load_data("15 Minutos")
            precio_actual = m_data.get(s_asset, {}).get('price', 60000.0)
            if precio_actual == 0: precio_actual = 60000.0

            p_entrada = st.session_state.sim_precio_entrada
            monto_vivo = st.session_state.sim_monto_actual
            direccion = st.session_state.sim_dir
            estrategia = st.session_state.sim_estrategia

            # ----------------------------------------------------
            # MOTOR DE VIGILANCIA AUTOMÁTICA (OCO)
            # ----------------------------------------------------
            if "Automática" in estrategia:
                tp = st.session_state.sim_tp
                sl = st.session_state.sim_sl
                auto_close = False
                razon = ""
                precio_cierre = 0.0

                if "Compra" in direccion:
                    if precio_actual >= tp:
                        auto_close, razon, precio_cierre = True, "Take Profit (Meta alcanzada)", tp
                    elif precio_actual <= sl:
                        auto_close, razon, precio_cierre = True, "Stop Loss (Pérdida detenida)", sl
                else: # Short
                    if precio_actual <= tp:
                        auto_close, razon, precio_cierre = True, "Take Profit (Meta alcanzada)", tp
                    elif precio_actual >= sl:
                        auto_close, razon, precio_cierre = True, "Stop Loss (Pérdida detenida)", sl

                if auto_close:
                    if "Compra" in direccion: pnl_pct = ((precio_cierre - p_entrada) / p_entrada) * 100
                    else: pnl_pct = ((p_entrada - precio_cierre) / p_entrada) * 100
                    pnl_usd = monto_vivo * (pnl_pct / 100)
                    
                    st.session_state.sim_balance += pnl_usd
                    st.session_state.sim_pnl_historico += pnl_usd
                    st.session_state.sim_mensaje_oco = f"🤖 **¡ORDEN OCO EJECUTADA!** La operación se cerró automáticamente por **{razon}** al tocar los ${precio_cierre:,.2f}, generando un PnL de **${pnl_usd:,.2f} USD**."
                    st.session_state.sim_estado = 'CERRADO_OCO'
                    st.rerun()

            # ----------------------------------------------------
            # PnL FLOTANTE
            # ----------------------------------------------------
            if "Compra" in direccion:
                pnl_pct = ((precio_actual - p_entrada) / p_entrada) * 100
            else:
                pnl_pct = ((p_entrada - precio_actual) / p_entrada) * 100
                
            pnl_usd = monto_vivo * (pnl_pct / 100)

            # ----------------------------------------------------
            # INTERFAZ DEL TABLERO
            # ----------------------------------------------------
            dash1, dash2, dash3, dash4 = st.columns(4)
            dash1.metric("Activo", s_asset, direccion)
            dash2.metric("Precio Entrada", f"${p_entrada:,.2f}")
            dash3.metric("Precio Actual", f"${precio_actual:,.2f}")
            dash4.metric("PnL Flotante (Vivo)", f"${pnl_usd:,.2f} USD", f"{pnl_pct:.2f}%")

            if "Automática" in estrategia:
                st.info(f"🤖 **Modo Automático Activado:** La plataforma está vigilando el precio por ti. Se cerrará sola si toca tu Techo (${st.session_state.sim_tp:,.2f}) o tu Piso (${st.session_state.sim_sl:,.2f}).")
            else:
                if st.session_state.sim_pnl_realizado != 0:
                    st.success(f"💸 Ganancia ya asegurada (Fase 1): **${st.session_state.sim_pnl_realizado:,.2f} USD**")

            st.markdown("---")
            st.subheader("⚡ Acciones del Operador")
            
            col_acc1, col_acc2 = st.columns(2)
            
            with col_acc1:
                if "Manual" in estrategia:
                    if st.session_state.sim_estado == 'ABIERTO':
                        st.markdown("### Estrategia de Cierre Parcial")
                        st.caption("Si ya tocaste tu Meta 1, presiona aquí.")
                        if st.button("✅ Vender 50% y Mover a Break-Even"):
                            pnl_mitad = pnl_usd / 2
                            st.session_state.sim_pnl_realizado = pnl_mitad
                            st.session_state.sim_monto_actual = monto_vivo / 2
                            st.session_state.sim_balance += pnl_mitad
                            st.session_state.sim_pnl_historico += pnl_mitad
                            st.session_state.sim_estado = 'FASE1_COMPLETADA'
                            st.rerun()
                    else:
                        st.info("✅ Ya aseguraste el 50% de esta operación y tu riesgo actual es CERO. Persigue el resto.")
                else:
                    st.markdown("### Estrategia Automática")
                    st.caption("Los botones manuales están deshabilitados porque Binance está controlando la operación.")

            with col_acc2:
                st.markdown("### Cierre de Emergencia")
                st.caption("Cierra la operación manualmente sin importar la estrategia.")
                if st.button("🛑 Cerrar Posición Totalmente y Salir"):
                    st.session_state.sim_balance += pnl_usd
                    st.session_state.sim_pnl_historico += pnl_usd
                    st.session_state.sim_estado = 'INACTIVO'
                    st.rerun()

        ejecutar_simulador_vivo()
