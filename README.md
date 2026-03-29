# 🤖 Agente Telegram — Jira Project Manager Bot

Bot de Telegram que actúa como un Project Manager virtual. Lee mensajes en un grupo de usuarios autorizados, extrae tareas usando IA (Llama 3 via Groq), y las registra automáticamente en **Jira Cloud**.

**100% gratuito** — Usa únicamente planes gratuitos (free tiers).

## 🏗️ Tech Stack

| Componente | Herramienta |
|-----------|-------------|
| Canal | Telegram Bot API |
| IA | Llama 3.3 70b (via Groq Cloud) |
| Hosting | Render.com (free tier) |
| Organización | Jira Cloud |
| Lenguaje | Python 3.11+ |

---

## 📋 Lo Que Necesitas Hacer (Paso a Paso)

### Paso 1 — Crear el Bot de Telegram

1. Abre Telegram y busca **@BotFather**
2. Envía `/newbot`
3. Ponle un nombre (ej: "Agente PM")
4. Ponle un username (ej: `pm_agente_bot`)
5. **Copia el token** que te da — va en `TELEGRAM_BOT_TOKEN`

### Paso 2 — Obtener IDs Autorizados

1. Busca **@userinfobot** en Telegram
2. Envía un mensaje y obtén tu **ID numérico** (ej: `12345678`).
3. Dile a tu jefe que haga lo mismo o reenvía un mensaje suyo a ese bot.
4. Anota los IDs separados por coma — van en `AUTHORIZED_USER_IDS` (ej: `12345678,87654321`).

### Paso 3 — Obtener API Key de Groq

1. Ve a 👉 **https://console.groq.com/**
2. Crea una cuenta y genera una **API Key**.
3. Cópiala — va en `GROQ_API_KEY`.

### Paso 4 — Configurar Jira Cloud

1. Ve a 👉 **https://id.atlassian.com/manage-profile/security/api-tokens**
2. Haz clic en **"Create API token"**.
3. Ponle un nombre (ej: "Telegram Bot") y copia el token — va en `JIRA_API_TOKEN`.
4. El `JIRA_EMAIL` es el correo de tu cuenta de Atlassian.
5. El `JIRA_URL` es la URL de tu instancia (ej: `https://tu-dominio.atlassian.net`).
6. El `JIRA_PROJECT_KEY` es el código corto de tu proyecto (ej: `KAN`, `PROJ`).

### Paso 5 — Crear el Grupo de Telegram

1. Crea un **grupo nuevo** en Telegram.
2. Agrega a los usuarios autorizados y al **bot**.
3. Haz al bot **admin** del grupo (necesario para leer mensajes).

### Paso 6 — Deploy en Render.com

1. Sube este código a GitHub.
2. Crea un **Web Service** en Render.com conectado a tu repo.
3. Configura las variables de entorno en la pestaña **Environment**:

| Variable | Valor |
|----------|-------|
| `TELEGRAM_BOT_TOKEN` | Token de BotFather |
| `AUTHORIZED_USER_IDS` | IDs separados por coma (ej: `123,456`) |
| `GROQ_API_KEY` | Tu API Key de Groq |
| `JIRA_URL` | Tu dominio de Jira |
| `JIRA_EMAIL` | Tu email de Atlassian |
| `JIRA_API_TOKEN` | El token del Paso 4 |
| `JIRA_PROJECT_KEY` | El Key de tu proyecto |
| `WEBHOOK_URL` | URL de tu servicio en Render |

---

## 📎 Comandos del Bot

| Comando | Descripción |
|---------|-------------|
| `/ayuda` | Muestra información de uso |
| `/estado` | Verifica conexión con Jira y Groq |

---

## 📁 Estructura del Proyecto

```
agenteTelegram/
├── bot/
│   ├── main.py                  # Flask app + webhook
│   ├── config.py                # Variables de entorno
│   ├── telegram_handler.py      # Procesamiento de mensajes
│   ├── ai_extractor.py          # Integración con Groq (Llama 3)
│   ├── jira_manager.py          # Integración con Jira API v3
│   └── prompts.py               # Prompts para la IA
├── requirements.txt
├── render.yaml                  # Config de Render.com
├── .env.example                 # Template de credenciales
└── README.md
```
