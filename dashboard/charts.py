# dashboard/charts.py
import plotly.graph_objects as go
from utils.config import USER_DRAWING_STYLE

def create_institutional_chart(df, asset_name, timeframe, show_emas=True, orb_levels=None):
    """Genera el gráfico avanzado de velas con soporte de dibujo y niveles institucionales."""
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], 
        low=df["Low"], close=df["Close"], name=asset_name
    ))

    if show_emas and "EMA_50" in df.columns and "EMA_200" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA_50"], line=dict(color="orange", width=1.5), name="EMA 50"))
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA_200"], line=dict(color="blue", width=1.5), name="EMA 200"))

    if orb_levels:
        orb_high, orb_low = orb_levels
        if orb_high and orb_low:
            fig.add_hline(y=orb_high, line_dash="dash", line_color="#10b981", annotation_text="Techo ORB")
            fig.add_hline(y=orb_low, line_dash="dash", line_color="#ef4444", annotation_text="Piso ORB")

    fig.update_layout(
        template="plotly_dark", 
        height=650, 
        margin=dict(l=20, r=20, t=40, b=20), 
        dragmode='zoom', 
        xaxis=dict(rangeslider=dict(visible=False)),
        title=f"Terminal Cuantitativa - {asset_name} [{timeframe}]",
        newshape=USER_DRAWING_STYLE
    )
    return fig
