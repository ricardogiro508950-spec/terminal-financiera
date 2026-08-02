import streamlit as st
import pandas as pd
import os

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Oculoos Terminal Financiera x S. Loaiza",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Terminal Financiera Oculoos x S. Loaiza (222 km/h)")
st.markdown("Panel de Control Institucional, Gestión de Riesgo y Mapeo en Vivo.")

# --- Barra Lateral: Configuración y Estrategias ---
st.sidebar.header("⚙️ Configuración del Sistema")

estrategia_seleccionada = st.sidebar.selectbox(
    "Seleccione Estrategia Activa:",
    [
        "Cazador de Pullbacks (Estrat. 1)", 
        "Confirmación por OB en 1m (Estrat. 2)", 
        "Caja de Gann [0, 0.5, 1] + Fibo [0.85/0.95] (Estrat. 3)", 
        "Confluencia Institucional VIP (Gann 0.5 + Fibo 0.618/0.95)"
    ]
)

st.sidebar.subheader("📊 Gestión de Riesgo (222 km/h)")
riesgo_operacion = st.sidebar.slider("Riesgo Máximo por Operación (%)", 0.5, 2.0, 1.0) # Base estricta 1%[span_2](start_span)[span_2](end_span)
limite_diario = st.sidebar.slider("Pérdida Máxima Diaria (%)", 1.0, 5.0, 3.0) # Límite de 3%[span_3](start_span)[span_3](end_span)
ratio_minimo = st.sidebar.selectbox("Ratio Mínimo Aceptable", ["1:2", "1:3", "1:2.78"])

st.sidebar.info(
    "💡 **Reglas Institucionales:**\n"
    "- Stop Loss obligatorio al abrir la operación (máximo 2 minutos)[span_4](start_span)[span_4](end_span).\n"
    "- Riesgo máximo del 1% por trade para proteger el capital[span_5](start_span)[span_5](end_span)."
)

# --- Contenido Principal ---
col1, col2, col3 = st.columns(3)

archivo_csv = "historial_sensibilidades_real.csv"

# Carga de datos de la bitácora compartida desde la nube
if os.path.exists(archivo_csv):
    try:
        df = pd.read_csv(archivo_csv)
        
        # Métricas principales de la cuenta
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
        st.subheader("📋 Bitácora Histórica en Tiempo Real (Sincronizada con Nube y Telegram)")
        st.dataframe(df, use_container_width=True)
        
        # Botón para descargar el historial en CSV
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Bitácora Completa (CSV)",
            data=csv_data,
            file_name="bitacora_oculoos_institucional.csv",
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
        
    st.warning("⚠️ Esperando registros iniciales del bot en la nube para poblar las métricas.")

# --- Sección de Referencia Técnica y Metodología ---
st.markdown("---")
st.subheader("📐 Parámetros Técnicos del Sistema (222 km/h)")
tab1, tab2, tab3 = st.tabs(["Caja de Gann", "Fibonacci Institucional", "Reglas de Ejecución"])

with tab1:
    st.markdown("""
    * **Niveles Activos:** `0`, `0.5`, `1`[span_6](start_span)[span_6](end_span).
    * **Enfoque:** El nivel `0.5` representa la zona crítica de decisión institucional donde el mercado define continuidad o reversión[span_7](start_span)[span_7](end_span).
    * **Visualización:** Etiquetas izquierda y derecha activas para evitar errores de lectura[span_8](start_span)[span_8](end_span).
    """)

with tab2:
    st.markdown("""
    * **Niveles Activos:** `0`, `0.5`, `0.618`, `0.85`, `0.95`, `1`[span_9](start_span)[span_9](end_span).
    * **Enfoque clave:** Los niveles `0.85` y `0.95` son las zonas ocultas que generan las reacciones más fuertes de precio en activos de alta volatilidad[span_10](start_span)[span_10](end_span).
    """)

with tab3:
    st.markdown("""
    1. **Confluencia:** Cuando la Caja de Gann y los niveles clave de Fibonacci apuntan al mismo precio, la zona adquiere máxima probabilidad estadística[span_11](start_span)[span_11](end_span).
    2. **Control de Riesgo:** No sobreoperar; el límite diario estricto es de 3 pérdidas consecutivas o 3% de drawdown[span_12](start_span)[span_12](end_span).
    3. **Disciplina:** Todo trade debe contar con su respectivo escenario analítico previo[span_13](start_span)[span_13](end_span).
    """)
