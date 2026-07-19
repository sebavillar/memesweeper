#!/usr/bin/env python3
"""Enriquece comparables con la ANTIGÜEDAD leída de la ficha de cada aviso.

Uso:
    docker compose exec app python -m scripts.enrich_details [por_fuente]

Visita hasta N fichas pendientes por fuente (default 60), con pausas. Imprime un
diagnóstico por fuente; si alguna sale con "sin_dato" alto, pegá la salida y se
recalibra la extracción."""
from __future__ import annotations

import json
import logging
import sys

from app import enrich

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> int:
    por_fuente = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 60
    try:
        res = enrich.run(per_source=por_fuente)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1

    for src, d in res["fuentes"].items():
        print(f"{src:14} visitadas={d['visitadas']:3}  con_dato={d['con_dato']:3}  "
              f"sin_dato={d['sin_dato']:3}  errores={d['errores']}")
    print("\n=== DIAGNÓSTICO ===")
    print(json.dumps(res, ensure_ascii=False, indent=2)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
