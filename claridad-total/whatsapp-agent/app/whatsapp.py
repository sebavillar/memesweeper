"""Cliente mínimo de la WhatsApp Cloud API (Meta) para enviar mensajes.
Si no hay credenciales configuradas (modo simulación/CLI), registra en consola."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import settings

log = logging.getLogger("whatsapp")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }


def send_text(to: str, body: str) -> dict[str, Any]:
    """Envía un mensaje de texto. Dentro de la ventana de 24 h abierta por el
    cliente, estos mensajes son gratuitos."""
    if not settings.whatsapp_ready:
        log.info("[SIMULACIÓN] → %s: %s", to, body)
        return {"simulated": True, "to": to, "body": body}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": True, "body": body},
    }
    resp = httpx.post(settings.graph_url, headers=_headers(), json=payload, timeout=20)
    if resp.status_code >= 400:
        log.error("Error enviando a %s: %s %s", to, resp.status_code, resp.text)
    resp.raise_for_status()
    return resp.json()


def notify_corredor(body: str) -> None:
    """Aviso interno al corredor (visita agendada / handoff). Requiere una
    plantilla aprobada si está fuera de su ventana de 24 h; en Fase 0 se asume
    que el corredor tiene conversación abierta o se ve en el panel/log."""
    if not settings.corredor_notify_number:
        log.info("[AVISO CORREDOR] %s", body)
        return
    try:
        send_text(settings.corredor_notify_number, body)
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo avisar al corredor: %s", exc)
