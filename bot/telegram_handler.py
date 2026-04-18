import traceback
import httpx
from bot.config import AUTHORIZED_USER_IDS, TELEGRAM_BOT_TOKEN, JIRA_URL
from bot.ai_extractor import extract_task, transcribe_audio
from bot.jira_manager import create_task, transition_issue
from bot.jira_users import resolve_assignee
from bot.reminder_scheduler import schedule_task_reminders
from bot.strategy_agents import process_strategy_flow


# Emojis para las prioridades en el mensaje de confirmación
PRIORITY_DISPLAY = {
    "Alta": "🔴 Alta",
    "Media": "🟡 Media",
    "Baja": "🟢 Baja",
}


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


def _download_telegram_file(file_id: str) -> bytes | None:
    """Descarga un archivo desde los servidores de Telegram."""
    try:
        # 1. Obtener la ruta del archivo
        get_file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
        resp = httpx.get(get_file_url, params={"file_id": file_id}, timeout=10.0)
        file_data = resp.json()
        
        if not file_data.get("ok"):
            print(f"❌ Error en getFile: {file_data}")
            return None
            
        file_path = file_data["result"]["file_path"]
        
        # 2. Descargar el archivo binario
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        file_resp = httpx.get(download_url, timeout=30.0)
        
        if file_resp.status_code == 200:
            return file_resp.content
        return None
    except Exception as e:
        print(f"❌ Error descargando archivo de Telegram: {e}")
        return None


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

        # ── Filtro 1: Autorización ──────────────────────────────
        if user_id not in AUTHORIZED_USER_IDS:
            return  # Ignorar mensajes de otros usuarios

        # ── Filtro 2: Detección de Audio/Voz ─────────────────────
        voice = message.get("voice")
        audio = message.get("audio")
        is_audio = False
        transcription = ""

        if not text and (voice or audio):
            is_audio = True
            file_id = voice["file_id"] if voice else audio["file_id"]
            mime_type = voice.get("mime_type", "audio/ogg") if voice else audio.get("mime_type", "audio/mpeg")
            # Determinar extensión básica
            ext = "ogg" if "ogg" in mime_type else "mp3"
            
            print(f"🎙️ Audio detectado de {user_name}. Transcribiendo...")
            
            # (Opcional) Notificar que se está procesando
            # _send_message(chat_id, "🎙️ Transcribiendo audio...", reply_to_message_id=message_id)

            audio_content = _download_telegram_file(file_id)
            if audio_content:
                transcription = transcribe_audio(audio_content, f"audio.{ext}")
                text = transcription
            
            if not text:
                _send_message(chat_id, "❌ No pude entender el audio o hubo un error en la transcripción.", reply_to_message_id=message_id)
                return

        # ── Filtro 3: Ignorar si no hay texto ni audio válido ───
        if not text:
            return 

        # ── Filtro 4: Comandos del bot ──────────────────────────
        if text.startswith("/"):
            stripped = text.strip()
            lower = stripped.lower()

            if stripped == "/estado":
                _send_status(chat_id)
            elif stripped in ("/ayuda", "/help"):
                _send_help(chat_id)
            elif lower == "/s" or lower.startswith("/s ") or lower.startswith("/s\n"):
                _handle_strategy_flow(chat_id, message_id, user_name, stripped)
            return

        # ── Procesar con IA ─────────────────────────────────────
        print(f"📨 Procesando mensaje de {user_name}: {text[:100]}...")

        task_data = extract_task(text)

        if task_data is None:
            print("⚠️ No se pudo procesar el mensaje con la IA")
            _send_message(
                chat_id=chat_id,
                text="⚠️ El bot está saturado o hubo un error procesando la tarea. Intenta en unos minutos.",
                reply_to_message_id=message_id,
            )
            return

        # ── Filtro 5: ¿Es realmente una tarea? ─────────────────
        if not task_data.get("is_task", False):
            if is_audio:
                # Si era audio y no es tarea, al menos mostramos la transcripción si es amigable
                print(f"💬 Audio ignorado (no es tarea): {text[:50]}...")
            return 

        # ── Resolver asignado ──────────────────────────────────
        raw_assignee = task_data.get("assignee")  # nombre tal como lo devuelve la IA
        assignee_resolved = resolve_assignee(raw_assignee) if raw_assignee else None
        # assignee_resolved es (nombre_canónico, accountId) o None
        assignee_name = assignee_resolved[0] if assignee_resolved else None
        assignee_account_id = assignee_resolved[1] if assignee_resolved else None

        # ── Registrar en Jira ──────────────────────────────────
        original_to_save = f"[Transcripción Audio]: {text}" if is_audio else text
        jira_result = create_task(task_data, original_to_save, user_name, assignee_account_id)

        if jira_result:
            jira_key = jira_result.get("key", "N/A")
            jira_link = f"{JIRA_URL.rstrip('/')}/browse/{jira_key}"

            # ── Transicionar estado si no es "Por hacer" ──────────
            task_status = task_data.get("status", "Por hacer")
            if task_status in ("En curso", "Finalizado"):
                transition_issue(jira_key, task_status)

            # Construir mensaje de confirmación
            priority_display = PRIORITY_DISPLAY.get(task_data.get("priority", "Media"), "🟡 Media")
            deadline = task_data.get("deadline", "Sin fecha definida")
            deadline_display = f"📅 {deadline}" if deadline != "Sin fecha definida" else "📅 Sin fecha definida"

            STATUS_DISPLAY = {
                "Por hacer":   "Por hacer ⏳",
                "En curso":    "En curso 🔄",
                "Finalizado":  "Finalizado ✅",
            }
            status_display = STATUS_DISPLAY.get(task_status, "Por hacer ⏳")

            header = "🎙️ **Audio transcrito y registrado**" if is_audio else "✅ **Tarea registrada en Jira**"
            transcription_block = f"\n📖 *Texto detectado:* \"{text}\"\n" if is_audio else ""
            assignee_display_line = f"👤 Asignado a: **{assignee_name}**\n" if assignee_name else "👤 Sin asignar\n"

            confirmation = (
                f"{header}\n\n"
                f"🆔 **[{jira_key}]({jira_link})**\n"
                f"📌 **{task_data['task']}**\n"
                f"{transcription_block}"
                f"{deadline_display}\n"
                f"{assignee_display_line}"
                f"🏷️ Prioridad: {priority_display}\n"
                f"📊 Estado: {status_display}"
            )

            _send_message(
                chat_id=chat_id,
                text=confirmation,
                reply_to_message_id=message_id,
                parse_mode="Markdown",
            )

            # ── Programar recordatorios ────────────────────────
            schedule_task_reminders(
                chat_id=chat_id,
                jira_key=jira_key,
                task_title=task_data["task"],
                assignee_display=assignee_name or "",
                deadline_str=deadline if deadline != "Sin fecha definida" else None,
                jira_link=jira_link,
            )
        else:
            _send_message(
                chat_id=chat_id,
                text="❌ Hubo un error al guardar en Jira. Revisa los logs.",
                reply_to_message_id=message_id,
            )

    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
        traceback.print_exc()


def _handle_strategy_flow(chat_id: int, message_id: int, user_name: str, full_text: str) -> None:
    """
    Flujo /s: Strategy (Hormozi roast) → PM (tareas accionables) → Jira.
    Las tareas se crean en Jira con assignee; el análisis se muestra en el chat.
    """
    # Extraer el contenido después de "/s"
    content = full_text[2:].lstrip()

    if not content:
        _send_message(
            chat_id=chat_id,
            text="⚠️ Uso: /s <mensaje estratégico>\n\nEjemplo: /s Estamos perdiendo leads en negociación, deberíamos bajar precios.",
            reply_to_message_id=message_id,
        )
        return

    # Resolver el nombre del remitente al canónico del equipo (Sony/Dylan/Sebastian)
    # Si el remitente no está en el equipo, se usa su nombre de Telegram tal cual.
    resolved_sender = resolve_assignee(user_name)
    sender_canonical = resolved_sender[0] if resolved_sender else user_name

    print(f"🧠 Flujo estratégico disparado por {user_name} (canónico: {sender_canonical}): {content[:80]}...")
    _send_message(chat_id=chat_id, text="🧠 Procesando estrategia...", reply_to_message_id=message_id)

    strategy_text, pm_result = process_strategy_flow(content, sender_canonical)

    if not strategy_text:
        _send_message(
            chat_id=chat_id,
            text="❌ Error en el agente Strategy. Intenta de nuevo.",
            reply_to_message_id=message_id,
        )
        return

    # Enviar el análisis estratégico (plain text para evitar romper Markdown)
    _send_message(
        chat_id=chat_id,
        text=f"🧠 STRATEGY\n\n{strategy_text}",
        reply_to_message_id=message_id,
    )

    if not pm_result:
        _send_message(
            chat_id=chat_id,
            text="❌ Error en el agente PM — no se pudieron extraer tareas ejecutables.",
            reply_to_message_id=message_id,
        )
        return

    # Crear las tareas del PM en Jira
    tasks = pm_result.get("tasks", [])
    priority_emoji = {"Alta": "🔴", "Media": "🟡", "Baja": "🟢"}
    created_lines = []

    for t in tasks:
        owner_raw = t.get("owner")
        resolved = resolve_assignee(owner_raw) if owner_raw else None
        assignee_name = resolved[0] if resolved else None
        assignee_account_id = resolved[1] if resolved else None

        task_data = {
            "task": t.get("task", "Sin título"),
            "description": t.get("context", ""),
            "deadline": "Sin fecha definida",
            "priority": t.get("priority", "Media"),
        }

        jira_result = create_task(task_data, content, user_name, assignee_account_id)

        if jira_result:
            key = jira_result.get("key", "N/A")
            link = f"{JIRA_URL.rstrip('/')}/browse/{key}"
            emoji = priority_emoji.get(task_data["priority"], "🟡")
            who = assignee_name or "Sin asignar"
            created_lines.append(f"{emoji} {task_data['task']} — {who}\n   {key}: {link}")
        else:
            created_lines.append(f"❌ NO se creó: {t.get('task', '(sin título)')}")

    # Construir y enviar el mensaje del PM
    parts = ["📋 EXECUTION PLAN\n"]

    if created_lines:
        parts.append("Tareas registradas en Jira:")
        parts.extend(created_lines)
    else:
        parts.append("⚠️ El PM no generó tareas ejecutables.")

    if pm_result.get("execution_check"):
        parts.append(f"\n❓ EXECUTION CHECK\n{pm_result['execution_check']}")

    if pm_result.get("challenge"):
        parts.append(f"\n⚠️ CHALLENGE\n{pm_result['challenge']}")

    _send_message(
        chat_id=chat_id,
        text="\n".join(parts),
        reply_to_message_id=message_id,
    )


def _send_help(chat_id: int) -> None:
    """Envía el mensaje de ayuda."""
    help_text = (
        "🤖 **Agente PM — Ayuda**\n\n"
        "Soy tu asistente de gestión de tareas. "
        "Cuando un usuario autorizado envía una indicación (texto o voz), "
        "la analizo y la registro en Jira.\n\n"
        "**Comandos disponibles:**\n"
        "/ayuda — Muestra este mensaje\n"
        "/estado — Verifica el estado del bot\n"
        "/s <mensaje> — Análisis estratégico (roast) + tareas ejecutables en Jira\n\n"
        "**¿Cómo funciono?**\n"
        "1. Escribes o mandas un audio con una indicación\n"
        "2. Si es audio, lo transcribo automáticamente\n"
        "3. Registro la tarea en Jira y te mando el link\n\n"
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
        "🧠 Groq/Whisper: ✅ Activo\n"
        "📡 Telegram: ✅ Activo\n"
    )
    _send_message(chat_id=chat_id, text=status_text, parse_mode="Markdown")

