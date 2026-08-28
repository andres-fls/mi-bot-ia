from telegram import Update
from telegram.ext import ContextTypes
from .ai_core import ai_engine
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " ¡Hola! Soy Mi-Bot-IA v3.0.\n\n"
        "Tengo cerebro propio con múltiples modelos de IA:\n"
        " Rápido para charlas simples.\n"
        "💪 Potente para código y lógica.\n"
        "️ Respaldo automático si algo falla.\n\n"
        "Escribe algo o pide un PDF/Word!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Eliminamos send_chat_action para evitar conflictos de loop en este entorno específico
    # La IA responderá lo suficientemente rápido para que no sea necesario el indicador "typing"
    
    try:
        resultado = await ai_engine.process_message(user_text, user_id, detect_file_type=True)
        
        respuesta = resultado["response"]
        file_buffer = resultado["file_buffer"]
        filename = resultado["filename"]
        file_type = resultado["file_type"]

        if file_buffer and filename:
            await update.message.reply_document(
                document=file_buffer,
                filename=filename,
                caption=f"Aquí tienes tu respuesta en formato {file_type.upper()} 📄"
            )
        else:
            if len(respuesta) > 4000:
                respuesta = respuesta[:4000] + "\n\n...(mensaje truncado por longitud)"
            
            await update.message.reply_text(respuesta)

    except Exception as e:
        logger.error(f"Error en handle_message: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Ocurrió un error interno inesperado. Intenta de nuevo.")