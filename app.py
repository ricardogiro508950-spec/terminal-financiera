import streamlit as st
import pandas as pd
import os

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Oculoos Terminal Financiera",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Oculoos Terminal Financiera & Simulación")
st.markdown("Panel de Control, Bitácora y Mapeo en Vivo.")

# --- Barra Lateral: Configuración y Estrategias ---
st.sidebar.header("⚙️ Configuración del Sistema")

estrategia_seleccionada = st.sidebar.selectbox(
    "Seleccione Estrategia Activa:",
    [
        "Cazador de Pullbacks", 
        "Cruce de EMAs (Institucional)", 
        "Ruptura de Rango de Volumen", 
        "Retrocesos de Fibonacci (Aura/Niveles Clave)",
        "Confluencia Avanzada (Gann + Fibo)"
    ]
)

st.sidebar.subheader("📊 Parámetros de Riesgo")
riesgo_operacion = st.sidebar.slider("Riesgo por Operación (%)", 0.5, 2.0, 1.0)
limite_diario = st.sidebar.slider("Pérdida Máxima Diaria (%)", 1.0, 5.0, 3.0)

# --- Contenido Principal ---
col1, col2, col3 = st.columns(3)

archivo_csv = "historial_sensibilidades_real.csv"

if os.path.exists(archivo_csv):
    try:
        df = pd.read_csv(archivo_csv)
        
        ultimo_capital = df.iloc[-1]['Capital_Acumulado'] if not df.empty else 100.0
        rendimiento_global = df.iloc[-1]['Rendimiento_Total_Pct'] if not df.empty else "+0.00%"
        total_ops = len(df)
        
        with col1:
            st.metric(label="💰 Capital Total Actual", value=f"${ultimo_capital:,.2f} USD")
        with col2:
            st.metric(label="📊 Rendimiento Global", value=rendimiento_global)
        with col3:
            st.metric(label="📈 Operaciones Registradas", value=str(total_ops))

        st.markdown("---")
        st.subheader("📋 Bitácora de Oculoos Simulación en Tiempo Real")
        st.dataframe(df, use_container_width=True)
        
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Bitácora Completa (CSV)",
            data=csv_data,
            file_name="bitacora_oculoos_simulacion.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error al procesar la bitácora: {e}")
else:
    with col1:
        st.metric(label="💰 Capital Base", value="$100.00 USD")
    with col2:
        st.metric(label="📊 Rendimiento Global", value="+0.00%")
    with col3:
        st.metric(label="📈 Operaciones Registradas", value="0")
        
    st.warning("⚠️ Esperando registros del bot en la nube para poblar las métricas.")
