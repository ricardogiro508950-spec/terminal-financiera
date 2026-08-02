import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- Configuración Avanzada de la Página ---
st.set_page_config(
    page_title="Oculoos Terminal Financiera Profesional",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Estilos CSS Personalizados para la Interfaz ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 5px; color: white; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; }
    </style>
""", unsafe_allow_html=True)

# --- Encabezado Principal ---
st.title("🛡️ Oculoos Terminal Financiera & Motor Multi-Activo")
st.markdown("Plataforma analítica centralizada, control de riesgo institucional y sincronización en tiempo real con el motor de la nube.")

# --- Barra Lateral: Configuración Completa del Sistema ---
st.sidebar.header("⚙️ Panel de Control & Estrategias")

activo_seleccionado = st.sidebar.selectbox(
    "Seleccionar Mercado / Activo:",
    ["Todos los Activos", "Bitcoin (BTCUSDT)", "Ethereum (ETHUSDT)", "Oro / XAU", "Nasdaq / NQ", "Petróleo / WTI"]
)

estrategia_seleccionada = st.sidebar.selectbox(
    "Seleccionar Estrategia Activa:",
    [
        "Todas las Estrategias",
        "Cazador de Pullbacks", 
        "Cruce de EMAs (Institucional)", 
        "Ruptura de Rango de Volumen", 
        "Retrocesos de Fibonacci (Aura/Niveles Clave)",
        "Confluencia Avanzada (Gann + Fibo)"
    ]
)

sensibilidad_nivel = st.sidebar.selectbox(
    "Nivel de Sensibilidad del Motor:",
    [
        "Sensibilidad 0 (Estándar/Base)", 
        "Sensibilidad 1 (Moderada)", 
        "Sensibilidad 2 (Activa)", 
        "Sensibilidad 3 (Agresiva/Exploratoria)"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Parámetros de Gestión de Riesgo")
riesgo_op = st.sidebar.slider("Riesgo Máximo por Operación (%)", 0.5, 3.0, 1.0, 0.1)
drawdown_max = st.sidebar.slider("Límite de Pérdida Diaria (%)", 1.0, 10.0, 3.0, 0.5)
apalancamiento = st.sidebar.selectbox("Factor de Apalancamiento", ["1x", "5x", "10x", "20x"])

st.sidebar.info(
    "💡 **Instrucciones:**\n"
    "- Los datos se actualizan automáticamente desde el archivo de la nube.\n"
    "- Utiliza las pestañas principales para alternar entre análisis de rendimiento, bitácora y gráficos técnicos."
)

# --- Carga y Procesamiento del Historial (CSV Unificado) ---
archivo_csv = "historial_sensibilidades_real.csv"

if os.path.exists(archivo_csv):
    try:
        df = pd.read_csv(archivo_csv)
        
        # Validación de columnas básicas
        if df.empty:
            st.warning("⚠️ El archivo de bitácora está vacío actualmente.")
        
        # Filtrado dinámico según la barra lateral
        df_filtrado = df.copy()
        if activo_seleccionado != "Todos los Activos" and 'Activo' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Activo'].str.contains(activo_seleccionado.split()[0], case=False, na=False)]
            
        if estrategia_seleccionada != "Todas las Estrategias" and 'Estrategia' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Estrategia'] == estrategia_seleccionada]

        # Métricas Principales del Dashboard
        capital_actual = df.iloc[-1]['Capital_Acumulado'] if not df.empty else 100.0
        rendimiento_global = df.iloc[-1]['Rendimiento_Total_Pct'] if not df.empty else "+0.00%"
        total_operaciones = len(df)
        
        # Cálculo de WinRate (Tasa de acierto)
        if not df.empty and 'Resultado' in df.columns:
            ganadas = df[df['Resultado'].str.contains("GANANCIA", na=False)].shape[0]
            win_rate = (ganadas / total_operaciones) * 100 if total_operaciones > 0 else 0.0
        else:
            win_rate = 0.0

        # --- Panel de Métricas Superior (KPIs) ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="💰 Capital Total Actual", value=f"${capital_actual:,.2f} USD")
        with col2:
            st.metric(label="📊 Rendimiento Global", value=rendimiento_global)
        with col3:
            st.metric(label="🎯 Tasa de Acierto (WinRate)", value=f"{win_rate:.1f}%")
        with col4:
            st.metric(label="📈 Operaciones Totales", value=str(total_operaciones))

        st.markdown("---")

        # --- Pestañas de Análisis Completo ---
        tab_bitacora, tab_rendimiento, tab_activos, tab_indicadores, tab_config = st.tabs([
            "📋 Bitácora en Vivo", 
            "📊 Rendimiento por Estrategia", 
            "🌐 Rendimiento por Activo",
            "📉 Motor Técnico y Gráficos", 
            "⚙️ Respaldo y Datos"
        ])

        with tab_bitacora:
            st.subheader("Registro Detallado de Operaciones (Sincronizado con Nube)")
            st.markdown("Visualización completa de cada ejecución enviada por el bot a Telegram y almacenada en la base de datos.")
            
            if not df_filtrado.empty:
                st.dataframe(df_filtrado, use_container_width=True)
            else:
                st.info("No hay registros que coincidan con los filtros seleccionados en la barra lateral.")

        with tab_rendimiento:
            st.subheader("Estadísticas de Rentabilidad Cruzada por Estrategia")
            st.markdown("Análisis detallado de qué estrategias están generando mayor impacto positivo en dólares y volumen.")
            
            if not df.empty and 'Estrategia' in df.columns:
                resumen_est = df.groupby('Estrategia').agg(
                    Impacto_Total_USD=('Impacto_USD', 'sum'),
                    Total_Operaciones=('Impacto_USD', 'count')
                ).reset_index()
                
                st.dataframe(resumen_est, use_container_width=True)
                
                if 'Capital_Acumulado' in df.columns:
                    st.markdown("#### Evolución Gráfica del Capital Compuesto")
                    st.line_chart(df['Capital_Acumulado'])
            else:
                st.info("Recopilando suficientes métricas para el desglose por estrategia...")

        with tab_activos:
            st.subheader("Rendimiento Desglosado por Mercado / Activo")
            st.markdown("Compara el comportamiento del capital operando en Bitcoin, Ethereum, Oro, Nasdaq y Petróleo.")
            
            if not df.empty and 'Activo' in df.columns:
                resumen_activos = df.groupby('Activo').agg(
                    Impacto_USD=('Impacto_USD', 'sum'),
                    Operaciones=('Impacto_USD', 'count')
                ).reset_index()
                
                st.dataframe(resumen_activos, use_container_width=True)
                st.bar_chart(resumen_activos.set_index('Activo')['Impacto_USD'])
            else:
                st.info("Esperando datos multi-activo para generar la comparativa...")

        with tab_indicadores:
            st.subheader("Motor Técnico y Comportamiento del Precio")
            st.markdown("Seguimiento en tiempo real de los precios de mercado registrados por las llamadas a las APIs.")
            
            if not df.empty and 'Precio_Mercado' in df.columns and 'Fecha_Hora' in df.columns:
                st.line_chart(df.set_index('Fecha_Hora')['Precio_Mercado'])
            elif not df.empty and 'Precio_Binance' in df.columns and 'Fecha_Hora' in df.columns:
                st.line_chart(df.set_index('Fecha_Hora')['Precio_Binance'])
            else:
                st.info("El flujo de precios se graficará automáticamente al completarse nuevos ciclos.")

        with tab_config:
            st.subheader("Exportación y Respaldo del Historial")
            st.markdown("Descarga la base de datos completa en formato CSV para análisis externo o respaldos locales.")
            
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Base de Datos Completa (.CSV)",
                data=csv_data,
                file_name="historial_oculoos_multiactivo_completo.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error procesando la estructura de datos: {e}")
else:
    # Estado inicial si el archivo CSV aún no ha sido creado por el bot de la nube
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="💰 Capital Base", value="$100.00 USD")
    with col2:
        st.metric(label="📊 Rendimiento Global", value="+0.00%")
    with col3:
        st.metric(label="🎯 Tasa de Acierto", value="0.0%")
    with col4:
        st.metric(label="📈 Operaciones Totales", value="0")
        
    st.warning("⚠️ El motor en la nube se encuentra activo, pero aún no se han registrado operaciones en el archivo CSV compartido. Los datos aparecerán automáticamente en la interfaz en cuanto se ejecute el primer ciclo.")

# --- Pie de Página Técnico ---
st.markdown("---")
st.markdown("🔒 **Oculoos Engine Pro** - Sistema Centralizado de Alta Precisión y Control de Riesgo Multi-Activo.")
