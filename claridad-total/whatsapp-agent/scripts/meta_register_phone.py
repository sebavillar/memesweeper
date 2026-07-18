#!/usr/bin/env python3
"""Registra el número en la Cloud API (paso obligatorio antes de enviar).

Equivale a: POST /{PHONE_NUMBER_ID}/register  con un PIN de verificación en dos
pasos de 6 dígitos (lo elegís vos; si el número ya tenía uno, usá ese).

Uso:  python -m scripts.meta_register_phone 123456
"""
from __future__ import annotations

import sys

import httpx

from app.config import settings


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python -m scripts.meta_register_phone <PIN_6_DIGITOS>")
        return 1
    pin = sys.argv[1]
    if not (settings.whatsapp_access_token and settings.whatsapp_phone_number_id):
        print("Falta WHATSAPP_ACCESS_TOKEN o WHATSAPP_PHONE_NUMBER_ID en .env")
        return 1
    url = f"{settings.graph_base}/{settings.whatsapp_phone_number_id}/register"
    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        json={"messaging_product": "whatsapp", "pin": pin},
        timeout=20,
    )
    print(resp.status_code, resp.text)
    return 0 if resp.status_code < 400 else 1


if __name__ == "__main__":
    sys.exit(main())
