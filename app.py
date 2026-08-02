import streamlit as st
import pandas as pd

st.title("🛡️ Terminal Financiera Oculoos x S. Loaiza (222 km/h)")

# --- Selector de Estrategias Oficiales ---
st.sidebar.header("⚙️ Configuración de Estrategias")
estrategia_seleccionada = st.sidebar.selectbox(
    "Seleccione Estrategia Activa:",
    [
        "Cazador de Pullbacks (Estrat. 1)", 
        "Confirmación por OB en 1m (Estrat. 2)", 
        "Caja de Gann [0, 0.5, 1] + Fibo [0.85/0.95] (Estrat. 3)", 
        "Confluencia Institucional VIP (Gann 0.5 + Fibo 0.618/0.95)"
    ]
)

# --- Parámetros de Gestión de Riesgo Institucional ---
st.sidebar.subheader("📊 Gestión de Riesgo (222 km/h)")
riesgo_operacion = st.sidebar.slider("Riesgo Máximo por Operación (%)", 0.5, 2.0, 1.0) # Base 1% recomendada
limite_diario = st.sidebar.slider("Pérdida Máxima Diaria (%)", 1.0, 5.0, 3.0) # Límite estricto 3%
ratio_minimo = st.sidebar.text_input("Ratio Mínimo Aceptable", "1:2 o 1:3")

# --- Visualización en la App ---
st.subheader(f"📈 Monitoreo Activo: {estrategia_seleccionada}")
st.write(f"Parámetros de control aplicados bajo la directriz institucional de S. Loaiza.")

# Carga de la bitácora interna de la app
try:
    df_bitacora = pd.read_csv("historial_sensibilidades_real.csv")
    st.dataframe(df_bitacora.tail(10), use_container_width=True)
except Exception:
    st.info("Esperando registros en la bitácora de la nube...")
