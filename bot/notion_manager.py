"""
Integración con Notion API.
Crea páginas en una base de datos de Notion con las tareas extraídas.
"""

import traceback
from datetime import datetime

import httpx
from bot.config import NOTION_TOKEN, NOTION_DATABASE_ID

# ── Constantes ────────────────────────────────────────────
NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}

# Mapeo de prioridad a emoji para las opciones de Notion
PRIORITY_EMOJI = {
    "Alta": "🔴",
    "Media": "🟡",
    "Baja": "🟢",
}


def create_task(task_data: dict, original_message: str, boss_name: str = "Jefe") -> dict | None:
    """
    Crea una nueva página en la base de datos de Notion.
    
    Args:
        task_data: dict con keys: task, description, deadline, priority
        original_message: texto original del mensaje del jefe
        boss_name: nombre del jefe para el registro
    
    Returns:
        dict con la respuesta de Notion o None si hubo error
    """
    try:
        # Construir propiedades de la página
        properties = {
            # Título de la tarea
            "Tarea": {
                "title": [
                    {
                        "text": {
                            "content": task_data.get("task", "Sin título")
                        }
                    }
                ]
            },
            # Estado inicial
            "Estado": {
                "select": {
                    "name": "Por hacer ⏳"
                }
            },
            # Prioridad
            "Prioridad": {
                "select": {
                    "name": f"{PRIORITY_EMOJI.get(task_data.get('priority', 'Media'), '🟡')} {task_data.get('priority', 'Media')}"
                }
            },
            # Fecha de registro
            "Fecha de registro": {
                "date": {
                    "start": datetime.now().strftime("%Y-%m-%d")
                }
            },
            # Asignado por
            "Asignado por": {
                "rich_text": [
                    {
                        "text": {
                            "content": boss_name
                        }
                    }
                ]
            },
        }

        # Agregar fecha límite solo si se definió
        deadline = task_data.get("deadline", "")
        if deadline and deadline != "Sin fecha definida":
            properties["Fecha límite"] = {
                "date": {
                    "start": deadline
                }
            }

        # Construir el body de la request
        body = {
            "parent": {
                "database_id": NOTION_DATABASE_ID
            },
            "properties": properties,
            # Contenido de la página (body)
            "children": [
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "📝 Descripción"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": task_data.get("description", "Sin descripción")}}]
                    }
                },
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                },
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "💬 Mensaje original"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "quote",
                    "quote": {
                        "rich_text": [{"type": "text", "text": {"content": original_message}}]
                    }
                },
            ]
        }

        # Hacer la request a Notion
        response = httpx.post(NOTION_API_URL, headers=HEADERS, json=body, timeout=30)

        if response.status_code == 200:
            print(f"✅ Tarea creada en Notion: {task_data.get('task')}")
            return response.json()
        else:
            print(f"❌ Error de Notion ({response.status_code}): {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error creando tarea en Notion: {e}")
        traceback.print_exc()
        return None


def test_connection() -> bool:
    """Verifica que la conexión con Notion funcione."""
    try:
        url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
        response = httpx.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            db_title = response.json().get("title", [{}])[0].get("plain_text", "Sin nombre")
            print(f"✅ Conexión con Notion exitosa. Base de datos: '{db_title}'")
            return True
        else:
            print(f"❌ Error conectando a Notion ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error de conexión con Notion: {e}")
        return False
