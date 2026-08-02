import requests
import time
import csv
import os
import json
import threading
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import yfinance as yf
from flask import Flask

# ==========================================
# CONFIGURACIÓN
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8807352507:AAEI5mhH0Ao-heGHrsBtJVpM6geGtlMTAUo")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8260761627")

ARCHIVO_CSV = "historial_senales_reales.csv"
ARCHIVO_CAPITAL = "capital_estrategias.json"

ACTIVOS = {"Oro": "GC=F", "Bitcoin": "BTC-USD", "Petróleo": "CL=F"}
ESTRATEGIAS = ["Soporte/Resistencia", "Fibonacci 61.8%", "Estructura (HH/HL)", "Perfil Volumen (POC)", "Patrones Velas"]

# INTERVALOS REALISTAS
INTERVALO_SCAN_SEG = 300       # Revisar cada 5 minutos (velas de 5m y 15m)
INTERVALO_EVAL_SEG = 120       # Evaluar señales abiertas cada 2 minutos

# TIEMPO DE MADURACIÓN POR ESTRATEGIA (horas para decidir si ganó o perdió)
HORAS_EVALUACION = {
    "Soporte/Resistencia": 24,
    "Fibonacci 61.8%": 24,
    "Estructura (HH/HL)": 12,
    "Perfil Volumen (POC)": 12,
    "Patrones Velas": 6,       # Los patrones de velas son de corto plazo
}

CAPITAL_INICIAL_POR_ESTRATEGIA = 1000.0
LOTE_FIJO_POR_ESTRATEGIA = 0.10
VALOR_PIP_POR_ACTIVO = {"Bitcoin": 1.0, "Oro": 10.0, "Petróleo": 10.0}

# ==========================================
# SERVIDOR WEB (para Render)
# ==========================================
app = Flask(__name__)
@app.route('/')
def home():
    return "🟢 Bot Velas & Estructura — Activo."
def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# UTILIDADES Y DATOS
# ==========================================
def enviar_alerta(mensaje):
    if not TOKEN or "PON_TU_TOKEN" in TOKEN:
        print(f"🔔 {mensaje}")
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}, timeout=10)
    except Exception:
        pass

def obtener_historico(ticker, period="1mo", interval="1h"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        return df if not df.empty else None
    except Exception:
        return None

def precio_actual(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1d", interval="5m")
        return float(df["Close"].iloc[-1]) if not df.empty else None
    except Exception:
        return None

# ==========================================
# GESTIÓN DE CAPITAL DE PAPEL
# ==========================================
def cargar_capital():
    if os.path.exists(ARCHIVO_CAPITAL):
        try:
            with open(ARCHIVO_CAPITAL, "r") as f: return json.load(f)
        except: pass
    return {e: CAPITAL_INICIAL_POR_ESTRATEGIA for e in ESTRATEGIAS}

def guardar_capital(capital):
    with open(ARCHIVO_CAPITAL, "w") as f: json.dump(capital, f)

def calcular_resultado_financiero(estrategia, activo, precio_entrada, precio_salida, señal):
    capital = cargar_capital()
    balance_actual = capital.get(estrategia, CAPITAL_INICIAL_POR_ESTRATEGIA)
    riesgo_1R = balance_actual * 0.01
    valor_pip = VALOR_PIP_POR_ACTIVO.get(activo, 1.0)
    puntos_movimiento = (precio_salida - precio_entrada)
    
    es_compra = "COMPRAR" in señal
    es_venta = "VENDER" in señal
    
    ganancia_usd = 0
    if es_compra:
        ganancia_usd = (puntos_movimiento / 0.01) * valor_pip * LOTE_FIJO_POR_ESTRATEGIA
    elif es_venta:
        ganancia_usd = (-puntos_movimiento / 0.01) * valor_pip * LOTE_FIJO_POR_ESTRATEGIA

    r_multiplo = round(ganancia_usd / riesgo_1R, 2) if riesgo_1R > 0 else 0.0
    nuevo_balance = round(balance_actual + ganancia_usd, 2)
    capital[estrategia] = nuevo_balance
    guardar_capital(capital)
    return ganancia_usd, r_multiplo, nuevo_balance

# ==========================================
# ANÁLISIS 1, 2, 3, 4: ESTRUCTURA, FIBONACCI, SOPORTE/RESISTENCIA, VOLUMEN
# ==========================================
def analizar_estructura_y_fib(ticker):
    df = obtener_historico(ticker, period="3mo", interval="1h")
    if df is None or len(df) < 50: return None
    
    close = df["Close"].iloc[-1]
    high_20 = df["High"].tail(20).max()
    low_20 = df["Low"].tail(20).min()
    rango = high_20 - low_20
    
    # 1. Estructura HH/HL
    ultimos_maximos = df["High"].tail(10)
    ultimos_minimos = df["Low"].tail(10)
    estructura_alcista = close > ultimos_maximos.max() and ultimos_minimos.min() > df["Low"].iloc[-11]
    
    # 2. Fibonacci 61.8%
    fib_618 = high_20 - (0.618 * rango)
    cerca_fib = abs(close - fib_618) <= (rango * 0.02)
    
    # 3. Soporte / Resistencia (Niveles redondos psicológicos)
    nivel_redondo = round(close, -2) # Redondea a la centena (ej. 2000, 2050)
    cerca_soporte = abs(close - nivel_redondo) <= 5.0

    if estructura_alcista and cerca_fib and cerca_soporte:
        return {"señal": "🟢 COMPRAR (Fib 61.8 + Estructura)", "precio": close}
    elif not estructura_alcista and cerca_fib:
        return {"señal": "🔴 VENDER (Zona Fib 61.8 sin soporte)", "precio": close}
    
    return None

def analizar_volumen_poc(ticker):
    df = obtener_historico(ticker, period="1mo", interval="15m")
    if df is None or len(df) < 50: return None
    
    # Filtro POC simplificado: Buscar si el volumen de la última vela es 2x el promedio
    close = df["Close"].iloc[-1]
    vol_actual = df["Volume"].iloc[-1]
    vol_promedio = df["Volume"].tail(20).mean()
    
    if vol_actual > (vol_promedio * 2):
        return {"señal": "🟢 COMPRAR (Volumen de ruptura)", "precio": close}
    return None

# ==========================================
# ANÁLISIS 5: PATRONES DE VELAS (GEOMETRÍA DE LAS IMÁGENES)
# ==========================================
def analizar_patrones_velas(ticker):
    df = obtener_historico(ticker, period="1mo", interval="1h")
    if df is None or len(df) < 5: return None
    
    # Extraer las últimas 3 velas para patrones de 3
    v1_o, v1_c, v1_h, v1_l = df["Open"].iloc[-3], df["Close"].iloc[-3], df["High"].iloc[-3], df["Low"].iloc[-3]
    v2_o, v2_c, v2_h, v2_l = df["Open"].iloc[-2], df["Close"].iloc[-2], df["High"].iloc[-2], df["Low"].iloc[-2]
    v3_o, v3_c, v3_h, v3_l = df["Open"].iloc[-1], df["Close"].iloc[-1], df["High"].iloc[-1], df["Low"].iloc[-1]
    
    # Cálculos geométricos
    cuerpo1 = abs(v1_c - v1_o)
    cuerpo2 = abs(v2_c - v2_o)
    cuerpo3 = abs(v3_c - v3_o)
    rango3 = v3_h - v3_l
    mecha_sup3 = v3_h - max(v3_o, v3_c)
    mecha_inf3 = min(v3_o, v3_c) - v3_l
    
    # --- PATRONES ALCISTAS (COMPRA) ---
    # 1. Martillo (Hammer)
    if rango3 > 0 and mecha_inf3 >= (2 * cuerpo3) and mecha_sup3 < (0.2 * cuerpo3):
        return {"señal": "🟢 COMPRAR (Martillo)", "precio": v3_c}
    
    # 2. Estrella de la Mañana (Morning Star) - 3 Velas
    if (v1_c < v1_o) and (cuerpo2 < 0.3 * rango3) and (v3_c > v3_o) and (v3_c > (v1_c + (cuerpo1 * 0.5))):
        return {"señal": "🟢 COMPRAR (Estrella Mañana)", "precio": v3_c}

    # 3. Envolvente Alcista (Bullish Engulfing)
    if (v1_c < v1_o) and (v3_c > v3_o) and (v3_o < v1_c) and (v3_c > v1_o):
        return {"señal": "🟢 COMPRAR (Envolvente Alcista)", "precio": v3_c}

    # 4. Kicker Alcista
    if (v1_c < v1_o) and (v3_c > v3_o) and (v3_o > v1_c) and (v3_c > v1_h):
        return {"señal": "🟢 COMPRAR (Kicker Alcista)", "precio": v3_c}

    # --- PATRONES BAJISTAS (VENTA) ---
    # 5. Hombre Colgado (Hanging Man)
    if rango3 > 0 and mecha_inf3 >= (2 * cuerpo3) and mecha_sup3 < (0.2 * cuerpo3) and (v3_c < v3_o):
        return {"señal": "🔴 VENDER (Hombre Colgado)", "precio": v3_c}

    # 6. Estrella de la Tarde (Evening Star)
    if (v1_c > v1_o) and (cuerpo2 < 0.3 * rango3) and (v3_c < v3_o) and (v3_c < (v1_c - (cuerpo1 * 0.5))):
        return {"señal": "🔴 VENDER (Estrella Tarde)", "precio": v3_c}

    # 7. Envolvente Bajista (Bearish Engulfing)
    if (v1_c > v1_o) and (v3_c < v3_o) and (v3_o > v1_c) and (v3_c < v1_o):
        return {"señal": "🔴 VENDER (Envolvente Bajista)", "precio": v3_c}

    # 8. Tres Cuervos Negros (3 Black Crows)
    if (v1_c < v1_o) and (v2_c < v2_o) and (v3_c < v3_o) and (v2_c < v1_c) and (v3_c < v2_c):
        return {"señal": "🔴 VENDER (Tres Cuervos)", "precio": v3_c}
        
    return None

# ==========================================
# MOTOR DE REGISTRO Y EVALUACIÓN
# ==========================================
def registrar_y_evaluar():
    if not os.path.exists(ARCHIVO_CSV):
        with open(ARCHIVO_CSV, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Fecha_Señal", "Activo", "Estrategia", "Señal", "Precio_Señal", "Fecha_Eval", "Precio_Eval", "Variacion_%", "R_Multiplo", "Resultado_USD", "Balance_Final"])

    # ESCANEAR NUEVAS SEÑALES
    for activo, ticker in ACTIVOS.items():
        price = precio_actual(ticker)
        if not price: continue
        
        funciones = [
            ("Estructura (HH/HL)", analizar_estructura_y_fib),
            ("Perfil Volumen (POC)", analizar_volumen_poc),
            ("Patrones Velas", analizar_patrones_velas),
        ]
        
        for nombre, func in funciones:
            resultado = func(ticker)
            if resultado:
                with open(ARCHIVO_CSV, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        f"{activo}_{nombre}_{int(time.time())}",
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        activo, nombre, resultado["señal"], round(resultado["precio"], 2),
                        "", "", "", "", "", ""
                    ])
                enviar_alerta(f"📊 *{nombre}*\n{activo}: {resultado['señal']} a ${resultado['precio']}")

    # EVALUAR SEÑALES PENDIENTES
    if os.path.exists(ARCHIVO_CSV):
        df = pd.read_csv(ARCHIVO_CSV)
        cambios = False
        for idx, row in df[df["Fecha_Eval"] == ""].iterrows():
            try:
                fecha_señal = datetime.strptime(row["Fecha_Señal"], "%Y-%m-%d %H:%M:%S")
                horas_espera = HORAS_EVALUACION.get(row["Estrategia"], 6)
                if (datetime.now() - fecha_señal) < timedelta(hours=horas_espera):
                    continue
                
                precio_hoy = precio_actual(ACTIVOS.get(row["Activo"]))
                if not precio_hoy: continue
                
                usd_change, r_mult, new_bal = calcular_resultado_financiero(
                    row["Estrategia"], row["Activo"], float(row["Precio_Señal"]), precio_hoy, row["Señal"]
                )
                
                df.at[idx, "Fecha_Eval"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df.at[idx, "Precio_Eval"] = round(precio_hoy, 2)
                df.at[idx, "R_Multiplo"] = r_mult
                df.at[idx, "Resultado_USD"] = round(usd_change, 2)
                df.at[idx, "Balance_Final"] = new_bal
                cambios = True

                emoji = "✅" if usd_change > 0 else "❌"
                enviar_alerta(
                    f"⚡ *EVALUACIÓN ({horas_espera}h)*\n"
                    f"{row['Activo']} | {row['Estrategia']}\n"
                    f"Entrada: ${float(row['Precio_Señal'])} → Salida: ${precio_hoy}\n"
                    f"R-Múltiplo: {r_mult}R | {emoji} ${usd_change:+.2f}"
                )
            except Exception:
                pass
        
        if cambios:
            df.to_csv(ARCHIVO_CSV, index=False)

# ==========================================
# CICLO PRINCIPAL
# ==========================================
if __name__ == '__main__':
    guardar_capital(cargar_capital())
    enviar_alerta("🚀 *Bot Velas y Estructura Iniciado*")
    
    def ciclo():
        while True:
            try:
                registrar_y_evaluar()
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(INTERVALO_SCAN_SEG)

    t1 = threading.Thread(target=ciclo)
    t2 = threading.Thread(target=mantener_vivo)
    t1.start()
    t2.start()
    t1.join()