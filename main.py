import os
import sys
from dotenv import load_dotenv 

# Cargar variables desde el archivo .env
load_dotenv() 

current_dir = os.path.dirname(os.path.abspath(__file__))

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import logging
import asyncio
import nest_asyncio  # <--- IMPORTAR

# APLICAR NEST_ASYNCIO INMEDIATAMENTE
nest_asyncio.apply() 

from flask import Flask, request, jsonify

from bot_logic.handlers import start, handle_message
from bot_logic.ai_core import ai_engine

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Configuración
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("⚠️ Falta TELEGRAM_TOKEN en variables de entorno")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- INICIALIZACIÓN DE TELEGRAM APP ---
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Registramos los handlers IMPORTADOS desde bot_logic
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Inicializar app de Telegram manualmente (necesario para Webhook)
try:
    loop_init = asyncio.new_event_loop()
    asyncio.set_event_loop(loop_init)
    loop_init.run_until_complete(application.initialize())
    loop_init.close()
    logger.info("✅ Aplicación de Telegram inicializada correctamente.")
except Exception as e:
    logger.error(f"❌ Error al inicializar Telegram App: {e}")
    raise e

# --- RUTAS FLASK ---

@app.route('/')
def home():
    return jsonify({
        "service": "Mi-Bot-IA",
        "status": "running",
        "architecture": "Modular (Fase 2)",
        "components": ["Flask", "Telegram Webhook", "bot_logic"]
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok", "cpu": "ready", "ai_core": "loaded"})

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    try:
        update = Update.de_json(data, application.bot)
        if update is None:
            return jsonify({"status": "error", "message": "Invalid update"}), 400

        # Procesar update
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(application.process_update(update))
        finally:
            loop.close()
        
        logger.info(f"✅ Mensaje procesado de usuario ID: {update.effective_user.id}")
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error en webhook: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Iniciando servidor web en puerto {port}...")
    app.run(host='0.0.0.0', port=port)