"""App FastAPI: webhook de WhatsApp Cloud API + endpoint de simulación.

Verificación:  GET  /webhook   (Meta valida el token y devuelve hub.challenge)
Recepción:     POST /webhook   (Meta entrega los mensajes entrantes)
Prueba local:  POST /simulate  {"from": "549...", "text": "hola"}  -> respuesta del agente
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

import functools

from . import agent, db, enrich, inmoclick, mendozaprop, remax, scraper
from .api import router as api_router
from .config import settings
from .panel import router as panel_router
from .whatsapp import send_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")

app = FastAPI(title="Claridad Total · Agente de WhatsApp", version="0.4.0")
app.include_router(panel_router)
app.include_router(api_router)  # API JSON para el panel web (Next.js)

# Fotos de propiedades: guardadas en el disco persistente y servidas públicamente
# en /media para que WhatsApp/Meta puedan descargarlas.
MEDIA_DIR = Path(os.environ.get("DATA_DIR") or "data") / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

db.init()  # base de datos de mercado (comparables de oferta)


@app.on_event("startup")
async def _market_updater() -> None:
    """Actualiza la oferta (MercadoLibre + RE/MAX) automáticamente: una vez al
    arrancar y cada 24 h. Sin comandos manuales. Volumen contenido para minimizar
    riesgo de baneo (MELI ~1.000/día con pausas). Si una fuente falla (p. ej. falta
    credencial/URL), lo registra en el log y reintenta al día siguiente."""
    # ~1.000 avisos/día en MELI: 21 páginas × 48 con pausa de 4 s. RE/MAX: 4 páginas.
    fuentes = [
        ("MercadoLibre", functools.partial(scraper.scrape, 21)),
        ("RE/MAX", functools.partial(remax.scrape, 21)),  # ~500 avisos/día (21×24)
        ("Inmoclick", functools.partial(inmoclick.scrape, 5)),  # Mendoza, 3 tipos × 5 pág.
        ("MendozaProp", functools.partial(mendozaprop.scrape, 25)),  # API JSON, venta
    ]

    async def loop() -> None:
        await asyncio.sleep(25)  # dejar que termine de arrancar
        while True:
            for nombre, fn in fuentes:
                try:
                    res = await asyncio.get_running_loop().run_in_executor(None, fn)
                    if res.get("error"):
                        log.info("Oferta %s: %s", nombre, res["error"])
                    else:
                        log.info("Oferta actualizada (%s): guardados=%s venta_usd=%s",
                                 nombre, res.get("guardados"), res.get("venta_usd"))
                except Exception as exc:  # noqa: BLE001
                    log.warning("No se pudo actualizar la oferta (%s): %s", nombre, exc)
            # Señal de barrio privado desde los títulos de los avisos nuevos.
            try:
                bp = await asyncio.get_running_loop().run_in_executor(None, db.marcar_privados)
                if bp:
                    log.info("Barrio privado detectado en %d avisos (por título).", bp)
            except Exception as exc:  # noqa: BLE001
                log.warning("No se pudo marcar barrios privados: %s", exc)
            # Enriquecimiento gradual: antigüedad desde las fichas de avisos
            # nuevos (60 por fuente/día, con pausas). Ver app/enrich.py.
            try:
                res = await asyncio.get_running_loop().run_in_executor(
                    None, functools.partial(enrich.run, 60))
                log.info("Antigüedad enriquecida: %s",
                         {k: v["con_dato"] for k, v in res["fuentes"].items()})
            except Exception as exc:  # noqa: BLE001
                log.warning("No se pudo enriquecer fichas: %s", exc)
            await asyncio.sleep(24 * 3600)

    asyncio.create_task(loop())


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
