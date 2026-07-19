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
    privado: str | None = None,
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
        if privado == "si" and r.get("barrio_privado") != 1:
            continue
        if privado == "no" and r.get("barrio_privado") == 1:
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
    privado: str | None = Query(None),
) -> dict[str, Any]:
    return {"depto": depto, "tipo": tipo, "fuente": fuente, "usd_min": usd_min,
            "usd_max": usd_max, "m2_min": m2_min, "m2_max": m2_max, "privado": privado}


@router.get("/market/filters")
def market_filters() -> dict[str, Any]:
    """Valores disponibles para armar los selectores del panel."""
    rows = _rows()
    deptos: dict[str, int] = {}
    tipos: dict[str, int] = {}
    fuentes: dict[str, int] = {}
    fuentes_last: dict[str, str] = {}
    for r in rows:
        if r["depto_norm"]:
            deptos[r["depto_norm"]] = deptos.get(r["depto_norm"], 0) + 1
        if r.get("tipo"):
            tipos[r["tipo"]] = tipos.get(r["tipo"], 0) + 1
        fuentes[r["source"]] = fuentes.get(r["source"], 0) + 1
        ft = r.get("fetched_at") or ""
        if ft > fuentes_last.get(r["source"], ""):
            fuentes_last[r["source"]] = ft
    st = db.stats()
    return {
        "departamentos": [{"nombre": k, "n": v} for k, v in sorted(deptos.items(), key=lambda x: -x[1])],
        "tipos": [{"nombre": k, "n": v} for k, v in sorted(tipos.items(), key=lambda x: -x[1])],
        "fuentes": [{"nombre": k, "n": v} for k, v in sorted(fuentes.items(), key=lambda x: -x[1])],
        "privados": sum(1 for r in rows if r.get("barrio_privado") == 1),
        "fuentes_last": fuentes_last,
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
                     field: str = Query("precio_usd"),
                     f: dict[str, Any] = Depends(_filtros_qs)) -> dict[str, Any]:
    """Distribución en buckets para histogramas.
    field=precio_usd → precios (USD) · field=ppm → precio por m² (USD/m²)."""
    if field not in ("precio_usd", "ppm"):
        raise HTTPException(400, "field debe ser precio_usd|ppm")
    if field == "ppm":
        # rango sano de USD/m² (descarta errores de carga tipo 45 USD/m² por m² de finca)
        precios = sorted(r["ppm"] for r in _rows(**f)
                         if r.get("ppm") and 100 <= r["ppm"] <= 20000)
    else:
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


_BANDAS_EDAD = [(0, 0, "A estrenar"), (1, 5, "1–5"), (6, 10, "6–10"), (11, 20, "11–20"),
                (21, 30, "21–30"), (31, 50, "31–50"), (51, 100, "50+")]


@router.get("/market/age")
def market_age(f: dict[str, Any] = Depends(_filtros_qs)) -> dict[str, Any]:
    """Relación precio por m² vs antigüedad: puntos individuales + mediana por
    banda de edad. Solo avisos ya enriquecidos con antigüedad (crece a diario)."""
    pts = []
    for r in _rows(**f):
        edad = r.get("antiguedad")
        if edad is None or not r.get("ppm") or not (100 <= r["ppm"] <= 20000) or edad > 100:
            continue
        pts.append({"edad": edad, "ppm": r["ppm"], "tipo": r.get("tipo"), "depto": r["depto_norm"]})
    bandas = []
    for lo, hi, label in _BANDAS_EDAD:
        vals = [p["ppm"] for p in pts if lo <= p["edad"] <= hi]
        if len(vals) >= 3:
            bandas.append({"banda": label, "edad": round((lo + hi) / 2),
                           "n": len(vals), "ppm": round(statistics.median(vals))})
    return {"points": pts[:800], "bandas": bandas, "n": len(pts)}


@router.get("/market/privado_gap")
def market_privado_gap(f: dict[str, Any] = Depends(_filtros_qs)) -> dict[str, Any]:
    """Diferencial de precio por m²: barrio privado vs abierto (mediana), global
    y por departamento (solo donde ambos lados tienen muestra >=5)."""
    rows = [r for r in _rows(**f) if r.get("ppm") and 100 <= r["ppm"] <= 20000]

    def _med(vals: list[float]) -> int | None:
        return round(statistics.median(vals)) if vals else None

    def _split(rs: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
        return ([r["ppm"] for r in rs if r.get("barrio_privado") == 1],
                [r["ppm"] for r in rs if r.get("barrio_privado") != 1])

    def _gap(p: int | None, a: int | None) -> int | None:
        return round((p - a) / a * 100) if p and a else None

    priv, ab = _split(rows)
    global_ = {"ppm_privado": _med(priv), "ppm_abierto": _med(ab),
               "n_privado": len(priv), "n_abierto": len(ab),
               "gap_pct": _gap(_med(priv), _med(ab))}

    grupos: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r["depto_norm"]:
            grupos.setdefault(r["depto_norm"], []).append(r)
    por_depto = []
    for g, rs in grupos.items():
        p, a = _split(rs)
        if len(p) >= 5 and len(a) >= 5:
            por_depto.append({"grupo": g, "ppm_privado": _med(p), "ppm_abierto": _med(a),
                              "n_privado": len(p), "n_abierto": len(a),
                              "gap_pct": _gap(_med(p), _med(a))})
    por_depto.sort(key=lambda x: -(x["n_privado"] + x["n_abierto"]))
    return {"global": global_, "por_depto": por_depto}


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
                                       "dormitorios", "antiguedad", "barrio_privado",
                                       "depto_norm", "fetched_at")}
                for r in rows[ini:ini + page_size]]
    return {"total": len(rows), "page": page, "page_size": page_size, "rows": visibles}


# ─────────────────────────── Consultas (leads del bot) ───────────────────────
_TEMP_ORDER = {"caliente": 0, "tibio": 1, "frio": 2}


def _lead_view(l: dict[str, Any]) -> dict[str, Any]:
    wa = l.get("wa_id") or ""
    ult = store.last_message(wa) if wa else None
    return {
        "wa_id": wa,
        "nombre": l.get("nombre"),
        "telefono": l.get("telefono") or wa,
        "wa_link": f"https://wa.me/{wa}" if wa else None,
        "temperatura": l.get("temperatura") or "frio",
        "score": l.get("score") or 0,
        "presupuesto_usd": l.get("presupuesto_usd"),
        "zona": l.get("zona"),
        "tipo": l.get("tipo"),
        "ambientes": l.get("ambientes"),
        "urgencia": l.get("urgencia"),
        "necesita_credito": l.get("necesita_credito"),
        "handoff": bool(l.get("handoff")),
        "handoff_motivo": l.get("handoff_motivo"),
        "visita_agendada": bool(l.get("visita_agendada")),
        "mensajes": l.get("mensajes") or 0,
        "creado": l.get("creado"),
        "actualizado": l.get("actualizado"),
        "ultimo_mensaje": ult,
    }


@router.get("/leads")
def leads_list() -> list[dict[str, Any]]:
    leads = [_lead_view(l) for l in store.list_leads()]
    # Orden: por actividad reciente; a igualdad, por score.
    leads.sort(key=lambda x: (x.get("actualizado") or "", x.get("score") or 0), reverse=True)
    return leads


@router.get("/leads/summary")
def leads_summary() -> dict[str, Any]:
    leads = store.list_leads()
    visitas = store.list_visitas()
    return {
        "total": len(leads),
        "calientes": sum(1 for l in leads if l.get("temperatura") == "caliente"),
        "tibios": sum(1 for l in leads if l.get("temperatura") == "tibio"),
        "handoffs": sum(1 for l in leads if l.get("handoff")),
        "con_visita": sum(1 for l in leads if l.get("visita_agendada")),
        "visitas": len(visitas),
    }


@router.get("/visitas")
def visitas_list() -> list[dict[str, Any]]:
    vs = list(store.list_visitas())
    vs.sort(key=lambda v: v.get("creada") or "", reverse=True)
    return vs


@router.get("/leads/{wa_id}")
def lead_detail(wa_id: str) -> dict[str, Any]:
    lead = next((l for l in store.list_leads() if l.get("wa_id") == wa_id), None)
    if not lead:
        raise HTTPException(404, "no existe esa consulta")
    visitas = [v for v in store.list_visitas() if v.get("wa_id") == wa_id]
    return {"lead": _lead_view(lead), "conversacion": store.transcript(wa_id), "visitas": visitas}


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
