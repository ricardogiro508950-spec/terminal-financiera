# utils/config.py

# ==========================================
# CONFIGURACIÓN GENERAL DEL SISTEMA
# ==========================================
ACTIVOS_DISPONIBLES = ["Bitcoin", "Oro", "Petróleo"]

TICKER_MAP = {
    "Bitcoin": "BTC-USD",
    "Oro": "GC=F",
    "Petróleo": "CL=F",
    "DXY (Dólar)": "DX-Y.NYB",
    "Bonos 10Y": "^TNX"
}

PRECIO_DEFECTO = {
    "Bitcoin": 60000.0,
    "Oro": 2000.0,
    "Petróleo": 75.0
}

# Comisiones y Fricción de Mercado
FEE_BINANCE = 0.001  # 0.1% comisión estándar Maker/Taker de Binance

# ==========================================
# CONFIGURACIÓN VISUAL (PLOTLY & UI)
# ==========================================
PLOTLY_CONFIG = {
    'scrollZoom': True,
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToAdd': ['drawline', 'drawrect', 'eraseshape'],
    'modeBarButtonsToRemove': ['lasso2d', 'select2d']
}

# Estilo Neón para las marcas del usuario
USER_DRAWING_STYLE = dict(
    line_color="#00FFFF", 
    fillcolor="rgba(0, 255, 255, 0.15)", 
    line_width=2
)
