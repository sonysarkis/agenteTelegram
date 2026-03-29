"""
Manejo de mensajes de Telegram.
Filtra mensajes, procesa con IA, y registra tareas en Jira.
"""

import traceback
from bot.config import AUTHORIZED_USER_IDS, TELEGRAM_BOT_TOKEN, JIRA_URL
from bot.ai_extractor import extract_task
from bot.jira_manager import create_task


# Emojis para las prioridades en el mensaje de confirmación
PRIORITY_DISPLAY = {
    "Alta": "🔴 Alta",
    "Media": "🟡 Media",
    "Baja": "🟢 Baja",
}


import httpx


def _send_message(chat_id: int, text: str, reply_to_message_id: int = None, parse_mode: str = None) -> None:
    """Envía un mensaje a Telegram de manera síncrona usando la API HTTP."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        httpx.post(url, json=payload, timeout=10.0)
    except Exception as e:
        print(f"❌ Error enviando mensaje a Telegram: {e}")


def handle_message(update_data: dict) -> None:
    """
    Procesa un update de Telegram de forma síncrona.
    
    Args:
        update_data: dict con el update de Telegram JSON crudo
    """
    try:
        # Extraer información del update
        message = update_data.get("message")
        if not message:
            return  # No es un mensaje (puede ser edit, callback, etc.)

        # Extraer datos del mensaje
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        user_name = message.get("from", {}).get("first_name", "Desconocido")
        message_id = message.get("message_id")

        # ── Filtro 1: Solo procesar mensajes de texto ───────────
        if not text:
            return  # Ignorar: fotos sin caption, stickers, etc.

        # ── Filtro 2: Solo procesar mensajes de usuarios autorizados ──
        if user_id not in AUTHORIZED_USER_IDS:
            return  # Ignorar mensajes de otros usuarios

        # ── Filtro 3: Ignorar comandos del bot ──────────────────
        if text.startswith("/"):
            if text.strip() == "/estado":
                _send_status(chat_id)
            elif text.strip() in ("/ayuda", "/help"):
                _send_help(chat_id)
            return

        # ── Procesar con IA ─────────────────────────────────────
        print(f"📨 Mensaje de {user_name} (ID: {user_id}): {text[:100]}...")

        task_data = extract_task(text)

        if task_data is None:
            print("⚠️ No se pudo procesar el mensaje con la IA")
            _send_message(
                chat_id=chat_id,
                text="⚠️ El bot está saturado (límite de IA alcanzado) o hubo un error. Intenta en unos minutos.",
                reply_to_message_id=message_id,
            )
            return

        # ── Filtro 4: ¿Es realmente una tarea? ─────────────────
        if not task_data.get("is_task", False):
            print(f"💬 Mensaje ignorado (no es tarea): {text[:50]}...")
            return  # No responder a mensajes casuales

        # ── Registrar en Jira ──────────────────────────────────
        jira_result = create_task(task_data, text, user_name)

        if jira_result:
            # Construir mensaje de confirmación
            priority_display = PRIORITY_DISPLAY.get(task_data.get("priority", "Media"), "🟡 Media")
            deadline = task_data.get("deadline", "Sin fecha definida")
            deadline_display = f"📅 {deadline}" if deadline != "Sin fecha definida" else "📅 Sin fecha definida"
            
            jira_key = jira_result.get("key", "N/A")
            jira_link = f"{JIRA_URL.rstrip('/')}/browse/{jira_key}"

            confirmation = (
                f"✅ **Tarea registrada en Jira**\n\n"
                f"🆔 **[{jira_key}]({jira_link})**\n"
                f"📌 **{task_data['task']}**\n"
                f"{deadline_display}\n"
                f"🏷️ Prioridad: {priority_display}\n"
                f"📊 Estado: Por hacer ⏳"
            )

            _send_message(
                chat_id=chat_id,
                text=confirmation,
                reply_to_message_id=message_id,
                parse_mode="Markdown",
            )
        else:
            _send_message(
                chat_id=chat_id,
                text="❌ Hubo un error al guardar la tarea en Jira. Revisa los logs.",
                reply_to_message_id=message_id,
            )

    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
        traceback.print_exc()


def _send_help(chat_id: int) -> None:
    """Envía el mensaje de ayuda."""
    help_text = (
        "🤖 **Agente PM — Ayuda**\n\n"
        "Soy tu asistente de gestión de tareas. "
        "Cuando un usuario autorizado envíe un mensaje con una indicación, "
        "lo analizo automáticamente y lo registro en Jira.\n\n"
        "**Comandos disponibles:**\n"
        "/ayuda — Muestra este mensaje\n"
        "/estado — Verifica el estado del bot\n\n"
        "**¿Cómo funciono?**\n"
        "1. Escribes una indicación en este grupo\n"
        "2. Yo la analizo con IA para extraer la tarea\n"
        "3. La registro automáticamente en Jira\n"
        "4. Confirmo aquí con el link a Jira\n\n"
        "💡 Ignoro mensajes casuales como \"ok\", \"gracias\", etc."
    )
    _send_message(chat_id=chat_id, text=help_text, parse_mode="Markdown")


def _send_status(chat_id: int) -> None:
    """Envía el estado actual del bot."""
    from bot.jira_manager import test_connection

    jira_ok = test_connection()
    jira_status = "✅ Conectado" if jira_ok else "❌ Error de conexión"

    status_text = (
        "🤖 **Estado del Agente PM**\n\n"
        f"🔗 Jira: {jira_status}\n"
        "🧠 Gemini/Llama: ✅ Disponible\n"
        "📡 Telegram: ✅ Activo\n"
    )
    _send_message(chat_id=chat_id, text=status_text, parse_mode="Markdown")

