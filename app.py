import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS AVANZADOS
# ==========================================
st.set_page_config(
    page_title="Oculoos Terminal Financiera Profesional",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: #f0f6fc; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 6px; color: #c9d1d9; padding: 10px 18px; font-weight: 600; border: 1px solid #30363d; }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; color: #ffffff !important; border: 1px solid #2ea043; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ENCABEZADO Y DESCRIPCIÓN
# ==========================================
st.title("🛡️ Oculoos Terminal Financiera")
st.markdown("Plataforma analítica centralizada, control de riesgo y sincronización en tiempo real.")

# ==========================================
# 3. PANEL DE CONTROL Y FILTROS RESPONSIVOS
# ==========================================
st.markdown("---")
st.subheader("⚙️ Panel de Control & Filtros")

# Filtros organizados de forma limpia para evitar colapsos visuales en móviles
activo_seleccionado = st.selectbox(
    "🌐 Filtrar por Mercado / Activo:",
    ["Todos los Activos", "Bitcoin (BTCUSDT)", "Ethereum (ETHUSDT)", "Oro / XAU", "Nasdaq / NQ", "Petróleo / WTI"]
)

estrategia_seleccionada = st.selectbox(
    "📈 Filtrar por Estrategia Activa:",
    [
        "Todas las Estrategias",
        "Cazador de Pullbacks", 
        "Cruce de EMAs (Institucional)", 
        "Ruptura de Rango de Volumen", 
        "Retrocesos de Fibonacci (Aura/Niveles Clave)",
        "Confluencia Avanzada (Gann + Fibo)"
    ]
)

sensibilidad_nivel = st.selectbox(
    "⚙️ Nivel de Sensibilidad:",
    [
        "Todos los Niveles",
        "Sensibilidad 0 (Estándar/Base)", 
        "Sensibilidad 1 (Moderada)", 
        "Sensibilidad 2 (Activa)", 
        "Sensibilidad 3 (Agresiva/Exploratoria)"
    ]
)

# Configuración lateral complementaria
st.sidebar.header("⚙️ Gestión de Riesgo")
riesgo_op = st.sidebar.slider("Riesgo Máximo por Operación (%)", 0.5, 3.0, 1.0, 0.1)
drawdown_max = st.sidebar.slider("Límite de Pérdida Diaria (%)", 1.0, 10.0, 3.0, 0.5)
apalancamiento = st.sidebar.selectbox("Factor de Apalancamiento", ["1x", "5x", "10x", "20x", "50x"])

st.sidebar.info("💡 **Oculoos Engine:** Sincronizado con la nube y persistencia local CSV.")

st.markdown("---")

# ==========================================
# 4. CARGA Y PROCESAMIENTO DE DATOS
# ==========================================
archivo_csv = "historial_sensibilidades_real.csv"

if os.path.exists(archivo_csv):
    try:
        df_original = pd.read_csv(archivo_csv)
    except Exception:
        df_original = pd.DataFrame()
else:
    df_original = pd.DataFrame()

df = df_original.copy()

if not df.empty:
    if activo_seleccionado != "Todos los Activos" and 'Activo' in df.columns:
        df = df[df['Activo'].str.contains(activo_seleccionado.split()[0], case=False, na=False)]
        
    if estrategia_seleccionada != "Todas las Estrategias" and 'Estrategia' in df.columns:
        df = df[df['Estrategia'] == estrategia_seleccionada]
        
    if sensibilidad_nivel != "Todos los Niveles" and 'Sensibilidad' in df.columns:
        df = df[df['Sensibilidad'].str.contains(sensibilidad_nivel.split()[0], case=False, na=False)]

# ==========================================
# 5. CÁLCULOS ESTADÍSTICOS
# ==========================================
if not df_original.empty and 'Capital_Acumulado' in df_original.columns:
    capital_actual = df_original.iloc[-1]['Capital_Acumulado']
    rendimiento_global = df_original.iloc[-1]['Rendimiento_Total_Pct']
    total_operaciones = len(df_original)
    ganadas = df_original[df_original['Resultado'].str.contains("GANANCIA", na=False)].shape[0] if 'Resultado' in df_original.columns else 0
    win_rate = (ganadas / total_operaciones) * 100 if total_operaciones > 0 else 0.0
    impacto_neto = df_original['Impacto_USD'].sum() if 'Impacto_USD' in df_original.columns else 0.0
else:
    capital_actual = 100.0
    rendimiento_global = "+0.00%"
    total_operaciones = 0
    win_rate = 0.0
    impacto_neto = 0.0

# ==========================================
# 6. MÉTRICAS SUPERIORES (DISEÑO ADAPTABLE)
# ==========================================
m1, m2 = st.columns(2)
with m1:
    st.metric(label="💰 Capital Actual", value=f"${capital_actual:,.2f} USD")
    st.metric(label="🎯 Tasa de Acierto", value=f"{win_rate:.1f}%")
with m2:
    st.metric(label="📊 Rendimiento Global", value=rendimiento_global)
    st.metric(label="📈 Operaciones Totales", value=str(total_operaciones))

st.markdown("---")

# ==========================================
# 7. PESTAÑAS DE ANÁLISIS E INTERACTIVIDAD
# ==========================================
tab_bitacora, tab_estrategias, tab_activos, tab_graficos, tab_registro, tab_exportar = st.tabs([
    "📋 Bitácora", 
    "📊 Estrategias", 
    "🌐 Activos",
    "📉 Gráficos", 
    "✍️ Registrar",
    "⚙️ Exportar"
])

with tab_bitacora:
    st.subheader("Bitácora General de Operaciones")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay registros disponibles con los filtros actuales o esperando datos de la nube.")

with tab_estrategias:
    st.subheader("Rendimiento por Estrategia")
    if not df_original.empty and 'Estrategia' in df_original.columns:
        resumen_est = df_original.groupby('Estrategia').agg(
            Impacto_Total_USD=('Impacto_USD', 'sum'),
            Total_Operaciones=('Impacto_USD', 'count')
        ).reset_index()
        st.dataframe(resumen_est, use_container_width=True)
        st.bar_chart(resumen_est.set_index('Estrategia')['Impacto_Total_USD'])
    else:
        st.info("Sin datos suficientes para procesar estrategias.")

with tab_activos:
    st.subheader("Rendimiento por Mercado / Activo")
    if not df_original.empty and 'Activo' in df_original.columns:
        resumen_act = df_original.groupby('Activo').agg(
            Impacto_Total_USD=('Impacto_USD', 'sum'),
            Total_Operaciones=('Impacto_USD', 'count')
        ).reset_index()
        st.dataframe(resumen_act, use_container_width=True)
        st.bar_chart(resumen_act.set_index('Activo')['Impacto_Total_USD'])
    else:
        st.info("Sin datos suficientes para procesar activos.")

with tab_graficos:
    st.subheader("Curva de Capital y Precios")
    if not df_original.empty:
        if 'Capital_Acumulado' in df_original.columns:
            st.markdown("#### Capital Acumulado")
            st.line_chart(df_original['Capital_Acumulado'])
        if 'Precio_Mercado' in df_original.columns:
            st.markdown("#### Comportamiento de Precios")
            st.line_chart(df_original.set_index('Fecha_Hora')['Precio_Mercado'])
    else:
        st.info("Esperando registros para graficar.")

with tab_registro:
    st.subheader("Registro Manual de Operaciones")
    with st.form("form_manual"):
        m_activo = st.selectbox("Activo", ["Bitcoin (BTCUSDT)", "Ethereum (ETHUSDT)", "Oro / XAU", "Nasdaq / NQ", "Petróleo / WTI"])
        m_estrat = st.selectbox("Estrategia", ["Cazador de Pullbacks", "Cruce de EMAs (Institucional)", "Ruptura de Rango de Volumen", "Retrocesos de Fibonacci (Aura/Niveles Clave)", "Confluencia Avanzada (Gann + Fibo)"])
        m_sens = st.selectbox("Sensibilidad", ["Sensibilidad 0 (Estándar/Base)", "Sensibilidad 1 (Moderada)", "Sensibilidad 2 (Activa)", "Sensibilidad 3 (Agresiva/Exploratoria)"])
        m_precio = st.number_input("Precio", value=60000.0)
        m_res = st.selectbox("Resultado", ["✅ GANANCIA", "❌ PÉRDIDA"])
        m_impacto = st.number_input("Impacto USD (+/-)", value=1.50)
        
        submitted = st.form_submit_button("Guardar Operación")
        if submitted:
            nc = capital_actual + m_impacto
            nr = ((nc - 100.0) / 100.0) * 100
            nf = pd.DataFrame([{
                "Fecha_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Activo": m_activo,
                "Estrategia": m_estrat,
                "Sensibilidad": m_sens,
                "Precio_Mercado": m_precio,
                "Resultado": m_res,
                "Impacto_USD": m_impacto,
                "Capital_Acumulado": round(nc, 2),
                "Rendimiento_Total_Pct": f"{nr:+.2f}%",
                "Contexto": "Manual"
            }])
            df_new = pd.concat([df_original, nf], ignore_index=True)
            df_new.to_csv(archivo_csv, index=False)
            st.success("Guardado correctamente.")
            st.rerun()

with tab_exportar:
    st.subheader("Exportar Datos")
    if not df_original.empty:
        csv_data = df_original.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV Completo", data=csv_data, file_name="historial_oculoos.csv", mime="text/csv")
    else:
        st.info("No hay datos para exportar.")

# ==========================================
# 8. PIE DE PÁGINA
# ==========================================
st.markdown("---")
st.markdown("🔒 **Oculoos Terminal Engine Pro** - Sistema Multi-Activo.")
