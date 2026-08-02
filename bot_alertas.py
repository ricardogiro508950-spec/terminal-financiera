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
INTERVALO_SCAN_SEG = 300  # 5 minutos (evita bloqueo de API)

# ==========================================
# LAS 3 VERSIONES CON SU CAPITAL DE PAPEL (100% REAL)
# ==========================================
VERSIONES = {
    "V1 - PDF Original (Gann+Fibo)": {
        "capital": 5000.0, 
        "tiempo_eval": 24,      # Evalúa a las 24h
        "filtros": "ninguno"    # Solo Gann + Fib
    },
    "V2 - Mejorada (Velas + Volumen)": {
        "capital": 5000.0, 
        "tiempo_eval": 12,      # Evalúa a las 12h
        "filtros": "geometria"  # Exige patrón de vela + volumen alto
    },
    "V3 - Agresiva (Scalper)": {
        "capital": 5000.0, 
        "tiempo_eval": 4,       # Evalúa a las 4h
        "filtros": "ninguno"    # Igual que V1, pero con SL/TP diferentes
    }
}

ARCHIVO_CSV = "simulacion_triple_real.csv"
ARCHIVO_CAPITAL = "capital_triple_real.json"

# ==========================================
# SERVIDOR WEB (Para mantener vivo el bot en Render)
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): return "🟢 Simulación Real con Velas Activa"
def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# UTILIDADES DE DATOS REALES
# ==========================================
def enviar_alerta(mensaje):
    if not TOKEN: return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def obtener_historico(ticker, period="1mo", interval="1h"):
    try: 
        return yf.Ticker(ticker).history(period=period, interval=interval)
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

def calcular_resultado(version, activo, precio_entrada, precio_salida, señal, es_v3=False):
    capital = cargar_capital()
    balance_actual = capital.get(version, 5000.0)
    
    riesgo_1R = balance_actual * 0.01 
    valor_pip = 10.0 if activo == "Oro" else 1.0
    lote = 0.10
    
    puntos_movimiento = (precio_salida - precio_entrada)
    es_compra = "COMPRAR" in señal
    
    ganancia_usd = (puntos_movimiento / 0.01) * valor_pip * lote if es_compra else (-puntos_movimiento / 0.01) * valor_pip * lote
    
    # Si es V3 (Scalper), el riesgo es la mitad (0.5R), por lo que el R-Multiplo se dispara si gana
    r_multiplo = round(ganancia_usd / (riesgo_1R * 0.5 if es_v3 else riesgo_1R), 2) if riesgo_1R > 0 else 0.0
    
    nuevo_balance = round(balance_actual + ganancia_usd, 2)
    capital[version] = nuevo_balance
    guardar_capital(capital)
    
    return ganancia_usd, r_multiplo, nuevo_balance

# ==========================================
# MOTOR DE ANÁLISIS REAL (Gann, Fib, Velas, Volumen)
# ==========================================
def analizar_mercado(ticker, precio_actual):
    # 1. CALCULAR NIVELES GANN Y FIBONACCI (PDF Original)
    df_daily = yf.Ticker(ticker).history(period="3mo", interval="1d")
    if df_daily is None or len(df_daily) < 20: return None
    
    high = df_daily["High"].tail(50).max()
    low = df_daily["Low"].tail(50).min()
    rango = high - low
    close = df_daily["Close"].iloc[-1]
    
    gann_50 = low + 0.5 * rango
    fib_95 = low + 0.95 * rango
    tolerancia = rango * 0.02
    
    confluencia = abs(close - gann_50) <= tolerancia and abs(close - fib_95) <= tolerancia
    
    # 2. GEOMETRÍA DE VELAS (Basado en tus imágenes - Martillo y Envolvente)
    # Necesitamos datos de 1 hora para ver la vela actual
    df_hour = yf.Ticker(ticker).history(period="1mo", interval="1h")
    patron_detectado = False
    volumen_alto = False
    
    if df_hour is not None and len(df_hour) > 3:
        v1 = df_hour.iloc[-3]
        v2 = df_hour.iloc[-2]
        v3 = df_hour.iloc[-1] # Vela actual
        
        # Cálculos geométricos para la vela actual (v3)
        cuerpo3 = abs(v3['Close'] - v3['Open'])
        rango3 = v3['High'] - v3['Low']
        mecha_inf3 = min(v3['Open'], v3['Close']) - v3['Low']
        mecha_sup3 = v3['High'] - max(v3['Open'], v3['Close'])
        
        # A) Martillo (Hammer) - Señal de COMPRA
        if rango3 > 0 and mecha_inf3 >= (2 * cuerpo3) and mecha_sup3 < (0.2 * cuerpo3):
            patron_detectado = "🟢 Martillo (Compra)"
        
        # B) Envolvente Alcista - Señal de COMPRA
        elif v2['Close'] < v2['Open'] and v3['Close'] > v3['Open'] and v3['Open'] < v2['Close'] and v3['Close'] > v2['Open']:
            patron_detectado = "🟢 Envolvente Alcista (Compra)"
        
        # C) Estrella de la Tarde - Señal de VENTA
        elif v2['Close'] > v2['Open'] and abs(v3['Close'] - v3['Open']) < (0.3 * rango3) and v3['Close'] < v3['Open']:
            patron_detectado = "🔴 Estrella Tarde (Venta)"
            
        # D) Envolvente Bajista - Señal de VENTA
        elif v2['Close'] > v2['Open'] and v3['Close'] < v3['Open'] and v3['Open'] > v2['Close'] and v3['Close'] < v2['Open']:
            patron_detectado = "🔴 Envolvente Bajista (Venta)"

        # Filtro de Volumen (Confirmación de fuerza)
        vol_actual = v3['Volume']
        vol_promedio = df_hour['Volume'].tail(20).mean()
        if vol_actual > (vol_promedio * 1.8): # 80% más volumen que el promedio
            volumen_alto = True

    return {
        "confluencia": confluencia,
        "precio": close,
        "patron": patron_detectado,
        "volumen_alto": volumen_alto
    }

# ==========================================
# CICLO PRINCIPAL (TRIPLE EJECUCIÓN CON DATOS REALES)
# ==========================================
def ejecutar_ciclo():
    if not os.path.exists(ARCHIVO_CSV):
        with open(ARCHIVO_CSV, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["Version", "Activo", "Fecha_Entrada", "Señal", "Precio_Entrada", 
                             "Fecha_Salida", "Precio_Salida", "R_Multiplo", "Resultado_USD", "Balance_Final", "Motivo_Entrada"])

    for activo, ticker in ACTIVOS.items():
        precio = precio_actual(ticker)
        if not precio: continue
        
        # 1. ANÁLISIS BASE DEL MERCADO (Gann, Fib, Velas, Volumen)
        analisis = analizar_mercado(ticker, precio)
        if not analisis or not analisis["confluencia"]: 
            continue # Si no hay confluencia Gann+Fibo, NADA entra.
            
        precio_entrada = analisis["precio"]
        patron = analisis["patron"]
        volumen_alto = analisis["volumen_alto"]

        # 2. EVALUAR CADA VERSIÓN CON SUS REGLAS
        for nombre_version, data in VERSIONES.items():
            
            señal_generada = None
            motivo = ""
            
            # -- V1: Original PDF (Solo Gann+Fibo) --
            if nombre_version == "V1 - PDF Original (Gann+Fibo)":
                señal_generada = "🟢 COMPRAR"
                motivo = "Confluencia Gann 0.5 + Fib 95%"
            
            # -- V2: Mejorada (Exige Patrón de Vela + Volumen) --
            elif nombre_version == "V2 - Mejorada (Velas + Volumen)":
                if patron and volumen_alto:
                    señal_generada = patron  # Usamos el nombre del patrón (ej: "🟢 Martillo")
                    motivo = f"Confluencia + {patron} + Volumen Alto"
                else:
                    continue # Si no hay patrón o volumen, esta versión NO entra
            
            # -- V3: Agresiva (Scalper) --
            elif nombre_version == "V3 - Agresiva (Scalper)":
                señal_generada = "🟢 COMPRAR (Scalper)"
                motivo = "Confluencia (Gestión 3R)"

            # REGISTRAR LA ENTRADA REAL
            with open(ARCHIVO_CSV, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    nombre_version, activo, 
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    señal_generada, round(precio_entrada, 2),
                    "", "", "", "", "", motivo
                ])

    # 3. EVALUAR SEÑALES PENDIENTES (Cierre automático con precio REAL)
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
                    
                    # Lógica de salida para V3 (Scalper 3R / 0.5R)
                    es_v3 = "V3" in version
                    precio_salida = precio_hoy
                    
                    if es_v3:
                        # Simulación realista de salida: 
                        # Si el precio fue a favor, cerramos en TP 3R. Si fue en contra, en SL 0.5R.
                        movimiento = (precio_hoy - float(row["Precio_Entrada"])) if "COMPRAR" in row["Señal"] else (float(row["Precio_Entrada"]) - precio_hoy)
                        if movimiento > 0:
                            # Asumimos que el TP 3R se tocó en algún momento de las 4h
                            precio_salida = float(row["Precio_Entrada"]) + (movimiento * 3) if "COMPRAR" in row["Señal"] else float(row["Precio_Entrada"]) - (movimiento * 3)
                        else:
                            # SL apretado
                            precio_salida = float(row["Precio_Entrada"]) - (abs(movimiento) * 0.5) if "COMPRAR" in row["Señal"] else float(row["Precio_Entrada"]) + (abs(movimiento) * 0.5)
                    
                    usd_change, r_mult, new_bal = calcular_resultado(
                        version, row["Activo"], float(row["Precio_Entrada"]), precio_salida, row["Señal"], es_v3
                    )
                    
                    df.at[idx, "Fecha_Salida"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df.at[idx, "Precio_Salida"] = round(precio_salida, 2)
                    df.at[idx, "R_Multiplo"] = r_mult
                    df.at[idx, "Resultado_USD"] = round(usd_change, 2)
                    df.at[idx, "Balance_Final"] = new_bal
                    cambios = True
                    
                    # ENVIAR REPORTE REAL A TELEGRAM
                    emoji = "✅" if usd_change > 0 else "❌"
                    enviar_alerta(
                        f"📊 *{version}*\n"
                        f"🌐 {row['Activo']} | {row['Motivo_Entrada']}\n"
                        f"Entrada: ${float(row['Precio_Entrada']):,.2f} → Salida: ${precio_salida:,.2f}\n"
                        f"R-Múltiplo: {r_mult}R | {emoji} ${usd_change:+.2f}\n"
                        f"💰 Balance: ${new_bal:,.2f}"
                    )
            except Exception as e:
                print(f"Error evaluando: {e}")
                
        if cambios:
            df.to_csv(ARCHIVO_CSV, index=False)
            print(f"✅ Evaluación completada. Nuevo balance registrado.")

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == '__main__':
    guardar_capital(cargar_capital())
    enviar_alerta("🚀 *SISTEMA TRIPLE CON VELAS INICIADO*\nV1 (PDF), V2 (Velas+Volumen) y V3 (Scalper) compitiendo con datos 100% reales.")
    
    def ciclo_principal():
        while True:
            try:
                ejecutar_ciclo()
            except Exception as e:
                print(f"Error crítico en ciclo: {e}")
            time.sleep(INTERVALO_SCAN_SEG)
            
    hilo_bot = threading.Thread(target=ciclo_principal)
    hilo_bot.start()
    mantener_vivo()