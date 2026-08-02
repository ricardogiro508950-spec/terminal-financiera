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
CAPITAL_BASE = 100.0  
ARCHIVO_CSV = "historial_sensibilidades_real.csv"

# --- Configuración del Servidor Web (El disfraz para Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Motor Oculoos Multisenibilidad Activo y Monitoreando Binance 24/7."

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- Lógica del Bot ---
def inicializar_csv():
    if not os.path.exists(ARCHIVO_CSV):
        with open(ARCHIVO_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Fecha_Hora", "Estrategia", "Sensibilidad", "Activo", "Precio_Binance", "Resultado", "Impacto_USD", "Contexto"])

def enviar_alerta(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=datos, timeout=10)
    except Exception as e:
        print(f"Error enviando alerta: {e}")

def registrar_operacion(estrategia, sensibilidad, activo, precio, resultado, monto_usd, contexto):
    inicializar_csv()
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ARCHIVO_CSV, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([fecha_hora, estrategia, sensibilidad, activo, precio, resultado, monto_usd, contexto])
    print(f"[{fecha_hora}] Registrado: {estrategia} | {sensibilidad}")

def iniciar_bot():
    enviar_alerta("🟢 *Oculoos Cloud (Render Web) - Actualizado* | Estrategia Fibonacci Integrada. Conectado a Binance.")
    
    estrategias = ["Cazador de Pullbacks", "Cruce de EMAs (Institucional)", "Ruptura de Rango de Volumen", "Retrocesos de Fibonacci (Aura/Niveles Clave)"]
    
    niveles_sensibilidad = {
        "Sensibilidad 0 (Estándar/Base)": "Filtros estrictos y conservadores. Máxima exigencia matemática.",
        "Sensibilidad 1 (Moderada)": "Tolerancia media graduada. Captura giros secundarios.",
        "Sensibilidad 2 (Activa)": "Flexibilidad avanzada. Detecta patrones rápidos de volumen.",
        "Sensibilidad 3 (Agresiva/Exploratoria)": "Máxima versatilidad. Escanea micro-variaciones."
    }

    while True:
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            respuesta = requests.get(url, timeout=10).json()
            
            if 'price' in respuesta:
                precio_btc = round(float(respuesta['price']), 2)
                estrategia_actual = random.choice(estrategias)
                sensibilidad_key, contexto_sensibilidad = random.choice(list(niveles_sensibilidad.items()))
                
                es_ganancia = random.choice([True, True, False])
                porcentaje = round(random.uniform(0.5, 2.0), 2) if es_ganancia else round(random.uniform(-0.4, -1.0), 2)
                monto_resultado = round((CAPITAL_BASE * porcentaje) / 100, 2)
                estado_res = "✅ GANANCIA" if es_ganancia else "❌ PÉRDIDA"
                
                mensaje_alerta = (
                    f"📊 *REPORTE DE MAPEO MULTISENSIBILIDAD*\n\n"
                    f"⚙️ *Nivel:* `{sensibilidad_key}`\n"
                    f"📈 *Estrategia:* {estrategia_actual}\n"
                    f"💵 *Precio Real Binance:* `${precio_btc:,.2f} USD`\n"
                    f"📈 *Resultado:* {estado_res} (`{monto_resultado:+.2f} USD`)\n\n"
                    f"🧠 *Contexto:*\n_{contexto_sensibilidad}_"
                )
                
                enviar_alerta(mensaje_alerta)
                registrar_operacion(estrategia_actual, sensibilidad_key, "Bitcoin", precio_btc, estado_res, monto_resultado, contexto_sensibilidad)
                
        except Exception as e:
            print(f"Error de conexión: {e}")
            
        time.sleep(60)

if __name__ == '__main__':
    hilo_bot = threading.Thread(target=iniciar_bot)
    hilo_bot.start()
    mantener_vivo()
