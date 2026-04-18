"""
Integración con Jira Cloud REST API v3.
Crea issues en un proyecto de Jira con las tareas extraídas.
"""

import traceback
import base64
from datetime import datetime, timezone, timedelta
import httpx
from bot.config import JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY

# ── Constantes ────────────────────────────────────────────
# Auth: Basic (Email:Token en base64)
_auth_str = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
_auth_b64 = base64.b64encode(_auth_str.encode()).decode()

HEADERS = {
    "Authorization": f"Basic {_auth_b64}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Mapeo de prioridad (Telegram -> Jira)
PRIORITY_MAPPING = {
    "Alta": "High",
    "Media": "Medium",
    "Baja": "Low",
}


def create_task(
    task_data: dict,
    original_message: str,
    user_name: str = "Usuario",
    assignee_account_id: str | None = None,
) -> dict | None:
    """
    Crea un nuevo issue en Jira.

    Args:
        task_data: dict con keys: task, description, deadline, priority
        original_message: texto original del mensaje
        user_name: nombre del usuario que envió el mensaje
        assignee_account_id: accountId de Jira del asignado (opcional)

    Returns:
        dict con la respuesta de Jira o None si hubo error
    """
    try:
        url = f"{JIRA_URL.rstrip('/')}/rest/api/3/issue"
        
        # Construir descripción en Atlassian Document Format (ADF)
        description_adf = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [{"type": "text", "text": "📝 Descripción"}]
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": task_data.get("description", "Sin descripción")}]
                },
                {
                    "type": "rule"
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "💬 Mensaje original ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": f"(por {user_name}):"}
                    ]
                },
                {
                    "type": "blockquote",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": original_message}]
                        }
                    ]
                }
            ]
        }

        # Construir el body de la request
        fields = {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": task_data.get("task", "Sin título"),
            "issuetype": {"name": "Task"},
            "description": description_adf,
            "priority": {"name": PRIORITY_MAPPING.get(task_data.get("priority"), "Medium")},
        }

        # Agregar fecha límite si existe (formato YYYY-MM-DD)
        deadline = task_data.get("deadline", "")
        if deadline and deadline != "Sin fecha definida":
            fields["duedate"] = deadline

        # Asignar a un miembro del equipo si se resolvió su accountId
        if assignee_account_id:
            fields["assignee"] = {"accountId": assignee_account_id}

        payload = {"fields": fields}

        # Hacer la request a Jira
        response = httpx.post(url, headers=HEADERS, json=payload, timeout=30)

        if response.status_code == 201:
            result = response.json()
            print(f"✅ Tarea creada en Jira: {result.get('key')}")
            return result
        else:
            print(f"❌ Error de Jira ({response.status_code}): {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error creando tarea en Jira: {e}")
        traceback.print_exc()
        return None


# Mapeo de estado en español → posibles nombres de columna en Jira (en orden de preferencia)
STATUS_NAME_MAPPING = {
    "En curso":    ["In Progress", "En curso", "En Curso", "In progress"],
    "Finalizado":  ["Done", "Finalizado", "Completado", "Closed", "Cerrado"],
}


def transition_issue(issue_key: str, target_status: str) -> bool:
    """
    Mueve un issue de Jira al estado indicado usando la API de transiciones.

    Args:
        issue_key: clave del issue (ej: "KAN-42")
        target_status: "En curso" o "Finalizado"

    Returns:
        True si la transición fue exitosa, False si no
    """
    if target_status == "Por hacer":
        return True  # Ya está en ese estado por defecto

    try:
        # 1. Obtener transiciones disponibles para este issue
        url = f"{JIRA_URL.rstrip('/')}/rest/api/3/issue/{issue_key}/transitions"
        response = httpx.get(url, headers=HEADERS, timeout=15)

        if response.status_code != 200:
            print(f"❌ Error obteniendo transiciones ({response.status_code}): {response.text}")
            return False

        transitions = response.json().get("transitions", [])

        # 2. Buscar la transición que coincida con el estado deseado
        candidate_names = STATUS_NAME_MAPPING.get(target_status, [])
        transition_id = None

        for candidate in candidate_names:
            for t in transitions:
                if t.get("to", {}).get("name", "").lower() == candidate.lower():
                    transition_id = t["id"]
                    break
            if transition_id:
                break

        if not transition_id:
            available = [t.get("to", {}).get("name") for t in transitions]
            print(f"⚠️ No se encontró transición hacia '{target_status}'. Disponibles: {available}")
            return False

        # 3. Ejecutar la transición
        payload = {"transition": {"id": transition_id}}
        resp = httpx.post(url, headers=HEADERS, json=payload, timeout=15)

        if resp.status_code == 204:
            print(f"✅ Issue {issue_key} movido a '{target_status}'")
            return True
        else:
            print(f"❌ Error en transición ({resp.status_code}): {resp.text}")
            return False

    except Exception as e:
        print(f"❌ Error al transicionar issue {issue_key}: {e}")
        traceback.print_exc()
        return False


def test_connection() -> bool:
    """Verifica que la conexión con Jira funcione."""
    try:
        # Intentamos obtener información del proyecto
        url = f"{JIRA_URL.rstrip('/')}/rest/api/3/project/{JIRA_PROJECT_KEY}"
        response = httpx.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            proj_name = response.json().get("name", "Sin nombre")
            print(f"✅ Conexión con Jira exitosa. Proyecto: '{proj_name}'")
            return True
        else:
            print(f"❌ Error conectando a Jira ({response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error de conexión con Jira: {e}")
        return False
