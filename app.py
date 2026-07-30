import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Configuración de la página (Diseño amplio para gráficos institucionales)
st.set_page_config(
    page_title="Terminal Financiera Institucional", page_icon="📊", layout="wide"
)

st.title("📊 Terminal Financiera Institucional v2.0")
st.caption(
    "Panel de Control Patrimonial Avanzado | Análisis Cuantitativo, Macroeconomía"
    " y Gestión de Riesgo"
)
st.markdown("---")


# Función para calcular el RSI (Índice de Fuerza Relativa)
def calculate_rsi(series, period=14):
  delta = series.diff()
  gain = delta.clip(lower=0)
  loss = -1 * delta.clip(upper=0)
  avg_gain = gain.rolling(window=period).mean()
  avg_loss = loss.rolling(window=period).mean()
  rs = avg_gain / avg_loss
  return 100 - (100 / (1 + rs))


# Descarga de datos macro y de mercado optimizada con caché
@st.cache_data(ttl=600)
def load_data():
  tickers = {
      "Bitcoin": "BTC-USD",
      "Oro": "GC=F",
      "DXY (Dólar)": "DX-Y.NYB",
      "Bonos 10Y": "^TNX",
  }
  data = {}
  history = {}
  for name, ticker in tickers.items():
    try:
      t = yf.Ticker(ticker)
      df = t.history(period="6mo")
      if not df.empty:
        history[name] = df
        current_price = df["Close"].iloc[-1]
        prev_price = df["Close"].iloc[-2] if len(df) >= 2 else current_price
        change = ((current_price - prev_price) / prev_price) * 100
        data[name] = {"price": current_price, "change": change}
      else:
        data[name] = {"price": 0.0, "change": 0.0}
    except Exception:
      data[name] = {"price": 0.0, "change": 0.0}
  return data, history


market_data, market_history = load_data()

# ==========================================
# 1. PANEL MACROECONÓMICO Y DE MERCADOS
# ==========================================
st.subheader("🌐 Panel Intermercados y Macroeconomía")
col1, col2, col3, col4 = st.columns(4)

btc_info = market_data.get("Bitcoin", {"price": 0, "change": 0})
gold_info = market_data.get("Oro", {"price": 0, "change": 0})
dxy_info = market_data.get("DXY (Dólar)", {"price": 0, "change": 0})
bond_info = market_data.get("Bonos 10Y", {"price": 0, "change": 0})

col1.metric(
    "Bitcoin (BTC/USD)",
    f"${btc_info['price']:,.2f}",
    f"{btc_info['change']:.2f}%",
)
col2.metric(
    "Oro (XAU/USD)", f"${gold_info['price']:,.2f}", f"{gold_info['change']:.2f}%"
)
col3.metric(
    "Índice Dólar (DXY)",
    f"{dxy_info['price']:,.2f}",
    f"{dxy_info['change']:.2f}%",
)
col4.metric(
    "Bono 10 Años (US10Y)",
    f"{bond_info['price']:,.2f}",
    f"{bond_info['change']:.2f}%",
)

st.markdown("---")

# ==========================================
# 2. MOTOR TÉCNICO Y GRÁFICOS INTERACTIVOS (PLOTLY)
# ==========================================
st.subheader("📈 Análisis Cuantitativo & Gráficos Interactivos")

asset_choice = st.selectbox(
    "Seleccione activo para análisis técnico detallado:", ["Bitcoin", "Oro"]
)

if asset_choice in market_history:
  df_asset = market_history[asset_choice].copy()
  df_asset["EMA_50"] = df_asset["Close"].ewm(span=50, adjust=False).mean()
  df_asset["EMA_200"] = (
      df_asset["Close"].ewm(span=200, adjust=False).mean()
      if len(df_asset) >= 200
      else df_asset["Close"].ewm(span=len(df_asset), adjust=False).mean()
  )
  df_asset["RSI"] = calculate_rsi(df_asset["Close"])

  current_close = df_asset["Close"].iloc[-1]
  current_ema50 = df_asset["EMA_50"].iloc[-1]
  current_ema200 = df_asset["EMA_200"].iloc[-1]
  current_rsi = df_asset["RSI"].iloc[-1]

  t_col1, t_col2, t_col3 = st.columns(3)
  t_col1.metric(
      "RSI (14 períodos)",
      f"{current_rsi:.2f}",
      (
          "Sobrecompra (>70)"
          if current_rsi > 70
          else ("Sobreventa (<30)" if current_rsi < 30 else "Zona Neutral")
      ),
  )
  t_col2.metric("EMA 50", f"${current_ema50:,.2f}")
  t_col3.metric("EMA 200", f"${current_ema200:,.2f}")

  # Gráfico de Velas con Plotly
  fig = go.Figure()
  fig.add_trace(
      go.Candlestick(
          x=df_asset.index,
          open=df_asset["Open"],
          high=df_asset["High"],
          low=df_asset["Low"],
          close=df_asset["Close"],
          name="Precio",
      )
  )
  fig.add_trace(
      go.Scatter(
          x=df_asset.index,
          y=df_asset["EMA_50"],
          line=dict(color="orange", width=1.5),
          name="EMA 50",
      )
  )
  fig.add_trace(
      go.Scatter(
          x=df_asset.index,
          y=df_asset["EMA_200"],
          line=dict(color="blue", width=1.5),
          name="EMA 200",
      )
  )

  fig.update_layout(
      title=f"Acción del Precio e Indicadores - {asset_choice}",
      yaxis_title="Precio (USD)",
      xaxis_title="Fecha",
      template="plotly_white",
      height=500,
      margin=dict(l=20, r=20, t=40, b=20),
  )
  st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ==========================================
# 3. ALGORITMO DE DECISIÓN INSTITUCIONAL CONFLUENTE
# ==========================================
st.subheader("🧠 Algoritmo de Decisión Cuantitativo (Confluencia)")

score = 0
reasons = []

if "Bitcoin" in market_history and len(market_history["Bitcoin"]) > 0:
  btc_df = market_history["Bitcoin"]
  btc_close = btc_df["Close"].iloc[-1]
  ema_50_val = btc_df["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
  rsi_val = calculate_rsi(btc_df["Close"]).iloc[-1]

  if btc_close > ema_50_val:
    score += 1
    reasons.append("✔ Precio de Bitcoin sobre la EMA de 50 (Tendencia alcista)")
  else:
    score -= 1
    reasons.append(
        "✖ Precio de Bitcoin bajo la EMA de 50 (Tendencia bajista o de"
        " precaución)"
    )

  if 40 <= rsi_val <= 60:
    score += 1
    reasons.append("✔ RSI en rango de equilibrio saludable")
  elif rsi_val > 70:
    score -= 1
    reasons.append("⚠ RSI en zona de Sobrecompra (Riesgo de corrección)")
  elif rsi_val < 30:
    score += 1
    reasons.append(
        "✔ RSI en zona de Sobreventa (Posible oportunidad de acumulación)"
    )

dxy_change = dxy_info["change"]
if dxy_change < 0:
  score += 1
  reasons.append("✔ Dólar (DXY) a la baja (Favorable para activos de riesgo)")
else:
  score -= 1
  reasons.append(
      "✖ Dólar (DXY) al alza (Presión bajista sobre cripto y materias primas)"
  )

st.markdown(f"**Puntuación de Confluencia Institucional:** `{score}/3`")
for r in reasons:
  st.write(r)

if score >= 2:
  st.success(
      "🟢 **ESTADO ACTIVO: Condiciones favorables.** Ventana propicia para"
      " despliegue moderado de capital con gestión de riesgo ajustada."
  )
elif score == 1:
  st.warning(
      "🟡 **ESTADO DE PRECAUCIÓN:** Señales mixtas en el mercado. Mantener"
      " alta ponderación de capital en liquidez (USDT)."
  )
else:
  st.error(
      "🔴 **ESTADO DEFENSIVO:** Alta presión macroeconómica o técnica"
      " adversa. Priorizar preservación de capital."
  )

st.markdown("---")
st.caption(
    "Desarrollado en Python con Arquitectura Cuantitativa y Plotly. Datos en"
    " tiempo real."
)
