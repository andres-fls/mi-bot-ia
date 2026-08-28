import os
import logging
import asyncio
import io
from huggingface_hub import InferenceClient
from fpdf import FPDF
from docx import Document

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE MODELOS COMPATIBLES CON EL ROUTER ESTÁNDAR ---
# Estos modelos funcionan nativamente en router.huggingface.co sin configurar proveedores externos
MODELOS = {
    "rapido": "microsoft/Phi-3-mini-4k-instruct",       # Microsoft Phi-3: Rápido, inteligente y 100% compatible.
    "potente_codigo": "Qwen/Qwen2.5-Coder-7B-Instruct", # Qwen Coder: Probaremos si funciona, si no, usará respaldo.
    "respaldo": "google/gemma-2-2b-it"                  # Google Gemma 2B: Ligero y muy estable en el router free.
}

class AICore:
    def __init__(self):
        logger.info("🧠 Inicializando Núcleo de IA...")
        
        self.hf_token = os.getenv("HF_TOKEN")
        if not self.hf_token:
            logger.warning("⚠️ HF_TOKEN no encontrado.")
            self.client = None
        else:
            self.client = InferenceClient(token=self.hf_token, timeout=60)
            logger.info("✅ Cliente de Hugging Face conectado.")

    def elegir_modelo(self, mensaje: str) -> str:
        texto_lower = mensaje.lower()
        keywords_complejas = ["código", "función", "clase", "programa", "script", "debug", "arquitectura", "python", "java", "sql"]
        
        if any(k in texto_lower for k in keywords_complejas) or len(mensaje) > 150:
            logger.info("🧠 Tarea compleja/código -> Usando modelo POTENTE.")
            return MODELOS["potente_codigo"]
        
        logger.info(" Tarea simple -> Usando modelo RÁPIDO.")
        return MODELOS["rapido"]

    async def llamar_ia_con_respaldo(self, messages: list, modelo_forzado: str = None) -> str:
        if not self.client:
            return "⚠️ Error: No tengo acceso a los servicios de IA (falta HF_TOKEN)."

        if modelo_forzado:
            modelo_actual = modelo_forzado
        else:
            ultimo_mensaje = messages[-1]["content"] if messages else ""
            modelo_actual = self.elegir_modelo(ultimo_mensaje)

        intentos = [modelo_actual, MODELOS["respaldo"]]
        
        for modelo in intentos:
            try:
                logger.info(f" Intentando con modelo: {modelo}")
                
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.chat_completion(
                        model=modelo,
                        messages=messages,
                        max_tokens=1024,
                        temperature=0.7,
                        top_p=0.95
                    )
                )
                
                if response and response.choices and len(response.choices) > 0:
                    contenido = response.choices[0].message.content
                    if contenido:
                        logger.info(f"✅ Respuesta exitosa de {modelo}")
                        return contenido.strip()
                
                logger.warning(f"️ Respuesta vacía de {modelo}")
                continue

            except Exception as e:
                error_msg = str(e)
                if "400" in error_msg or "not supported" in error_msg:
                    logger.error(f"❌ Modelo {modelo} NO SOPORTADO en este router. Saltando.")
                else:
                    logger.warning(f"❌ Error con {modelo}: {error_msg[:150]}... Intentando respaldo.")
                continue
        
        return "😕 Lo siento, todos mis modelos están teniendo problemas ahora mismo. Intenta más tarde."

    def generar_archivo(self, contenido: str, tipo: str) -> tuple:
        filename = f"respuesta.{tipo}"
        try:
            if tipo == "pdf":
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
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
                return contenido.encode('utf-8'), filename
        except Exception as e:
            logger.error(f"Error generando archivo {tipo}: {e}")
            return None, None

    async def process_message(self, text: str, user_id: int, detect_file_type: bool = False) -> dict:
        logger.info(f"Procesando mensaje de usuario {user_id}: {text[:50]}...")
        messages = [
            {"role": "system", "content": "Eres un asistente útil. Responde en español."},
            {"role": "user", "content": text}
        ]
        tipo_archivo = None
        texto_limpio = text
        if detect_file_type:
            texto_lower = text.lower()
            if "pdf" in texto_lower: tipo_archivo = "pdf"
            elif "word" in texto_lower or "docx" in texto_lower: tipo_archivo = "docx"
            if tipo_archivo:
                for palabra in ["pdf", ".pdf", "word", ".docx", "en formato", "genera un"]:
                    texto_limpio = texto_limpio.replace(palabra, "")
                messages[-1]["content"] = texto_limpio

        respuesta_ia = await self.llamar_ia_con_respaldo(messages)
        file_buffer, filename = None, None
        if tipo_archivo and respuesta_ia and not respuesta_ia.startswith(""):
            file_buffer, filename = self.generar_archivo(respuesta_ia, tipo_archivo)
        
        return {"response": respuesta_ia, "file_buffer": file_buffer, "filename": filename, "file_type": tipo_archivo}

ai_engine = AICore()