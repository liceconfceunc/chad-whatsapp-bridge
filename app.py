import os
from datetime import datetime, timezone

from flask import Flask, request
from supabase import create_client

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
)


@app.get("/")
def inicio():
    return {
        "status": "ok",
        "service": "CHAD WhatsApp Bridge",
    }, 200


@app.get("/webhook")
def verificar_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if (
        mode == "subscribe"
        and token == VERIFY_TOKEN
    ):
        return challenge, 200

    return "Forbidden", 403


@app.post("/webhook")
def recibir_webhook():
    datos = request.get_json(
        silent=True
    ) or {}

    try:
        for entry in datos.get(
            "entry",
            [],
        ):
            for change in entry.get(
                "changes",
                [],
            ):
                value = change.get(
                    "value",
                    {},
                )

                phone_number_id = (
                    value
                    .get("metadata", {})
                    .get("phone_number_id")
                )

                contacts = value.get(
                    "contacts",
                    [],
                )

                sender_name = None

                if contacts:
                    sender_name = (
                        contacts[0]
                        .get("profile", {})
                        .get("name")
                    )

                for message in value.get(
                    "messages",
                    [],
                ):
                    if (
                        message.get("type")
                        != "text"
                    ):
                        continue

                    texto = (
                        message
                        .get("text", {})
                        .get("body")
                    )

                    if not texto:
                        continue

                    job = {
                        "message_id":
                            message.get("id"),
                        "phone_number_id":
                            phone_number_id,
                        "sender":
                            message.get("from"),
                        "sender_name":
                            sender_name,
                        "message_text":
                            texto,
                        "status":
                            "pending",
                    }

                    (
                        supabase
                        .table("whatsapp_jobs")
                        .upsert(
                            job,
                            on_conflict="message_id",
                        )
                        .execute()
                    )

                    print(
                        f"Mensaje guardado: "
                        f"{texto!r}",
                        flush=True,
                    )

    except Exception as error:
        print(
            "ERROR guardando webhook:",
            error,
            flush=True,
        )

    return "EVENT_RECEIVED", 200


@app.get("/jobs/next")
def siguiente_job():
    resultado = (
        supabase
        .table("whatsapp_jobs")
        .select("*")
        .eq(
            "status",
            "pending",
        )
        .order("created_at")
        .limit(1)
        .execute()
    )

    if not resultado.data:
        return {
            "job": None
        }, 200

    job = resultado.data[0]

    # Marcamos el mensaje como processing
    # antes de entregárselo al worker.
    (
        supabase
        .table("whatsapp_jobs")
        .update({
            "status": "processing",
        })
        .eq(
            "id",
            job["id"],
        )
        .execute()
    )

    job["status"] = "processing"

    return {
        "job": job
    }, 200


@app.post("/jobs/result")
def guardar_resultado():
    datos = request.get_json(
        silent=True
    ) or {}

    job_id = datos.get("id")
    respuesta = datos.get(
        "response_text"
    )

    if (
        not job_id
        or respuesta is None
    ):
        return {
            "error":
                "Faltan id o response_text"
        }, 400

    procesado = datetime.now(
        timezone.utc
    ).isoformat()

    (
        supabase
        .table("whatsapp_jobs")
        .update({
            "status": "answered",
            "response_text": respuesta,
            "processed_at": procesado,
        })
        .eq(
            "id",
            job_id,
        )
        .execute()
    )

    print(
        f"Job {job_id} completado.",
        flush=True,
    )

    return {
        "status": "ok",
        "id": job_id,
    }, 200


if __name__ == "__main__":
    puerto = int(
        os.environ.get(
            "PORT",
            5000,
        )
    )

    app.run(
        host="0.0.0.0",
        port=puerto,
    )
