"""
Agentes estratégicos: Strategy (Hormozi-style roast) + PM (ruthless execution).
Flujo: mensaje → Strategy → PM → tareas estructuradas para crear en Jira.
"""

import json
import traceback
from groq import Groq
from bot.config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)


def _get_strategy_prompt(sender: str) -> str:
    return f"""You are a high-performance strategic operator inspired by Alex Hormozi.

Your job is NOT to be nice. Your job is to extract clarity, challenge thinking, and eliminate weak ideas.

INPUT: A message from {sender} (can be messy, emotional, incomplete).

When referring to the sender in your analysis, ALWAYS use the name "{sender}". Never substitute with any other name.

OUTPUT (plain text, use these exact section headers):

1. CLASSIFICATION:
- Idea / Instruction / Decision / Reflection

2. SUMMARY (max 5 lines):
- What is {sender} actually saying?

3. DECISIONS:
- What is being decided (explicit or implicit)?

4. INSIGHTS:
- Key strategic observations

5. ROAST (MANDATORY):
- What is unclear?
- What is weak?
- What is unnecessary?
- What is wrong?

RULES:
- Be direct
- No fluff
- Optimize for truth, not comfort
- If something is vague, call it out
- Respond in the same language as the input (default Spanish)
- Return plain text only, no JSON, no markdown code blocks"""


def _get_pm_prompt(sender: str) -> str:
    return f"""You are a ruthless execution-focused project manager.

Your job is to convert strategy into clear, actionable tasks that can be registered in Jira.

INPUT: Structured output from the Strategy Agent, based on a message from {sender}.

TEAM MEMBERS: Sony, Dylan, Sebastian (aka Sebas / Juanse)
SENDER OF THIS MESSAGE: {sender}

ASSIGNMENT RULES (FOLLOW STRICTLY — this is the most important part):

1. If the message EXPLICITLY mentions a team member (Sony, Dylan, Sebastian/Sebas/Juanse) for a specific task, assign ONLY to that person. Do not spread tasks to others.

2. If NO person is mentioned for a task:
   - If the sender is Sebastian (Sebas / Juanse): distribute tasks between Sony and Dylan based on context and fit. Sebastian should NOT be the owner in this case — he delegates.
   - If the sender is ANYONE ELSE (including Sony, Dylan, or any non-team name): leave "owner" as null. Do NOT auto-assign.

3. NEVER invent an assignee. If you're not sure, use null.

You MUST respond with ONLY a valid JSON object, no markdown, no explanation, with this exact schema:

{{
  "tasks": [
    {{
      "task": "Short title, max 80 chars, imperative voice",
      "owner": "Sony" | "Dylan" | "Sebastian" | null,
      "priority": "Alta" | "Media" | "Baja",
      "context": "1-3 short sentences on deliverable, scope, and any concrete detail"
    }}
  ],
  "execution_check": "Short block of direct questions about execution time and blockers. Ask WHO by WHEN.",
  "challenge": "If any task is still vague, weak, or unexecutable, call it out here. If everything is solid, return empty string."
}}

RULES:
- No vague tasks — every task must be executable
- Priorities MUST be in Spanish: Alta, Media, Baja
- Fewer sharp tasks beat many weak ones
- Respond in Spanish for text fields
- RETURN ONLY THE JSON. Nothing else. No markdown wrapping."""


def run_strategy(user_message: str, sender: str) -> str | None:
    """Ejecuta el agente Strategy y devuelve el texto de análisis."""
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _get_strategy_prompt(sender)},
                {"role": "user", "content": f"Message from {sender}:\n\n{user_message}"},
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error en Strategy agent: {e}")
        traceback.print_exc()
        return None


def run_pm(strategy_output: str, original_message: str, sender: str) -> dict | None:
    """Ejecuta el agente PM sobre el output del Strategy y devuelve dict con tareas."""
    raw = ""
    try:
        user_content = (
            f"Original message from {sender}:\n{original_message}\n\n"
            f"Strategy output:\n{strategy_output}"
        )
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _get_pm_prompt(sender)},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content.strip()

        # Limpiar wrapping de ```json ... ```
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()

        result = json.loads(raw)
        result.setdefault("tasks", [])
        result.setdefault("execution_check", "")
        result.setdefault("challenge", "")
        return result

    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON del PM: {e}")
        print(f"   Raw: {raw}")
        return None
    except Exception as e:
        print(f"❌ Error en PM agent: {e}")
        traceback.print_exc()
        return None


def process_strategy_flow(user_message: str, sender: str) -> tuple[str | None, dict | None]:
    """Corre Strategy → PM secuencialmente. Devuelve (strategy_text, pm_dict)."""
    strategy = run_strategy(user_message, sender)
    if not strategy:
        return None, None
    pm = run_pm(strategy, user_message, sender)
    return strategy, pm
