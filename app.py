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
    .stMetric { background-color: #161b22; padding: 18px; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 8px; color: #c9d1d9; padding: 12px 24px; font-weight: 600; border: 1px solid #30363d; }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; color: #ffffff !important; border: 1px solid #2ea043; }
    .sidebar .sidebar-content { background-color: #161b22; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ENCABEZADO Y DESCRIPCIÓN DE LA TERMINAL
# ==========================================
st.title("🛡️ Oculoos Terminal Financiera & Motor Analítico Multi-Activo")
st.markdown("Plataforma centralizada de alta precisión. Procesamiento de estadísticas, cruce de estrategias, gestión de riesgo y análisis en tiempo real.")

# ==========================================
# 3. CONTROLES Y FILTROS PRINCIPALES (VISIBLES EN MOVIL Y PC)
# ==========================================
st.markdown("---")
st.subheader("⚙️ Panel de Control & Filtros Activos")

col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    activo_seleccionado = st.selectbox(
        "🌐 Filtrar por Mercado / Activo:",
        ["Todos los Activos", "Bitcoin (BTCUSDT)", "Ethereum (ETHUSDT)", "Oro / XAU", "Nasdaq / NQ", "Petróleo / WTI"]
    )

with col_c2:
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

with col_c3:
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

# Barra lateral complementaria de gestión de riesgo
st.sidebar.header("⚙️ Configuración Avanzada")
riesgo_op = st.sidebar.slider("Riesgo Máximo por Operación (%)", 0.5, 3.0, 1.0, 0.1)
drawdown_max = st.sidebar.slider("Límite de Pérdida Diaria (%)", 1.0, 10.0, 3.0, 0.5)
apalancamiento = st.sidebar.selectbox("Factor de Apalancamiento", ["1x", "5x", "10x", "20x", "50x"])

st.sidebar.info(
    "💡 **Centro de Control Oculoos:**\n"
    "- Sincronizado en tiempo real con el motor en la nube.\n"
    "- Permite visualización cruzada y registro manual."
)

st.markdown("---")

# ==========================================
# 4. CARGA Y PROCESAMIENTO DE DATOS (CSV UNIFICADO)
# ==========================================
archivo_csv = "historial_sensibilidades_real.csv"

# Inicializamos un DataFrame vacío o cargamos el real si existe
if os.path.exists(archivo_csv):
    try:
        df_original = pd.read_csv(archivo_csv)
    except Exception:
        df_original = pd.DataFrame()
else:
    df_original = pd.DataFrame()

# Copia de trabajo para filtrado interactivo
df = df_original.copy()

if not df.empty:
    if activo_seleccionado != "Todos los Activos" and 'Activo' in df.columns:
        df = df[df['Activo'].str.contains(activo_seleccionado.split()[0], case=False, na=False)]
        
    if estrategia_seleccionada != "Todas las Estrategias" and 'Estrategia' in df.columns:
        df = df[df['Estrategia'] == estrategia_seleccionada]
        
    if sensibilidad_nivel != "Todos los Niveles" and 'Sensibilidad' in df.columns:
        df = df[df['Sensibilidad'].str.contains(sensibilidad_nivel.split()[0], case=False, na=False)]

# ==========================================
# 5. CÁLCULOS MATEMÁTICOS Y ESTADÍSTICOS
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
# 6. PANEL DE MÉTRICAS SUPERIOR (KPIs)
# ==========================================
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(label="💰 Capital Total Actual", value=f"${capital_actual:,.2f} USD")
with col2:
    st.metric(label="📊 Rendimiento Global", value=rendimiento_global)
with col3:
    st.metric(label="🎯 Tasa de Acierto (WinRate)", value=f"{win_rate:.1f}%")
with col4:
    st.metric(label="💵 Impacto Neto (USD)", value=f"${impacto_neto:+,.2f}")
with col5:
    st.metric(label="📈 Operaciones Totales", value=str(total_operaciones))

st.markdown("---")

# ==========================================
# 7. PESTAÑAS DE ANÁLISIS E INTERACTIVIDAD
# ==========================================
tab_bitacora, tab_estrategias, tab_activos, tab_matematico, tab_registro, tab_exportar = st.tabs([
    "📋 Bitácora Interactiva", 
    "📊 Rendimiento por Estrategia", 
    "🌐 Rendimiento por Activo",
    "📉 Motor Matemático y Gráficos", 
    "✍️ Registro Manual de Trades",
    "⚙️ Gestión y Exportación"
])

# --- PESTAÑA 1: BITÁCORA INTERACTIVA ---
with tab_bitacora:
    st.subheader("Bitácora General de Operaciones")
    st.markdown("Registro detallado filtrado según los parámetros seleccionados en el panel superior.")
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        st.markdown("#### Resumen Rápido del Filtro Actual")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            st.metric("Operaciones en Filtro", len(df))
        with f_col2:
            impacto_filtro = df['Impacto_USD'].sum() if 'Impacto_USD' in df.columns else 0.0
            st.metric("Impacto del Filtro (USD)", f"${impacto_filtro:+,.2f}")
        with f_col3:
            ganadas_filtro = df[df['Resultado'].str.contains("GANANCIA", na=False)].shape[0] if 'Resultado' in df.columns else 0
            wr_filtro = (ganadas_filtro / len(df)) * 100 if len(df) > 0 else 0.0
            st.metric("WinRate del Filtro", f"{wr_filtro:.1f}%")
    else:
        st.info("No hay registros todavía o no coinciden con los filtros aplicados. Utiliza la pestaña 'Registro Manual de Trades' para insertar datos de prueba o espera el reporte automático de la nube.")

# --- PESTAÑA 2: RENDIMIENTO POR ESTRATEGIA ---
with tab_estrategias:
    st.subheader("Estadísticas Cruzadas por Estrategia")
    st.markdown("Evaluación matemática del desempeño individual de cada estrategia aplicada en el sistema.")
    
    if not df_original.empty and 'Estrategia' in df_original.columns:
        resumen_est = df_original.groupby('Estrategia').agg(
            Impacto_Total_USD=('Impacto_USD', 'sum'),
            Total_Operaciones=('Impacto_USD', 'count'),
            Promedio_Impacto=('Impacto_USD', 'mean')
        ).reset_index()
        
        resumen_est['Impacto_Total_USD'] = resumen_est['Impacto_Total_USD'].round(2)
        resumen_est['Promedio_Impacto'] = resumen_est['Promedio_Impacto'].round(2)
        
        st.dataframe(resumen_est, use_container_width=True)
        
        st.markdown("#### Gráfico de Impacto Financiero por Estrategia")
        st.bar_chart(resumen_est.set_index('Estrategia')['Impacto_Total_USD'])
    else:
        st.info("Recopilando suficientes métricas para el desglose por estrategia...")

# --- PESTAÑA 3: RENDIMIENTO POR ACTIVO ---
with tab_activos:
    st.subheader("Desglose Analítico por Mercado / Activo")
    st.markdown("Comparativa de rentabilidad y volumen de operaciones entre los diferentes activos monitoreados.")
    
    if not df_original.empty and 'Activo' in df_original.columns:
        resumen_act = df_original.groupby('Activo').agg(
            Impacto_Total_USD=('Impacto_USD', 'sum'),
            Total_Operaciones=('Impacto_USD', 'count')
        ).reset_index()
        
        resumen_act['Impacto_Total_USD'] = resumen_act['Impacto_Total_USD'].round(2)
        
        st.dataframe(resumen_act, use_container_width=True)
        
        st.markdown("#### Comparativa de Ganancias/Pérdidas por Activo")
        st.bar_chart(resumen_act.set_index('Activo')['Impacto_Total_USD'])
    else:
        st.info("Esperando flujo de datos multi-activo...")

# --- PESTAÑA 4: MOTOR MATEMÁTICO Y GRÁFICOS ---
with tab_matematico:
    st.subheader("Evolución del Capital y Comportamiento de Precios")
    st.markdown("Análisis visual de la curva de crecimiento compuesto y el comportamiento de los activos en el tiempo.")
    
    if not df_original.empty:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("#### Curva de Capital Acumulado")
            if 'Capital_Acumulado' in df_original.columns:
                st.line_chart(df_original['Capital_Acumulado'])
            else:
                st.info("Datos insuficientes para la curva de capital.")
                
        with col_g2:
            st.markdown("#### Comportamiento de Precios de Mercado")
            if 'Precio_Mercado' in df_original.columns and 'Fecha_Hora' in df_original.columns:
                st.line_chart(df_original.set_index('Fecha_Hora')['Precio_Mercado'])
            elif 'Precio_Binance' in df_original.columns and 'Fecha_Hora' in df_original.columns:
                st.line_chart(df_original.set_index('Fecha_Hora')['Precio_Binance'])
            else:
                st.info("Datos insuficientes para graficar precios.")
    else:
        st.info("Esperando registros activos para procesar los gráficos matemáticos.")

# --- PESTAÑA 5: REGISTRO MANUAL DE TRADES ---
with tab_registro:
    st.subheader("Formulario de Inserción Manual a la Bitácora")
    st.markdown("Agrega una operación manual con persistencia local inmediata en el archivo CSV unificado.")
    
    with st.form("form_registro_manual"):
        m_activo = st.selectbox("Activo / Mercado", ["Bitcoin (BTCUSDT)", "Ethereum (ETHUSDT)", "Oro / XAU", "Nasdaq / NQ", "Petróleo / WTI"])
        m_estrat = st.selectbox("Estrategia Aplicada", [
            "Cazador de Pullbacks", 
            "Cruce de EMAs (Institucional)", 
            "Ruptura de Rango de Volumen", 
            "Retrocesos de Fibonacci (Aura/Niveles Clave)",
            "Confluencia Avanzada (Gann + Fibo)"
        ])
        m_sens = st.selectbox("Sensibilidad", [
            "Sensibilidad 0 (Estándar/Base)", 
            "Sensibilidad 1 (Moderada)", 
            "Sensibilidad 2 (Activa)", 
            "Sensibilidad 3 (Agresiva/Exploratoria)"
        ])
        m_precio = st.number_input("Precio de Ejecución", value=60000.0, step=10.0)
        m_res = st.selectbox("Resultado", ["✅ GANANCIA", "❌ PÉRDIDA"])
        m_impacto = st.number_input("Impacto en USD (+/-)", value=1.50, step=0.1)
        
        submit_manual = st.form_submit_button("Registrar Operación Manualmente")
        
        if submit_manual:
            nuevo_capital = capital_actual + m_impacto
            nuevo_rend = ((nuevo_capital - 100.0) / 100.0) * 100
            nueva_fila = pd.DataFrame([{
                "Fecha_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Activo": m_activo,
                "Estrategia": m_estrat,
                "Sensibilidad": m_sens,
                "Precio_Mercado": m_precio,
                "Resultado": m_res,
                "Impacto_USD": m_impacto,
                "Capital_Acumulado": round(nuevo_capital, 2),
                "Rendimiento_Total_Pct": f"{nuevo_rend:+.2f}%",
                "Contexto": "Registro manual realizado desde la app web."
            }])
            
            df_actualizado = pd.concat([df_original, nueva_fila], ignore_index=True)
            df_actualizado.to_csv(archivo_csv, index=False)
            st.success("✅ Operación registrada y guardada exitosamente en el historial unificado.")
            st.rerun()

# --- PESTAÑA 6: GESTIÓN Y EXPORTACIÓN ---
with tab_exportar:
    st.subheader("Herramientas de Respaldo y Exportación de Datos")
    st.markdown("Descarga los archivos limpios y procesados para auditorías o análisis externos en hojas de cálculo.")
    
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        if not df_original.empty:
            csv_data = df_original.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Base de Datos Completa (.CSV)",
                data=csv_data,
                file_name="historial_oculoos_general_completo.csv",
                mime="text/csv"
            )
        else:
            st.info("No hay datos para descargar todavía.")
    with col_exp2:
        if not df.empty:
            csv_filtrado = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Datos Filtrados Actuales (.CSV)",
                data=csv_filtrado,
                file_name="historial_oculoos_filtrado.csv",
                mime="text/csv"
            )

# ==========================================
# 8. PIE DE PÁGINA INSTITUCIONAL
# ==========================================
st.markdown("---")
st.markdown("🔒 **Oculoos Terminal Engine Pro v4.5** - Plataforma Analítica Independiente, Multi-Activo y de Alto Rendimiento.")
