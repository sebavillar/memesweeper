"""API JSON para el panel web (Next.js): analítica de mercado + inventario.

Prefijo /api/v1. Autenticación: HTTP Basic con la misma clave del panel
(PANEL_PASSWORD); el frontend la manda server-side por la red interna de Docker.

Los datos vienen de la base de comparables (MercadoLibre + RE/MAX + Inmoclick).
Como los departamentos llegan escritos distinto según la fuente ("Villa Marini,
Godoy Cruz", "Godoy Cruz", "Lujan de Cuyo"...), acá se normalizan a los
departamentos oficiales de Mendoza para poder agrupar y filtrar con sentido."""
from __future__ import annotations

import statistics
import unicodedata
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from . import analysis, db, inventory, store
from .panel import _auth  # misma autenticación que el panel clásico

router = APIRouter(prefix="/api/v1", dependencies=[Depends(_auth)])

# Departamentos oficiales de Mendoza (clave normalizada → nombre para mostrar).
_DEPTOS = {
    "capital": "Capital", "ciudad de mendoza": "Capital", "ciudad": "Capital",
    "godoy cruz": "Godoy Cruz", "guaymallen": "Guaymallén", "las heras": "Las Heras",
    "maipu": "Maipú", "lujan de cuyo": "Luján de Cuyo", "lujan": "Luján de Cuyo",
    "chacras de coria": "Luján de Cuyo", "lavalle": "Lavalle",
    "san martin": "San Martín", "junin": "Junín", "rivadavia": "Rivadavia",
    "santa rosa": "Santa Rosa", "la paz": "La Paz", "tupungato": "Tupungato",
    "tunuyan": "Tunuyán", "san carlos": "San Carlos", "san rafael": "San Rafael",
    "general alvear": "General Alvear", "malargue": "Malargüe",
}
# Orden de matcheo: claves más largas primero ("lujan de cuyo" antes que "lujan").
_DEPTO_KEYS = sorted(_DEPTOS, key=len, reverse=True)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def _depto_de(row: dict[str, Any]) -> str | None:
    texto = _norm(f"{row.get('departamento') or ''} {row.get('barrio') or ''} {row.get('titulo') or ''}")
    for k in _DEPTO_KEYS:
        if k in texto:
            return _DEPTOS[k]
    return None


def _rows(
    depto: str | None = None,
    tipo: str | None = None,
    fuente: str | None = None,
    usd_min: float | None = None,
    usd_max: float | None = None,
    m2_min: float | None = None,
    m2_max: float | None = None,
    solo_usd: bool = True,
) -> list[dict[str, Any]]:
    """Carga los comparables en venta y aplica filtros en memoria (la base es
    chica; cuando crezca, esto baja a SQL sin cambiar la interfaz)."""
    db.init()
    with db._conn() as c:  # noqa: SLF001 - módulo hermano
        raw = [dict(r) for r in c.execute(
            "SELECT * FROM comparables WHERE operacion='venta'").fetchall()]

    out = []
    for r in raw:
        r["depto_norm"] = _depto_de(r)
        m2 = r.get("m2_cubierta") or r.get("m2_total")
        usd = r.get("precio_usd")
        r["ppm"] = round(usd / m2) if usd and m2 else None
        if solo_usd and not usd:
            continue
        if depto and r["depto_norm"] != depto:
            continue
        if tipo and (r.get("tipo") or "") != tipo:
            continue
        if fuente and r.get("source") != fuente:
            continue
        if usd_min is not None and (usd or 0) < usd_min:
            continue
        if usd_max is not None and (usd or 0) > usd_max:
            continue
        if m2_min is not None and not (m2 and m2 >= m2_min):
            continue
        if m2_max is not None and not (m2 and m2 <= m2_max):
            continue
        out.append(r)
    return out


def _mediana(vals: list[float]) -> float | None:
    return round(statistics.median(vals)) if vals else None


def _stats_de(rows: list[dict[str, Any]]) -> dict[str, Any]:
    precios = [r["precio_usd"] for r in rows if r.get("precio_usd")]
    ppms = [r["ppm"] for r in rows if r.get("ppm") and 100 <= r["ppm"] <= 20000]
    q = statistics.quantiles(ppms, n=4) if len(ppms) >= 4 else None
    return {
        "n": len(rows),
        "mediana_usd": _mediana(precios),
        "ppm_mediano": _mediana(ppms),
        "ppm_p25": round(q[0]) if q else None,
        "ppm_p75": round(q[2]) if q else None,
        "con_m2": len(ppms),
    }


def _filtros_qs(
    depto: str | None = Query(None),
    tipo: str | None = Query(None),
    fuente: str | None = Query(None),
    usd_min: float | None = Query(None),
    usd_max: float | None = Query(None),
    m2_min: float | None = Query(None),
    m2_max: float | None = Query(None),
) -> dict[str, Any]:
    return {"depto": depto, "tipo": tipo, "fuente": fuente, "usd_min": usd_min,
            "usd_max": usd_max, "m2_min": m2_min, "m2_max": m2_max}


@router.get("/market/filters")
def market_filters() -> dict[str, Any]:
    """Valores disponibles para armar los selectores del panel."""
    rows = _rows()
    deptos: dict[str, int] = {}
    tipos: dict[str, int] = {}
    fuentes: dict[str, int] = {}
    for r in rows:
        if r["depto_norm"]:
            deptos[r["depto_norm"]] = deptos.get(r["depto_norm"], 0) + 1
        if r.get("tipo"):
            tipos[r["tipo"]] = tipos.get(r["tipo"], 0) + 1
        fuentes[r["source"]] = fuentes.get(r["source"], 0) + 1
    st = db.stats()
    return {
        "departamentos": [{"nombre": k, "n": v} for k, v in sorted(deptos.items(), key=lambda x: -x[1])],
        "tipos": [{"nombre": k, "n": v} for k, v in sorted(tipos.items(), key=lambda x: -x[1])],
        "fuentes": [{"nombre": k, "n": v} for k, v in sorted(fuentes.items(), key=lambda x: -x[1])],
        "total": st["total"], "last_fetch": st["last_fetch"],
    }


@router.get("/market/summary")
def market_summary(f: dict[str, Any] = Depends(_filtros_qs)) -> dict[str, Any]:
    return _stats_de(_rows(**f))


@router.get("/market/breakdown")
def market_breakdown(by: str = Query("departamento"),
                     f: dict[str, Any] = Depends(_filtros_qs)) -> list[dict[str, Any]]:
    """Estadísticas agrupadas por departamento, tipo o fuente."""
    if by not in ("departamento", "tipo", "fuente"):
        raise HTTPException(400, "by debe ser departamento|tipo|fuente")
    key = {"departamento": "depto_norm", "tipo": "tipo", "fuente": "source"}[by]
    grupos: dict[str, list[dict[str, Any]]] = {}
    for r in _rows(**f):
        g = r.get(key)
        if g:
            grupos.setdefault(g, []).append(r)
    out = [{"grupo": g, **_stats_de(rows)} for g, rows in grupos.items()]
    out.sort(key=lambda x: -(x["n"] or 0))
    return out


@router.get("/market/histogram")
def market_histogram(bins: int = Query(12, ge=4, le=30),
                     f: dict[str, Any] = Depends(_filtros_qs)) -> dict[str, Any]:
    """Distribución de precios (USD) en buckets para el histograma."""
    precios = sorted(r["precio_usd"] for r in _rows(**f) if r.get("precio_usd"))
    if not precios:
        return {"buckets": [], "recortados": 0}
    # Recorte al p95 para que los outliers (fincas millonarias) no aplasten el gráfico.
    corte = precios[min(len(precios) - 1, int(len(precios) * 0.95))]
    base = [p for p in precios if p <= corte]
    lo, hi = base[0], base[-1]
    ancho = max((hi - lo) / bins, 1)
    buckets = [{"desde": round(lo + i * ancho), "hasta": round(lo + (i + 1) * ancho), "n": 0}
               for i in range(bins)]
    for p in base:
        i = min(int((p - lo) / ancho), bins - 1)
        buckets[i]["n"] += 1
    return {"buckets": buckets, "recortados": len(precios) - len(base)}


@router.get("/market/scatter")
def market_scatter(limit: int = Query(600, le=2000),
                   f: dict[str, Any] = Depends(_filtros_qs)) -> list[dict[str, Any]]:
    """Puntos precio vs superficie (para dispersión). Filtra outliers obvios."""
    pts = []
    for r in _rows(**f):
        m2 = r.get("m2_cubierta") or r.get("m2_total")
        if not (r.get("precio_usd") and m2 and 10 <= m2 <= 2000 and r["precio_usd"] <= 2_000_000):
            continue
        pts.append({"m2": m2, "usd": r["precio_usd"], "tipo": r.get("tipo"),
                    "depto": r["depto_norm"], "fuente": r["source"]})
    return pts[:limit]


@router.get("/market/listings")
def market_listings(page: int = Query(1, ge=1), page_size: int = Query(25, le=100),
                    sort: str = Query("-fetched_at"),
                    f: dict[str, Any] = Depends(_filtros_qs)) -> dict[str, Any]:
    """Tabla paginada de avisos (con orden)."""
    rows = _rows(**f)
    campo = sort.lstrip("-")
    if campo not in ("precio_usd", "ppm", "m2_cubierta", "fetched_at"):
        raise HTTPException(400, "sort inválido")
    rows.sort(key=lambda r: (r.get(campo) is None, r.get(campo)), reverse=sort.startswith("-"))
    ini = (page - 1) * page_size
    visibles = [{k: r.get(k) for k in ("source", "listing_id", "titulo", "url", "tipo",
                                       "precio_usd", "m2_cubierta", "m2_total", "ppm",
                                       "dormitorios", "depto_norm", "fetched_at")}
                for r in rows[ini:ini + page_size]]
    return {"total": len(rows), "page": page, "page_size": page_size, "rows": visibles}


@router.get("/inventory")
def inventory_list() -> list[dict[str, Any]]:
    props = inventory.load()
    for p in props:
        p["stats"] = store.get_prop_stats(p["id"])
    return props


@router.get("/inventory/{prop_id}")
def inventory_detail(prop_id: str) -> dict[str, Any]:
    p = inventory.get(prop_id)
    if not p:
        raise HTTPException(404, "no existe")
    return {"prop": p, "stats": store.get_prop_stats(prop_id), "valuacion": analysis.valuar(p)}
