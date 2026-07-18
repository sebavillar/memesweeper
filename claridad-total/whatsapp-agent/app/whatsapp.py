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


def _ar_msisdn(to: str) -> str:
    """Formato del destinatario para Argentina.

    Por defecto se responde al wa_id tal cual (lo canónico, y lo que funciona con
    un número de PRODUCCIÓN real). El número de PRUEBA de Meta, en cambio, suele
    registrar los celulares argentinos en el viejo formato doméstico con '15'
    (54 + área + 15 + abonado). Para esos casos, con WHATSAPP_AR_15=1 se
    transforma 549XXXXXXXXXX -> 54 + área + 15 + abonado."""
    d = (to or "").lstrip("+")
    if not (settings.whatsapp_ar_15 and d.startswith("549") and len(d) == 13):
        return d
    national = d[3:]                       # 10 dígitos: área + abonado
    area_len = 2 if national.startswith("11") else 3   # AMBA=11 (2), resto ~3 (Mendoza=261)
    return "54" + national[:area_len] + "15" + national[area_len:]


def send_text(to: str, body: str) -> dict[str, Any]:
    """Envía un mensaje de texto. Dentro de la ventana de 24 h abierta por el
    cliente, estos mensajes son gratuitos."""
    to = _ar_msisdn(to)
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


def send_image(to: str, link: str, caption: str | None = None) -> dict[str, Any]:
    """Envía una imagen nativa de WhatsApp. `link` debe ser una URL pública HTTPS
    accesible por Meta (jpg/png). Dentro de la ventana de 24 h es gratuito."""
    to = _ar_msisdn(to)
    if not settings.whatsapp_ready:
        log.info("[SIMULACIÓN] 🖼️ → %s: %s (%s)", to, link, caption or "")
        return {"simulated": True, "to": to, "image": link, "caption": caption}
    image: dict[str, Any] = {"link": link}
    if caption:
        image["caption"] = caption
    payload = {"messaging_product": "whatsapp", "to": to, "type": "image", "image": image}
    resp = httpx.post(settings.graph_url, headers=_headers(), json=payload, timeout=30)
    if resp.status_code >= 400:
        log.error("Error enviando imagen a %s: %s %s", to, resp.status_code, resp.text)
    resp.raise_for_status()
    return resp.json()


def send_images(to: str, links: list[str], caption: str | None = None) -> None:
    """Envía varias fotos: la primera lleva el caption, el resto van sin texto."""
    for i, link in enumerate(links):
        send_image(to, link, caption if i == 0 else None)


def send_template(
    to: str,
    template_name: str,
    variables: list[str] | None = None,
    lang: str | None = None,
) -> dict[str, Any]:
    """Envía una plantilla aprobada (para reabrir conversación fuera de las 24 h).
    `variables` completa los {{1}}, {{2}}, ... del cuerpo en orden."""
    to = _ar_msisdn(to)
    components = []
    if variables:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": str(v)} for v in variables],
        })
    template: dict[str, Any] = {
        "name": template_name,
        "language": {"code": lang or settings.template_lang},
    }
    if components:
        template["components"] = components
    if not settings.whatsapp_ready:
        log.info("[SIMULACIÓN] 📄 plantilla '%s' → %s vars=%s", template_name, to, variables)
        return {"simulated": True, "to": to, "template": template_name, "variables": variables}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "template", "template": template}
    resp = httpx.post(settings.graph_url, headers=_headers(), json=payload, timeout=20)
    if resp.status_code >= 400:
        log.error("Error enviando plantilla a %s: %s %s", to, resp.status_code, resp.text)
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
