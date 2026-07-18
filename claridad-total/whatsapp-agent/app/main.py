"""App FastAPI: webhook de WhatsApp Cloud API + endpoint de simulación.

Verificación:  GET  /webhook   (Meta valida el token y devuelve hub.challenge)
Recepción:     POST /webhook   (Meta entrega los mensajes entrantes)
Prueba local:  POST /simulate  {"from": "549...", "text": "hola"}  -> respuesta del agente
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from . import agent
from .config import settings
from .panel import router as panel_router
from .whatsapp import send_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")

app = FastAPI(title="Claridad Total · Agente de WhatsApp", version="0.2.0")
app.include_router(panel_router)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "whatsapp_ready": settings.whatsapp_ready, "model": settings.agent_model}


@app.get("/webhook")
def verify(request: Request) -> Response:
    """Verificación del webhook (handshake de Meta)."""
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and \
            params.get("hub.verify_token") == settings.whatsapp_verify_token:
        return PlainTextResponse(params.get("hub.challenge", ""))
    return PlainTextResponse("forbidden", status_code=403)


@app.post("/webhook")
async def receive(request: Request) -> Response:
    """Recibe mensajes entrantes y responde con el agente."""
    body = await request.json()
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        # Fase 0 solo maneja texto; otros tipos se ignoran cordialmente.
                        send_text(msg["from"], "Por ahora te puedo ayudar por texto 🙂. Contame qué buscás.")
                        continue
                    wa_id = msg["from"]
                    texto = msg["text"]["body"]
                    log.info("← %s: %s", wa_id, texto)
                    respuesta = agent.responder(wa_id, texto)
                    send_text(wa_id, respuesta)
    except Exception as exc:  # noqa: BLE001
        log.exception("Error procesando webhook: %s", exc)
    # Siempre 200 para que Meta no reintente en loop.
    return JSONResponse({"status": "ok"})


@app.post("/simulate")
async def simulate(request: Request) -> Response:
    """Probar el agente sin WhatsApp real. Body: {"from": "...", "text": "..."}"""
    body = await request.json()
    wa_id = body.get("from", "sim-tester")
    texto = body.get("text", "")
    respuesta = agent.responder(wa_id, texto)
    return JSONResponse({"from": wa_id, "reply": respuesta})
