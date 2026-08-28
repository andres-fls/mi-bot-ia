from telegram import Update
from telegram.ext import ContextTypes
from .ai_core import ai_engine
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start"""
    await update.message.reply_text(
        " ¡Hola! Soy Mi-Bot-IA v3.0.\n\n"
        "Tengo cerebro propio con múltiples modelos de IA:\n"
        "⚡ Rápido para charlas simples.\n"
        "💪 Potente para código y lógica.\n"
        "🛡️ Respaldo automático si algo falla.\n\n"
        "Escribe algo o pide un PDF/Word!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes de texto normales"""
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Indicador de "escribiendo..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        # 1. Llamar al núcleo de IA (detect_file_type=True busca palabras como "pdf")
        resultado = await ai_engine.process_message(user_text, user_id, detect_file_type=True)
        
        respuesta = resultado["response"]
        file_buffer = resultado["file_buffer"]
        filename = resultado["filename"]
        file_type = resultado["file_type"]

        # 2. Enviar respuesta
        if file_buffer and filename:
            # Si hay archivo, enviarlo primero
            await update.message.reply_document(
                document=file_buffer,
                filename=filename,
                caption=f"Aquí tienes tu respuesta en formato {file_type.upper()} 📄"
            )
            # Opcional: También enviar el texto breve
            # await update.message.reply_text(respuesta[:1000] + "...") 
        else:
            # Si no hay archivo, enviar texto normal
            # Telegram tiene límite de 4096 caracteres, si es muy largo lo cortamos o enviamos en partes
            if len(respuesta) > 4000:
                respuesta = respuesta[:4000] + "\n\n...(mensaje truncado por longitud)"
            
            await update.message.reply_text(respuesta)

    except Exception as e:
        logger.error(f"Error en handle_message: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Ocurrió un error interno inesperado. Intenta de nuevo.")