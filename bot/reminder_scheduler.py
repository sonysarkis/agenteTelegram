"""
Scheduler de recordatorios para tareas de Jira.

Usa APScheduler (BackgroundScheduler) para programar mensajes de Telegram
cuando se acercan las fechas límite de las tareas.

Lógica de recordatorios (tiempos medidos desde la creación de la tarea):
┌─────────────────────────┬──────────────────────────────────────────────────┐
│ Tiempo hasta deadline   │ Recordatorios programados                        │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ > 5 días  (> 120h)      │ 12h post-creación → 72h antes → 24h antes → 2h  │
│ 2–5 días  (48h–120h)    │ 12h post-creación → 24h antes → 2h antes        │
│ 18h–48h                 │ 12h post-creación → 2h antes                    │
│ 4h–18h                  │ Solo 2h antes                                    │
│ < 4h                    │ Sin recordatorios (la confirmación es el aviso)  │
└─────────────────────────┴──────────────────────────────────────────────────┘

Regla para el recordatorio de 12h: solo se programa si
  deadline > ahora + 18h  (para que cuando se dispare queden ≥ 6h útiles).

Tareas SIN fecha: un único recordatorio 24h después de crearlas.

Persistencia:
  - Por defecto usa MemoryJobStore (jobs se pierden si el proceso se reinicia).
  - Si se define la variable de entorno DATABASE_URL, usa SQLAlchemyJobStore
    para que los jobs sobrevivan reinicios (recomendado en producción).
"""

import os
from datetime import datetime, timezone, timedelta
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

from bot.config import TELEGRAM_BOT_TOKEN, JIRA_URL

# Zona horaria del equipo (UTC-4)
_TZ = timezone(timedelta(hours=-4))

# Instancia singleton del scheduler
_scheduler: BackgroundScheduler | None = None


# ── Inicialización ────────────────────────────────────────

def init_scheduler() -> BackgroundScheduler:
    """Crea y arranca el scheduler. Llamar una sola vez al iniciar la app."""
    global _scheduler

    job_stores = {"default": MemoryJobStore()}

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
            job_stores["default"] = SQLAlchemyJobStore(url=database_url)
            print("✅ Scheduler: usando SQLAlchemy job store (persistente)")
        except Exception as e:
            print(f"⚠️ Scheduler: no se pudo usar SQLAlchemy ({e}). Usando memoria.")
    else:
        print("ℹ️  Scheduler: usando memoria (jobs no persisten en reinicios).")
        print("   → Para persistencia añade DATABASE_URL en Render.")

    _scheduler = BackgroundScheduler(jobstores=job_stores, timezone=_TZ)
    _scheduler.start()
    print("✅ Scheduler iniciado")
    return _scheduler


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler


# ── Envío de mensajes ─────────────────────────────────────

def _send_telegram(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        httpx.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10.0,
        )
    except Exception as e:
        print(f"❌ Error enviando recordatorio a Telegram: {e}")


# ── Funciones que APScheduler llama ──────────────────────

def _fire_reminder(
    chat_id: int,
    jira_key: str,
    task_title: str,
    assignee_display: str,
    deadline_str: str,
    jira_link: str,
    label: str,
) -> None:
    """Envía el mensaje de recordatorio al chat."""
    remaining = _human_remaining(deadline_str)
    assignee_line = f"👤 Asignado a: *{assignee_display}*\n" if assignee_display else ""

    text = (
        f"⏰ *Recordatorio — {jira_key}*\n\n"
        f"📌 {task_title}\n"
        f"{assignee_line}"
        f"📅 Vence en *{remaining}*\n"
        f"🔗 [{jira_key}]({jira_link})"
    )
    _send_telegram(chat_id, text)
    print(f"⏰ Recordatorio '{label}' enviado: {jira_key}")


def _fire_no_deadline_reminder(
    chat_id: int,
    jira_key: str,
    task_title: str,
    jira_link: str,
) -> None:
    """Recordatorio para tareas creadas sin fecha de entrega."""
    text = (
        f"📋 *Tarea sin fecha — {jira_key}*\n\n"
        f"📌 {task_title}\n\n"
        f"⚠️ Esta tarea fue creada hace 24 horas y *no tiene fecha de entrega*.\n"
        f"¿Le asignamos una?\n\n"
        f"🔗 [{jira_key}]({jira_link})"
    )
    _send_telegram(chat_id, text)
    print(f"📋 Recordatorio sin-fecha enviado: {jira_key}")


# ── Programación de recordatorios ────────────────────────

def schedule_task_reminders(
    chat_id: int,
    jira_key: str,
    task_title: str,
    assignee_display: str,
    deadline_str: str | None,
    jira_link: str,
) -> None:
    """
    Programa los recordatorios para una tarea recién creada.

    Args:
        chat_id:          ID del chat de Telegram donde enviar los avisos.
        jira_key:         Clave del issue (ej: "PROJ-42").
        task_title:       Título de la tarea.
        assignee_display: Nombre del asignado o "" si no hay.
        deadline_str:     Fecha límite en formato "YYYY-MM-DD" o None/"Sin fecha definida".
        jira_link:        URL directa al issue en Jira.
    """
    scheduler = get_scheduler()
    if not scheduler:
        print("⚠️ Scheduler no inicializado, no se programaron recordatorios")
        return

    now_utc = datetime.now(timezone.utc)

    # ── Sin fecha → recordatorio a las 24h ───────────────
    if not deadline_str or deadline_str == "Sin fecha definida":
        _add_job(
            scheduler,
            func=_fire_no_deadline_reminder,
            fire_time=now_utc + timedelta(hours=24),
            job_id=f"{jira_key}_nodl",
            args=[chat_id, jira_key, task_title, jira_link],
        )
        return

    # ── Parsear deadline (fin del día en zona del equipo) ─
    try:
        deadline_local = datetime.strptime(deadline_str, "%Y-%m-%d").replace(
            hour=23, minute=59, second=0, tzinfo=_TZ
        )
        deadline_utc = deadline_local.astimezone(timezone.utc)
    except ValueError:
        print(f"⚠️ Scheduler: no se pudo parsear la fecha '{deadline_str}'")
        return

    delta_h = (deadline_utc - now_utc).total_seconds() / 3600

    base_args = [chat_id, jira_key, task_title, assignee_display, deadline_str, jira_link]

    # 2h antes — solo si deadline > 4h desde ahora
    if delta_h > 4:
        _add_job(
            scheduler,
            func=_fire_reminder,
            fire_time=deadline_utc - timedelta(hours=2),
            job_id=f"{jira_key}_2h",
            args=base_args + ["2h_antes"],
        )

    # 12h post-creación — solo si deadline > 18h desde ahora
    if delta_h > 18:
        _add_job(
            scheduler,
            func=_fire_reminder,
            fire_time=now_utc + timedelta(hours=12),
            job_id=f"{jira_key}_12h",
            args=base_args + ["12h_creacion"],
        )

    # 24h antes — solo si deadline > 30h desde ahora
    if delta_h > 30:
        _add_job(
            scheduler,
            func=_fire_reminder,
            fire_time=deadline_utc - timedelta(hours=24),
            job_id=f"{jira_key}_24h",
            args=base_args + ["24h_antes"],
        )

    # 72h antes — solo si deadline > 120h desde ahora (> 5 días)
    if delta_h > 120:
        _add_job(
            scheduler,
            func=_fire_reminder,
            fire_time=deadline_utc - timedelta(hours=72),
            job_id=f"{jira_key}_72h",
            args=base_args + ["72h_antes"],
        )


# ── Helpers internos ──────────────────────────────────────

def _add_job(scheduler, func, fire_time: datetime, job_id: str, args: list) -> None:
    """Añade un job al scheduler si la hora de disparo está en el futuro."""
    now_utc = datetime.now(timezone.utc)
    if fire_time <= now_utc:
        return  # Ya pasó, no tiene sentido programarlo
    try:
        scheduler.add_job(
            func,
            trigger="date",
            run_date=fire_time,
            args=args,
            id=job_id,
            replace_existing=True,
        )
        local_time = fire_time.astimezone(_TZ).strftime("%d/%m %H:%M")
        print(f"   ⏱  Job '{job_id}' programado para {local_time} (hora equipo)")
    except Exception as e:
        print(f"❌ Error programando job '{job_id}': {e}")


def _human_remaining(deadline_str: str) -> str:
    """Convierte una fecha YYYY-MM-DD en texto legible del tiempo restante."""
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").replace(
            hour=23, minute=59, second=0, tzinfo=_TZ
        )
        delta = deadline - datetime.now(_TZ)
        hours = delta.total_seconds() / 3600

        if hours < 0:
            return "ya venció"
        elif hours < 2:
            return "menos de 2 horas"
        elif hours < 24:
            return f"{int(hours)} horas"
        elif hours < 48:
            return "1 día"
        else:
            return f"{int(hours / 24)} días"
    except Exception:
        return "fecha próxima"
