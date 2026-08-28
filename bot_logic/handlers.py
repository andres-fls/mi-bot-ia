from telegram import Update
from telegram.ext import ContextTypes
from .ai_core import ai_engine
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " ¡Hola! Soy Mi-Bot-IA v3.1.\n\n"
        "Tengo cerebro propio con múltiples modelos de IA:\n"
        " Rápido para charlas simples.\n"
        "💪 Potente para código y lógica.\n"
        "️ Respaldo automático si algo falla.\n\n"
        "Escribe algo o pide un PDF/Word!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    try:
        # 1. Llamar al núcleo de IA
        resultado = await ai_engine.process_message(user_text, user_id, detect_file_type=True)
        
        respuesta = resultado["response"]
        file_buffer = resultado["file_buffer"]
        filename = resultado["filename"]
        file_type = resultado["file_type"]

        # 2. Enviar respuesta
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
        # Capturamos cualquier error inesperado para que el bot no se caiga
        logger.error(f"Error inesperado en handle_message: {e}", exc_info=True)
        # Enviamos un mensaje amigable al usuario en lugar de romper el flujo
        try:
            await update.message.reply_text("⚠️ Ocurrió un error interno inesperado. Intenta de nuevo en unos segundos.")
        except:
            pass # Si ni siquiera podemos enviar el error, mejor no hacer nada