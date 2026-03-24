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
BOSS_USER_ID: int = int(_get_required("BOSS_USER_ID"))

# ── Groq (IA ultrarrápida y gratuita) ────────────────────
GROQ_API_KEY: str = _get_required("GROQ_API_KEY")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Notion ────────────────────────────────────────────────
NOTION_TOKEN: str = _get_required("NOTION_TOKEN")
NOTION_DATABASE_ID: str = _get_required("NOTION_DATABASE_ID")

# ── App ───────────────────────────────────────────────────
WEBHOOK_URL: str = _get_required("WEBHOOK_URL")
PORT: int = int(os.getenv("PORT", "5000"))
