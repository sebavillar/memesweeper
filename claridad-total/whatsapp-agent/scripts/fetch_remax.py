#!/usr/bin/env python3
"""Trae comparables de oferta de RE/MAX (API JSON) y los guarda en la base.

Requisito: definir REMAX_API_URL en el .env (ver app/remax.py para cómo obtenerla
desde DevTools del navegador, es 1 sola vez).

Uso:
    docker compose exec app python -m scripts.fetch_remax [paginas]

La primera vez imprime un DIAGNÓSTICO con el PRIMER ITEM CRUDO del JSON; pegá esa
salida y afinamos el mapeo de campos (precio, m², zona, etc.) con precisión."""
from __future__ import annotations

import json
import logging
import sys

from app import remax
from app.db import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> int:
    paginas = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4
    try:
        res = remax.scrape(max_pages=paginas)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1

    if res.get("error"):
        print(f"⚠️  {res['error']}")
        return 2

    s = stats()
    print(f"OK · guardados ahora: {res['guardados']} (venta USD: {res['venta_usd']})")
    print(f"Base total: {s['total']} comparables · última actualización: {s['last_fetch']}")
    print("\n=== DIAGNÓSTICO · PRIMER ITEM CRUDO (pegá esto para calibrar el mapeo) ===")
    print(json.dumps(res["diagnostico"], ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
