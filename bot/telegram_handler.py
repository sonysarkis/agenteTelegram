"""
Manejo de mensajes de Telegram.
Filtra mensajes, procesa con IA, y registra tareas en Notion.
"""

import traceback
from bot.config import BOSS_USER_ID
from bot.ai_extractor import extract_task
from bot.notion_manager import create_task


# Emojis para las prioridades en el mensaje de confirmación
PRIORITY_DISPLAY = {
    "Alta": "🔴 Alta",
    "Media": "🟡 Media",
    "Baja": "🟢 Baja",
}


async def handle_message(update_data: dict, bot) -> None:
    """
    Procesa un update de Telegram.
    
    Args:
        update_data: dict con el update de Telegram
        bot: instancia del bot de Telegram para enviar respuestas
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

        # ── Filtro 2: Solo procesar mensajes del jefe ───────────
        if user_id != BOSS_USER_ID:
            return  # Ignorar mensajes de otros usuarios

        # ── Filtro 3: Ignorar comandos del bot ──────────────────
        if text.startswith("/"):
            # Manejar comandos especiales
            if text.strip() == "/estado":
                await _send_status(bot, chat_id)
            elif text.strip() == "/ayuda" or text.strip() == "/help":
                await _send_help(bot, chat_id)
            return

        # ── Procesar con IA ─────────────────────────────────────
        print(f"📨 Mensaje del jefe ({user_name}): {text[:100]}...")

        task_data = extract_task(text)

        if task_data is None:
            print("⚠️ No se pudo procesar el mensaje con Gemini")
            await bot.send_message(
                chat_id=chat_id,
                text="⚠️ No pude procesar ese mensaje. Intenta de nuevo.",
                reply_to_message_id=message_id,
            )
            return

        # ── Filtro 4: ¿Es realmente una tarea? ─────────────────
        if not task_data.get("is_task", False):
            print(f"💬 Mensaje ignorado (no es tarea): {text[:50]}...")
            return  # No responder a mensajes casuales

        # ── Registrar en Notion ─────────────────────────────────
        notion_result = create_task(task_data, text, user_name)

        if notion_result:
            # Construir mensaje de confirmación
            priority_display = PRIORITY_DISPLAY.get(task_data.get("priority", "Media"), "🟡 Media")
            deadline = task_data.get("deadline", "Sin fecha definida")
            deadline_display = f"📅 {deadline}" if deadline != "Sin fecha definida" else "📅 Sin fecha definida"

            confirmation = (
                f"✅ **Tarea registrada**\n\n"
                f"📌 **{task_data['task']}**\n"
                f"{deadline_display}\n"
                f"🏷️ Prioridad: {priority_display}\n"
                f"📊 Estado: Por hacer ⏳"
            )

            await bot.send_message(
                chat_id=chat_id,
                text=confirmation,
                reply_to_message_id=message_id,
                parse_mode="Markdown",
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Hubo un error al guardar la tarea en Notion. Revisa los logs.",
                reply_to_message_id=message_id,
            )

    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
        traceback.print_exc()


async def _send_help(bot, chat_id: int) -> None:
    """Envía el mensaje de ayuda."""
    help_text = (
        "🤖 **Agente PM — Ayuda**\n\n"
        "Soy tu asistente de gestión de tareas. "
        "Cuando tu jefe envíe un mensaje con una indicación, "
        "lo analizo automáticamente y lo registro en Notion.\n\n"
        "**Comandos disponibles:**\n"
        "/ayuda — Muestra este mensaje\n"
        "/estado — Verifica el estado del bot\n\n"
        "**¿Cómo funciono?**\n"
        "1. Tu jefe escribe una indicación en este grupo\n"
        "2. Yo la analizo con IA para extraer la tarea\n"
        "3. La registro automáticamente en Notion\n"
        "4. Confirmo aquí con los detalles\n\n"
        "💡 Ignoro mensajes casuales como \"ok\", \"gracias\", etc."
    )
    await bot.send_message(chat_id=chat_id, text=help_text, parse_mode="Markdown")


async def _send_status(bot, chat_id: int) -> None:
    """Envía el estado actual del bot."""
    from bot.notion_manager import test_connection

    notion_ok = test_connection()
    notion_status = "✅ Conectado" if notion_ok else "❌ Error de conexión"

    status_text = (
        "🤖 **Estado del Agente PM**\n\n"
        f"🔗 Notion: {notion_status}\n"
        "🧠 Gemini: ✅ Disponible\n"
        "📡 Telegram: ✅ Activo\n"
    )
    await bot.send_message(chat_id=chat_id, text=status_text, parse_mode="Markdown")
