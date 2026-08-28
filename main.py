import os
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import asyncio # Asegúrate de importar asyncio

# Importamos tus tokens
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy Mi-Bot-IA v2.0 (Webhook Mode).")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text(f"Recibí tu mensaje por Webhook: '{user_text}'. Pronto procesaré esto con IA.")

# --- INICIALIZACIÓN DE TELEGRAM APP ---
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 🔴 CORRECCIÓN AQUÍ: Inicializar la aplicación manualmente para modo Webhook
# Esto debe hacerse en el hilo principal antes de que Flask empiece a recibir requests
try:
    asyncio.run(application.initialize())
    logger.info("✅ Aplicación de Telegram inicializada correctamente para Webhooks.")
except Exception as e:
    logger.error(f"❌ Error al inicializar Telegram App: {e}")

# --- RUTAS FLASK ---

@app.route('/')
def home():
    return jsonify({"service": "Mi-Bot-IA", "status": "running", "mode": "Webhook"})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "cpu": "ready"})

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    try:
        update = Update.de_json(data, application.bot)
        
        # Procesar el update
        # Nota: application.process_update ya es una corrutina, la ejecutamos con asyncio.run
        asyncio.run(application.process_update(update))
        
        logger.info(f"✅ Mensaje procesado de usuario {update.effective_user.id}")
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Iniciando servidor web en puerto {port}...")
    app.run(host='0.0.0.0', port=port)