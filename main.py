import os
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Importamos tokens 
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# HANDLERS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy Mi-Bot-IA v2.0 (Webhook Mode).")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    user_text = update.message.text
    await update.message.reply_text(f"Recibí tu mensaje por Webhook: '{user_text}'. Pronto procesaré esto con IA.")

# --- INICIALIZACIÓN DE LA APP DE TELEGRAM ---
# Nota: En modo Webhook, NO usamos run_polling(). Solo creamos la aplicación para procesar updates.
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- RUTAS FLASK ---

@app.route('/')
def home():
    return jsonify({"service": "Mi-Bot-IA", "status": "running", "mode": "Webhook"})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "cpu": "ready"})

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    # 1. Obtener el JSON que Telegram envía
    data = request.get_json()
    
    # 2. Convertirlo a un objeto Update de python-telegram-bot
    try:
        update = Update.de_json(data, application.bot)
        
        # 3. Procesar el update (esto ejecutará tus handlers: start, handle_message, etc.)
        # Usamos asyncio.run porque estamos fuera de un loop asíncrono principal
        import asyncio
        asyncio.run(application.process_update(update))
        
        logger.info(f"✅ Mensaje procesado de usuario {update.effective_user.id}")
        
        # 4. Responder a Telegram inmediatamente con OK (para que sepa que lo recibimos)
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Iniciando servidor web en puerto {port}...")
    app.run(host='0.0.0.0', port=port)