"""
Entry point — Flask app con webhook de Telegram.

Este archivo:
1. Crea la app Flask
2. Configura el endpoint del webhook
3. Registra el webhook con Telegram al iniciar
4. Expone /health para monitoreo
"""

import asyncio
import traceback

from flask import Flask, request, jsonify
from telegram import Bot

from bot.config import TELEGRAM_BOT_TOKEN, WEBHOOK_URL, PORT
from bot.telegram_handler import handle_message

# ── Inicializar Flask y Bot ───────────────────────────────
app = Flask(__name__)
bot = Bot(token=TELEGRAM_BOT_TOKEN)


# ── Health Check ──────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    """
    Endpoint de salud. 
    Render lo usa para verificar que el servicio está vivo.
    También Telegram puede usarlo si el webhook falla.
    """
    return jsonify({
        "status": "ok",
        "service": "Agente Telegram PM",
        "message": "Bot activo y escuchando 🤖"
    }), 200


# ── Webhook de Telegram ──────────────────────────────────
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """
    Recibe updates de Telegram via webhook.
    Cada mensaje del grupo llega aquí como POST.
    """
    try:
        update_data = request.get_json(force=True)

        # Procesar el mensaje de forma asíncrona
        asyncio.run(handle_message(update_data, bot))

        return jsonify({"ok": True}), 200

    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        traceback.print_exc()
        # Siempre retornar 200 para que Telegram no reintente infinitamente
        return jsonify({"ok": True}), 200


# ── Registrar Webhook con Telegram ───────────────────────
def setup_webhook():
    """Registra la URL del webhook en Telegram."""
    webhook_url = f"{WEBHOOK_URL}/webhook"
    try:
        result = asyncio.run(bot.set_webhook(url=webhook_url))
        if result:
            print(f"✅ Webhook registrado: {webhook_url}")
        else:
            print(f"❌ Error registrando webhook")
    except Exception as e:
        print(f"❌ Error configurando webhook: {e}")
        traceback.print_exc()


# ── Startup ──────────────────────────────────────────────
# Registrar webhook al iniciar la app
with app.app_context():
    print("🚀 Iniciando Agente Telegram PM...")
    print(f"📡 Webhook URL: {WEBHOOK_URL}/webhook")
    setup_webhook()
    print("✅ Bot listo para recibir mensajes")


# ── Ejecución local ──────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
