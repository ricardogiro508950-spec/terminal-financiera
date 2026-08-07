import os
import time
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

# ==========================================
# CONFIGURACIÓN (TUS CREDENCIALES)
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Usamos un activo real muy líquido en Binomo
ACTIVO = "EURUSD=X" 

def enviar_alerta(mensaje):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=datos, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")

def calcular_indicadores(df):
    """Inyecta RSI, EMAs y MACD para la estrategia de 5 min"""
    # RSI (14 periodos)
    delta = df['Close'].diff()
    ganancia = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    perdida = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = ganancia / perdida.replace(0, pd.NA)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # EMAs (9 y 21)
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # MACD 
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['Senal_MACD'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Histograma'] = df['MACD'] - df['Senal_MACD']
    
    return df

def esperar_cierre_vela():
    """Sincronizador: Espera hasta el segundo 58 del minuto actual"""
    ahora = datetime.now()
    segundos_restantes = 58 - ahora.second
    if segundos_restantes < 0:
        segundos_restantes = 60 + segundos_restantes
    time.sleep(segundos_restantes)

def motor_binomo():
    print(f"🤖 Motor Binomo Sincronizado. Analizando {ACTIVO} en velas de 1m...")
    ultima_alerta = None
    
    while True:
        try:
            # 1. El bot se pausa solo y despierta en el segundo 58 de la vela
            esperar_cierre_vela()
            
            # 2. Descarga la data de la vela que está a 2 segundos de cerrar
            data = yf.download(ACTIVO, period="1d", interval="1m", progress=False)
            
            if data.empty or len(data) < 30:
                time.sleep(2)
                continue
                
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
                
            data = calcular_indicadores(data)
            
            # 3. Lectura de variables técnicas
            ema9 = float(data['EMA_9'].iloc[-1])
            ema21 = float(data['EMA_21'].iloc[-1])
            rsi = float(data['RSI'].iloc[-1])
            hist_actual = float(data['Histograma'].iloc[-1])
            hist_previo = float(data['Histograma'].iloc[-2])
            
            senal = None
            
            # ==========================================
            # FILTRO DE CONFLUENCIA DE IMPULSO
            # ==========================================
            # COMPRA: Tendencia alcista + MACD creciendo + RSI sano (no sobrecomprado)
            if (ema9 > ema21) and (hist_actual > 0 and hist_actual > hist_previo) and (50 < rsi < 70):
                senal = "🟢 COMPRAR | SUBE"
                
            # VENTA: Tendencia bajista + MACD cayendo + RSI sano (no sobrevendido)
            elif (ema9 < ema21) and (hist_actual < 0 and hist_actual < hist_previo) and (30 < rsi < 50):
                senal = "🔴 VENDER | BAJA"
            
            hora_alerta = datetime.now().strftime("%H:%M")
            
            # 4. Disparo inmediato para entrar en Binomo
            if senal and hora_alerta != ultima_alerta:
                mensaje = (
                    f"⚡ **EJECUCIÓN BINOMO** ⚡\n\n"
                    f"🌍 **Activo:** EUR/USD (Mercado Real)\n"
                    f"🎯 **Acción:** {senal}\n"
                    f"⏱ **Reloj:** Poner a 5 Minutos\n\n"
                    f"⚙️ **Confirmación Interna:**\n"
                    f"• Momentum MACD: A favor\n"
                    f"• RSI: {rsi:.1f}\n\n"
                    f"⚠️ *Entrar exactamente al iniciar la siguiente vela.*"
                )
                enviar_alerta(mensaje)
                print(f"[{hora_alerta}] Señal Binomo: {senal}")
                ultima_alerta = hora_alerta
                
                # Bloqueo de 5 minutos mientras dura tu operación en Binomo
                time.sleep(300)
            
            # Si no hubo señal, espera 2 segundos para llegar al segundo 00 y reiniciar ciclo
            time.sleep(2)
            
        except Exception as e:
            print(f"Error analizando: {e}")
            time.sleep(5)

if __name__ == "__main__":
    enviar_alerta("✅ Motor Algorítmico para BINOMO activado. Sincronizando reloj de servidor...")
    motor_binomo()
