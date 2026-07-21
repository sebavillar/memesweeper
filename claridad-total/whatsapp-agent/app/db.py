"""Base de datos SQLite para datos de mercado (comparables de oferta).

Un solo archivo en el disco persistente; sin servicios extra. Cuando el volumen
crezca, la interfaz se puede portar a PostgreSQL sin tocar el resto."""
from __future__ import annotations

import os
import re
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
        if "barrio_privado" not in cols:
            c.execute("ALTER TABLE comparables ADD COLUMN barrio_privado INTEGER")
        # Migración: historial de actividad. first_seen = cuándo entró a la base;
        # precio_prev/precio_cambio_at = último cambio de precio detectado.
        if "first_seen" not in cols:
            c.execute("ALTER TABLE comparables ADD COLUMN first_seen TEXT")
            c.execute("UPDATE comparables SET first_seen = fetched_at WHERE first_seen IS NULL")
        if "precio_prev" not in cols:
            c.execute("ALTER TABLE comparables ADD COLUMN precio_prev REAL")
        if "precio_cambio_at" not in cols:
            c.execute("ALTER TABLE comparables ADD COLUMN precio_cambio_at TEXT")


def upsert(rows: list[dict[str, Any]]) -> int:
    rows = [r for r in rows if r.get("listing_id")]
    if not rows:
        return 0
    init()
    placeholders = ",".join(f":{c}" for c in _COLS)
    updates = ",".join(f"{c}=excluded.{c}" for c in _COLS if c not in ("source", "listing_id"))
    # En un aviso ya existente: NO pisamos first_seen (fecha de alta), y si cambió
    # el precio en USD guardamos el anterior + la fecha del cambio.
    cambio = ("excluded.precio_usd IS NOT NULL AND comparables.precio_usd IS NOT NULL "
              "AND excluded.precio_usd <> comparables.precio_usd")
    with _conn() as c:
        c.executemany(
            f"INSERT INTO comparables ({','.join(_COLS)}, first_seen) "
            f"VALUES ({placeholders}, :fetched_at) "
            f"ON CONFLICT(source, listing_id) DO UPDATE SET {updates}, "
            f"precio_prev = CASE WHEN {cambio} THEN comparables.precio_usd ELSE comparables.precio_prev END, "
            f"precio_cambio_at = CASE WHEN {cambio} THEN excluded.fetched_at ELSE comparables.precio_cambio_at END",
            [{k: r.get(k) for k in _COLS} for r in rows],
        )
    return len(rows)


def actividad(dias: int = 30) -> dict[str, Any]:
    """Resumen día por día de la base: avisos nuevos (por first_seen) por fuente,
    cambios de precio, y stock activo visto ese día. Para el tablero de actividad."""
    init()
    with _conn() as c:
        nuevos = c.execute(
            "SELECT substr(first_seen,1,10) d, source, COUNT(*) n FROM comparables "
            "WHERE first_seen IS NOT NULL GROUP BY d, source").fetchall()
        cambios = c.execute(
            "SELECT substr(precio_cambio_at,1,10) d, COUNT(*) n FROM comparables "
            "WHERE precio_cambio_at IS NOT NULL GROUP BY d").fetchall()
        vistos = c.execute(
            "SELECT substr(fetched_at,1,10) d, COUNT(*) n FROM comparables "
            "WHERE fetched_at IS NOT NULL GROUP BY d").fetchall()
    dnuevos: dict[str, dict[str, int]] = {}
    for r in nuevos:
        dnuevos.setdefault(r["d"], {})[r["source"]] = r["n"]
    dcambios = {r["d"]: r["n"] for r in cambios}
    dvistos = {r["d"]: r["n"] for r in vistos}
    fechas = sorted(set(dnuevos) | set(dcambios) | set(dvistos), reverse=True)[:dias]
    return {"dias": [{
        "fecha": f,
        "nuevos": sum(dnuevos.get(f, {}).values()),
        "por_fuente": dnuevos.get(f, {}),
        "cambios_precio": dcambios.get(f, 0),
        "vistos": dvistos.get(f, 0),
    } for f in fechas]}


def query(tipo: str | None = None, departamento: str | None = None,
          operacion: str = "venta", solo_con_m2: bool = False,
          limit: int | None = 8) -> list[dict[str, Any]]:
    """Comparables filtrados. Orden DETERMINISTA (fecha, fuente, id) para que el
    resultado no cambie entre llamadas cuando hay muchos avisos con la misma
    marca de tiempo (p. ej. una carga masiva de una fuente). limit=None = sin tope."""
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
    # Desempate por source+listing_id: sin esto, los avisos con igual fetched_at
    # salen en orden físico arbitrario y el "top N" varía entre consultas.
    q += " ORDER BY fetched_at DESC, source, listing_id"
    if limit is not None:
        q += " LIMIT ?"
        args.append(limit)
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


# Señales de barrio privado / cerrado en Mendoza (títulos y fichas).
_RE_PRIVADO = re.compile(
    r"barrio\s+(privado|cerrado)|b[°ºo]\.?\s*privado|club\s+de\s+campo|"
    r"\bcountry\b|condominio\s+(privado|cerrado)|barrio\s+priv\.", re.I)


def es_privado(texto: str) -> bool:
    return bool(_RE_PRIVADO.search(texto or ""))


def marcar_privados() -> int:
    """Marca barrio_privado (1/0) según título + barrio en los avisos que aún no
    fueron evaluados. Retroactivo para toda la base y automático para los nuevos.
    La visita a la ficha (enrich) puede subir un 0 → 1 si la descripción lo dice."""
    init()
    with _conn() as c:
        rows = c.execute("SELECT source, listing_id, titulo, barrio FROM comparables "
                         "WHERE barrio_privado IS NULL").fetchall()
        updates = []
        marcados = 0
        for r in rows:
            v = 1 if es_privado(f"{r['titulo'] or ''} {r['barrio'] or ''}") else 0
            marcados += v
            updates.append((v, r["source"], r["listing_id"]))
        c.executemany("UPDATE comparables SET barrio_privado = ? WHERE source = ? AND listing_id = ?",
                      updates)
    return marcados


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


def set_details_bulk(filas: list[tuple[str, str, float | None, str]]) -> int:
    """Guarda antigüedad + detail_at para muchos avisos de una (una sola conexión).
    `filas` = [(source, listing_id, antiguedad, when), ...]. Usado por fuentes que
    ya traen la antigüedad en el listado (p. ej. InmoUp), para no visitar fichas."""
    filas = [f for f in filas if f[1]]
    if not filas:
        return 0
    with _conn() as c:
        c.executemany(
            "UPDATE comparables SET antiguedad = ?, detail_at = ? "
            "WHERE source = ? AND listing_id = ?",
            [(ant, when, src, lid) for (src, lid, ant, when) in filas],
        )
    return len(filas)


def set_detail(source: str, listing_id: str, antiguedad: float | None, when: str,
               privado: bool | None = None) -> None:
    """Registra el resultado de visitar la ficha (aunque no haya dato, para no
    reintentar). Si la ficha menciona barrio privado, sube la marca a 1 (nunca
    baja un 1 puesto por el título)."""
    with _conn() as c:
        if privado:
            c.execute("UPDATE comparables SET antiguedad = ?, detail_at = ?, barrio_privado = 1 "
                      "WHERE source = ? AND listing_id = ?", (antiguedad, when, source, listing_id))
        else:
            c.execute("UPDATE comparables SET antiguedad = ?, detail_at = ? "
                      "WHERE source = ? AND listing_id = ?", (antiguedad, when, source, listing_id))


def stats() -> dict[str, Any]:
    init()
    with _conn() as c:
        r = c.execute(
            "SELECT COUNT(*) n, MAX(fetched_at) last, "
            "SUM(CASE WHEN operacion='venta' AND precio_usd>0 THEN 1 ELSE 0 END) venta "
            "FROM comparables"
        ).fetchone()
        return {"total": r["n"] or 0, "venta_usd": r["venta"] or 0, "last_fetch": r["last"]}
