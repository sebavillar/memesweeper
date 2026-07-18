#!/usr/bin/env python3
"""Crea (envía a aprobación) las plantillas de `meta/templates.py`.

Equivale a: POST /{WABA_ID}/message_templates  por cada plantilla.
Requiere en .env: WHATSAPP_ACCESS_TOKEN, WHATSAPP_BUSINESS_ACCOUNT_ID.

Uso:  python -m scripts.meta_create_templates
Las plantillas quedan 'PENDING' hasta que Meta las aprueba (suele ser rápido).
"""
from __future__ import annotations

import sys

import httpx

from app.config import settings
from meta.templates import TEMPLATES


def main() -> int:
    if not (settings.whatsapp_access_token and settings.whatsapp_business_account_id):
        print("Falta WHATSAPP_ACCESS_TOKEN o WHATSAPP_BUSINESS_ACCOUNT_ID en .env")
        return 1
    url = f"{settings.graph_base}/{settings.whatsapp_business_account_id}/message_templates"
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}",
               "Content-Type": "application/json"}
    rc = 0
    for tpl in TEMPLATES:
        resp = httpx.post(url, headers=headers, json=tpl, timeout=20)
        estado = "OK" if resp.status_code < 400 else "ERROR"
        print(f"[{estado}] {tpl['name']} ({tpl['category']}) -> {resp.status_code} {resp.text}")
        if resp.status_code >= 400:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
