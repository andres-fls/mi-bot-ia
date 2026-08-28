import os
import sys
import asyncio
import logging
import threading
import atexit

from dotenv import load_dotenv


# ============================================================
# CONFIGURACIÓN DEL ENTORNO
# ============================================================

# Directorio donde se encuentra main.py
current_dir = os.path.dirname(os.path.abspath(__file__))

# Asegurar que el directorio del proyecto esté en sys.path
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


# Cargar explícitamente el archivo .env
env_path = os.path.join(current_dir, ".env")
load_dotenv(env_path)


# ============================================================
# IMPORTACIONES DE LA APLICACIÓN
# ============================================================

from flask import Flask, request, jsonify

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot_logic.handlers import start, handle_message


# ============================================================
# CONFIGURACIÓN
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError(
        "⚠️ Falta TELEGRAM_TOKEN en variables de entorno"
    )


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# TELEGRAM APPLICATION
# ============================================================

application = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .build()
)


# Registrar handlers
application.add_handler(
    CommandHandler("start", start)
)

application.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)


# ============================================================
# EVENT LOOP PERSISTENTE PARA TELEGRAM
# ============================================================

telegram_loop = asyncio.new_event_loop()


def run_telegram_loop():
    """
    Ejecuta un único event loop permanente para
    python-telegram-bot.

    El loop permanece activo durante toda la vida
    del proceso.
    """

    asyncio.set_event_loop(telegram_loop)

    try:

        # Inicializar Telegram dentro del mismo loop
        telegram_loop.run_until_complete(
            application.initialize()
        )

        logger.info(
            "✅ Aplicación de Telegram inicializada correctamente."
        )

        # Mantener el event loop activo
        telegram_loop.run_forever()

    except Exception as e:

        logger.error(
            f"❌ Error en el event loop de Telegram: {e}",
            exc_info=True
        )

    finally:

        try:

            telegram_loop.run_until_complete(
                application.shutdown()
            )

            logger.info(
                "🛑 Aplicación de Telegram cerrada correctamente."
            )

        except Exception as e:

            logger.error(
                f"❌ Error cerrando Telegram: {e}",
                exc_info=True
            )


# Crear hilo dedicado para Telegram
telegram_thread = threading.Thread(
    target=run_telegram_loop,
    name="telegram-event-loop",
    daemon=True,
)

telegram_thread.start()


# ============================================================
# RUTAS FLASK
# ============================================================

@app.route("/")
def home():

    return jsonify({
        "service": "Mi-Bot-IA",
        "status": "running",
        "architecture": "Modular (Fase 2)",
        "components": [
            "Flask",
            "Telegram Webhook",
            "bot_logic",
            "Persistent Async Event Loop"
        ]
    })


@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "cpu": "ready",
        "ai_core": "loaded",
        "telegram_loop": (
            "running"
            if telegram_loop.is_running()
            else "stopped"
        )
    })


# ============================================================
# TELEGRAM WEBHOOK
# ============================================================

@app.route("/telegram", methods=["POST"])
def telegram_webhook():

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "status": "error",
            "message": "No data"
        }), 400


    try:

        # ----------------------------------------------------
        # Convertir JSON recibido desde Telegram en Update
        # ----------------------------------------------------

        update = Update.de_json(
            data,
            application.bot
        )


        if update is None:

            return jsonify({
                "status": "error",
                "message": "Invalid update"
            }), 400


        # ----------------------------------------------------
        # Verificar que el event loop esté funcionando
        # ----------------------------------------------------

        if not telegram_loop.is_running():

            logger.error(
                "❌ El event loop de Telegram no está ejecutándose."
            )

            return jsonify({
                "status": "error",
                "message": "Telegram event loop is not running"
            }), 503


        # ----------------------------------------------------
        # Enviar el procesamiento al event loop persistente.
        #
        # NO creamos un event loop nuevo por cada mensaje.
        # ----------------------------------------------------

        future = asyncio.run_coroutine_threadsafe(
            application.process_update(update),
            telegram_loop
        )


        # ----------------------------------------------------
        # IMPORTANTE:
        #
        # run_coroutine_threadsafe() devuelve un Future.
        #
        # Si process_update() falla, la excepción queda dentro
        # del Future.
        #
        # Este callback permite capturarla y mostrarla en logs.
        # ----------------------------------------------------

        def log_future_result(f):

            try:

                f.result()

                logger.info(
                    "✅ Update de Telegram procesado correctamente."
                )

            except Exception as e:

                logger.error(
                    "❌ Error procesando update de Telegram: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True
                )


        future.add_done_callback(
            log_future_result
        )


        logger.info(
            "📨 Update recibido de Telegram. "
            "Procesamiento enviado al event loop."
        )


        # ----------------------------------------------------
        # Respondemos inmediatamente al webhook.
        #
        # El procesamiento de la IA continúa en segundo plano.
        # ----------------------------------------------------

        return jsonify({
            "status": "ok"
        }), 200


    except Exception as e:

        logger.error(
            f"❌ Error en webhook: {e}",
            exc_info=True
        )

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================================================
# CIERRE LIMPIO
# ============================================================

def shutdown_telegram():

    if telegram_loop.is_running():

        logger.info(
            "🛑 Solicitando cierre del event loop de Telegram..."
        )

        telegram_loop.call_soon_threadsafe(
            telegram_loop.stop
        )


atexit.register(
    shutdown_telegram
)


# ============================================================
# SERVIDOR
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    logger.info(
        f"🚀 Iniciando servidor web en puerto {port}..."
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )