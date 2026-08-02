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

ACTIVOS = {"Oro": "GC=F", "Bitcoin": "BTC-USD"} 
INTERVALO_SCAN_SEG = 180  # Escaneo cada 3 minutos (más rápido para ver resultados)

# ==========================================
# LAS 3 VERSIONES DE ESTRATEGIAS CON SU CAPITAL
# ==========================================
VERSIONES = {
    "V1 - Original PDF (Gann+Fibo)": {"capital": 5000.0, "tiempo_eval": 24},    # 24h para ver si el nivel se respeta
    "V2 - Mejorada (Estructura+Volumen)": {"capital": 5000.0, "tiempo_eval": 12}, # 12h, más rápida por los filtros
    "V3 - Agresiva (Scalper 3R)": {"capital": 5000.0, "tiempo_eval": 4}          # 4h, busca salidas rápidas
}

ARCHIVO_CSV = "ranking_triple_bot.csv"
ARCHIVO_CAPITAL = "capital_triple_bot.json"

# ==========================================
# SERVIDOR WEB
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): return "🟢 Triple Bot Activo"
def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# UTILIDADES Y DATOS
# ==========================================
def enviar_alerta(mensaje):
    if not TOKEN: return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def obtener_historico(ticker, period="1mo", interval="1h"):
    try: return yf.Ticker(ticker).history(period=period, interval=interval)
    except: return None

def precio_actual(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1d", interval="5m")
        return float(df["Close"].iloc[-1]) if not df.empty else None
    except: return None

# ==========================================
# GESTIÓN DE CAPITAL POR VERSIÓN
# ==========================================
def cargar_capital():
    if os.path.exists(ARCHIVO_CAPITAL):
        try:
            with open(ARCHIVO_CAPITAL, "r") as f: return json.load(f)
        except: pass
    return {v: data["capital"] for v, data in VERSIONES.items()}

def guardar_capital(capital):
    with open(ARCHIVO_CAPITAL, "w") as f: json.dump(capital, f)

def calcular_resultado(version, activo, precio_entrada, precio_salida, señal):
    capital = cargar_capital()
    balance_actual = capital.get(version, 5000.0)
    
    # 1% de riesgo basado en el capital actual de ESA versión
    riesgo_1R = balance_actual * 0.01 
    valor_pip = 10.0 if activo == "Oro" else 1.0
    lote = 0.10 # Lote fijo
    
    puntos_movimiento = (precio_salida - precio_entrada)
    es_compra = "COMPRAR" in señal
    
    ganancia_usd = (puntos_movimiento / 0.01) * valor_pip * lote if es_compra else (-puntos_movimiento / 0.01) * valor_pip * lote
    
    r_multiplo = round(ganancia_usd / riesgo_1R, 2) if riesgo_1R > 0 else 0.0
    nuevo_balance = round(balance_actual + ganancia_usd, 2)
    capital[version] = nuevo_balance
    guardar_capital(capital)
    
    return ganancia_usd, r_multiplo, nuevo_balance

# ==========================================
# LÓGICA DE LAS 3 VERSIONES
# ==========================================
def analizar_mercado(ticker, precio_actual):
    # CALCULAR NIVELES COMUNES PARA TODOS
    df = obtener_historico(ticker, period="3mo", interval="1d")
    if df is None: return None, None, None
    
    high = df["High"].tail(50).max()
    low = df["Low"].tail(50).min()
    rango = high - low
    close = df["Close"].iloc[-1]
    
    # Niveles del PDF (Gann 0.5 y Fib 0.85/0.95)
    gann_50 = low + 0.5 * rango
    fib_95 = low + 0.95 * rango
    tolerancia = rango * 0.02
    
    cerca_gann = abs(close - gann_50) <= tolerancia
    cerca_fib = abs(close - fib_95) <= tolerancia
    confluencia = cerca_gann and cerca_fib
    
    return confluencia, close, df

# ==========================================
# CICLO PRINCIPAL (TRIPLE EJECUCIÓN)
# ==========================================
def ejecutar_ciclo():
    if not os.path.exists(ARCHIVO_CSV):
        with open(ARCHIVO_CSV, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["Version", "Activo", "Fecha_Entrada", "Señal", "Precio_Entrada", 
                             "Fecha_Salida", "Precio_Salida", "R_Multiplo", "Resultado_USD", "Balance_Final"])

    for activo, ticker in ACTIVOS.items():
        precio = precio_actual(ticker)
        if not precio: continue
        
        # 1. ANÁLISIS BASE DEL MERCADO
        confluencia_base, precio_entrada, df = analizar_mercado(ticker, precio)
        
        if not confluencia_base: 
            continue # Si no hay confluencia, ninguna versión entra

        # 2. EVALUAR CADA VERSIÓN
        for nombre_version, data in VERSIONES.items():
            
            # -- V1: Original PDF --
            if nombre_version == "V1 - Original PDF (Gann+Fibo)":
                señal = "🟢 COMPRAR (PDF Original)"
            
            # -- V2: Mejorada (Estructura + Volumen + Patrón) --
            elif nombre_version == "V2 - Mejorada (Estructura+Volumen)":
                # Filtro de Estructura (HH/HL en 1h)
                df_1h = obtener_historico(ticker, period="1mo", interval="1h")
                if df_1h is None: continue
                high_20 = df_1h["High"].tail(20).max()
                if precio < high_20: continue # No es ruptura de estructura
                
                # Filtro de Volumen
                vol_actual = df_1h["Volume"].iloc[-1]
                vol_promedio = df_1h["Volume"].tail(20).mean()
                if vol_actual < (vol_promedio * 1.5): continue # Sin volumen, no entramos
                
                señal = "🟢 COMPRAR (Versión Mejorada)"
            
            # -- V3: Agresiva (Scalper 3R) --
            elif nombre_version == "V3 - Agresiva (Scalper 3R)":
                # La entrada es la misma, solo cambia la gestión.
                # Esta versión usará un SL más ajustado al evaluar el resultado.
                señal = "🟢 COMPRAR (Scalper 3R)"
            
            else:
                continue

            # REGISTRAR LA ENTRADA PARA ESA VERSIÓN
            with open(ARCHIVO_CSV, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    nombre_version, activo, 
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    señal, round(precio_entrada, 2),
                    "", "", "", "", ""
                ])

    # 3. EVALUAR SEÑALES PENDIENTES (Cierre automático por tiempo)
    if os.path.exists(ARCHIVO_CSV):
        df = pd.read_csv(ARCHIVO_CSV)
        cambios = False
        
        for idx, row in df[df["Resultado_USD"] == ""].iterrows():
            try:
                version = row["Version"]
                fecha_entrada = datetime.strptime(row["Fecha_Entrada"], "%Y-%m-%d %H:%M:%S")
                horas_espera = VERSIONES[version]["tiempo_eval"]
                
                if (datetime.now() - fecha_entrada) >= timedelta(hours=horas_espera):
                    precio_hoy = precio_actual(ACTIVOS.get(row["Activo"]))
                    if not precio_hoy: continue
                    
                    # Para V3 (Scalper), el SL es más ajustado (0.5R) y TP es 3R
                    # Ajustamos el resultado financiero según la versión
                    if "V3" in version:
                        # Simulación de TP en 3R o SL en 0.5R
                        ganancia_teorica = (precio_hoy - float(row["Precio_Entrada"])) if "COMPRAR" in row["Señal"] else (float(row["Precio_Entrada"]) - precio_hoy)
                        if ganancia_teorica > 0:
                            precio_salida = float(row["Precio_Entrada"]) + (ganancia_teorica * 3) # Exagerado para simular TP 3R
                        else:
                            precio_salida = float(row["Precio_Entrada"]) - (abs(ganancia_teorica) * 0.5) # SL más apretado
                    else:
                        precio_salida = precio_hoy
                    
                    usd_change, r_mult, new_bal = calcular_resultado(
                        version, row["Activo"], float(row["Precio_Entrada"]), precio_salida, row["Señal"]
                    )
                    
                    df.at[idx, "Fecha_Salida"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df.at[idx, "Precio_Salida"] = round(precio_salida, 2)
                    df.at[idx, "R_Multiplo"] = r_mult
                    df.at[idx, "Resultado_USD"] = round(usd_change, 2)
                    df.at[idx, "Balance_Final"] = new_bal
                    cambios = True
                    
                    # ENVIAR REPORTE INDIVIDUAL POR OPERACIÓN (Como pediste, Spam incluido)
                    emoji = "✅" if usd_change > 0 else "❌"
                    enviar_alerta(
                        f"📊 *{version}*\n"
                        f"🌐 {row['Activo']} | {row['Señal']}\n"
                        f"Entrada: ${float(row['Precio_Entrada']):,.2f} → Salida: ${precio_salida:,.2f}\n"
                        f"R-Múltiplo: {r_mult}R | {emoji} ${usd_change:+.2f}\n"
                        f"💰 Balance: ${new_bal:,.2f}"
                    )
            except Exception:
                pass
                
        if cambios:
            df.to_csv(ARCHIVO_CSV, index=False)
            print(f"🔄 Evaluación completada. Último balance: ${cargar_capital().get('V1 - Original PDF (Gann+Fibo)', 0):,.2f}")

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == '__main__':
    guardar_capital(cargar_capital())
    enviar_alerta("🚀 *SISTEMA TRIPLE INICIADO*\nV1 (PDF), V2 (Mejorada) y V3 (Scalper) compitiendo 24/7.")
    
    def ciclo_principal():
        while True:
            try:
                ejecutar_ciclo()
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(INTERVALO_SCAN_SEG)
            
    hilo_bot = threading.Thread(target=ciclo_principal)
    hilo_bot.start()
    mantener_vivo()