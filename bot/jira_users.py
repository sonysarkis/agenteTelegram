"""
Resolución de usuarios de Jira.

Al arrancar el bot, busca el accountId de cada miembro del equipo por email
y lo cachea en memoria. Luego expone resolve_assignee() que acepta un nombre
tal como llega del mensaje de Telegram (incluyendo typos) y devuelve
(nombre_canónico, accountId) usando alias exactos + fuzzy matching.
"""

import difflib
import traceback
import base64
import httpx

from bot.config import JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, TEAM_MEMBERS, TEAM_ALIASES, JIRA_NAME_HINTS

# ── Auth headers ──────────────────────────────────────────
_auth_b64 = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
_HEADERS = {
    "Authorization": f"Basic {_auth_b64}",
    "Accept": "application/json",
}

# ── Cache: nombre_canónico → accountId ───────────────────
_account_ids: dict[str, str] = {}


def load_team_account_ids() -> None:
    """
    Consulta la API de Jira para obtener el accountId de cada miembro
    del equipo definido en TEAM_MEMBERS y lo guarda en caché.

    Estrategia de búsqueda (Jira Cloud oculta emails por privacidad):
    1. Busca por email — funciona si el usuario tiene email público.
    2. Si no lo encuentra, busca por nombre canónico (display name).
    3. Toma el primer resultado activo cuyo displayName contenga el nombre.
    """
    global _account_ids
    url = f"{JIRA_URL.rstrip('/')}/rest/api/3/user/search"

    for canonical_name, email in TEAM_MEMBERS.items():
        try:
            # ── Intento 1: buscar por email ───────────────────
            resp = httpx.get(url, headers=_HEADERS, params={"query": email}, timeout=10)
            matched = None

            if resp.status_code == 200:
                users = resp.json()
                # Jira puede devolver el email o no (privacidad)
                matched = next(
                    (u for u in users
                     if u.get("emailAddress", "").lower() == email.lower()
                     and u.get("accountType") == "atlassian"),
                    None,
                )

            # ── Intento 2: buscar por nombre hint si el email falló ─
            resp2 = None
            if not matched:
                # Usar el hint de nombre de Jira si está definido (ej: "Juanse" para Sebastian)
                name_hint = JIRA_NAME_HINTS.get(canonical_name, canonical_name)
                resp2 = httpx.get(url, headers=_HEADERS, params={"query": name_hint}, timeout=10)
                if resp2.status_code == 200:
                    users2 = resp2.json()
                    hint_lower = name_hint.lower()
                    # 2a. Con filtro de accountType
                    matched = next(
                        (u for u in users2
                         if hint_lower in u.get("displayName", "").lower()
                         and u.get("accountType") == "atlassian"),
                        None,
                    )
                    # 2b. Sin filtro de accountType (fallback por si Jira devuelve otro tipo)
                    if not matched:
                        matched = next(
                            (u for u in users2
                             if hint_lower in u.get("displayName", "").lower()),
                            None,
                        )

            if matched:
                _account_ids[canonical_name] = matched["accountId"]
                print(f"✅ Usuario Jira cargado: {canonical_name} → {matched['accountId']} "
                      f"(displayName='{matched.get('displayName', '')}', accountType='{matched.get('accountType', '')}')")
            else:
                # Mostrar qué devolvió Jira para diagnosticar el problema de nombres
                found_names = []
                if resp.status_code == 200:
                    found_names += [f"{u.get('displayName','')}({u.get('accountType','')})" for u in resp.json()]
                if resp2 and resp2.status_code == 200:
                    found_names += [f"{u.get('displayName','')}({u.get('accountType','')})" for u in resp2.json()]
                print(f"⚠️ No se encontró usuario Jira para {canonical_name} ({email}). "
                      f"Resultados de Jira: {found_names or '(ninguno)'}")

        except Exception as e:
            print(f"❌ Error cargando usuario Jira {canonical_name}: {e}")
            traceback.print_exc()


def resolve_assignee(raw_name: str) -> tuple[str, str] | None:
    """
    Resuelve un nombre (posiblemente con typos) al (nombre_canónico, accountId).

    Estrategia:
    1. Alias exacto (case-insensitive) del diccionario TEAM_ALIASES.
    2. Fuzzy match con difflib contra todos los alias + nombres canónicos.
       Se acepta similitud ≥ 0.60.

    Retorna None si no se encuentra coincidencia suficiente o si el
    accountId no está cargado en caché (carga fallida al inicio).
    """
    if not raw_name or not raw_name.strip():
        return None

    name_lower = raw_name.strip().lower()

    # 1. Alias exacto
    canonical = TEAM_ALIASES.get(name_lower)
    if canonical and canonical in _account_ids:
        return (canonical, _account_ids[canonical])

    # 2. Fuzzy matching contra todos los alias y nombres canónicos
    all_known = list(TEAM_ALIASES.keys()) + [n.lower() for n in _account_ids.keys()]
    matches = difflib.get_close_matches(name_lower, all_known, n=1, cutoff=0.60)

    if matches:
        best = matches[0]
        # Resolver al nombre canónico
        resolved_canonical = TEAM_ALIASES.get(best) or best.capitalize()
        # Buscar accountId (case-insensitive)
        for name, acct_id in _account_ids.items():
            if name.lower() == resolved_canonical.lower():
                print(f"🔍 Fuzzy match: '{raw_name}' → '{name}' (similitud ≥ 0.60)")
                return (name, acct_id)

    print(f"⚠️ No se pudo resolver el asignado: '{raw_name}'")
    return None
