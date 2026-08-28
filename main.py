import os
import logging
from flask import Flask, request, jsonify
# Importaremos la lógica del bot más tarde
# from bot_logic.handlers import process_telegram_update 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Ruta principal (Landing Page mínima)
@app.route('/')
def home():
    return jsonify({
        "service": "Mi-Bot-IA",
        "status": "running",
        "message": "Bienvenido al cerebro de IA. Usa /telegram para webhooks."
    })

# Ruta de Salud (Health Check) - Vital para Azure
@app.route('/health')
def health():
    return jsonify({"status": "ok", "cpu": "ready"})

# Ruta para Webhook de Telegram (La dejaremos lista pero vacía por ahora)
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    # Aquí procesaremos los mensajes cuando migremos de Polling a Webhook
    data = request.get_json()
    logger.info("Recibido webhook de Telegram")
    # Lógica futura: process_telegram_update(data)
    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    # Render y Azure usan la variable de entorno PORT. Por defecto 10000.
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Iniciando servidor web en puerto {port}...")
    # host='0.0.0.0' es OBLIGATORIO para que Render/Azure detecten el puerto
    app.run(host='0.0.0.0', port=port)