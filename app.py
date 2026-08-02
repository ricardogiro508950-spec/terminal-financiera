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

# --- Estilos CSS Personalizados ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Oculoos Terminal Financiera & Motor de Simulación")
st.markdown("Plataforma analítica centralizada, gestión de riesgo institucional y control multi-activo en tiempo real.")

# --- Barra Lateral: Configuración y Controles Técnicos ---
st.sidebar.header("⚙️ Configuración del Sistema")

activo_seleccionado = st.sidebar.selectbox(
    "Seleccionar Mercado / Activo:",
    ["Bitcoin (BTCUSDT)", "Ethereum (ETHUSDT)", "Oro / XAU", "Nasdaq / NQ", "Petróleo / WTI"]
)

estrategia_seleccionada = st.sidebar.selectbox(
    "Seleccionar Estrategia Activa:",
    [
        "Cazador de Pullbacks", 
        "Cruce de EMAs (Institucional)", 
        "Ruptura de Rango de Volumen", 
        "Retrocesos de Fibonacci (Aura/Niveles Clave)",
        "Confluencia Avanzada (Gann + Fibo)"
    ]
)

sensibilidad_nivel = st.sidebar.selectbox(
    "Nivel de Sensibilidad:",
    [
        "Sensibilidad 0 (Estándar/Base)", 
        "Sensibilidad 1 (Moderada)", 
        "Sensibilidad 2 (Activa)", 
        "Sensibilidad 3 (Agresiva/Exploratoria)"
    ]
)

st.sidebar.subheader("📊 Parámetros de Gestión de Riesgo")
riesgo_op = st.sidebar.slider("Riesgo Máximo por Operación (%)", 0.5, 3.0, 1.0, 0.1)
drawdown_max = st.sidebar.slider("Límite de Pérdida Diaria (%)", 1.0, 10.0, 3.0, 0.5)
apalancamiento = st.sidebar.selectbox("Factor de Apalancamiento", ["1x", "5x", "10x", "20x"])

# --- Carga y Procesamiento del Historial (CSV Unificado) ---
archivo_csv = "historial_sensibilidades_real.csv"

if os.path.exists(archivo_csv):
    try:
        df = pd.read_csv(archivo_csv)
        
        # Métricas Principales del Dashboard
        capital_actual = df.iloc[-1]['Capital_Acumulado'] if not df.empty else 100.0
        rendimiento_global = df.iloc[-1]['Rendimiento_Total_Pct'] if not df.empty else "+0.00%"
        total_operaciones = len(df)
        
        # Cálculo de tasa de acierto (WinRate simulado/real según resultados)
        if not df.empty and 'Resultado' in df.columns:
            ganadas = df[df['Resultado'].str.contains("GANANCIA", na=False)].shape[0]
            win_rate = (ganadas / total_operaciones) * 100 if total_operaciones > 0 else 0.0
        else:
            win_rate = 0.0

        # --- Panel de Métricas Superior ---
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
        tab_bitacora, tab_rendimiento, tab_indicadores, tab_config = st.tabs([
            "📋 Bitácora en Vivo", 
            "📊 Rendimiento por Estrategia", 
            "📉 Indicadores y Motores Matemáticos", 
            "⚙️ Configuración y Exportación"
        ])

        with tab_bitacora:
            st.subheader("Registro Detallado de Operaciones (Sincronizado con Nube)")
            
            # Filtros interactivos para la tabla
            filtro_activo = st.selectbox("Filtrar por Activo en Bitácora:", ["Todos"] + list(df['Activo'].unique()) if 'Activo' in df.columns else ["Todos"])
            if filtro_activo != "Todos":
                df_filtrado = df[df['Activo'] == filtro_activo]
            else:
                df_filtrado = df
                
            st.dataframe(df_filtrado, use_container_width=True)

        with tab_rendimiento:
            st.subheader("Estadísticas de Rentabilidad Cruzada")
            if not df.empty and 'Estrategia' in df.columns:
                # Análisis de impacto por estrategia
                resumen_est = df.groupby('Estrategia')['Impacto_USD'].agg(['sum', 'count']).reset_index()
                resumen_est.columns = ['Estrategia', 'Impacto Total (USD)', 'Total Operaciones']
                st.dataframe(resumen_est, use_container_width=True)
                
                # Gráfico de rendimiento acumulado
                if 'Capital_Acumulado' in df.columns:
                    st.line_chart(df['Capital_Acumulado'])
            else:
                st.info("Generando suficientes métricas de rendimiento...")

        with tab_indicadores:
            st.subheader("Motor Técnico y Simulación Matemática")
            st.write("Visualización interna del comportamiento del precio y filtros de volatilidad ATR / EMAs / RSI.")
            
            # Gráfico de simulación de precios con base en los datos reales de mercado
            if not df.empty and 'Precio_Mercado' in df.columns:
                st.line_chart(df.set_index('Fecha_Hora')['Precio_Mercado'])
            else:
                st.info("Esperando flujo de precios en tiempo real...")

        with tab_config:
            st.subheader("Exportación y Respaldo de Datos")
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Base de Datos Completa (.CSV)",
                data=csv_data,
                file_name="historial_oculoos_completo.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error procesando la estructura de datos: {e}")
else:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="💰 Capital Base", value="$100.00 USD")
    with col2:
        st.metric(label="📊 Rendimiento Global", value="+0.00%")
    with col3:
        st.metric(label="🎯 Tasa de Acierto", value="0.0%")
    with col4:
        st.metric(label="📈 Operaciones Totales", value="0")
        
    st.warning("⚠️ El motor en la nube está activo pero aún no ha registrado operaciones. Los datos aparecerán automáticamente en cuanto se ejecute el primer ciclo.")

# --- Pie de Página Técnico ---
st.markdown("---")
st.markdown("🔒 **Oculoos Engine** - Sistema de Alta Precisión y Control de Riesgo Multi-Activo.")
