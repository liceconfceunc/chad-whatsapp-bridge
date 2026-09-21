import os

from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")


@app.get("/")
def inicio():
    return {
        "status": "ok",
        "service": "CHAD WhatsApp Bridge"
    }, 200


@app.get("/webhook")
def verificar_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Forbidden", 403


@app.post("/webhook")
def recibir_webhook():
    datos = request.get_json(silent=True)

    print("=== WEBHOOK DE WHATSAPP ===")
    print(datos)
    print("===========================")

    # Meta necesita recibir rápidamente un 200.
    return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
