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

# ── Base de datos (opcional, para persistencia del scheduler) ──
# Si se define, APScheduler guarda los jobs en esta BD y sobrevive reinicios.
# En Render puedes añadir una PostgreSQL gratuita y pegar su Internal URL aquí.
DATABASE_URL: str | None = os.getenv("DATABASE_URL")

# ── Equipo (para auto-asignación en Jira) ─────────────────
# Mapeo nombre canónico → correo de Jira
TEAM_MEMBERS: dict[str, str] = {
    "Sony":      "sonygomez6@gmail.com",
    "Dylan":     "dyez1110@gmail.com",
    "Sebastian": "soyjuanseyepes@gmail.com",
}

# Pista de nombre para buscar en Jira cuando el email no es visible.
# Usar parte del displayName exacto como aparece en el perfil de Jira.
# Sony     → displayName contiene "Sony"
# Dylan    → displayName es "Dylan Bermudez Cardona"
# Sebastian→ displayName es "Juanse Yepes" (nombre real en Jira)
JIRA_NAME_HINTS: dict[str, str] = {
    "Sony":      "Sony",
    "Dylan":     "Dylan",
    "Sebastian": "Juanse",
}

# Todos los alias reconocidos (en minúsculas) → nombre canónico.
# El fuzzy matching atrapa errores tipográficos, pero estos alias son
# la primera línea de defensa para variantes conocidas.
TEAM_ALIASES: dict[str, str] = {
    # Sony
    "sony":      "Sony",
    "soni":      "Sony",
    "sonym":     "Sony",
    "sonya":     "Sony",
    # Dylan
    "dylan":     "Dylan",
    "dyla":      "Dylan",
    "dyln":      "Dylan",
    "dilan":     "Dylan",
    "dilon":     "Dylan",
    "dylan bermudez": "Dylan",
    # Sebastian / Sebas / Juanse
    "sebastian": "Sebastian",
    "sebastián": "Sebastian",
    "sebas":     "Sebastian",
    "seba":      "Sebastian",
    "sebasti":   "Sebastian",
    "juanse":    "Sebastian",
    "juanseye":  "Sebastian",
    "yepes":     "Sebastian",
}
