import os
import logging
import asyncio

# 1. APLICAR NEST_ASYNCIO INMEDIATAMENTE
import nest_asyncio
nest_asyncio.apply()

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
        " ¡Hola! Soy Mi-Bot-IA v2.0.\n"
        "Modo: Webhook (Serverless)\n"
        "Estado: Listo para recibir mensajes."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    # Respuesta temporal antes de integrar la IA completa
    await update.message.reply_text(
        f"✅ Recibido por Webhook: '{user_text}'\n"
        "🚀 Próximamente: Procesamiento con IA y generación de archivos."
    )

# --- INICIALIZACIÓN DE LA APLICACIÓN DE TELEGRAM ---
# Construimos la aplicación
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Registramos los handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Inicializamos la aplicación manualmente (requerido para modo Webhook sin polling)
try:
    # Usamos asyncio.run porque estamos fuera de un loop principal al inicio
    asyncio.run(application.initialize())
    logger.info("✅ Aplicación de Telegram inicializada correctamente para Webhooks.")
except Exception as e:
    logger.error(f"❌ Error crítico al inicializar Telegram App: {e}")
    # Si falla aquí, el bot no funcionará, así que lanzamos la excepción para detener el despliegue
    raise e

# --- RUTAS FLASK ---

@app.route('/')
def home():
    return jsonify({
        "service": "Mi-Bot-IA",
        "status": "running",
        "mode": "Webhook",
        "message": "Servidor activo. Usa /telegram para recibir mensajes."
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok", "cpu": "ready"})

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    
    if not data:
        logger.warning("️ Webhook recibido sin datos JSON.")
        return jsonify({"status": "error", "message": "No data"}), 400

    try:
        # Convertir JSON a objeto Update de python-telegram-bot
        update = Update.de_json(data, application.bot)
        
        if update is None:
            logger.warning("⚠️ No se pudo convertir el JSON a Update.")
            return jsonify({"status": "error", "message": "Invalid update"}), 400

        # Procesar el update
        # Gracias a nest_asyncio, esto funciona dentro de Flask sin cerrar el loop
        asyncio.run(application.process_update(update))
        
        logger.info(f"✅ Mensaje procesado exitosamente de usuario ID: {update.effective_user.id}")
        
        # Responder a Telegram inmediatamente con OK (200) para confirmar recepción
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f" Iniciando servidor web en puerto {port}...")
    # host='0.0.0.0' es OBLIGATORIO para Render/Azure
    app.run(host='0.0.0.0', port=port)