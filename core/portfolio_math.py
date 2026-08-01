# core/portfolio_math.py
import numpy as np
import pandas as pd

def run_monte_carlo_simulation(current_price, days_forward=30, num_simulations=500, volatility=0.02, drift=0.0005):
    """
    Ejecuta simulaciones de Monte Carlo para proyectar la trayectoria probabilística 
    del precio de un activo en el corto/mediano plazo.
    """
    try:
        # Matriz para almacenar los caminos de precios (días x simulaciones)
        price_paths = np.zeros((days_forward, num_simulations))
        price_paths[0] = current_price

        for t in range(1, days_forward):
            # Movimiento Browniano Geométrico con Deriva (Drift) y Volatilidad
            random_shocks = np.random.normal(0, 1, num_simulations)
            price_paths[t] = price_paths[t-1] * np.exp((drift - 0.5 * volatility**2) + volatility * random_shocks)

        return price_paths
    except Exception as e:
        return None

def calculate_kelly_criterion(win_rate_pct, win_loss_ratio):
    """
    Calcula el Criterio de Kelly Óptimo para determinar el porcentaje matemático 
    de capital que se debe arriesgar por operación.
    Kelly % = W - [(1 - W) / R]
    Donde W = Win Rate (probabilidad de éxito) y R = Ratio Ganancia/Pérdida.
    """
    if win_loss_ratio <= 0:
        return 0.0
    
    w = win_rate_pct / 100.0
    r = win_loss_ratio
    
    kelly_pct = w - ((1.0 - w) / r)
    
    # Por seguridad institucional, comúnmente se usa el "Half-Kelly" (la mitad del valor óptimo) 
    # para evitar volatilidades agresivas en la cuenta.
    half_kelly = (kelly_pct / 2.0) * 100.0
    
    return max(0.0, round(half_kelly, 2))
