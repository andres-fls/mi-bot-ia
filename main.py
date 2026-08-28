import os
import logging
import asyncio
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Configuración de Tokens
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("⚠️ Faltan las variables de entorno: TELEGRAM_TOKEN")

# Configuración de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- HANDLERS DE TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy Mi-Bot-IA v2.0.\n"
        "Modo: Webhook (Serverless)\n"
        "Estado: Listo para recibir mensajes."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text(
        f"✅ Recibido por Webhook: '{user_text}'\n"
        "🚀 Próximamente: Procesamiento con IA y generación de archivos."
    )

# --- INICIALIZACIÓN DE LA APLICACIÓN DE TELEGRAM ---
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Inicializar la aplicación al inicio (fuera del loop de Flask)
try:
    # Creamos un loop temporal solo para la inicialización
    loop_init = asyncio.new_event_loop()
    asyncio.set_event_loop(loop_init)
    loop_init.run_until_complete(application.initialize())
    loop_init.close()
    logger.info("✅ Aplicación de Telegram inicializada correctamente.")
except Exception as e:
    logger.error(f"❌ Error crítico al inicializar: {e}")
    raise e

# --- RUTAS FLASK ---

@app.route('/')
def home():
    return jsonify({
        "service": "Mi-Bot-IA",
        "status": "running",
        "mode": "Webhook"
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok", "cpu": "ready"})

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    try:
        update = Update.de_json(data, application.bot)
        
        if update is None:
            return jsonify({"status": "error", "message": "Invalid update"}), 400

        # SOLUCIÓN: Crear un nuevo loop de eventos exclusivo para procesar este update
        # Esto evita conflictos con el entorno de Flask y errores de referencias débiles
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(application.process_update(update))
        finally:
            loop.close()
        
        logger.info(f"✅ Mensaje procesado de usuario ID: {update.effective_user.id}")
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f" Error procesando webhook: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f" Iniciando servidor web en puerto {port}...")
    app.run(host='0.0.0.0', port=port)