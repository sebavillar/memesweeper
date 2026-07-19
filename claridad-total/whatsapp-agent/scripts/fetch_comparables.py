#!/usr/bin/env python3
"""Trae comparables de oferta (web pública de MercadoLibre) y los guarda en la base.

Uso:
    docker compose exec app python -m scripts.fetch_comparables [paginas]

La primera vez imprime un DIAGNÓSTICO de calibración (qué encontró en la página);
pegá esa salida para afinar los selectores. Pensado para correr manual o por cron."""
from __future__ import annotations

import json
import logging
import sys

from app import scraper
from app.db import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> int:
    paginas = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 6
    try:
        res = scraper.scrape(max_pages=paginas)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1

    s = stats()
    print(f"OK · guardados ahora: {res['guardados']} (venta USD: {res['venta_usd']})")
    print(f"Base total: {s['total']} comparables · última actualización: {s['last_fetch']}")
    print("\n=== DIAGNÓSTICO (pegá esto para calibrar) ===")
    print(json.dumps(res["diagnostico"], ensure_ascii=False, indent=2)[:3500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
