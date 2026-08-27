import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from huggingface_hub import InferenceClient
from fpdf import FPDF
from docx import Document
import io

# --- CONFIGURACIÓN ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Tokens (Usar variables de entorno en producción)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

if not TELEGRAM_TOKEN or not HF_TOKEN:
    logger.error("Faltan tokens. Configura TELEGRAM_TOKEN y HF_TOKEN en las variables de entorno.")
    exit(1)

# Definición de Modelos
MODELOS = {
    "rapido": "meta-llama/Llama-3.1-8B-Instruct",
    "potente": "Qwen/Qwen2.5-Coder-32B-Instruct",
    "respaldo": "mistralai/Mistral-7B-Instruct-v0.3"
}

# Cliente de Hugging Face
client = InferenceClient(token=HF_TOKEN)

# Memoria Global (Diccionario simple en RAM)
historial_conversaciones = {}
MAX_HISTORIAL = 6  # Guardar últimos 3 intercambios (6 mensajes)

# --- LÓGICA DE IA ---

def elegir_modelo(mensaje):
    """Selecciona el modelo según la complejidad del mensaje."""
    m_lower = mensaje.lower()
    keywords_complejas = ["código", "función", "clase", "arquitectura", "debug", "script", "explica detalladamente", "crea un", "desarrolla"]
    
    if any(k in m_lower for k in keywords_complejas) or len(mensaje) > 200:
        return MODELOS["potente"]
    return MODELOS["rapido"]

def llamar_ia_con_respaldo(messages):
    """Llama a la IA con lógica de reintento automático."""
    modelo_principal = elegir_modelo(messages[-1]["content"])
    intentos = [modelo_principal, MODELOS["respaldo"]]
    
    for modelo in intentos:
        try:
            logger.info(f"Usando modelo: {modelo}")
            response = client.chat_completion(
                model=modelo, 
                messages=messages, 
                max_tokens=1500,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Error con {modelo}: {e}. Intentando respaldo...")
            continue
    
    return "Lo siento, todos los modelos están fallando actualmente. Intenta más tarde."

def generar_archivo(contenido, tipo):
    """Genera archivos PDF, DOCX o MD en memoria."""
    filename = f"respuesta.{tipo}"
    
    if tipo == "md":
        return contenido.encode('utf-8'), filename
    
    elif tipo == "pdf":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        # FPDF tiene problemas con UTF-8 directo, usamos latin-1 como fallback simple
        texto_safe = contenido.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=texto_safe)
        
        buffer = io.BytesIO()
        pdf_output = pdf.output(dest='S').encode('latin-1')
        buffer.write(pdf_output)
        buffer.seek(0)
        return buffer, filename
        
    elif tipo == "docx":
        doc = Document()
        doc.add_paragraph(contenido)
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer, filename
    
    return None, None

# --- HANDLERS DE TELEGRAM ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 ¡Hola! Soy tu Asistente de IA Avanzado.\n\n"
        "Puedo generar código, documentos y responder dudas.\n"
        "Ejemplos:\n"
        "- 'Crea una función en Python'\n"
        "- 'Resume esto en un PDF'\n"
        "- 'Hazme un resumen de la charla'"
    )
    # Limpiar historial al iniciar
    if update.effective_user.id in historial_conversaciones:
        del historial_conversaciones[update.effective_user.id]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # --- LÓGICA DE DETECCIÓN INTELIGENTE MEJORADA ---
    tipo_archivo = None
    texto_real = user_text
    texto_lower = user_text.lower()

    # Función auxiliar para detectar si hay alguna palabra clave presente
    def contiene_palabras_clave(texto, lista_claves):
        return any(clave in texto for clave in lista_claves)

    # Listas ampliadas y más flexibles
    claves_pdf = ["pdf", ".pdf", "archivo pdf", "documento pdf", "en pdf", "como pdf", "formato pdf"]
    claves_docx = ["word", ".docx", "documento word", "en word", "como word", "archivo word"]
    claves_md = ["markdown", ".md", "en markdown", "como md", "archivo md"]

    # Detectar PDF
    if contiene_palabras_clave(texto_lower, claves_pdf):
        tipo_archivo = "pdf"
        # Limpiar el texto: quitamos las palabras clave comunes para que la IA no se confunda
        for clave in sorted(claves_pdf, key=len, reverse=True):
            texto_real = texto_real.lower().replace(clave, "").strip()
    
    # Detectar DOCX
    elif contiene_palabras_clave(texto_lower, claves_docx):
        tipo_archivo = "docx"
        for clave in sorted(claves_docx, key=len, reverse=True):
            texto_real = texto_real.lower().replace(clave, "").strip()
            
    # Detectar Markdown
    elif contiene_palabras_clave(texto_lower, claves_md):
        tipo_archivo = "md"
        for clave in sorted(claves_md, key=len, reverse=True):
            texto_real = texto_real.lower().replace(clave, "").strip()

    # Comando de resumen (también ampliado)
    if "/resumen" in texto_lower or ("resume" in texto_lower and len(texto_real.strip()) < 10):
        await generar_resumen(update, context)
        return

    # Si después de limpiar no queda texto, pedir al usuario que escriba algo
    if not texto_real:
        await update.message.reply_text("¡Entendido! Pero necesito que me digas **qué** quieres que ponga en el archivo. 😉")
        return
    
    # 1. Gestionar Memoria
    chat_history = historial_conversaciones.get(user_id, [])
    
    messages = [{"role": "system", "content": "Eres un asistente útil. Responde en el mismo idioma que el usuario."}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": texto_real}) # Usamos el texto limpio

    # Indicador de escritura
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    # 2. Llamar a la IA
    try:
        respuesta_ia = llamar_ia_con_respaldo(messages)
        
        # Determinar qué modelo se usó realmente (para informar al usuario)
        modelo_usado = elegir_modelo(texto_real)
        nombre_modelo_corto = modelo_usado.split('/')[-1]

        # 3. Actualizar Memoria
        chat_history.append({"role": "user", "content": texto_real})
        chat_history.append({"role": "assistant", "content": respuesta_ia})
        if len(chat_history) > MAX_HISTORIAL:
            chat_history = chat_history[-MAX_HISTORIAL:]
        historial_conversaciones[user_id] = chat_history

        # 4. Preparar mensaje final con info del modelo
        mensaje_final = f"{respuesta_ia}\n\n_ Modelo usado: {nombre_modelo_corto}_"

        # 5. Enviar Respuesta (Texto o Archivo)
        if tipo_archivo:
            archivo_buffer, nombre = generar_archivo(respuesta_ia, tipo_archivo)
            if archivo_buffer:
                await update.message.reply_document(document=archivo_buffer, filename=nombre)
                # Opcional: Enviar también el mensaje de texto con el nombre del modelo
                await update.message.reply_text(mensaje_final, parse_mode='Markdown')
            else:
                await update.message.reply_text("Error generando el archivo.")
        else:
            await update.message.reply_text(mensaje_final, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error general: {e}")
        await update.message.reply_text("Ocurrió un error inesperado. Intenta de nuevo.")

async def generar_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_history = historial_conversaciones.get(user_id, [])
    
    if not chat_history:
        await update.message.reply_text("No hay conversación previa para resumir.")
        return
    
    texto_conversacion = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history])
    prompt_resumen = f"Resume la siguiente conversación en 5 puntos clave:\n{texto_conversacion}"
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    resumen = llamar_ia_con_respaldo([{"role": "user", "content": prompt_resumen}])
    await update.message.reply_text(f"📝 **Resumen:**\n\n{resumen}", parse_mode='Markdown')

# --- SERVIDOR FAKE (FLASK) PARA RENDER FREE ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Mi-Bot-IA está vivo y corriendo 🤖"

def run_flask_server():
    port = int(os.environ.get('PORT', 10000))
    app_flask.run(host='0.0.0.0', port=port)

# --- MAIN ---
if __name__ == '__main__':
    # 1. Iniciar Servidor Web en hilo separado (para engañar a Render y mantener puerto abierto)
    thread = threading.Thread(target=run_flask_server, daemon=True)
    thread.start()
    logger.info(f"✅ Servidor web iniciado en puerto {os.environ.get('PORT', 10000)}")

    # 2. Iniciar Bot de Telegram
    logger.info(" Iniciando bot de Telegram...")
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, handle_message)) 
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)