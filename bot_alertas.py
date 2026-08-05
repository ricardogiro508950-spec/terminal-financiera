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
SALDO_INICIAL = 50.0  # <--- CAMBIA ESTO SI ACTUALIZAS EL CÓDIGO Y LLEVABAS OTRO MONTO
PAYOUT_BINOMO = 0.82  # En Binomo pagan aprox 82% por operación ganada
INVERTIR_TODO_EL_SALDO = False # Ponlo en True si quieres arriesgar el 100% cada vez (All-In)
MONTO_FIJO = 10.0 # Solo se usa si el de arriba está en False

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
    return "🟢 Motor Gann-Fibonacci + Simulador 24/7."

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
# GESTOR DE LA CUENTA (BILLETERA VIRTUAL)
# ==========================================
def cargar_estado():
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"saldo": SALDO_INICIAL, "pendientes": []}

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
            print(f"🔄 INICIANDO ESCANEO (SALDO ACTUAL: ${estado['saldo']:.2f})")
            print("="*50)
            
            # 1. EVALUAR OPERACIONES PENDIENTES (Cerrando trades de hace 5 min)
            if estado['pendientes']:
                nuevos_pendientes = []
                for op in estado['pendientes']:
                    try:
                        df = yf.Ticker(op['ticker']).history(period="1d", interval="5m")
                        if df.empty:
                            nuevos_pendientes.append(op)
                            continue
                        
                        # El precio en vivo en este exacto momento
                        precio_salida = df.iloc[-1]['Close'] 
                        
                        ganada = False
                        empate = False
                        
                        # Verificar victoria
                        if "COMPRA" in op['accion']:
                            if precio_salida > op['precio_entrada']: ganada = True
                            elif precio_salida == op['precio_entrada']: empate = True
                        elif "VENTA" in op['accion']:
                            if precio_salida < op['precio_entrada']: ganada = True
                            elif precio_salida == op['precio_entrada']: empate = True
                            
                        # Actualizar Billetera
                        if ganada:
                            # Te devuelven tu inversión + la ganancia del 82%
                            retorno = op['inversion'] + (op['inversion'] * PAYOUT_BINOMO)
                            estado['saldo'] += retorno
                            res_txt = "✅ GANADA"
                        elif empate:
                            estado['saldo'] += op['inversion'] # Te devuelven el dinero
                            res_txt = "➖ EMPATE (Reembolso)"
                        else:
                            # Si se pierde, no se suma nada porque ya se descontó al entrar
                            res_txt = "❌ PERDIDA"
                            
                        msj_sim = (
                            f"🧾 *TICKET DE SIMULACIÓN (Cierre a 5 min)*\n\n"
                            f"🌐 *Activo:* {op['nombre']}\n"
                            f"⚖️ *Operación:* {op['accion']}\n"
                            f"💵 *Entrada:* ${op['precio_entrada']:,.4f}\n"
                            f"🏁 *Salida:* ${precio_salida:,.4f}\n"
                            f"🎯 *Resultado:* {res_txt}\n\n"
                            f"💰 *Inversión:* ${op['inversion']:.2f}\n"
                            f"🏦 *NUEVO SALDO TOTAL: ${estado['saldo']:.2f}*"
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
                        # Calcular cuánto invertir según configuración
                        if INVERTIR_TODO_EL_SALDO:
                            inversion = estado['saldo']
                        else:
                            inversion = MONTO_FIJO
                            if inversion > estado['saldo']:
                                inversion = estado['saldo']
                                
                        # Cobrar el dinero de la cuenta y registrar el trade
                        estado['saldo'] -= inversion
                        estado['pendientes'].append({
                            "nombre": nombre,
                            "ticker": ticker,
                            "accion": resultado['señal'],
                            "precio_entrada": resultado['precio'],
                            "inversion": inversion
                        })
                        guardar_estado(estado)
                        
                        msj = (
                            f"🎯 *SEÑAL GANN/FIBO DETECTADA*\n\n"
                            f"🌐 *Activo:* {nombre}\n"
                            f"📊 *Acción:* {resultado['señal']}\n"
                            f"💵 *Precio Actual:* ${resultado['precio']:,.4f}\n"
                            f"📐 *Zona Fibo:* ${resultado['fibo_85']:,.4f} - ${resultado['fibo_95']:,.4f}\n\n"
                            f"🤖 *SIMULADOR AUTOMÁTICO:*\n"
                            f"Se ha invertido automáticamente ${inversion:.2f} de tu cuenta virtual. El saldo temporal es ${estado['saldo']:.2f}. Te enviaré el ticket de resultado en 5 minutos."
                        )
                        enviar_alerta(msj)
            else:
                print("⚠️ SALDO AGOTADO. El simulador está en quiebra. Modifica SALDO_INICIAL en el código y reinicia.")

            print("⏳ Escaneo finalizado. Esperando 5 minutos...")
        except Exception as e:
            print(f"Error general: {e}")
        
        time.sleep(300)

if __name__ == "__main__":
    t = threading.Thread(target=mantener_vivo)
    t.daemon = True
    t.start()
    
    estado_ini = cargar_estado()
    enviar_alerta(f"✅ *SIMULADOR INICIADO:* El bot operará automáticamente con dinero virtual.\n🏦 *Saldo Inicial:* ${estado_ini['saldo']:.2f}")
    
    ciclo_principal()
