#!/usr/bin/env python3
"""Trae comparables de venta de MendozaProp (API JSON) y los guarda en la base.

Uso:
    docker compose exec app python -m scripts.fetch_mendozaprop [paginas]

La primera vez imprime un DIAGNÓSTICO con el primer aviso parseado; pegá la
salida si hay que recalibrar el mapeo."""
from __future__ import annotations

import json
import logging
import sys

from app import mendozaprop
from app.db import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> int:
    pag = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 25
    try:
        res = mendozaprop.scrape(max_pages=pag)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1
    s = stats()
    print(f"OK · guardados ahora: {res['guardados']} (venta USD: {res['venta_usd']})")
    print(f"Base total: {s['total']} comparables · última actualización: {s['last_fetch']}")
    print("\n=== DIAGNÓSTICO ===")
    print(json.dumps(res["diagnostico"], ensure_ascii=False, indent=2)[:3500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
