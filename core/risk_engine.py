# core/risk_engine.py

def calculate_position_size(capital, risk_pct, stop_loss_pct):
    """
    Calcula el tamaño de la posición seguro basado en la gestión de riesgo institucional.
    """
    if stop_loss_pct <= 0:
        return 0.0, 0.0
        
    riesgo_usd = capital * (risk_pct / 100)
    tamano_posicion = riesgo_usd / (stop_loss_pct / 100)
    
    return tamano_posicion, riesgo_usd
