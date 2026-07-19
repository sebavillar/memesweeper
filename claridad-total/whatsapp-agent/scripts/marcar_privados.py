#!/usr/bin/env python3
"""Marca los avisos en BARRIO PRIVADO a partir del título/barrio ya guardados.

Uso:
    docker compose exec app python -m scripts.marcar_privados

Corre en segundos (sin pedidos a internet): recorre la base entera una vez y
deja la marca. Después, el ciclo diario mantiene la señal para los avisos
nuevos, y la visita a fichas (antigüedad) la refina con la descripción."""
from __future__ import annotations

import sqlite3

from app import db


def main() -> int:
    nuevos = db.marcar_privados()
    with db._conn() as c:  # noqa: SLF001
        c.row_factory = sqlite3.Row
        tot = c.execute("SELECT COUNT(*) FROM comparables WHERE barrio_privado = 1").fetchone()[0]
        por_fuente = c.execute(
            "SELECT source, COUNT(*) n FROM comparables WHERE barrio_privado = 1 "
            "GROUP BY source ORDER BY n DESC").fetchall()
        muestra = c.execute(
            "SELECT titulo FROM comparables WHERE barrio_privado = 1 LIMIT 5").fetchall()
    print(f"OK · en barrio privado: {tot} avisos (evaluados ahora: {nuevos})")
    for r in por_fuente:
        print(f"  {r['source']:14} {r['n']}")
    print("Ejemplos:")
    for r in muestra:
        print(f"  - {(r['titulo'] or '')[:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
