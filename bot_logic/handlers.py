from telegram import Update
from telegram.ext import ContextTypes

from .ai_core import ai_engine

import logging


logger = logging.getLogger(__name__)


# ============================================================
# COMANDO /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        logger.info(
            "📌 Comando /start recibido de usuario %s",
            update.effective_user.id
        )

        await update.message.reply_text(
            "👋 ¡Hola! Soy Mi-Bot-IA v3.1.\n\n"
            "Tengo cerebro propio con múltiples modelos de IA:\n"
            "⚡ Rápido para charlas simples.\n"
            "💪 Potente para código y lógica.\n"
            "🔄 Respaldo automático si algo falla.\n\n"
            "Escribe algo o pide un PDF/Word."
        )

        logger.info(
            "✅ Respuesta /start enviada correctamente."
        )

    except Exception as e:

        logger.error(
            "❌ Error en comando /start: %s: %s",
            type(e).__name__,
            e,
            exc_info=True
        )


# ============================================================
# MENSAJES DE TEXTO
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # --------------------------------------------------------
    # Validaciones básicas
    # --------------------------------------------------------

    if not update.effective_user:

        logger.warning(
            "⚠️ Update recibido sin effective_user."
        )

        return


    if not update.message:

        logger.warning(
            "⚠️ Update recibido sin message."
        )

        return


    user_id = update.effective_user.id
    user_text = update.message.text


    logger.info(
        "📨 Mensaje recibido | Usuario: %s | Texto: %s",
        user_id,
        user_text[:100] if user_text else "<vacío>"
    )


    try:

        # ----------------------------------------------------
        # 1. Llamar al núcleo de IA
        # ----------------------------------------------------

        logger.info(
            "🧠 Enviando mensaje al AI Core..."
        )

        resultado = await ai_engine.process_message(
            user_text,
            user_id,
            detect_file_type=True
        )


        logger.info(
            "✅ AI Core respondió correctamente."
        )


        # ----------------------------------------------------
        # 2. Extraer resultado
        # ----------------------------------------------------

        respuesta = resultado.get("response")
        file_buffer = resultado.get("file_buffer")
        filename = resultado.get("filename")
        file_type = resultado.get("file_type")


        if not respuesta:

            logger.warning(
                "⚠️ AI Core devolvió una respuesta vacía."
            )

            respuesta = (
                "⚠️ No recibí una respuesta válida de la IA."
            )


        # ----------------------------------------------------
        # 3. Enviar archivo
        # ----------------------------------------------------

        if file_buffer and filename:

            logger.info(
                "📄 Enviando archivo generado: %s",
                filename
            )

            await update.message.reply_document(
                document=file_buffer,
                filename=filename,
                caption=(
                    f"Aquí tienes tu respuesta "
                    f"en formato {file_type.upper()} 📄"
                )
            )

            logger.info(
                "✅ Archivo enviado correctamente."
            )

            return


        # ----------------------------------------------------
        # 4. Enviar respuesta de texto
        # ----------------------------------------------------

        if len(respuesta) > 4000:

            logger.info(
                "✂️ Respuesta superior a 4000 caracteres. "
                "Será truncada."
            )

            respuesta = (
                respuesta[:4000]
                + "\n\n...(mensaje truncado por longitud)"
            )


        await update.message.reply_text(
            respuesta
        )


        logger.info(
            "✅ Respuesta enviada correctamente a usuario %s.",
            user_id
        )


    except Exception as e:

        # ----------------------------------------------------
        # ERROR REAL
        # ----------------------------------------------------

        logger.error(
            "❌ ERROR EN HANDLE_MESSAGE\n"
            "Usuario: %s\n"
            "Tipo: %s\n"
            "Mensaje: %s",
            user_id,
            type(e).__name__,
            str(e),
            exc_info=True
        )


        # ----------------------------------------------------
        # Intentar informar al usuario
        # ----------------------------------------------------

        try:

            await update.message.reply_text(
                "⚠️ Ocurrió un error interno inesperado.\n\n"
                "El error fue registrado en los logs."
            )

        except Exception as reply_error:

            logger.error(
                "❌ No fue posible enviar el mensaje de error "
                "al usuario: %s: %s",
                type(reply_error).__name__,
                reply_error,
                exc_info=True
            )