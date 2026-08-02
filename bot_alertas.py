import requests
import time
import csv
import os
import json
import threading
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from flask import Flask

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8807352507:AAEI5mhH0Ao-heGHrsBtJVpM6geGtlMTAUo")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8260761627")

ARCHIVO_CSV = "ranking_estrategias_simulacion.csv"
ARCHIVO_CAPITAL = "capital_simulado_estrategias.json"

ACTIVOS = {"Bitcoin": "BTC-USD", "Oro": "GC=F"} 

INTERVALO_SCAN_SEG = 300  # 5 minutos
INTERVALO_EVAL_SEG = 60   # 1 minuto

CAPITAL_INICIAL_POR_ESTRATEGIA = 5000.0 
LOTE_POR_ESTRATEGIA = 0.10 
VALOR_PIP = {"Oro": 10.0, "Bitcoin": 1.0}

HORAS_EVALUACION = {
    "Cazador de Pullbacks": 6,
    "Cruce de EMAs": 24,
    "Ruptura de Rango de Volumen": 6,
    "Retrocesos de Fibonacci": 72,
    "Confluencia Avanzada (Gann + Fibo)": 72
}

# ==========================================
# SERVIDOR WEB
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): return "🟢 Simulación Activa"
def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# UTILIDADES
# ==========================================
def obtener_historico(ticker, period="1mo", interval="1h"):
    try: return yf.Ticker(ticker).history(period=period, interval=interval)
    except: return None

def precio_actual(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1d", interval="5m")
        return float(df["Close"].iloc[-1]) if not df.empty else None
    except: return None

# ==========================================
# GESTIÓN DE CAPITAL SIMULADO
# ==========================================
def cargar_capital():
    if os.path.exists(ARCHIVO_CAPITAL):
        try:
            with open(ARCHIVO_CAPITAL, "r") as f: return json.load(f)
        except: pass
    return {e: CAPITAL_INICIAL_POR_ESTRATEGIA for e in HORAS_EVALUACION.keys()}

def guardar_capital(capital):
    with open(ARCHIVO_CAPITAL, "w") as f: json.dump(capital, f)

def calcular_resultado_financiero(estrategia, activo, precio_entrada, precio_salida, señal):
    capital = cargar_capital()
    balance_actual = capital.get(estrategia, CAPITAL_INICIAL_POR_ESTRATEGIA)
    
    riesgo_1R = balance_actual * 0.01 
    valor_pip = VALOR_PIP.get(activo, 1.0)
    
    puntos_movimiento = (precio_salida - precio_entrada)
    es_compra = "COMPRAR" in señal
    
    ganancia_usd = 0
    if es_compra:
        ganancia_usd = (puntos_movimiento / 0.01) * valor_pip * LOTE_POR_ESTRATEGIA
    else:
        ganancia_usd = (-puntos_movimiento / 0.01) * valor_pip * LOTE_POR_ESTRATEGIA

    r_multiplo = round(ganancia_usd / riesgo_1R, 2) if riesgo_1R > 0 else 0.0
    nuevo_balance = round(balance_actual + ganancia_usd, 2)
    capital[estrategia] = nuevo_balance
    guardar_capital(capital)
    
    return ganancia_usd, r_multiplo, nuevo_balance

# ==========================================
# LAS 5 ESTRATEGIAS
# ==========================================
def estrategia_pullback(ticker):
    df = obtener_historico(ticker, period="1mo", interval="1h")
    if df is None: return None
    close = df["Close"].iloc[-1]
    ema50 = df["Close"].ewm(span=50).mean().iloc[-1]
    if abs(close - ema50) / ema50 < 0.005:
        return {"señal": "🟢 COMPRAR", "precio": close}
    return None

def estrategia_emas(ticker):
    df = obtener_historico(ticker, period="1mo", interval="1h")
    if df is None: return None
    close = df["Close"].iloc[-1]
    ema20 = df["Close"].ewm(span=20).mean().iloc[-1]
    ema50 = df["Close"].ewm(span=50).mean().iloc[-1]
    if ema20 > ema50 and close > ema20:
        return {"señal": "🟢 COMPRAR", "precio": close}
    return None

def estrategia_volumen(ticker):
    df = obtener_historico(ticker, period="1mo", interval="1h")
    if df is None: return None
    close = df["Close"].iloc[-1]
    vol_actual = df["Volume"].iloc[-1]
    vol_promedio = df["Volume"].tail(20).mean()
    if vol_actual > (vol_promedio * 3):
        return {"señal": "🟢 COMPRAR", "precio": close}
    return None

def estrategia_fibonacci(ticker):
    df = obtener_historico(ticker, period="3mo", interval="1d")
    if df is None: return None
    high = df["High"].tail(50).max()
    low = df["Low"].tail(50).min()
    rango = high - low
    close = df["Close"].iloc[-1]
    fib_618 = low + 0.618 * rango
    if abs(close - fib_618) <= (rango * 0.02):
        return {"señal": "🟢 COMPRAR", "precio": close}
    return None

def estrategia_gann_fibo(ticker):
    df = obtener_historico(ticker, period="3mo", interval="1d")
    if df is None: return None
    high = df["High"].tail(50).max()
    low = df["Low"].tail(50).min()
    rango = high - low
    close = df["Close"].iloc[-1]
    gann_50 = low + 0.5 * rango
    if abs(close - gann_50) <= (rango * 0.02):
        return {"señal": "🟢 COMPRAR", "precio": close}
    return None

# ==========================================
# MOTOR DE SIMULACIÓN Y RANKING
# ==========================================
def ejecutar_ciclo():
    if not os.path.exists(ARCHIVO_CSV):
        with open(ARCHIVO_CSV, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Estrategia", "Activo", "Fecha_Señal", "Señal", "Precio_Entrada", 
                             "Fecha_Eval", "Precio_Salida", "R_Multiplo", "Resultado_USD", "Balance_Final"])

    # 1. BUSCAR NUEVAS SEÑALES
    for activo, ticker in ACTIVOS.items():
        price = precio_actual(ticker)
        if not price: continue
        
        estrategias = [
            ("Cazador de Pullbacks", estrategia_pullback),
            ("Cruce de EMAs", estrategia_emas),
            ("Ruptura de Rango de Volumen", estrategia_volumen),
            ("Retrocesos de Fibonacci", estrategia_fibonacci),
            ("Confluencia Avanzada (Gann + Fibo)", estrategia_gann_fibo)
        ]
        
        for nombre, func in estrategias:
            resultado = func(ticker)
            if resultado:
                with open(ARCHIVO_CSV, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        f"{nombre}_{int(time.time())}", nombre, activo, 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                        resultado["señal"], round(resultado["precio"], 2),
                        "", "", "", "", ""
                    ])

    # 2. EVALUAR SEÑALES PENDIENTES Y ENVIAR REPORTE
    if os.path.exists(ARCHIVO_CSV):
        df = pd.read_csv(ARCHIVO_CSV)
        cambios = False
        mensajes_enviados_hoy = set() # Para no spamear el mismo reporte
        
        for idx, row in df[df["Resultado_USD"] == ""].iterrows():
            try:
                fecha_señal = datetime.strptime(row["Fecha_Señal"], "%Y-%m-%d %H:%M:%S")
                horas_espera = HORAS_EVALUACION.get(row["Estrategia"], 24)
                
                if (datetime.now() - fecha_señal) >= timedelta(hours=horas_espera):
                    precio_hoy = precio_actual(ACTIVOS.get(row["Activo"]))
                    if not precio_hoy: continue
                    
                    usd_change, r_mult, new_bal = calcular_resultado_financiero(
                        row["Estrategia"], row["Activo"], float(row["Precio_Entrada"]), precio_hoy, row["Señal"]
                    )
                    
                    df.at[idx, "Fecha_Eval"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df.at[idx, "Precio_Salida"] = round(precio_hoy, 2)
                    df.at[idx, "R_Multiplo"] = r_mult
                    df.at[idx, "Resultado_USD"] = round(usd_change, 2)
                    df.at[idx, "Balance_Final"] = new_bal
                    cambios = True
            except Exception:
                pass
                
        if cambios:
            df.to_csv(ARCHIVO_CSV, index=False)
            
            # Generar el REPORTE TIPO OCULOOS (Como la imagen que enviaste)
            capital_actual = cargar_capital()
            balance_total = sum(capital_actual.values())
            rendimiento_global = ((balance_total - (CAPITAL_INICIAL_POR_ESTRATEGIA * len(HORAS_EVALUACION))) / (CAPITAL_INICIAL_POR_ESTRATEGIA * len(HORAS_EVALUACION))) * 100
            
            # Construir el cuerpo del mensaje
            mensaje = f"""
🇮🇹 *OCULOOS REPORTE MULTI-ACTIVO*

🌐 *Mercado / Activo:* Bitcoin (BTCUSD)
⚙️ *Nivel:* Sensibilidad 0 (Estándar / Base)
📊 *Estrategia Activa:* Cazador de Pullbacks
💵 *Precio Actual:* ${precio_actual("BTC-USD"):,.2f} USD
📈 *Resultado Operación:* ✅
💰 *Capital Total Actual:* ${balance_total:,.2f} USD
🏳️ *Rendimiento Global:* +{rendimiento_global:.2f}%

📂 *Rendimiento por Estrategia:*
"""
            for nombre, balance in capital_actual.items():
                # Calculamos rendimiento individual para poner el emoji correcto
                ganancia_individual = balance - CAPITAL_INICIAL_POR_ESTRATEGIA
                porcentaje_individual = (ganancia_individual / CAPITAL_INICIAL_POR_ESTRATEGIA) * 100
                emoji = "👉" if ganancia_individual > 0 else "📉"
                
                mensaje += f"{emoji} *{nombre}:* {porcentaje_individual:+.2f}%\n"

            mensaje += """
🧠 *Contexto:*
Filtros estrictos y conservadores.
Máxima exigencia matemática.
"""
            # Enviar el reporte completo a Telegram
            try:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                              data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}, timeout=10)
                print("📨 Reporte de rendimiento enviado a Telegram.")
            except Exception as e:
                print(f"Error enviando reporte: {e}")

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == '__main__':
    guardar_capital(cargar_capital())
    print("🚀 Bot de Simulación Iniciado. Esperando reportes...")
    
    def ciclo_principal():
        while True:
            ejecutar_ciclo()
            time.sleep(INTERVALO_SCAN_SEG)
            
    hilo_bot = threading.Thread(target=ciclo_principal)
    hilo_bot.start()
    mantener_vivo()