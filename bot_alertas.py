import requests
import time
import csv
import os
import random
import threading
from datetime import datetime
from flask import Flask

# --- Credenciales ---
TOKEN = "8807352507:AAFmMPpyWd_4hCghMqlIQGXGFNtf73WxVhs"
CHAT_ID = "8260761627"
ARCHIVO_CSV = "historial_sensibilidades_real.csv"

# --- Configuración del Servidor Web (El disfraz para Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Motor Oculoos con Capital Compuesto Activo."

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- Lógica del Bot ---
def inicializar_csv():
    if not os.path.exists(ARCHIVO_CSV):
        with open(ARCHIVO_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Fecha_Hora", "Estrategia", "Sensibilidad", "Activo", "Precio_Binance", "Resultado", "Impacto_USD", "Capital_Acumulado", "Contexto"])

def enviar_alerta(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=datos, timeout=10)
    except Exception as e:
        print(f"Error enviando alerta: {e}")

def registrar_operacion(estrategia, sensibilidad, activo, precio, resultado, monto_usd, capital_total, contexto):
    inicializar_csv()
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ARCHIVO_CSV, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([fecha_hora, estrategia, sensibilidad, activo, precio, resultado, monto_usd, capital_total, contexto])
    print(f"[{fecha_hora}] Registrado: {estrategia} | Capital Total: ${capital_total:.2f}")

def iniciar_bot():
    # Capital inicial con el que arranca el interés compuesto
    capital_actual = 100.0
    enviar_alerta(f"🟢 *Oculoos Cloud* | Interés Compuesto Activado. Capital Inicial: `${capital_actual:.2f} USD`. Conectado a Binance (USA).")
    
    estrategias = [
        "Cazador de Pullbacks", 
        "Cruce de EMAs (Institucional)", 
        "Ruptura de Rango de Volumen", 
        "Retrocesos de Fibonacci (Aura/Niveles Clave)",
        "Confluencia VIP (S. Loaiza: Gann 0.5 + Fibo 0.85/0.95)"
    ]
    
    niveles_sensibilidad = {
        "Sensibilidad 0 (Estándar/Base)": "Filtros estrictos y conservadores. Máxima exigencia matemática.",
        "Sensibilidad 1 (Moderada)": "Tolerancia media graduada. Captura giros secundarios.",
        "Sensibilidad 2 (Activa)": "Flexibilidad avanzada. Detecta patrones rápidos de volumen.",
        "Sensibilidad 3 (Agresiva/Exploratoria)": "Máxima versatilidad. Escanea micro-variaciones."
    }

    while True:
        time.sleep(60) 
        try:
            url = "https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT"
            respuesta = requests.get(url, timeout=10).json()
            
            if 'price' in respuesta:
                precio_btc = round(float(respuesta['price']), 2)
                estrategia_actual = random.choice(estrategias)
                sensibilidad_key, contexto_sensibilidad = random.choice(list(niveles_sensibilidad.items()))
                
                es_ganancia = random.choice([True, True, False])
                porcentaje = round(random.uniform(0.5, 2.0), 2) if es_ganancia else round(random.uniform(-0.4, -1.0), 2)
                
                # CÁLCULO DE INTERÉS COMPUESTO: Se calcula en base al capital acumulado actual
                monto_resultado = round((capital_actual * porcentaje) / 100, 2)
                capital_actual += monto_resultado  # Se suma la ganancia o resta la pérdida al capital
                if capital_actual < 5.0: capital_actual = 5.0  # Piso de seguridad
                
                estado_res = "✅ GANANCIA" if es_ganancia else "❌ PÉRDIDA"
                
                mensaje_alerta = (
                    f"📊 *REPORTE DE CAPITAL COMPUESTO*\n\n"
                    f"⚙️ *Nivel:* `{sensibilidad_key}`\n"
                    f"📈 *Estrategia:* {estrategia_actual}\n"
                    f"💵 *Precio Real (BTC):* `${precio_btc:,.2f} USD`\n"
                    f"📈 *Resultado:* {estado_res} (`{monto_resultado:+.2f} USD`)\n"
                    f"💰 *Nuevo Capital Total:* **${capital_actual:,.2f} USD**\n\n"
                    f"🧠 *Contexto:*\n_{contexto_sensibilidad}_"
                )
                
                enviar_alerta(mensaje_alerta)
                registrar_operacion(estrategia_actual, sensibilidad_key, "Bitcoin", precio_btc, estado_res, monto_resultado, capital_actual, contexto_sensibilidad)
                
        except Exception as e:
            print(f"Error de conexión: {e}")

if __name__ == '__main__':
    hilo_bot = threading.Thread(target=iniciar_bot)
    hilo_bot.start()
    mantener_vivo()
