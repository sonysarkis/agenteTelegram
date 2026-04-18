"""
Integración con Groq API (IA ultrarrápida y gratuita).
Envía mensajes del jefe y recibe JSON estructurado con la tarea extraída.
"""

import json
import traceback
from groq import Groq
from bot.config import GROQ_API_KEY, GROQ_MODEL
from bot.prompts import get_extraction_prompt


# Inicializar cliente de Groq
client = Groq(api_key=GROQ_API_KEY)


def extract_task(message_text: str) -> dict | None:
    """
    Envía un mensaje a Groq y extrae la tarea como un dict.
    
    Retorna:
        dict con keys: is_task, task, description, deadline, priority
        None si hubo un error
    """
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": get_extraction_prompt(),
                },
                {
                    "role": "user",
                    "content": f'Analiza este mensaje del jefe y extrae la tarea:\n\n"{message_text}"',
                },
            ],
            temperature=0.1,
            max_tokens=500,
        )

        # Obtener la respuesta
        raw = response.choices[0].message.content.strip()

        # Limpiar la respuesta (a veces el modelo envuelve en ```json ... ```)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]  # Quitar primera línea (```json)
            raw = raw.rsplit("```", 1)[0]  # Quitar último ```
            raw = raw.strip()

        result = json.loads(raw)

        # Validar que tenga las keys esperadas
        required_keys = {"is_task", "task", "description", "deadline", "priority"}
        if not required_keys.issubset(result.keys()):
            print(f"⚠️ Respuesta de IA incompleta: {result}")
            return None

        # assignee es opcional — si no viene en la respuesta, lo ponemos en None
        result.setdefault("assignee", None)
        # status es opcional — por defecto "Por hacer"
        result.setdefault("status", "Por hacer")

        return result

    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON de IA: {e}")
        print(f"   Respuesta raw: {raw if 'raw' in dir() else 'N/A'}")
        return None
    except Exception as e:
        print(f"❌ Error llamando a Groq: {e}")
        traceback.print_exc()
        return None


def transcribe_audio(audio_file: bytes, filename: str) -> str | None:
    """
    Usa el modelo Whisper-3 de Groq para transcribir audio a texto.
    
    Args:
        audio_file: contenido binario del archivo
        filename: nombre del archivo para identificar la extensión
        
    Returns:
        str con el texto transcrito
        None si hubo error
    """
    try:
        # Groq espera un objeto tipo 'file', pasamos una tupla (filename, content)
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_file),
            model="whisper-large-v3",
            response_format="json",
            temperature=0.0,  # Máxima precisión
        )
        return transcription.text
    except Exception as e:
        print(f"❌ Error transcribiendo audio con Groq: {e}")
        traceback.print_exc()
        return None
