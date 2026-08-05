import os
import time
import threading
import requests
import pandas as pd
import yfinance as yf
from flask import Flask
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE TELEGRAM
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Activos reales a vigilar
ACTIVOS = {
    "Oro (XAUUSD)": "GC=F",
    "Bitcoin": "BTC-USD",
    "Euro / Dólar": "EURUSD=X",
    "Dólar / Yen": "USDJPY=X",
    "Euro / Libra": "EURGBP=X"
}

# ==========================================
# SERVIDOR WEB (Para UptimeRobot y Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Motor Gann-Fibonacci 24/7 — Operando y registrando Logs."

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# FUNCIÓN DE TELEGRAM
# ==========================================
def enviar_alerta(mensaje):
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=datos, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")

# ==========================================
# EL MOTOR DEL ALGORITMO (GANN + FIBO)
# ==========================================
def analizar_mercado(nombre, ticker):
    try:
        # Descargamos suficientes datos para encontrar el rango
        df = yf.Ticker(ticker).history(period="2d", interval="5m")
        if df.empty or len(df) < 60:
            return None

        # Tomamos las últimas 50 velas (aprox 4 horas) para definir el rango de Gann
        ventana = df.tail(50)
        
        # Identificamos el máximo y el mínimo del rango
        maximo = ventana['High'].max()
        minimo = ventana['Low'].min()
        rango_total = maximo - minimo
        
        if rango_total == 0:
            return None

        # 1. CAJA DE GANN (Nivel 0.5 - Mitad exacta)
        gann_05 = maximo - (rango_total * 0.5)

        # Identificamos si el impulso principal fue alcista o bajista
        idx_max = ventana['High'].idxmax()
        idx_min = ventana['Low'].idxmin()

        # Anatomía de la última vela cerrada para confirmación (Gatillo)
        vela = df.iloc[-2]
        c = vela['Close']
        o = vela['Open']
        h = vela['High']
        l = vela['Low']
        
        cuerpo = abs(c - o)
        mecha_sup = h - max(c, o)
        mecha_inf = min(c, o) - l

        # Variables de Fibonacci
        zona_fibo_activa = False
        tipo_operacion = ""
        fibo_85 = 0
        fibo_95 = 0

        # ==========================================
        # ESCENARIO ALCISTA (Buscando Compras)
        # ==========================================
        if idx_max > idx_min: 
            # El precio subió y ahora está retrocediendo hacia abajo
            fibo_85 = maximo - (rango_total * 0.85)
            fibo_95 = maximo - (rango_total * 0.95)
            
            # Verificamos si el precio actual cayó a la zona del 85%-95%
            if fibo_95 <= l <= fibo_85:
                zona_fibo_activa = True
                tipo_operacion = "🟢 COMPRA"
                gatillo = mecha_inf > (1.5 * cuerpo) # Confirmación de rechazo alcista

        # ==========================================
        # ESCENARIO BAJISTA (Buscando Ventas)
        # ==========================================
        else:
            # El precio bajó y ahora está retrocediendo hacia arriba
            fibo_85 = minimo + (rango_total * 0.85)
            fibo_95 = minimo + (rango_total * 0.95)
            
            # Verificamos si el precio actual subió a la zona del 85%-95%
            if fibo_85 <= h <= fibo_95:
                zona_fibo_activa = True
                tipo_operacion = "🔴 VENTA"
                gatillo = mecha_sup > (1.5 * cuerpo) # Confirmación de rechazo bajista

        # ==========================================
        # DIAGNÓSTICO INTERNO (LOGS EN RENDER)
        # ==========================================
        distancia_gann = abs(c - gann_05) / c * 100
        print(f"[{nombre}] Precio: ${c:,.4f} | Rango Gann 0.5: ${gann_05:,.4f} | Distancia: {distancia_gann:.2f}%")

        # ==========================================
        # CONFLUENCIA FINAL
        # ==========================================
        # Si el precio está en la zona Fibo 85-95 y la vela muestra rechazo
        if zona_fibo_activa and gatillo:
            print(f"⭐⭐⭐ ¡CONFLUENCIA FIBONACCI ENCONTRADA EN {nombre}! ⭐⭐⭐")
            return {
                "señal": tipo_operacion, 
                "precio": c, 
                "fibo_85": fibo_85, 
                "fibo_95": fibo_95
            }

        return None

    except Exception as e:
        print(f"Error analizando {ticker}: {e}")
        return None

# ==========================================
# CICLO PRINCIPAL
# ==========================================
def ciclo_principal():
    while True:
        try:
            ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print("\n" + "="*50)
            print(f"🔄 ESCANEANDO ZONAS GANN Y FIBONACCI - {ahora}")
            print("="*50)

            for nombre, ticker in ACTIVOS.items():
                resultado = analizar_mercado(nombre, ticker)
                
                if resultado:
                    msj = (
                        f"🎯 *CONFLUENCIA INSTITUCIONAL DETECTADA*\n\n"
                        f"🌐 *Activo:* {nombre}\n"
                        f"📊 *Acción:* {resultado['señal']}\n"
                        f"💵 *Precio Actual:* ${resultado['precio']:,.4f}\n"
                        f"📐 *Zona Fibo (85%-95%):* ${resultado['fibo_85']:,.4f} - ${resultado['fibo_95']:,.4f}\n\n"
                        f"⚠️ _El precio ha alcanzado la zona extrema de reversión. Confirmación de mecha detectada._"
                    )
                    enviar_alerta(msj)
            
            print("⏳ Escaneo finalizado. Esperando 5 minutos...")
        except Exception as e:
            print(f"Error en ciclo: {e}")
        
        time.sleep(300)

if __name__ == "__main__":
    t = threading.Thread(target=mantener_vivo)
    t.daemon = True
    t.start()
    enviar_alerta("✅ *SISTEMA ACTUALIZADO:* El motor de Caja de Gann y Fibonacci 85-95% está operando 24/7. Evaluando rangos de mercado.")
    ciclo_principal()
