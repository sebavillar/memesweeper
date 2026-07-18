#!/usr/bin/env python3
"""Trae la oferta real de Mendoza desde MercadoLibre y la guarda en la base.

Uso:
    docker compose exec app python -m scripts.fetch_comparables [cantidad]

Requiere en .env: MELI_CLIENT_ID + MELI_CLIENT_SECRET (o MELI_ACCESS_TOKEN).
Pensado para correr manualmente o por cron (ej. una vez por día)."""
from __future__ import annotations

import logging
import sys

from app import meli
from app.db import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
    try:
        res = meli.fetch(max_items=n)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1
    s = stats()
    print(f"OK · guardados ahora: {res['guardados']} (venta USD: {res['venta_usd']})")
    print(f"Base total: {s['total']} comparables · última actualización: {s['last_fetch']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
