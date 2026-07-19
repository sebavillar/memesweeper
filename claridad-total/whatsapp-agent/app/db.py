"""Base de datos SQLite para datos de mercado (comparables de oferta).

Un solo archivo en el disco persistente; sin servicios extra. Cuando el volumen
crezca, la interfaz se puede portar a PostgreSQL sin tocar el resto."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

_DB = Path(os.environ.get("DATA_DIR") or "data") / "market.db"

_COLS = [
    "source", "listing_id", "titulo", "url", "operacion", "tipo",
    "precio", "moneda", "precio_usd", "m2_cubierta", "m2_total",
    "ambientes", "dormitorios", "provincia", "departamento", "barrio",
    "lat", "lon", "fetched_at",
]


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(_DB, timeout=15)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS comparables (
                source TEXT, listing_id TEXT, titulo TEXT, url TEXT,
                operacion TEXT, tipo TEXT,
                precio REAL, moneda TEXT, precio_usd REAL,
                m2_cubierta REAL, m2_total REAL, ambientes INTEGER, dormitorios INTEGER,
                provincia TEXT, departamento TEXT, barrio TEXT,
                lat REAL, lon REAL, fetched_at TEXT,
                PRIMARY KEY (source, listing_id))"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS ix_comp_zona ON comparables(tipo, departamento, operacion)")
        # Migración: enriquecimiento por ficha (antigüedad). detail_at marca que la
        # ficha ya fue visitada (con o sin dato) para no repetir pedidos.
        cols = {r["name"] for r in c.execute("PRAGMA table_info(comparables)")}
        if "antiguedad" not in cols:
            c.execute("ALTER TABLE comparables ADD COLUMN antiguedad REAL")
        if "detail_at" not in cols:
            c.execute("ALTER TABLE comparables ADD COLUMN detail_at TEXT")


def upsert(rows: list[dict[str, Any]]) -> int:
    rows = [r for r in rows if r.get("listing_id")]
    if not rows:
        return 0
    init()
    placeholders = ",".join(f":{c}" for c in _COLS)
    updates = ",".join(f"{c}=excluded.{c}" for c in _COLS if c not in ("source", "listing_id"))
    with _conn() as c:
        c.executemany(
            f"INSERT INTO comparables ({','.join(_COLS)}) VALUES ({placeholders}) "
            f"ON CONFLICT(source, listing_id) DO UPDATE SET {updates}",
            [{k: r.get(k) for k in _COLS} for r in rows],
        )
    return len(rows)


def query(tipo: str | None = None, departamento: str | None = None,
          operacion: str = "venta", solo_con_m2: bool = False, limit: int = 8) -> list[dict[str, Any]]:
    init()
    q = "SELECT * FROM comparables WHERE precio_usd > 0"
    args: list[Any] = []
    if operacion:
        q += " AND operacion = ?"
        args.append(operacion)
    if tipo:
        q += " AND tipo = ?"
        args.append(tipo)
    if departamento:
        q += " AND (departamento LIKE ? OR barrio LIKE ?)"
        args += [f"%{departamento}%", f"%{departamento}%"]
    if solo_con_m2:
        q += " AND m2_cubierta > 0"
    q += " ORDER BY fetched_at DESC LIMIT ?"
    args.append(limit)
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def pending_detail(source: str | None = None, limit: int = 60) -> list[dict[str, Any]]:
    """Avisos cuya ficha todavía no se visitó (para enriquecer antigüedad).
    Los más recientes primero: los avisos nuevos del día entran antes."""
    init()
    q = "SELECT source, listing_id, url FROM comparables WHERE detail_at IS NULL AND url IS NOT NULL"
    args: list[Any] = []
    if source:
        q += " AND source = ?"
        args.append(source)
    q += " ORDER BY fetched_at DESC LIMIT ?"
    args.append(limit)
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def set_detail(source: str, listing_id: str, antiguedad: float | None, when: str) -> None:
    """Registra el resultado de visitar la ficha (aunque no haya dato, para no reintentar)."""
    with _conn() as c:
        c.execute("UPDATE comparables SET antiguedad = ?, detail_at = ? WHERE source = ? AND listing_id = ?",
                  (antiguedad, when, source, listing_id))


def stats() -> dict[str, Any]:
    init()
    with _conn() as c:
        r = c.execute(
            "SELECT COUNT(*) n, MAX(fetched_at) last, "
            "SUM(CASE WHEN operacion='venta' AND precio_usd>0 THEN 1 ELSE 0 END) venta "
            "FROM comparables"
        ).fetchone()
        return {"total": r["n"] or 0, "venta_usd": r["venta"] or 0, "last_fetch": r["last"]}
