# core/backtest_engine.py
import pandas as pd
import numpy as np

def run_backtest_ema_crossover(df, short_window=50, long_window=200):
    """
    Simula una estrategia cuantitativa de cruce de EMAs sobre datos históricos.
    Calcula el Win Rate y el Retorno Total.
    """
    if len(df) < long_window:
        return {"total_trades": 0, "win_rate": 0, "pnl_pct": 0.0}

    # Copiamos el dataframe para no alterar el original
    backtest_df = df.copy()
    
    # Calculamos las EMAs
    backtest_df['EMA_short'] = backtest_df['Close'].ewm(span=short_window, adjust=False).mean()
    backtest_df['EMA_long'] = backtest_df['Close'].ewm(span=long_window, adjust=False).mean()

    # Lógica del Algoritmo: 1.0 = Comprado (Long), 0.0 = Fuera del mercado
    backtest_df['Signal'] = 0.0
    backtest_df.loc[backtest_df['EMA_short'] > backtest_df['EMA_long'], 'Signal'] = 1.0
    
    # Identificamos cada vez que se abre o cierra una posición
    backtest_df['Position'] = backtest_df['Signal'].diff()

    # Calculamos los retornos diarios reales del activo
    backtest_df['Daily_Return'] = backtest_df['Close'].pct_change()
    
    # El retorno de nuestra estrategia es el retorno diario SOLO cuando estamos comprados (Signal == 1)
    backtest_df['Strategy_Return'] = backtest_df['Signal'].shift(1) * backtest_df['Daily_Return']

    # Métricas de rendimiento
    total_trades = abs(backtest_df['Position']).sum() / 2  # Entradas y salidas
    winning_days = len(backtest_df[backtest_df['Strategy_Return'] > 0])
    losing_days = len(backtest_df[backtest_df['Strategy_Return'] < 0])
    
    win_rate = (winning_days / (winning_days + losing_days)) * 100 if (winning_days + losing_days) > 0 else 0
    
    # Cálculo del PnL compuesto (Interés compuesto)
    total_pnl = (np.exp(np.log1p(backtest_df['Strategy_Return']).sum()) - 1) * 100

    return {
        "total_trades": int(total_trades),
        "win_rate": round(win_rate, 2),
        "pnl_pct": round(total_pnl, 2)
    }
