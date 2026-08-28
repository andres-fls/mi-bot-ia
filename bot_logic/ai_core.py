import os
import logging
import asyncio
import io

from huggingface_hub import InferenceClient
from fpdf import FPDF
from docx import Document

from .model_registry import MODELOS, obtener_modelo


logger = logging.getLogger(__name__)


# ============================================================
# AI CORE
# ============================================================

class AICore:

    def __init__(self):

        logger.info("🧠 Inicializando Núcleo de IA...")

        self.hf_token = os.getenv("HF_TOKEN")

        if not self.hf_token:

            logger.error(
                "❌ HF_TOKEN no encontrado. "
                "No se puede utilizar Hugging Face."
            )

            self.client = None

        else:

            try:

                self.client = InferenceClient(
                    api_key=self.hf_token,
                    provider="auto",
                    timeout=60,
                )

                logger.info(
                    "✅ Cliente de Hugging Face conectado."
                )

            except Exception as e:

                logger.error(
                    f"❌ Error inicializando Hugging Face: {e}",
                    exc_info=True
                )

                self.client = None


    # ========================================================
    # ROUTER SIMPLE
    # ========================================================

    def elegir_modelo(self, mensaje: str) -> str:

        texto_lower = mensaje.lower()

        keywords_complejas = [
            "código",
            "codigo",
            "función",
            "funcion",
            "clase",
            "programa",
            "script",
            "debug",
            "debugging",
            "arquitectura",
            "python",
            "java",
            "c#",
            "sql",
            "api",
            "docker",
            "linux",
        ]

        if (
            any(k in texto_lower for k in keywords_complejas)
            or len(mensaje) > 150
        ):

            logger.info(
                "🧠 Tarea compleja/código → modelo POTENTE."
            )

            return obtener_modelo("potente_codigo")

        logger.info(
            "💬 Tarea simple → modelo RÁPIDO."
        )

        return obtener_modelo("rapido")


    # ========================================================
    # LLAMADA A HUGGING FACE
    # ========================================================

    async def llamar_ia_con_respaldo(
        self,
        messages: list,
        modelo_forzado: str = None
    ) -> str:

        if not self.client:

            return (
                "⚠️ No tengo acceso a Hugging Face. "
                "Verifica que HF_TOKEN esté configurado."
            )


        # ----------------------------------------------------
        # Selección del modelo
        # ----------------------------------------------------

        if modelo_forzado:

            modelo_actual = modelo_forzado

        else:

            ultimo_mensaje = (
                messages[-1]["content"]
                if messages
                else ""
            )

            modelo_actual = self.elegir_modelo(
                ultimo_mensaje
            )


        # ----------------------------------------------------
        # Construcción de lista de intentos
        # ----------------------------------------------------

        intentos = []

        modelos_a_probar = [
            modelo_actual,
            MODELOS["respaldo"],
        ]

        for modelo in modelos_a_probar:

            if modelo and modelo not in intentos:

                intentos.append(modelo)


        # ----------------------------------------------------
        # Intentar modelos
        # ----------------------------------------------------

        for modelo in intentos:

            try:

                logger.info(
                    f"🤖 Intentando modelo: {modelo}"
                )


                # ------------------------------------------------
                # InferenceClient es síncrono.
                #
                # Lo ejecutamos en un thread para evitar
                # bloquear el event loop de Telegram.
                # ------------------------------------------------

                response = await asyncio.to_thread(
                    self.client.chat_completion,

                    model=modelo,

                    messages=messages,

                    max_tokens=1024,

                    temperature=0.7,

                    top_p=0.95,
                )


                # ------------------------------------------------
                # Validar respuesta
                # ------------------------------------------------

                if (
                    response
                    and response.choices
                    and len(response.choices) > 0
                ):

                    contenido = (
                        response
                        .choices[0]
                        .message
                        .content
                    )


                    if contenido:

                        logger.info(
                            f"✅ Respuesta exitosa de {modelo}"
                        )

                        return contenido.strip()


                logger.warning(
                    f"⚠️ Respuesta vacía de {modelo}"
                )


            except Exception as e:

                logger.error(
                    f"❌ Error usando modelo {modelo}: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True
                )

                continue


        # ----------------------------------------------------
        # Todos los modelos fallaron
        # ----------------------------------------------------

        logger.error(
            "❌ Todos los modelos configurados fallaron."
        )

        return (
            "😕 Lo siento, todos mis modelos están "
            "teniendo problemas ahora mismo. "
            "Intenta nuevamente más tarde."
        )


    # ========================================================
    # GENERACIÓN DE ARCHIVOS
    # ========================================================

    def generar_archivo(
        self,
        contenido: str,
        tipo: str
    ) -> tuple:

        filename = f"respuesta.{tipo}"

        try:

            # ------------------------------------------------
            # PDF
            # ------------------------------------------------

            if tipo == "pdf":

                pdf = FPDF()

                pdf.add_page()

                pdf.set_font(
                    "Arial",
                    size=12
                )

                texto_safe = (
                    contenido
                    .encode(
                        "latin-1",
                        "replace"
                    )
                    .decode("latin-1")
                )

                pdf.multi_cell(
                    0,
                    10,
                    text=texto_safe
                )

                pdf_output = pdf.output(
                    dest="S"
                )

                if isinstance(
                    pdf_output,
                    str
                ):

                    pdf_output = pdf_output.encode(
                        "latin-1"
                    )

                buffer = io.BytesIO(
                    pdf_output
                )

                buffer.seek(0)

                return buffer, filename


            # ------------------------------------------------
            # DOCX
            # ------------------------------------------------

            elif tipo == "docx":

                doc = Document()

                doc.add_paragraph(
                    contenido
                )

                buffer = io.BytesIO()

                doc.save(buffer)

                buffer.seek(0)

                return buffer, filename


            # ------------------------------------------------
            # Otros formatos
            # ------------------------------------------------

            else:

                return (
                    contenido.encode("utf-8"),
                    filename
                )


        except Exception as e:

            logger.error(
                f"❌ Error generando archivo "
                f"{tipo}: {e}",
                exc_info=True
            )

            return None, None


    # ========================================================
    # PROCESAMIENTO PRINCIPAL
    # ========================================================

    async def process_message(
        self,
        text: str,
        user_id: int,
        detect_file_type: bool = False
    ) -> dict:

        logger.info(
            f"📝 Procesando mensaje de usuario "
            f"{user_id}: {text[:80]}..."
        )


        # ----------------------------------------------------
        # Mensajes enviados al modelo
        # ----------------------------------------------------

        messages = [

            {
                "role": "system",
                "content": (
                    "Eres un asistente útil. "
                    "Responde en español."
                ),
            },

            {
                "role": "user",
                "content": text,
            }

        ]


        tipo_archivo = None

        texto_limpio = text


        # ----------------------------------------------------
        # Detección de archivos
        # ----------------------------------------------------

        if detect_file_type:

            texto_lower = text.lower()

            if "pdf" in texto_lower:

                tipo_archivo = "pdf"

            elif (
                "word" in texto_lower
                or "docx" in texto_lower
            ):

                tipo_archivo = "docx"


            if tipo_archivo:

                palabras_eliminar = [
                    "pdf",
                    ".pdf",
                    "word",
                    ".docx",
                    "en formato",
                    "genera un",
                ]

                for palabra in palabras_eliminar:

                    texto_limpio = texto_limpio.replace(
                        palabra,
                        ""
                    )

                messages[-1]["content"] = (
                    texto_limpio.strip()
                )


        # ----------------------------------------------------
        # Obtener respuesta de IA
        # ----------------------------------------------------

        respuesta_ia = await self.llamar_ia_con_respaldo(
            messages
        )


        # ----------------------------------------------------
        # Generar archivo si fue solicitado
        # ----------------------------------------------------

        file_buffer = None
        filename = None

        if tipo_archivo and respuesta_ia:

            file_buffer, filename = (
                self.generar_archivo(
                    respuesta_ia,
                    tipo_archivo
                )
            )


        # ----------------------------------------------------
        # Resultado
        # ----------------------------------------------------

        return {

            "response": respuesta_ia,

            "file_buffer": file_buffer,

            "filename": filename,

            "file_type": tipo_archivo,

        }


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

ai_engine = AICore()