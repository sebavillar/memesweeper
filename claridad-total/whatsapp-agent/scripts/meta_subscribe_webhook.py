#!/usr/bin/env python3
"""Suscribe la app al webhook de la WABA (para recibir mensajes).

Equivale a: POST /{WABA_ID}/subscribed_apps
Requiere en .env: WHATSAPP_ACCESS_TOKEN, WHATSAPP_BUSINESS_ACCOUNT_ID.

Uso:  python -m scripts.meta_subscribe_webhook
"""
from __future__ import annotations

import sys

import httpx

from app.config import settings


def main() -> int:
    if not (settings.whatsapp_access_token and settings.whatsapp_business_account_id):
        print("Falta WHATSAPP_ACCESS_TOKEN o WHATSAPP_BUSINESS_ACCOUNT_ID en .env")
        return 1
    url = f"{settings.graph_base}/{settings.whatsapp_business_account_id}/subscribed_apps"
    resp = httpx.post(url, headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"}, timeout=20)
    print(resp.status_code, resp.text)
    return 0 if resp.status_code < 400 else 1


if __name__ == "__main__":
    sys.exit(main())
