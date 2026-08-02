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

ACTIVOS = {"Oro": "GC=F", "Bitcoin": "BTC-USD", "Petróleo": "CL=F"}
INTERVALO_SCAN_SEG = 300  # 5 minutos

# ==========================================
# LAS 12 VERSIONES CON CAPITAL DE PAPEL
# ==========================================
VERSIONES = {
    # --- CONTROL (La original del PDF) ---
    "V1 - PDF Original (Control)": {"capital": 5000.0, "tiempo_eval": 24, "filtros": "ninguno"},
    
    # --- V2 - MEJORADAS (VELAS + VOLUMEN) ---
    "V2 - Ultra-Conservadora": {"capital": 5000.0, "tiempo_eval": 12, "filtros": "estricto"},
    "V2 - Estándar (Actual)": {"capital": 5000.0, "tiempo_eval": 12, "filtros": "medio"},
    "V2 - Agresiva (Rápida)": {"capital": 5000.0, "tiempo_eval": 6, "filtros": "laxo"},

    # --- V3 - SCALPERS (GESTIÓN AGRESIVA) ---
    "V3 - Scalper Agresivo (3R)": {"capital": 5000.0, "tiempo_eval": 4, "filtros": "ninguno"},
    "V3 - Ultra-Rápido (Trailing)": {"capital": 5000.0, "tiempo_eval": 2, "filtros": "ninguno"},
    
    # --- V4 - ANTI-RUINA (MARTINGALA + FILTRO VOLUMEN) ---
    "V4 - Martingala Agresiva": {"capital": 5000.0, "tiempo_eval": 8, "filtros": "martingala"},
    "V4 - Martingala Conservadora": {"capital": 5000.0, "tiempo_eval": 12, "filtros": "martingala"},

    # --- V5 - SENSIBILIDAD EXTREMA (TRAILING DINÁMICO) ---
    "V5 - Trailing Dinámico (Lento)": {"capital": 5000.0, "tiempo_eval": 4, "filtros": "trailing_lento"},
    "V5 - Trailing Dinámico (Rápido)": {"capital": 5000.0, "tiempo_eval": 2, "filtros": "trailing_rapido"},
    
    # --- V8 - MODO PRUEBAS (IGNORA TODO) ---
    "V8 - Ultra-Sensible (Modo Pruebas)": {"capital": 5000.0, "tiempo_eval": 1, "filtros": "pruebas"}
}

ARCHIVO_CSV = "simulacion_12_estrategias.csv"
ARCHIVO_CAPITAL = "capital_12_estrategias.json"

# ==========================================
# SERVIDOR WEB (Render)
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): return "🟢 Matriz 3D de Sensibilidad Activa (12 Estrategias)"

# ==========================================
# UTILIDADES
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
# GESTIÓN DE CAPITAL Y MARTINGALA
# ==========================================
def cargar_capital():
    if os.path.exists(ARCHIVO_CAPITAL):
        try:
            with open(ARCHIVO_CAPITAL, "r") as f: return json.load(f)
        except: pass
    return {v: data["capital"] for v, data in VERSIONES.items()}

def guardar_capital(capital):
    with open(ARCHIVO_CAPITAL, "w") as f: json.dump(capital, f)

def calcular_resultado(version, activo, precio_entrada, precio_salida, señal, perdidas_consecutivas=0):
    capital = cargar_capital()
    balance_actual = capital.get(version, 5000.0)
    
    # --- LÓGICA DE MARTINGALA (Solo para V4) ---
    if "Martingala" in version:
        # Si perdimos antes, duplicamos el riesgo. Si ganamos, volvemos a 1R.
        if perdidas_consecutivas > 0:
            multiplicador_riesgo = min(2 ** perdidas_consecutivas, 5) # Máximo 5x para no quemar
        else:
            multiplicador_riesgo = 1.0
        riesgo_1R = balance_actual * 0.01 * multiplicador_riesgo
    else:
        riesgo_1R = balance_actual * 0.01 
    
    valor_pip = 10.0 if activo in ["Oro", "Petróleo"] else 1.0
    lote = 0.10
    
    puntos_movimiento = (precio_salida - precio_entrada)
    es_compra = "COMPRAR" in señal
    ganancia_usd = (puntos_movimiento / 0.01) * valor_pip * lote if es_compra else (-puntos_movimiento / 0.01) * valor_pip * lote
    
    if "Ultra-Rápido" in version or "Trailing" in version:
        r_multiplo = round(ganancia_usd / riesgo_1R, 2)
    elif "Agresivo" in version:
        r_multiplo = round(ganancia_usd / (riesgo_1R * 0.3), 2)
    else:
        r_multiplo = round(ganancia_usd / riesgo_1R, 2)

    nuevo_balance = round(balance_actual + ganancia_usd, 2)
    capital[version] = nuevo_balance
    guardar_capital(capital)
    return ganancia_usd, r_multiplo, nuevo_balance

# ==========================================
# MOTOR DE ANÁLISIS CON SENSIBILIDADES Y FILTROS
# ==========================================
def analizar_mercado_con_sensibilidad(ticker, version):
    # 1. BASE COMÚN (Gann + Fib)
    df_daily = yf.Ticker(ticker).history(period="3mo", interval="1d")
    if df_daily is None or len(df_daily) < 20: return None, None
    
    high = df_daily["High"].tail(50).max()
    low = df_daily["Low"].tail(50).min()
    rango = high - low
    close = df_daily["Close"].iloc[-1]
    
    gann_50 = low + 0.5 * rango
    fib_95 = low + 0.95 * rango
    
    if "Pruebas" in version:
        tolerancia = rango * 0.20
    else:
        tolerancia = rango * 0.02
    
    confluencia = abs(close - gann_50) <= tolerancia and abs(close - fib_95) <= tolerancia
    if not confluencia and "Pruebas" not in version: return None, None

    # 2. FILTRO DE VOLUMEN MUERTO (Para todas menos V1, V3 y V8)
    if "V2" in version or "V4" in version or "V5" in version:
        df_hour = yf.Ticker(ticker).history(period="1mo", interval="1h")
        if df_hour is None or len(df_hour) < 20: return None, None
        
        vol_promedio_24h = df_hour['Volume'].tail(24).mean()
        vol_actual = df_hour['Volume'].iloc[-1]
        
        # Si el volumen actual es menor al 50% del promedio, es mercado muerto
        if vol_actual < (vol_promedio_24h * 0.5):
            return None, None # No operamos en mercado muerto

    # 3. ANÁLISIS DE VELAS (Solo para V2, V4, V5 y V8)
    if "V2" in version or "V4" in version or "V5" in version or "Pruebas" in version:
        df_hour = yf.Ticker(ticker).history(period="1mo", interval="1h")
        if df_hour is None or len(df_hour) < 3: return None, None
        
        v2 = df_hour.iloc[-2]
        v3 = df_hour.iloc[-1]
        
        cuerpo3 = abs(v3['Close'] - v3['Open'])
        rango3 = v3['High'] - v3['Low']
        mecha_inf3 = min(v3['Open'], v3['Close']) - v3['Low']
        mecha_sup3 = v3['High'] - max(v3['Open'], v3['Close'])
        
        if "Ultra-Conservadora" in version:
            condicion_vela = (mecha_inf3 >= (3 * cuerpo3) and mecha_sup3 < (0.1 * cuerpo3)) or (v2['Close'] < v2['Open'] and v3['Close'] > v3['Open'] and v3['Close'] > v2['Open'] * 1.05)
        elif "Agresiva" in version or "Pruebas" in version:
            condicion_vela = v3['Close'] > v3['Open']
        else:
            condicion_vela = (mecha_inf3 >= (2 * cuerpo3) and mecha_sup3 < (0.2 * cuerpo3)) or (v2['Close'] < v2['Open'] and v3['Close'] > v3['Open'] and v3['Open'] < v2['Close'] and v3['Close'] > v2['Open'])

        if not condicion_vela: return None, None

    return close, confluencia

# ==========================================
# CICLO PRINCIPAL
# ==========================================
def ejecutar_ciclo():
    informe = "🧪 *MATRIZ 3D DE SENSIBILIDAD - 5 MIN*\n\n"
    for activo, ticker in ACTIVOS.items():
        precio = precio_actual(ticker)
        if not precio: continue
        
        informe += f"🌐 *{activo}* | Precio: ${precio:,.2f}\n"
        
        for nombre_version in VERSIONES.keys():
            precio_entrada, confluencia = analizar_mercado_con_sensibilidad(ticker, nombre_version)
            
            if confluencia and precio_entrada:
                informe += f"  ✅ {nombre_version}: *ENTRADA* (${precio_entrada:.2f})\n"
                with open(ARCHIVO_CSV, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([nombre_version, activo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "COMPRAR", round(precio_entrada, 2), "", "", "", "", "", "Matriz"])
            else:
                informe += f"  ⏳ {nombre_version}: Sin confluencia\n"
        informe += "\n"
    
    enviar_alerta(informe)

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
                    
                    precio_salida = precio_hoy
                    # --- LÓGICA DE TRAILING DINÁMICO (Solo V5 y V3 Ultra-Rápido) ---
                    if "Trailing" in version or "Ultra-Rápido" in version:
                        movimiento = (precio_hoy - float(row["Precio_Entrada"])) if "COMPRAR" in row["Señal"] else (float(row["Precio_Entrada"]) - precio_hoy)
                        if movimiento > 0:
                            # Capturamos el 80% del movimiento si va a favor
                            precio_salida = float(row["Precio_Entrada"]) + (movimiento * 0.8) if "COMPRAR" in row["Señal"] else float(row["Precio_Entrada"]) - (movimiento * 0.8)
                        else:
                            # SL más ajustado en contra
                            precio_salida = float(row["Precio_Entrada"]) - (abs(movimiento) * 0.5) if "COMPRAR" in row["Señal"] else float(row["Precio_Entrada"]) + (abs(movimiento) * 0.5)

                    # --- CONTADOR DE PÉRDIDAS PARA MARTINGALA (V4) ---
                    perdidas_consecutivas = 0
                    if "Martingala" in version:
                        # Simulamos pérdidas consecutivas basándonos en resultados previos
                        historial = df[df["Version"] == version]
                        if not historial.empty:
                            ultimas_ops = historial.tail(3)
                            perdidas_consecutivas = len(ultimas_ops[ultimas_ops["Resultado_USD"].astype(float) < 0])

                    usd_change, r_mult, new_bal = calcular_resultado(version, row["Activo"], float(row["Precio_Entrada"]), precio_salida, row["Señal"], perdidas_consecutivas)
                    
                    df.at[idx, "Fecha_Salida"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df.at[idx, "Precio_Salida"] = round(precio_salida, 2)
                    df.at[idx, "R_Multiplo"] = r_mult
                    df.at[idx, "Resultado_USD"] = round(usd_change, 2)
                    df.at[idx, "Balance_Final"] = new_bal
                    cambios = True
                    
                    enviar_alerta(f"⚡ *CIERRE MATRIZ*\n{version} | {row['Activo']}\nR-Multiplo: {r_mult}R | ${usd_change:+.2f}\n💰 Balance: ${new_bal:,.2f}")
            except: pass
        if cambios: df.to_csv(ARCHIVO_CSV, index=False)

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == '__main__':
    guardar_capital(cargar_capital())
    enviar_alerta("🧪 *MATRIZ 3D DE SENSIBILIDAD INICIADA*\n12 Estrategias compitiendo con Martingala y Trailing Dinámico.")
    
    def ciclo_principal():
        while True:
            try:
                ejecutar_ciclo()
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(INTERVALO_SCAN_SEG)
            
    hilo_bot = threading.Thread(target=ciclo_principal)
    hilo_bot.start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)