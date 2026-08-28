import os
import logging
import asyncio
import io
from huggingface_hub import InferenceClient
from fpdf import FPDF
from docx import Document

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE MODELOS ---
# Aquí definimos nuestros "soldados". Diversidad de proveedores para resiliencia.
MODELOS = {
    "rapido": "meta-llama/Llama-3.2-3B-Instruct",       # Meta: Velocidad pura.
    "potente_codigo": "Qwen/Qwen2.5-Coder-7B-Instruct", # Alibaba: Especialista en código.
    "potente_general": "meta-llama/Llama-3.1-8B-Instruct", # Meta: Equilibrio perfecto.
    "respaldo": "mistralai/Mistral-7B-Instruct-v0.3"    # Mistral: El salvavidas.
}

class AICore:
    def __init__(self):
        logger.info("🧠 Inicializando Núcleo de IA...")
        
        # Obtener token de Hugging Face desde variables de entorno
        self.hf_token = os.getenv("HF_TOKEN")
        if not self.hf_token:
            logger.warning("⚠️ HF_TOKEN no encontrado. Las llamadas a IA fallarán.")
            self.client = None
        else:
            self.client = InferenceClient(token=self.hf_token)
            logger.info("✅ Cliente de Hugging Face conectado.")

    def elegir_modelo(self, mensaje: str) -> str:
        """Decide qué modelo usar basado en el contenido del mensaje."""
        texto_lower = mensaje.lower()
        
        # Palabras clave que indican complejidad o necesidad de código
        keywords_complejas = ["código", "función", "clase", "programa", "script", "debug", "arquitectura", "python", "java", "sql"]
        
        if any(k in texto_lower for k in keywords_complejas) or len(mensaje) > 150:
            logger.info("🧠 Detectada tarea compleja/código -> Usando modelo POTENTE.")
            return MODELOS["potente_codigo"] # O potente_general si prefieres
        
        logger.info("🧠 Tarea simple -> Usando modelo RÁPIDO.")
        return MODELOS["rapido"]

    async def llamar_ia_con_respaldo(self, messages: list, modelo_forzado: str = None) -> str:
        """Llama a la IA con lógica de reintentos automáticos."""
        
        if not self.client:
            return "⚠️ Error: No tengo acceso a los servicios de IA (falta HF_TOKEN)."

        # Determinar modelo inicial
        if modelo_forzado:
            modelo_actual = modelo_forzado
        else:
            # Si no hay modelo forzado, usamos el último mensaje para decidir
            ultimo_mensaje = messages[-1]["content"] if messages else ""
            modelo_actual = self.elegir_modelo(ultimo_mensaje)

        # Lista de intentos: Modelo elegido -> Respaldo
        intentos = [modelo_actual, MODELOS["respaldo"]]
        
        for modelo in intentos:
            try:
                logger.info(f" Intentando con modelo: {modelo}")
                
                # Llamada asíncrona a la API de Hugging Face (usando run_in_executor para no bloquear)
                # Nota: InferenceClient es síncrono por defecto, lo envolvemos en un hilo para no congelar Flask
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: self.client.chat_completion(
                        model=modelo,
                        messages=messages,
                        max_tokens=1500,
                        temperature=0.7
                    )
                )
                
                contenido = response.choices[0].message.content
                logger.info(f"✅ Respuesta exitosa de {modelo}")
                return contenido

            except Exception as e:
                logger.warning(f"❌ Error con {modelo}: {str(e)[:100]}... Intentando respaldo.")
                continue
        
        return "😕 Lo siento, todos mis modelos están teniendo problemas ahora mismo. Intenta más tarde."

    def generar_archivo(self, contenido: str, tipo: str) -> tuple:
        """Genera un archivo (PDF o DOCX) en memoria y devuelve (bytes, nombre)."""
        filename = f"respuesta.{tipo}"
        
        try:
            if tipo == "pdf":
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                # Manejo básico de caracteres especiales (latin-1)
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
            
            else:
                # Para markdown o texto plano
                return contenido.encode('utf-8'), filename

        except Exception as e:
            logger.error(f"Error generando archivo {tipo}: {e}")
            return None, None

    async def process_message(self, text: str, user_id: int, detect_file_type: bool = False) -> dict:
        """
        Función principal que Orquesta todo.
        Retorna un diccionario: {'response': str, 'file_buffer': BytesIO, 'filename': str, 'type': str}
        """
        logger.info(f"Procesando mensaje de usuario {user_id}: {text[:50]}...")

        # 1. Preparar mensajes para la IA (Historial simulado por ahora)
        messages = [
            {"role": "system", "content": "Eres un asistente útil, experto en programación y análisis. Responde en español."},
            {"role": "user", "content": text}
        ]

        # 2. Determinar si necesitamos generar un archivo
        tipo_archivo = None
        texto_limpio = text
        
        if detect_file_type:
            texto_lower = text.lower()
            if "pdf" in texto_lower or ".pdf" in texto_lower:
                tipo_archivo = "pdf"
            elif "word" in texto_lower or "docx" in texto_lower:
                tipo_archivo = "docx"
            
            # Limpiar palabras clave para que la IA no se confunda
            if tipo_archivo:
                for palabra in ["pdf", ".pdf", "word", ".docx", "en formato", "genera un"]:
                    texto_limpio = texto_limpio.replace(palabra, "")
                messages[-1]["content"] = texto_limpio # Actualizar mensaje a la IA

        # 3. Llamar a la IA
        respuesta_ia = await self.llamar_ia_con_respaldo(messages)

        # 4. Generar archivo si es necesario
        file_buffer = None
        filename = None
        
        if tipo_archivo and respuesta_ia and not respuesta_ia.startswith(""):
            file_buffer, filename = self.generar_archivo(respuesta_ia, tipo_archivo)
            if file_buffer:
                logger.info(f" Archivo {tipo_archivo} generado exitosamente.")
            else:
                logger.error("Falló la generación del archivo, enviando como texto.")
                tipo_archivo = None # Fallback a texto

        return {
            "response": respuesta_ia,
            "file_buffer": file_buffer,
            "filename": filename,
            "file_type": tipo_archivo
        }

# Instancia global única
ai_engine = AICore()