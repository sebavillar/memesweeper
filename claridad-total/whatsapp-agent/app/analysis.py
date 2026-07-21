"""Análisis de mercado por inmueble (primera versión).

Valuación EXPLICABLE con lógica heurística (mismo enfoque que el prototipo del
Pasaporte) + comparables tomados del propio inventario. Cada número viene con su
'porqué'. La integración real con catastro/ATM de Mendoza y el scraping en vivo de
portales se conecta en una fase posterior; la interfaz ya está preparada para eso."""
from __future__ import annotations

import statistics
import unicodedata
from typing import Any

from . import db, dedup, inventory, zonas

# USD/m² de referencia por zona (calibración de muestra Mendoza 2025).
_ZONA_M2 = {
    "quinta seccion": 1520, "ciudad de mendoza": 1260, "godoy cruz": 1150,
    "chacras de coria": 1320, "lujan de cuyo": 1300, "maipu": 960, "guaymallen": 900,
}
_DEFAULT_M2 = 1100
_GAP_CIERRE = 0.12  # los cierres cierran ~12% bajo el precio de oferta


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def _zona_m2(p: dict[str, Any]) -> tuple[int, str]:
    texto = _norm(f"{p.get('barrio','')} {p.get('departamento','')}")
    for clave, val in _ZONA_M2.items():
        if clave in texto:
            return val, clave
    return _DEFAULT_M2, _norm(p.get("departamento") or "zona")


def _comps_zona(p: dict[str, Any], solo_con_m2: bool = False, limit: int = 400) -> list[dict[str, Any]]:
    """Comparables del MISMO tipo y MISMO departamento de Mendoza que el inmueble.
    Matchea por departamento CANÓNICO (no por texto literal): así 'Capital Mendoza'
    de una propiedad matchea con 'Capital', 'Ciudad de Mendoza', etc. de los avisos."""
    tipo = (p.get("tipo") or "").lower()
    depto = zonas.de_row(p)
    if depto:  # traemos por tipo (amplio) y filtramos por depto canónico en memoria
        rows = db.query(tipo=tipo, departamento=None, operacion="venta",
                        solo_con_m2=solo_con_m2, limit=limit)
        rows = [c for c in rows if zonas.de_row(c) == depto]
    else:  # sin departamento reconocido: match textual clásico
        rows = db.query(tipo=tipo, departamento=p.get("departamento"), operacion="venta",
                        solo_con_m2=solo_con_m2, limit=limit)
    # Deduplicar reposteos entre portales: la misma unidad no debe pesar 2 o 3
    # veces en la mediana de US$/m² ni aparecer repetida en los comparables.
    return dedup.dedupe(rows, zonas.de_row)


def _market_stats(p: dict[str, Any]) -> dict[str, Any] | None:
    """USD/m² real de la oferta (todas las fuentes) para el tipo y zona del inmueble.
    Si hay muestra suficiente de comparables con antigüedad parecida (±15 años),
    calibra con esa banda: la edad mueve el precio y así se compara mejor."""
    comps = _comps_zona(p, solo_con_m2=True)
    # Si el inmueble está en barrio privado, comparar contra otros barrios privados
    # (el premium de seguridad/amenities distorsionaría la mediana general).
    banda_privado = False
    texto_p = f"{p.get('barrio', '')} {p.get('titulo', '')} {' '.join(p.get('caracteristicas') or [])}"
    if db.es_privado(texto_p):
        privados = [c for c in comps if c.get("barrio_privado") == 1]
        if len(privados) >= 5:
            comps = privados
            banda_privado = True
    banda_edad = False
    anti = p.get("antiguedad")
    if anti is not None:
        misma_edad = [c for c in comps
                      if c.get("antiguedad") is not None and abs(c["antiguedad"] - anti) <= 15]
        if len(misma_edad) >= 5:
            comps = misma_edad
            banda_edad = True
    ppms = [c["precio_usd"] / c["m2_cubierta"] for c in comps
            if c.get("m2_cubierta") and c.get("precio_usd")]
    if len(ppms) < 3:
        return None
    return {"n": len(ppms), "mediana_ppm": statistics.median(ppms),
            "banda_edad": banda_edad, "banda_privado": banda_privado}


def valuar(p: dict[str, Any]) -> dict[str, Any]:
    """Devuelve valor estimado + rango + confianza + factores + comparables."""
    m2, zona_clave = _zona_m2(p)
    cub = p.get("sup_cubierta") or 0

    # Calibración con datos reales de oferta (MercadoLibre) cuando hay muestra suficiente.
    market = _market_stats(p)
    fuente_m2 = "referencia de zona"
    if market:
        m2 = round(market["mediana_ppm"])
        fuente_m2 = f"mediana de {market['n']} publicaciones · portales (ML/RE/MAX/Inmoclick/MZaProp/InmoUp/Argenprop)"
        if market.get("banda_privado"):
            fuente_m2 += " · solo barrios privados"
        if market.get("banda_edad"):
            fuente_m2 += " · misma banda de antigüedad"

    pasos: list[dict[str, Any]] = []
    base = cub * m2
    pasos.append({"label": "Base por superficie",
                  "detalle": f"{cub} m² × US$ {m2:,}/m² · {fuente_m2}".replace(",", "."), "val": base})

    anti = p.get("antiguedad")
    if anti is not None:
        f = 0.05 if anti <= 2 else 0.0 if anti <= 10 else -0.06 if anti <= 30 else -0.12 if anti <= 50 else -0.18
        if f:
            pasos.append({"label": "Antigüedad", "detalle": f"{anti} años ({'+' if f>0 else ''}{round(f*100)}%)",
                          "val": base * f})

    carac = [_norm(c) for c in (p.get("caracteristicas") or [])]
    if p.get("cochera"):
        pasos.append({"label": "Cochera", "detalle": "valor de mercado",
                      "val": 8500 if _norm(p.get("tipo", "")) == "casa" else 6500})
    if any("pileta" in c for c in carac):
        pasos.append({"label": "Pileta", "detalle": "amenity", "val": 6000})
    if any("amenities" in c or "sum" in c for c in carac):
        pasos.append({"label": "Amenities", "detalle": "+4% s/ base", "val": base * 0.04})
    if any("luminos" in c or "piso alto" in c for c in carac):
        pasos.append({"label": "Luminosidad", "detalle": "+3% s/ base", "val": base * 0.03})

    valor = sum(s["val"] for s in pasos)

    comps = comparables(p)
    n = len(comps)
    conf = min(0.9, 0.55 + n * 0.08)
    half = valor * (0.06 + (0.09 - (conf - 0.55) * 0.05))
    low, high = valor - half, valor + half
    oferta = valor / (1 - _GAP_CIERRE) if valor else 0

    return {
        "valor": round(valor), "low": round(low), "high": round(high),
        "oferta_sugerida": round(oferta), "ppm": round(valor / cub) if cub else 0,
        "confianza": round(conf * 100), "n_comparables": n,
        "zona_m2": m2, "factores": [{**s, "val": round(s["val"])} for s in pasos],
        "comparables": comps,
        "fuentes": {"valuacion": "heurística calibrada con oferta real" if market else "heurística (estimación)",
                    "comparables": "MercadoLibre + RE/MAX + Inmoclick + MendozaProp + InmoUp + Argenprop + inventario propio",
                    "catastro": "no integrado (a pedido)"},
    }


def comparables(p: dict[str, Any], limite: int = 6) -> list[dict[str, Any]]:
    """Comparables: primero oferta real de MercadoLibre (misma zona/tipo), luego
    completamos con el inventario propio."""
    out: list[dict[str, Any]] = []

    # Priorizamos comparables CON m² (para poder mostrar US$/m²), luego el resto.
    zona_comps = _comps_zona(p, limit=200)
    zona_comps.sort(key=lambda c: (not (c.get("m2_cubierta") and c.get("precio_usd")),))
    for c in zona_comps[:limite]:
        cub = c.get("m2_cubierta") or 0
        precio = c.get("precio_usd") or 0
        out.append({"id": c.get("listing_id"), "titulo": c.get("titulo") or "Publicación",
                    "precio_usd": precio, "ppm": round(precio / cub) if cub and precio else 0,
                    "estado": "oferta", "source": c.get("source") or "mercadolibre", "url": c.get("url")})

    _, zona = _zona_m2(p)
    for q in inventory.load():
        if len(out) >= limite:
            break
        if q.get("id") == p.get("id") or _norm(q.get("tipo", "")) != _norm(p.get("tipo", "")):
            continue
        zq = _norm(f"{q.get('barrio','')} {q.get('departamento','')}")
        if zona not in zq and _norm(p.get("departamento", "")) not in zq:
            continue
        precio = q.get("precio_usd") or 0
        cub = q.get("sup_cubierta") or 0
        out.append({"id": q["id"], "titulo": q.get("titulo"), "precio_usd": precio,
                    "ppm": round(precio / cub) if cub else 0, "estado": q.get("estado"),
                    "source": "propio", "url": None})
    return out[:limite]
