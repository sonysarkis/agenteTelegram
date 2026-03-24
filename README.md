# 🤖 Agente Telegram — Project Manager Bot

Bot de Telegram que actúa como un Project Manager virtual. Lee los mensajes de tu jefe en un grupo, extrae tareas usando IA (Google Gemini), y las registra automáticamente en Notion.

**100% gratuito** — Usa únicamente planes gratuitos (free tiers).

## 🏗️ Tech Stack

| Componente | Herramienta |
|-----------|-------------|
| Canal | Telegram Bot API |
| IA | Google Gemini 2.0 Flash |
| Hosting | Render.com (free tier) |
| Organización | Notion |
| Lenguaje | Python 3.11+ |

---

## 📋 Lo Que Necesitas Hacer (Paso a Paso)

### Paso 1 — Crear el Bot de Telegram

1. Abre Telegram y busca **@BotFather**
2. Envía `/newbot`
3. Ponle un nombre (ej: "PM Asistente")
4. Ponle un username (ej: `pm_asistente_bot`)
5. **Copia el token** que te da — lo necesitarás como `TELEGRAM_BOT_TOKEN`

### Paso 2 — Obtener el ID de tu Jefe

1. Busca **@userinfobot** en Telegram  
2. Dile a tu jefe que le envíe cualquier mensaje a ese bot
3. El bot responderá con su **ID numérico** (ej: `123456789`)
4. Ese número va en `BOSS_USER_ID`

> 💡 **Alternativa**: Tu jefe puede reenviar un mensaje al bot @userinfobot, o tú puedes usar @RawDataBot en un grupo temporal.

### Paso 3 — Obtener API Key de Gemini

1. Ve a 👉 **https://aistudio.google.com/apikey**
2. Inicia sesión con tu cuenta de Google
3. Haz clic en **"Create API Key"**
4. **Copia la API key** — va en `GEMINI_API_KEY`

> ✅ No requiere tarjeta de crédito. El plan gratuito incluye 1,500 requests/día.

### Paso 4 — Configurar Notion

#### 4a. Crear la Integración (API Token)

1. Ve a 👉 **https://www.notion.so/my-integrations**
2. Haz clic en **"+ New integration"**
3. Ponle un nombre (ej: "PM Bot")
4. Selecciona tu workspace
5. En **Capabilities**, asegúrate de que tenga:
   - ✅ Read content
   - ✅ Insert content
   - ✅ Update content
6. Haz clic en **"Save"**
7. **Copia el "Internal Integration Secret"** — va en `NOTION_TOKEN`

#### 4b. Crear la Base de Datos en Notion

1. En Notion, crea una **nueva página**
2. Escribe `/database` y selecciona **"Database - Full page"**
3. Configura estas **propiedades** (columnas) con los nombres EXACTOS:

| Propiedad | Tipo | Notas |
|-----------|------|-------|
| **Tarea** | Title | Ya existe por defecto, solo renómbrala |
| **Estado** | Select | Opciones: `Por hacer ⏳`, `En progreso 🔄`, `Hecho ✅` |
| **Prioridad** | Select | Opciones: `🔴 Alta`, `🟡 Media`, `🟢 Baja` |
| **Fecha de registro** | Date | — |
| **Fecha límite** | Date | — |
| **Asignado por** | Text | — |

4. **Importante**: Haz clic en `...` (menú de la página) → **"Connections"** → Busca tu integración ("PM Bot") y **conéctala**.

#### 4c. Obtener el Database ID

1. Abre tu base de datos en Notion **en el navegador**
2. La URL se verá así:
   ```
   https://www.notion.so/tu-workspace/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX?v=...
   ```
3. El **Database ID** son los 32 caracteres después de la última `/` y antes del `?`
   ```
   Ejemplo: abc123def456789012345678abcdef12
   ```
4. Cópialo — va en `NOTION_DATABASE_ID`

### Paso 5 — Crear el Grupo de Telegram

1. Crea un **grupo nuevo** en Telegram
2. Agrega a **tu jefe** y al **bot** al grupo
3. En la configuración del grupo, ve a **"Administradores"** y haz al bot **admin** (necesita permisos para leer mensajes)

### Paso 6 — Deploy en Render.com

1. **Sube este código a GitHub** (crea un repo y haz push)
2. Ve a 👉 **https://render.com** y crea una cuenta
3. Haz clic en **"New → Web Service"**
4. Conecta tu repositorio de GitHub
5. Render detectará el `render.yaml` automáticamente. Configura:
   - **Name**: `agente-telegram-pm`
   - **Region**: Oregon o la más cercana
   - **Plan**: Free
6. Ve a **"Environment"** y agrega estas variables:

| Variable | Valor |
|----------|-------|
| `TELEGRAM_BOT_TOKEN` | El token del Paso 1 |
| `BOSS_USER_ID` | El ID numérico del Paso 2 |
| `GEMINI_API_KEY` | La API key del Paso 3 |
| `NOTION_TOKEN` | El token del Paso 4a |
| `NOTION_DATABASE_ID` | El ID del Paso 4c |
| `WEBHOOK_URL` | La URL de tu servicio en Render (ej: `https://agente-telegram-pm.onrender.com`) |

7. Haz clic en **"Create Web Service"**
8. Espera a que haga el deploy (~2-3 minutos)

### Paso 7 — ¡Probar!

1. Ve al grupo de Telegram
2. Pídele a tu jefe que escriba algo como:
   > "Necesito el reporte de ventas para el viernes, es urgente"
3. El bot debería responder con:
   ```
   ✅ Tarea registrada
   
   📌 Preparar reporte de ventas
   📅 2025-03-28
   🏷️ Prioridad: 🔴 Alta
   📊 Estado: Por hacer ⏳
   ```
4. Verifica en Notion que la tarea aparezca en la base de datos

---

## 🛠️ Desarrollo Local

```bash
# 1. Clonar el repositorio
git clone <tu-repo-url>
cd agenteTelegram

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# Editar .env con tus credenciales

# 5. Ejecutar (modo desarrollo)
python bot/main.py
```

Para desarrollo local con webhook, necesitas [ngrok](https://ngrok.com):
```bash
# En otra terminal:
ngrok http 5000
# Copiar la URL https de ngrok y ponerla en WEBHOOK_URL en el .env
```

---

## 📎 Comandos del Bot

| Comando | Descripción |
|---------|-------------|
| `/ayuda` | Muestra información de uso |
| `/estado` | Verifica conexión con Notion y Gemini |

---

## ⚠️ Limitaciones del Plan Gratuito

| Servicio | Límite | Impacto real |
|----------|--------|-------------|
| **Render** | 750 hrs/mes, spin-down tras 15min | Primer mensaje tras inactividad tarda ~1 min |
| **Gemini** | 15 RPM, 1,500 req/día | Imposible de alcanzar en uso normal |
| **Notion API** | 3 req/segundo | Imposible de alcanzar procesando 1 tarea a la vez |

---

## 📁 Estructura del Proyecto

```
agenteTelegram/
├── bot/
│   ├── __init__.py              # Inicialización del paquete
│   ├── main.py                  # Flask app + webhook
│   ├── config.py                # Variables de entorno
│   ├── telegram_handler.py      # Procesamiento de mensajes
│   ├── ai_extractor.py          # Integración con Gemini
│   ├── notion_manager.py        # Integración con Notion
│   └── prompts.py               # Prompts del sistema
├── requirements.txt
├── render.yaml                  # Config de Render.com
├── .env.example                 # Template de credenciales
├── .gitignore
└── README.md
```
