import os
import time
import threading
import requests
import json
import pandas as pd
import yfinance as yf
from flask import Flask
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DEL SIMULADOR DE DINERO
# ==========================================
ARCHIVO_ESTADO = "simulador.json"
SALDO_INICIAL = 58.20  # <--- Actualizado a tu saldo actual tras la victoria
PAYOUT_BINOMO = 0.82  
MONTO_FIJO = 10.0 
ESTRATEGIA_ANTI_MARTINGALA = True # <--- Tu nueva regla: $10 + Ganancia anterior

# ==========================================
# CONFIGURACIÓN DE TELEGRAM Y ACTIVOS
# ==========================================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

ACTIVOS = {
    "Oro (XAUUSD)": "GC=F",
    "Bitcoin": "BTC-USD",
    "Euro / Dólar": "EURUSD=X",
    "Dólar / Yen": "USDJPY=X",
    "Euro / Libra": "EURGBP=X"
}

app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Motor Gann-Fibonacci + Simulador Anti-Martingala 24/7."

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

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
# GESTOR DE LA CUENTA Y RACHAS
# ==========================================
def cargar_estado():
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, 'r') as f:
                data = json.load(f)
                # Aseguramos que tenga la variable de racha si es un archivo viejo
                if 'ultima_ganancia' not in data:
                    data['ultima_ganancia'] = 0.0
                return data
        except:
            pass
    return {"saldo": SALDO_INICIAL, "pendientes": [], "ultima_ganancia": 0.0}

def guardar_estado(estado):
    with open(ARCHIVO_ESTADO, 'w') as f:
        json.dump(estado, f)

# ==========================================
# EL MOTOR DEL ALGORITMO (GANN + FIBO)
# ==========================================
def analizar_mercado(nombre, ticker):
    try:
        df = yf.Ticker(ticker).history(period="2d", interval="5m")
        if df.empty or len(df) < 60:
            return None

        ventana = df.tail(50)
        maximo = ventana['High'].max()
        minimo = ventana['Low'].min()
        rango_total = maximo - minimo
        
        if rango_total == 0:
            return None

        idx_max = ventana['High'].idxmax()
        idx_min = ventana['Low'].idxmin()

        vela = df.iloc[-2]
        c = vela['Close']
        o = vela['Open']
        h = vela['High']
        l = vela['Low']
        
        cuerpo = abs(c - o)
        mecha_sup = h - max(c, o)
        mecha_inf = min(c, o) - l

        zona_fibo_activa = False
        tipo_operacion = ""
        fibo_85 = 0
        fibo_95 = 0

        # COMPRAS
        if idx_max > idx_min: 
            fibo_85 = maximo - (rango_total * 0.85)
            fibo_95 = maximo - (rango_total * 0.95)
            if fibo_95 <= l <= fibo_85:
                zona_fibo_activa = True
                tipo_operacion = "🟢 COMPRA"
                gatillo = mecha_inf > (1.5 * cuerpo)

        # VENTAS
        else:
            fibo_85 = minimo + (rango_total * 0.85)
            fibo_95 = minimo + (rango_total * 0.95)
            if fibo_85 <= h <= fibo_95:
                zona_fibo_activa = True
                tipo_operacion = "🔴 VENTA"
                gatillo = mecha_sup > (1.5 * cuerpo)

        if zona_fibo_activa and gatillo:
            return {
                "señal": tipo_operacion, 
                "precio": c, 
                "fibo_85": fibo_85, 
                "fibo_95": fibo_95
            }

        return None

    except Exception as e:
        return None

# ==========================================
# CICLO PRINCIPAL Y SIMULADOR
# ==========================================
def ciclo_principal():
    while True:
        try:
            estado = cargar_estado()
            print("\n" + "="*50)
            print(f"🔄 ESCANEANDO (SALDO: ${estado['saldo']:.2f} | RACHA: +${estado['ultima_ganancia']:.2f})")
            print("="*50)
            
            # 1. EVALUAR OPERACIONES PENDIENTES
            if estado['pendientes']:
                nuevos_pendientes = []
                for op in estado['pendientes']:
                    try:
                        df = yf.Ticker(op['ticker']).history(period="1d", interval="5m")
                        if df.empty:
                            nuevos_pendientes.append(op)
                            continue
                        
                        precio_salida = df.iloc[-1]['Close'] 
                        ganada = False
                        empate = False
                        
                        if "COMPRA" in op['accion']:
                            if precio_salida > op['precio_entrada']: ganada = True
                            elif precio_salida == op['precio_entrada']: empate = True
                        elif "VENTA" in op['accion']:
                            if precio_salida < op['precio_entrada']: ganada = True
                            elif precio_salida == op['precio_entrada']: empate = True
                            
                        # Actualizar Billetera y Memoria de Racha
                        if ganada:
                            ganancia_neta = op['inversion'] * PAYOUT_BINOMO
                            estado['saldo'] += op['inversion'] + ganancia_neta
                            
                            # Tu regla: guardar la ganancia para la próxima jugada
                            if ESTRATEGIA_ANTI_MARTINGALA:
                                estado['ultima_ganancia'] = ganancia_neta
                            else:
                                estado['ultima_ganancia'] = 0.0
                                
                            res_txt = "✅ GANADA"
                            racha_txt = f"📈 ¡Racha activa! Próxima inversión incluirá +${estado['ultima_ganancia']:.2f}"
                            
                        elif empate:
                            estado['saldo'] += op['inversion'] 
                            estado['ultima_ganancia'] = 0.0 # Se corta la racha
                            res_txt = "➖ EMPATE (Reembolso)"
                            racha_txt = "Reinicio a $10.00"
                            
                        else:
                            estado['ultima_ganancia'] = 0.0 # Pierde la ganancia, vuelve a $10
                            res_txt = "❌ PERDIDA"
                            racha_txt = "Reinicio a $10.00"
                            
                        msj_sim = (
                            f"🧾 *TICKET DE CIERRE (5 min)*\n\n"
                            f"🌐 *Activo:* {op['nombre']}\n"
                            f"⚖️ *Operación:* {op['accion']}\n"
                            f"💵 *Entrada:* ${op['precio_entrada']:,.4f}\n"
                            f"🏁 *Salida:* ${precio_salida:,.4f}\n"
                            f"🎯 *Resultado:* {res_txt}\n\n"
                            f"💰 *Inversión:* ${op['inversion']:.2f}\n"
                            f"🏦 *NUEVO SALDO TOTAL: ${estado['saldo']:.2f}*\n"
                            f"_{racha_txt}_"
                        )
                        enviar_alerta(msj_sim)
                        
                    except Exception as e:
                        print(f"Error revisando pendiente: {e}")
                        nuevos_pendientes.append(op)
                
                estado['pendientes'] = nuevos_pendientes
                guardar_estado(estado)

            # 2. ESCANEAR NUEVAS OPORTUNIDADES
            if estado['saldo'] > 0:
                for nombre, ticker in ACTIVOS.items():
                    resultado = analizar_mercado(nombre, ticker)
                    
                    if resultado:
                        # Cálculo de Anti-Martingala: Base + Ganancia anterior
                        inversion_calculada = MONTO_FIJO + estado.get('ultima_ganancia', 0.0)
                        
                        if inversion_calculada > estado['saldo']:
                            inversion_calculada = estado['saldo']
                                
                        estado['saldo'] -= inversion_calculada
                        estado['pendientes'].append({
                            "nombre": nombre,
                            "ticker": ticker,
                            "accion": resultado['señal'],
                            "precio_entrada": resultado['precio'],
                            "inversion": inversion_calculada
                        })
                        guardar_estado(estado)
                        
                        msj = (
                            f"🎯 *SEÑAL GANN/FIBO DETECTADA*\n\n"
                            f"🌐 *Activo:* {nombre}\n"
                            f"📊 *Acción:* {resultado['señal']}\n"
                            f"💵 *Precio Actual:* ${resultado['precio']:,.4f}\n"
                            f"📐 *Zona Fibo:* ${resultado['fibo_85']:,.4f} - ${resultado['fibo_95']:,.4f}\n\n"
                            f"🤖 *SIMULADOR ANTI-MARTINGALA:*\n"
                            f"Invirtiendo ${inversion_calculada:.2f} (Base + Racha). Saldo restante en caja: ${estado['saldo']:.2f}."
                        )
                        enviar_alerta(msj)
            else:
                print("⚠️ SALDO AGOTADO. Modifica SALDO_INICIAL en el código y reinicia.")

            print("⏳ Esperando 5 minutos...")
        except Exception as e:
            print(f"Error general: {e}")
        
        time.sleep(300)

if __name__ == "__main__":
    t = threading.Thread(target=mantener_vivo)
    t.daemon = True
    t.start()
    
    estado_ini = cargar_estado()
    enviar_alerta(f"✅ *SIMULADOR ANTI-MARTINGALA ACTIVO:*\n🏦 *Saldo Inicial:* ${estado_ini['saldo']:.2f}\nEstrategia: Invertir $10.00 base + ganancias consecutivas.")
    
    ciclo_principal()
