import streamlit as st
import pandas as pd
import os

st.set_page_config(
    page_title="Oculoos Terminal Multi-Activo",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Oculoos Terminal Financiera & Analizador Multi-Activo")
st.markdown("Panel centralizado sincronizado con el motor de la nube y Telegram.")

archivo_csv = "historial_sensibilidades_real.csv"

if os.path.exists(archivo_csv):
    try:
        df = pd.read_csv(archivo_csv)
        
        # Métricas principales
        ultimo_capital = df.iloc[-1]['Capital_Acumulado'] if not df.empty else 100.0
        rendimiento_global = df.iloc[-1]['Rendimiento_Total_Pct'] if not df.empty else "+0.00%"
        total_ops = len(df)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="💰 Capital Total Actual", value=f"${ultimo_capital:,.2f} USD")
        with col2:
            st.metric(label="📊 Rendimiento Global", value=rendimiento_global)
        with col3:
            st.metric(label="📈 Operaciones Totales", value=str(total_ops))

        st.markdown("---")
        st.subheader("📊 Análisis de Rentabilidad por Activo y Estrategia")
        
        if not df.empty and 'Activo' in df.columns:
            # Agrupación analítica para ver cuál activo y estrategia rinde más
            resumen_activo = df.groupby('Activo')['Impacto_USD'].sum().reset_index()
            st.write("### Impacto de Ganancias/Pérdidas por Mercado")
            st.dataframe(resumen_activo, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Bitácora Histórica Detallada")
        st.dataframe(df, use_container_width=True)
        
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Historial Completo (CSV)",
            data=csv_data,
            file_name="historial_oculoos_multiactivo.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error procesando los datos: {e}")
else:
    st.warning("⚠️ Esperando conexión con el motor en la nube para sincronizar los datos multi-activo.")
