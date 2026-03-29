"""
Configuración central del bot.
Carga variables de entorno y valida que estén presentes.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


def _get_required(key: str) -> str:
    """Obtiene una variable de entorno requerida o termina el programa."""
    value = os.getenv(key)
    if not value:
        print(f"❌ ERROR: La variable de entorno '{key}' es obligatoria. Revisa tu archivo .env")
        sys.exit(1)
    return value


# ── Telegram ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = _get_required("TELEGRAM_BOT_TOKEN")

# Lista de IDs autorizados (separados por coma en .env)
_auth_ids_raw = _get_required("AUTHORIZED_USER_IDS")
AUTHORIZED_USER_IDS: list[int] = [int(i.strip()) for i in _auth_ids_raw.split(",") if i.strip()]

# ── Groq (IA ultrarrápida y gratuita) ────────────────────
GROQ_API_KEY: str = _get_required("GROQ_API_KEY")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Jira ──────────────────────────────────────────────────
JIRA_URL: str = _get_required("JIRA_URL")
JIRA_EMAIL: str = _get_required("JIRA_EMAIL")
JIRA_API_TOKEN: str = _get_required("JIRA_API_TOKEN")
JIRA_PROJECT_KEY: str = _get_required("JIRA_PROJECT_KEY")

# ── App ───────────────────────────────────────────────────
WEBHOOK_URL: str = _get_required("WEBHOOK_URL")
PORT: int = int(os.getenv("PORT", "5000"))
