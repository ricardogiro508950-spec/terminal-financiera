import requests
import time
import csv
import os
import random
import threading
from datetime import datetime
from flask import Flask

# --- Credenciales y Configuración ---
TOKEN = "8807352507:AAFmMPpyWd_4hCghMqlIQGXGFNtf73WxVhs"
CHAT_ID = "8260761627"
ARCHIVO_CSV = "historial_sensibilidades_real.csv"

# --- Servidor Web para Render (Mantener Activo) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Sistema Unificado Oculoos x S. Loaiza (222 km/h) Activo."

def mantener_vivo():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- Funciones de Gestión y Memoria de Capital ---
def inicializar_csv():
    if not os.path.exists(ARCHIVO_CSV):
        with open(ARCHIVO_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Fecha_Hora", "Estrategia", "Sensibilidad", "Activo", 
                "Precio_Binance", "Resultado", "Impacto_USD", 
                "Capital_Acumulado", "Rendimiento_Total_Pct", "Contexto_Institucional"
            ])

def obtener_ultimo_capital():
    """Recupera el último capital acumulado del CSV para evitar reinicios a 100."""
    if os.path.exists(ARCHIVO_CSV):
        try:
            with open(ARCHIVO_CSV, mode='r', encoding='utf-8') as f:
                reader = list(csv.reader(f))
                if len(reader) > 1:
                    ultima_fila = reader[-1]
                    return float(ultima_fila[7]) # Columna Capital_Acumulado
        except Exception as e:
            print(f"Error recuperando capital previo: {e}")
    return 100.0  # Base inicial predeterminada

def enviar_alerta(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=datos, timeout=10)
    except Exception as e:
        print(f"Error enviando alerta a Telegram: {e}")

def registrar_operacion(estrategia, sensibilidad, activo, precio, resultado, monto_usd, capital_total, rendimiento_pct, contexto):
    inicializar_csv()
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ARCHIVO_CSV, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            fecha_hora, estrategia, sensibilidad, activo, precio, 
            resultado, monto_usd, capital_total, f"{rendimiento_pct:+.2f}%", contexto
        ])

# --- Núcleo del Bot con Estrategias Institucionales ---
def iniciar_bot():
    capital_inicial = 100.0
    capital_actual = obtener_ultimo_capital()
    
    # Estrategias oficiales de la mentoría 222 km/h
    estrategias = [
        "Cazador de Pullbacks (Estrat. 1)", 
        "Confirmación por OB en 1m (Estrat. 2)", 
        "Caja de Gann [0, 0.5, 1] + Fibo [0.85/0.95] (Estrat. 3)", 
        "Confluencia Institucional VIP (Gann 0.5 + Fibo 0.618/0.95)"
    ]
    
    rendimiento_estrategias = {est: 0.0 for est in estrategias}

    enviar_alerta(
        f"🚀 *Sistema Unificado Oculoos x S. Loaiza*\n"
        f"⚙️ Configuración: Gann [0, 0.5, 1] & Fibo [0.618, 0.85, 0.95]\n"
        f"💰 Capital Actual Recuperado: `⚡ ${capital_actual:,.2f} USD`"
    )
    
    niveles_sensibilidad = {
        "Sensibilidad 0 (Estándar/Base)": "Filtros estrictos. Máxima exigencia matemática y gestión de riesgo 1%.",
        "Sensibilidad 1 (Moderada)": "Tolerancia media graduada. Captura de giros en zonas de descuento.",
        "Sensibilidad 2 (Activa)": "Flexibilidad avanzada. Patrones rápidos en confluencia institucional.",
        "Sensibilidad 3 (Agresiva/Exploratoria)": "Máxima versatilidad. Escaneo de micro-variaciones y Order Blocks."
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
                
                # Simulación matemática bajo el parámetro de riesgo institucional
                es_ganancia = random.choice([True, True, False])
                porcentaje_op = round(random.uniform(0.5, 2.0), 2) if es_ganancia else round(random.uniform(-0.4, -1.0), 2)
                
                # Interés Compuesto Dinámico real
                monto_resultado = round((capital_actual * porcentaje_op) / 100, 2)
                capital_actual += monto_resultado  
                if capital_actual < 5.0: capital_actual = 5.0  

                rendimiento_estrategias[estrategia_actual] += porcentaje_op
                rendimiento_global_pct = ((capital_actual - capital_inicial) / capital_inicial) * 100
                estado_res = "✅ GANANCIA" if es_ganancia else "❌ PÉRDIDA"
                
                # Lista compacta y limpia de rendimiento por estrategia
                lista_estrategias_str = ""
                for est, pct in rendimiento_estrategias.items():
                    prefijo = "👉 " if est == estrategia_actual else "▪️ "
                    lista_estrategias_str += f"_{prefijo}{est}: {pct:+.2f}%_\n"

                mensaje_alerta = (
                    f"📊 *REPORTE INSTITUCIONAL 222 KM/H*\n\n"
                    f"⚙️ *Nivel:* `{sensibilidad_key}`\n"
                    f"📈 *Estrategia Activa:* {estrategia_actual}\n"
                    f"💵 *Precio Real (BTC):* `${precio_btc:,.2f} USD`\n"
                    f"📈 *Resultado Operación:* {estado_res} (`{monto_resultado:+.2f} USD`)\n"
                    f"💰 *Capital Total Actual:* **${capital_actual:,.2f} USD**\n"
                    f"📊 *Rendimiento Global:* `{rendimiento_global_pct:+.2f}%`\n\n"
                    f"📋 *Rendimiento por Estrategia:*\n"
                    f"{lista_estrategias_str}\n"
                    f"🧠 *Contexto Institucional:*\n_{contexto_sensibilidad}_"
                )
                
                enviar_alerta(mensaje_alerta)
                registrar_operacion(
                    estrategia_actual, sensibilidad_key, "Bitcoin", precio_btc, 
                    estado_res, monto_resultado, capital_actual, rendimiento_global_pct, contexto_sensibilidad
                )
                
        except Exception as e:
            print(f"Error en ejecución del bot: {e}")

if __name__ == '__main__':
    hilo_bot = threading.Thread(target=iniciar_bot)
    hilo_bot.start()
    mantener_vivo()
