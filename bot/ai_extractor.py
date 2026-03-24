"""
Integración con Gemini API (Google AI).
Envía mensajes del jefe y recibe JSON estructurado con la tarea extraída.
"""

import json
import traceback
from google import genai
from bot.config import GEMINI_API_KEY, GEMINI_MODEL
from bot.prompts import get_extraction_prompt


# Inicializar cliente de Gemini
client = genai.Client(api_key=GEMINI_API_KEY)


def extract_task(message_text: str) -> dict | None:
    """
    Envía un mensaje a Gemini y extrae la tarea como un dict.
    
    Retorna:
        dict con keys: is_task, task, description, deadline, priority
        None si hubo un error
    """
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"Analiza este mensaje del jefe y extrae la tarea:\n\n\"{message_text}\"",
            config=genai.types.GenerateContentConfig(
                system_instruction=get_extraction_prompt(),
                temperature=0.1,  # Baja temperatura para respuestas consistentes
                max_output_tokens=500,
            ),
        )

        # Limpiar la respuesta (a veces Gemini envuelve en ```json ... ```)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]  # Quitar primera línea (```json)
            raw = raw.rsplit("```", 1)[0]  # Quitar último ```
            raw = raw.strip()

        result = json.loads(raw)

        # Validar que tenga las keys esperadas
        required_keys = {"is_task", "task", "description", "deadline", "priority"}
        if not required_keys.issubset(result.keys()):
            print(f"⚠️ Respuesta de Gemini incompleta: {result}")
            return None

        return result

    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON de Gemini: {e}")
        print(f"   Respuesta raw: {raw if 'raw' in dir() else 'N/A'}")
        return None
    except Exception as e:
        print(f"❌ Error llamando a Gemini: {e}")
        traceback.print_exc()
        return None
