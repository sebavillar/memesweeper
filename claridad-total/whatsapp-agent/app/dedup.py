"""Deduplicación de avisos repetidos entre portales.

Una misma propiedad suele publicarse en varios portales a la vez (MercadoLibre +
Argenprop + Inmoclick…), cada uno con su propio (source, listing_id). Para los
conteos y las medianas de precio/m² eso la contaría 2 o 3 veces e inflaría el
mercado (y sesgaría la mediana hacia lo que más se repostea). Acá agrupamos los
avisos que son —casi con certeza— la misma unidad y elegimos UN representante por
grupo. No se borra nada de la base: cada portal conserva su fila y su URL.

Criterio deliberadamente CONSERVADOR (ante la duda, NO se fusiona): mismo tipo,
mismo departamento canónico, mismo precio en USD (±1%) y, además, tamaño
compatible: m² parecidos (±3% o ±2 m²) o dormitorios que coinciden. Con solo el
precio no alcanza (dos deptos distintos pueden costar lo mismo). Así juntamos
reposteos entre portales sin colapsar propiedades genuinamente distintas.
"""
from __future__ import annotations

from typing import Any, Callable

# Tolerancias del "mismo aviso en otro portal".
_PRECIO_TOL = 0.01   # ±1% en el precio USD (los reposteos suelen ser idénticos)
_M2_TOL_REL = 0.03   # ±3% en m²…
_M2_TOL_ABS = 2.0    # …o ±2 m² (lo que sea mayor), tolera redondeos de carga


def _m2(r: dict[str, Any]) -> float | None:
    return r.get("m2_cubierta") or r.get("m2_total")


def _similar(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """¿a y b son (casi con certeza) la misma propiedad publicada dos veces?
    Asume que ya comparten tipo y departamento canónico (se agrupa por eso antes)."""
    pa, pb = a.get("precio_usd"), b.get("precio_usd")
    if not (pa and pb):
        return False  # sin precio en ambos no arriesgamos una fusión
    if abs(pa - pb) > _PRECIO_TOL * max(pa, pb):
        return False

    ma, mb = _m2(a), _m2(b)
    da, db_ = a.get("dormitorios"), b.get("dormitorios")

    # m² incompatibles ⇒ no es el mismo inmueble (aunque el precio coincida).
    if ma and mb and abs(ma - mb) > max(_M2_TOL_ABS, _M2_TOL_REL * max(ma, mb)):
        return False
    # dormitorios que se contradicen (ambos presentes y distintos) ⇒ no.
    if da is not None and db_ is not None and da != db_:
        return False

    # El precio por sí solo es señal débil: exigimos al menos UNA coincidencia de
    # tamaño real (m² en ambos, o dormitorios en ambos). Si a los dos les falta
    # todo dato de tamaño, no fusionamos.
    tiene_m2 = bool(ma and mb)
    tiene_dorm = da is not None and db_ is not None
    return tiene_m2 or tiene_dorm


def _rank(r: dict[str, Any]) -> tuple:
    """Representante del grupo: preferimos el registro MÁS RICO (con m², con
    antigüedad) y, a igualdad, el más reciente. Así las stats conservan m²/edad."""
    return (
        1 if _m2(r) else 0,
        1 if r.get("antiguedad") is not None else 0,
        r.get("fetched_at") or "",
    )


def clusters(rows: list[dict[str, Any]],
             depto_of: Callable[[dict[str, Any]], str | None]) -> list[list[dict[str, Any]]]:
    """Agrupa filas en clusters de duplicados. `depto_of(row)` devuelve el
    departamento canónico (se inyecta para no acoplar este módulo a zonas)."""
    # Agrupamos primero por (tipo, depto): dos avisos solo pueden ser el mismo si
    # comparten ambos. Reduce el O(n²) a comparar dentro de cada zona/tipo.
    grupos: dict[tuple, list[int]] = {}
    for i, r in enumerate(rows):
        clave = ((r.get("tipo") or ""), depto_of(r) or "")
        grupos.setdefault(clave, []).append(i)

    parent = list(range(len(rows)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for idxs in grupos.values():
        for ai in range(len(idxs)):
            for bi in range(ai + 1, len(idxs)):
                i, j = idxs[ai], idxs[bi]
                if _similar(rows[i], rows[j]):
                    union(i, j)

    salida: dict[int, list[dict[str, Any]]] = {}
    for i in range(len(rows)):
        salida.setdefault(find(i), []).append(rows[i])
    return list(salida.values())


def dedupe(rows: list[dict[str, Any]],
           depto_of: Callable[[dict[str, Any]], str | None]) -> list[dict[str, Any]]:
    """Devuelve un aviso por propiedad (el representante de cada cluster), anotado
    con dup_count (cuántos avisos lo componen) y dup_sources (en qué portales)."""
    out: list[dict[str, Any]] = []
    for grupo in clusters(rows, depto_of):
        rep = dict(max(grupo, key=_rank))
        rep["dup_count"] = len(grupo)
        rep["dup_sources"] = sorted({g.get("source") for g in grupo if g.get("source")})
        out.append(rep)
    return out
