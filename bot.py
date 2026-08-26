import os
from dotenv import load_dotenv

# Importaciones necesarias para Telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Importación necesaria para Hugging Face (Aquí estaba el error antes)
from huggingface_hub import InferenceClient

# ==========================================
# CONFIGURACIÓN
# ==========================================

# Carga las variables desde el archivo .env
load_dotenv() 

# Leemos las variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Verificación de seguridad: Si faltan los tokens, el bot no arranca para evitar errores raros
if not TELEGRAM_TOKEN or not HF_TOKEN:
    raise Exception("⚠️ Faltan las variables de entorno TELEGRAM_TOKEN o HF_TOKEN. Revisa tu archivo .env")

# Modelo que usaremos (Qwen Coder es excelente para programar)
MODELO_IA = "Qwen/Qwen2.5-Coder-32B-Instruct"

# ==========================================
# LÓGICA DEL BOT
# ==========================================

# Inicializar el cliente de Hugging Face con tu token
client = InferenceClient(token=HF_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " ¡Hola! Soy tu Asistente de Desarrollo IA.\n\n"
        "Puedo ayudarte a:\n"
        "- Diseñar arquitectura (Fase 0)\n"
        "- Escribir código (Fase 1)\n"
        "- Revisar errores (Fase 2)\n\n"
        "Solo escribe tu pregunta o pega tu código."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Indicador de "Escribiendo..." en Telegram
    await update.message.chat.send_action(action="typing")

    try:
        # Construimos el prompt para que la IA sepa quién es
        system_prompt = (
            "Eres un experto desarrollador de software siguiendo una metodología estricta. "
            "Tu respuesta debe ser clara, técnica y directa. "
            "Si el usuario pide código, entrégalo listo para copiar y pegar. "
            "Si el usuario pide análisis, sé crítico y detallado."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]

        # Llamamos a la IA de Hugging Face
        response = client.chat_completion(
            model=MODELO_IA,
            messages=messages,
            max_tokens=1500, # Límite de longitud de respuesta
            temperature=0.7  # Creatividad balanceada
        )
        
        ai_reply = response.choices[0].message.content
        
        # Enviamos la respuesta a Telegram
        await update.message.reply_text(ai_reply)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ocurrió un error: {str(e)}\nIntenta de nuevo en unos segundos.")

def main():
    # Crear la aplicación
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))

    # Mensajes de texto (ignora comandos como /start)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot iniciado... Esperando mensajes en Telegram...")
    
    # Iniciar el bot
    app.run_polling()

if __name__ == '__main__':
    main()