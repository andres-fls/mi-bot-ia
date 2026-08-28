"""
Registro centralizado de modelos de IA.

Este módulo contiene la configuración de los modelos
utilizados por Mi-Bot-IA.

La lógica de selección y las llamadas a Hugging Face
permanecen en ai_core.py.
"""

# ============================================================
# REGISTRO DE MODELOS
# ============================================================

MODELOS = {
    "rapido": {
        "id": "meta-llama/Llama-3.1-8B-Instruct",
        "tipo": "general",
        "descripcion": "Modelo general para conversaciones y tareas sencillas.",
    },

    "potente_codigo": {
        "id": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "tipo": "codigo",
        "descripcion": "Modelo especializado en programación y tareas técnicas.",
    },

    "respaldo": {
        "id": "meta-llama/Llama-3.1-8B-Instruct",
        "tipo": "general",
        "descripcion": "Modelo de respaldo cuando el principal falla.",
    },
}


def obtener_modelo(nombre: str) -> str:
    """
    Devuelve el ID de Hugging Face correspondiente
    al modelo solicitado.
    """

    modelo = MODELOS.get(nombre)

    if not modelo:
        raise ValueError(
            f"Modelo '{nombre}' no está registrado."
        )

    return modelo["id"]