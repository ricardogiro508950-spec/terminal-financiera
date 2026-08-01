# app.py
import json
import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# IMPORTACIONES DE NUESTRA ARQUITECTURA MODULAR
# ==========================================
from utils.config import ACTIVOS_DISPONIBLES, PRECIO_DEFECTO, FEE_BINANCE, PLOTLY_CONFIG
from utils.logger import log
from utils.helpers import get_market_session_status, format_currency
from core.market_engine import load_data, get_orb_levels, load_mtf_data
from core.risk_engine import calculate_position_size
from core.backtest_engine import run_backtest_ema_crossover
from core.ai_engine import calculate_ai_score
from core.portfolio_math import run_monte_carlo_simulation, calculate_kelly_criterion
from core.alert_engine import send_telegram_alert
from core.pattern_engine import detect_candlestick_patterns # <--- NUEVO MOTOR DE PATRONES DE VELAS

# Indicadores especializados
from indicators.math_indicators import calculate_rsi, calculate_atr
from indicators.trend import calculate_emas
from indicators.momentum import calculate_macd
from indicators.volatility import calculate_bollinger_bands

# Motor gráfico institucional
from dashboard.charts import create_institutional_chart

# Configuración de la página
st.set_page_config(
    page_title="Oculoos Trading v7.0", page_icon="👁️", layout="wide", initial_sidebar_state="expanded"
)

# INYECCIÓN DE CSS
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 2.5rem !important; }
[data-testid="stMetricLabel"] { font-size: 1.2rem !important; }
p, li, span { font-size: 1.15rem !important; }
h2 { font-size: 2.2rem !important; }
h3 { font-size: 1.8rem !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# INICIALIZACIÓN DE ESTADOS
# ==========================================
if 'audit_cap' not in st.session_state: st.session_state.audit_cap = 1000.0
if 'audit_rsk' not in st.session_state: st.session_state.audit_rsk = 1.0
if 'audit_sl' not in st.session_state: st.session_state.audit_sl = 5.0
if 'monto_inv_term' not in st.session_state: st.session_state.monto_inv_term = 200.0

if 'sim_estado' not in st.session_state: st.session_state.sim_estado = 'INACTIVO'
if 'sim_balance' not in st.session_state: st.session_state.sim_balance = 10000.0 
if 'sim_pnl_historico' not in st.session_state: st.session_state.sim_pnl_historico = 0.0
if 'sim_fees_pagados' not in st.session_state: st.session_state.sim_fees_pagados = 0.0

def update_monto_term():
    cap, rsk, sl = st.session_state.get('audit_cap', 1000.0), st.session_state.get('audit_rsk', 1.0), st.session_state.get('audit_sl', 5.0)
    if sl > 0: st.session_state.monto_inv_term = (cap * (rsk / 100)) / (sl / 100)

market_data_init, market_history_init = load_data("1 Hora")

# ==========================================
# MENÚ LATERAL
# ==========================================
st.sidebar.image("https://img.icons8.com/color/96/000000/bullish.png", width=60)
st.sidebar.title("Menú Oculoos")
modo_app = st.sidebar.radio("Área de trabajo:", [
    "📊 Terminal Principal", 
    "🎮 Simulador Completo", 
    "🧪 Laboratorio Backtest", 
    "🔮 Simulador Monte Carlo", 
    "📡 Centro de Alertas",
    "📚 Guía de Velas y 6 Pasos (NUEVO)"
])
st.sidebar.markdown("---")
st.sidebar.caption("Oculoos Trading v7.0 | Institucional")

# =====================================================================
# MODO 1: TERMINAL PRINCIPAL
# =====================================================================
if modo_app == "📊 Terminal Principal":
    st.title("👁️ Oculoos Trading v7.0 | Terminal Institucional + Acción del Precio")
    st.caption("Arquitectura modular con IA, Gestión de Riesgo y Detección de Patrones.")
    st.markdown("---")

    st.subheader("🛡️ PASO 1: Auditoría de Capital y Riesgo")
    ac_col1, ac_col2, ac_col3 = st.columns(3)
    with ac_col1: capital = st.number_input("Capital Total (USD)", min_value=10.0, step=100.0, key="audit_cap", on_change=update_monto_term)
    with ac_col2: riesgo_pct = st.slider("Riesgo Máximo por Op. (%)", 0.5, 5.0, step=0.1, key="audit_rsk", on_change=update_monto_term)
    with ac_col3:
        activo_riesgo = st.selectbox("Activo a operar:", ACTIVOS_DISPONIBLES, key="risk_asset")
        sugerencia_sl_pct = 5.0
        if activo_riesgo in market_history_init:
            df_atr = market_history_init[activo_riesgo]
            if not df_atr.empty and len(df_atr) > 14:
                atr = calculate_atr(df_atr['High'], df_atr['Low'], df_atr['Close']).iloc[-1]
                sugerencia_sl_pct = (atr / df_atr['Close'].iloc[-1]) * 100 * 1.5 
        st.info(f"💡 **Sugerencia Stop Loss (ATR):** `{sugerencia_sl_pct:.2f}%`")
        stop_loss_pct = st.number_input("Tu Stop-Loss (%)", min_value=0.1, value=float(f"{sugerencia_sl_pct:.2f}"), step=0.1, key="audit_sl", on_change=update_monto_term)

    tamano_posicion, riesgo_usd = calculate_position_size(capital, riesgo_pct, stop_loss_pct)
    st.session_state.monto_inv_term = tamano_posicion

    r_col1, r_col2 = st.columns(2)
    with r_col1: st.error(f"**Pérdida Máxima (Riesgo):** {format_currency(riesgo_usd)}")
    with r_col2: st.success(f"**Límite Inversión Seguro:** {format_currency(tamano_posicion)}")
    st.markdown("---")

    @st.fragment(run_every=5)
    def render_live_market_main():
        ny_time_str, session_status = get_market_session_status()
        st.markdown(f"🕒 **Hora NY:** `{ny_time_str}` | **Estado:** {session_status}")
        st.markdown("---")

        st.subheader("⚙️ Configuración del Radar Multi-Estrategia")
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1: asset_choice = st.selectbox("Activo a analizar:", ACTIVOS_DISPONIBLES, key="asset_live_choice")
        with col_ctrl2: estrategia = st.selectbox("🎯 Motor Estratégico:", ["📊 Confluencia Clásica", "🌅 Primera Vela (ORB)", "🧲 Cazador de Pullbacks"], key="strat_selector")
        with col_ctrl3:
            if "Primera Vela" in estrategia: selected_timeframe = st.selectbox("Temporalidad:", ["15 Minutos (15m)", "5 Minutos (5m)"], key="tf_orb")
            elif "Pullbacks" in estrategia: selected_timeframe = st.selectbox("Temporalidad:", ["15 Minutos (15m)", "1 Hora (1h)"], key="tf_pull")
            else: selected_timeframe = st.selectbox("Temporalidad:", ["15 Minutos (15m)", "1 Hora (1h)", "4 Horas (4h)", "1 Día (1D)"], index=1, key="tf_clas")

        market_data, market_history = load_data(selected_timeframe)
        st.markdown("---")

        st.subheader("🌐 PASO 2: Clima Macroeconómico")
        c1, c2, c3, c4 = st.columns(4)
        def render_mc(col, title, info, is_currency=True):
            p, chg = info.get('price', 0), info.get('change', 0)
            p_str, color, sign = (format_currency(p) if is_currency else f"{p:,.2f}"), "#28a745" if chg >= 0 else "#dc3545", "+" if chg >= 0 else ""
            col.markdown(f"""<div style="background-color: #111827; padding: 10px; border-radius: 6px; border: 1px solid #1f2937; text-align: center;"><div style="font-size: 14px; color: #9ca3af;">{title}</div><div style="font-size: 28px; font-weight: bold; color: #f3f4f6;">{p_str}</div><div style="font-size: 14px; color: {color};">{sign}{chg:.2f}%</div></div>""", unsafe_allow_html=True)
        render_mc(c1, "Bitcoin", market_data.get("Bitcoin", {}))
        render_mc(c2, "Oro", market_data.get("Oro", {}))
        render_mc(c3, "DXY", market_data.get("DXY (Dólar)", {}), False)
        render_mc(c4, "Bono 10Y", market_data.get("Bonos 10Y", {}), False)

        # MÓDULO DE INTELIGENCIA ARTIFICIAL Y ACCIÓN DEL PRECIO
        if asset_choice in market_history:
            df_ai = market_history[asset_choice]
            ai_score, ai_verdict, ai_reasons = calculate_ai_score(df_ai)
            patron_vela = detect_candlestick_patterns(df_ai)
            
            st.markdown("---")
            st.subheader("🧠 Análisis Predictivo de IA & Patrones de Velas")
            ai_col1, ai_col2 = st.columns([1, 2])
            with ai_col1:
                st.metric("Score Algorítmico IA", f"{ai_score} / 100 pts", delta=ai_verdict)
                st.markdown(f"🕯️ **Patrón de Vela Detectado:**\n`{patron_vela}`")
            with ai_col2:
                st.markdown("**Factores evaluados por el modelo:**")
                for r in ai_reasons:
                    st.markdown(f"- {r}")

        orb_high, orb_low, c_close_actual = None, None, market_data.get(asset_choice, {}).get('price', 0.0)
        if "Primera Vela" in estrategia:
            orb_high, orb_low, _ = get_orb_levels(asset_choice)
            if orb_high and orb_low:
                estado_orb, color_orb = "⏳ En Rango de Apertura", "#6b7280"
                if c_close_actual > orb_high: estado_orb, color_orb = "🟢 RUPTURA ALCISTA (Busca Pullback)", "#10b981"
                elif c_close_actual > 0 and c_close_actual < orb_low: estado_orb, color_orb = "🔴 RUPTURA BAJISTA (Busca Pullback)", "#ef4444"
                st.markdown(f"""<div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px solid {color_orb}; margin-top: 10px;"><h4 style="color: {color_orb}; font-size: 1.5rem; margin-top:0;">{estado_orb}</h4><p style="color: #d1d5db; font-size: 1.2rem;">Precio: <b>{format_currency(c_close_actual)}</b></p><ul style="color: #9ca3af; font-size: 1.1rem;"><li><b>Techo:</b> {format_currency(orb_high)}</li><li><b>Piso:</b> {format_currency(orb_low)}</li></ul></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader(f"📈 Gráfico Cuantitativo Institucional [{selected_timeframe}]")
        
        if asset_choice in market_history:
            df_asset = market_history[asset_choice].copy()
            df_asset["EMA_50"], df_asset["EMA_200"] = calculate_emas(df_asset)
            df_asset["RSI"] = calculate_rsi(df_asset["Close"])
            df_asset["Vol_SMA_20"] = df_asset["Volume"].rolling(20).mean()

            current_close, current_ema50, current_rsi = df_asset["Close"].iloc[-1], df_asset["EMA_50"].iloc[-1], df_asset["RSI"].iloc[-1]
            current_vol = df_asset["Volume"].iloc[-1]
            avg_vol = df_asset["Vol_SMA_20"].iloc[-1] if not pd.isna(df_asset["Vol_SMA_20"].iloc[-1]) else current_vol
            rvol = (current_vol / avg_vol) if avg_vol > 0 else 1.0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("RSI (Momento)", f"{current_rsi:.2f}")
            m2.metric("EMA 50", format_currency(current_ema50))
            m3.metric("Filtro Volumen (RVOL)", f"{rvol:.2f}x", delta="Buen Volumen" if rvol >= 1.2 else "Volumen Bajo", delta_color="normal" if rvol >= 1.2 else "off")
            
            orb_tupla = (orb_high, orb_low) if "Primera Vela" in estrategia else None
            fig = create_institutional_chart(df_asset, asset_choice, selected_timeframe, show_emas=True, orb_levels=orb_tupla)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    render_live_market_main()
    st.markdown("---")

    st.subheader("💼 PASO 5: Bitácora de Nube")
    @st.cache_resource(ttl=60)
    def get_sheet_data():
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds_dict = json.loads(st.secrets["google_credentials_json"])
            client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope))
            sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1k-H50JiL6U41E6ne8qcmHeSvaoC8HCTe9DqWIQlP-Xo/edit").sheet1
            return sheet, pd.DataFrame(sheet.get_all_records())
        except: return None, pd.DataFrame()

    worksheet, df_trades = get_sheet_data()
    with st.form("registro_operacion", clear_on_submit=True):
        c_a, c_b, c_c = st.columns(3)
        with c_a: reg_activo = st.selectbox("Activo", ACTIVOS_DISPONIBLES)
        with c_b: reg_tipo_mov = st.selectbox("Movimiento", ["Apertura (Compra)", "Cierre Parcial 50%", "Cierre Total"])
        with c_c: reg_cantidad = st.number_input("Cantidad", min_value=0.00001, format="%.5f")
        c_d, c_e = st.columns(2)
        with c_d: reg_precio = st.number_input("Precio ($)", value=60000.0, format="%.2f")
        with c_e: reg_precio_ref = st.number_input("Precio Ref. (Solo Cierres)", value=60000.0, format="%.2f")
        
        if st.form_submit_button("➕ Registrar en Nube") and worksheet:
            fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            es_cierre = "Cierre" in reg_tipo_mov
            ganancia = (reg_precio - reg_precio_ref) * reg_cantidad if es_cierre else 0.0
            worksheet.append_row([fecha, reg_activo, reg_tipo_mov, float(reg_cantidad), float(reg_precio), float(reg_precio_ref) if es_cierre else "", float(ganancia) if es_cierre else ""])
            st.success("✅ Guardado.")
            st.rerun()

    if not df_trades.empty and 'Tipo_Movimiento' in df_trades.columns:
        df_trades['Ganancia_Realizada_USD'] = pd.to_numeric(df_trades.get('Ganancia_Realizada_USD', pd.Series(dtype=float)), errors='coerce').fillna(0)
        st.markdown("### 📊 Rendimiento Realizado")
        st.dataframe(df_trades, use_container_width=True)

# =====================================================================
# MODO 2: SIMULADOR DE PRÁCTICA
# =====================================================================
elif modo_app == "🎮 Simulador Completo":
    st.title("🎮 Simulador de Mercado Abierto")
    st.markdown(f"### 💰 Saldo de Práctica: **{format_currency(st.session_state.get('sim_balance', 10000.0))}**")
    st.markdown("---")
    # ... (código del simulador intacto)
    if st.session_state.get('sim_estado', 'INACTIVO') == 'INACTIVO':
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1: s_asset = st.selectbox("Activo:", ACTIVOS_DISPONIBLES)
        with col_s2: s_dir = st.selectbox("Posición:", ["Compra (Long)", "Venta (Short)"])
        with col_s3: s_monto = st.number_input("Inversión ($ USD):", min_value=10.0, value=500.0, step=50.0)
        with col_s4: st_sl_pct = st.number_input("Riesgo (SL %):", min_value=0.1, value=5.0, step=0.5)

        m_data_init, _ = load_data("1 Hora")
        if st.button("🚀 Abrir Posición en Simulador"):
            st.session_state.sim_estado, st.session_state.sim_activo, st.session_state.sim_dir = 'ABIERTO', s_asset, s_dir
            st.session_state.sim_monto_inicial, st.session_state.sim_precio_entrada = s_monto, m_data_init.get(s_asset, {}).get('price', 100.0)
            st.session_state.sim_fees_pagados = s_monto * FEE_BINANCE
            st.rerun()
    else:
        @st.fragment(run_every=2)
        def motor_simulador_vivo():
            if st.session_state.get('sim_estado') != 'ABIERTO': st.rerun()
            asset, monto, direccion = st.session_state.sim_activo, st.session_state.sim_monto_inicial, st.session_state.sim_dir
            p_entrada, fees_pagados = st.session_state.sim_precio_entrada, st.session_state.sim_fees_pagados
            m_data, m_history = load_data("5 Minutos")
            p_actual = m_data.get(asset, {}).get('price', p_entrada)
            pnl_bruto_pct = ((p_actual - p_entrada) / p_entrada) * 100 if "Compra" in direccion else ((p_entrada - p_actual) / p_entrada) * 100
            pnl_neto_usd = (monto * (pnl_bruto_pct / 100)) - fees_pagados - (monto * FEE_BINANCE)
            
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Activo", asset, direccion)
            d2.metric("Precio Entrada", format_currency(p_entrada))
            d3.metric("Precio Actual", format_currency(p_actual))
            d4.metric("PnL NETO", format_currency(pnl_neto_usd), f"{(pnl_neto_usd/monto)*100:.2f}%")

            if asset in m_history:
                df_sim = m_history[asset].tail(80)
                fig_sim = create_institutional_chart(df_sim, asset, "5 Minutos", show_emas=True)
                st.plotly_chart(fig_sim, use_container_width=True, config=PLOTLY_CONFIG)

            if st.button("🛑 CERRAR POSICIÓN"):
                st.session_state.sim_balance += pnl_neto_usd
                st.session_state.sim_estado = 'INACTIVO'
                st.rerun()
        motor_simulador_vivo()

# =====================================================================
# MODO 3: LABORATORIO DE BACKTESTING
# =====================================================================
elif modo_app == "🧪 Laboratorio Backtest":
    st.title("🧪 Laboratorio Cuantitativo (Backtesting)")
    col_bt1, col_bt2 = st.columns(2)
    with col_bt1: bt_asset = st.selectbox("Activo a evaluar:", ACTIVOS_DISPONIBLES)
    with col_bt2: bt_timeframe = st.selectbox("Datos Históricos:", ["1 Hora (1h)", "1 Día (1D)", "1 Semana (1W)"], index=1)
    
    if st.button("⚙️ Correr Simulación Matemática"):
        _, history_data = load_data(bt_timeframe)
        if bt_asset in history_data and not history_data[bt_asset].empty:
            resultados = run_backtest_ema_crossover(history_data[bt_asset])
            res1, res2, res3 = st.columns(3)
            res1.metric("Total de Operaciones", resultados['total_trades'])
            res2.metric("Win Rate", f"{resultados['win_rate']}%")
            res3.metric("PnL", f"{resultados['pnl_pct']}%")

# =====================================================================
# MODO 4: MONTE CARLO
# =====================================================================
elif modo_app == "🔮 Simulador Monte Carlo":
    st.title("🔮 Motor Cuantitativo: Monte Carlo & Criterio de Kelly")
    mc_asset = st.selectbox("Activo:", ACTIVOS_DISPONIBLES, key="mc_asset")
    mc_days = st.slider("Días:", 10, 90, 30)
    market_data_mc, _ = load_data("1 Día")
    current_p = market_data_mc.get(mc_asset, {}).get('price', 60000.0)
    if st.button("🚀 Ejecutar Monte Carlo"):
        paths = run_monte_carlo_simulation(current_p, days_forward=mc_days, num_simulations=200)
        if paths is not None:
            fig_mc = go.Figure()
            for i in range(50): fig_mc.add_trace(go.Scatter(y=paths[:, i], mode='lines', line=dict(width=1, color='rgba(0,255,255,0.1)'), showlegend=False))
            fig_mc.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig_mc, use_container_width=True)

# =====================================================================
# MODO 5: CENTRO DE ALERTAS
# =====================================================================
elif modo_app == "📡 Centro de Alertas":
    st.title("📡 Centro de Alertas Telegram")
    bot_token = st.text_input("Bot Token:", type="password")
    chat_id = st.text_input("Chat ID:")
    if st.button("📤 Enviar Prueba"):
        send_telegram_alert(bot_token, chat_id, "🚨 Alerta de prueba Oculoos v7.0")

# =====================================================================
# MODO 6: GUÍA DE VELAS Y 6 PASOS (NUEVO)
# =====================================================================
elif modo_app == "📚 Guía de Velas y 6 Pasos (NUEVO)":
    st.title("📚 Manual Institucional de Acción del Precio")
    st.caption("Guía interactiva basada en confluencia, estructura y velas de giro.")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["🔢 Los 6 Pasos", "🕯️ Patrones de Velas", "📊 Perfil de Volumen", "📐 Fibonacci & Órdenes"])

    with tab1:
        st.subheader("📋 Checklist de Confluencia: 6 Pasos Antes de Entrar")
        st.markdown("""
        1. **Estructura:** Buscar siempre máximos más altos (HH) y mínimos más altos (HL) en tendencia alcista.
        2. **Nivel Psicológico:** Identificar soportes y resistencias horizontales clave.
        3. **Fibonacci:** Esperar retrocesos hacia los niveles clave del **50%** y **61.8%**.
        4. **Línea de Tendencia:** Conectar al menos tres mínimos crecientes para confirmar el canal.
        5. **Velas Japonesas:** Buscar confirmación de giro (Martillos, Envolventes) en la zona caliente.
        6. **Volumen:** Validar la participación institucional (RVOL o nodos de volumen).
        """)

    with tab2:
        st.subheader("🕯️ Guía Rápida de Patrones de Giro")
        c_v1, c_v2 = st.columns(2)
        with c_v1:
            st.markdown("### 🟢 Patrones Alcistas (Compra)")
            st.markdown("- **Martillo / Pin Bar:** Mecha inferior larga, rechazo de mínimos.\n- **Estrella de la Mañana:** Vela roja grande, Doji o vela pequeña, y vela verde de confirmación.\n- **Envolvente Alcista:** Vela verde grande que engulle a la roja anterior.")
        with c_v2:
            st.markdown("### 🔴 Patrones Bajistas (Venta)")
            st.markdown("- **Estrella Fugaz:** Mecha superior larga, rechazo de máximos.\n- **Estrella de la Tarde:** Vela verde grande, Doji intermedio, y vela roja de caída.\n- **Envolvente Bajista:** Vela roja grande que engulle a la verde anterior.")

    with tab3:
        st.subheader("📊 Perfil de Volumen (Distribución del Mercado)")
        st.markdown("""
        - **D (Equilibrado):** Mercado en rango o consolidación simétrica.\n
        - **P (Volumen Arriba):** Acumulación en la parte alta, posible continuación alcista o trampa.\n
        - **b (Volumen Abajo):** Presión compradora absorbiendo en mínimos.\n
        - **B (Doble Distribución):** Transición fuerte de precio entre dos rangos de valor.\n
        *Conceptos clave:* **POC** (Fila con mayor volumen), **HVN** (Nodo de alto volumen), **LVN** (Nodo de bajo volumen).
        """)

    with tab4:
        st.subheader("📐 Fibonacci y Bloques de Órdenes (Order Blocks)")
        st.markdown("""
        - **Fibonacci:** Se traza siempre de izquierda a derecha (del mínimo al máximo en impulsos alcistas). Las zonas doradas de retroceso son **38.2%, 50% y 61.8%**.\n
        - **Bloques de Órdenes:** Zonas de indecisión o velas contrarias previas a un impulso institucional con rompimiento de estructura (BOS).
        """)
