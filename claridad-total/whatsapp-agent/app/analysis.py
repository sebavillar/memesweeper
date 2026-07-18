"""Análisis de mercado por inmueble (primera versión).

Valuación EXPLICABLE con lógica heurística (mismo enfoque que el prototipo del
Pasaporte) + comparables tomados del propio inventario. Cada número viene con su
'porqué'. La integración real con catastro/ATM de Mendoza y el scraping en vivo de
portales se conecta en una fase posterior; la interfaz ya está preparada para eso."""
from __future__ import annotations

import unicodedata
from typing import Any

from . import inventory

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


def valuar(p: dict[str, Any]) -> dict[str, Any]:
    """Devuelve valor estimado + rango + confianza + factores + comparables."""
    m2, zona_clave = _zona_m2(p)
    cub = p.get("sup_cubierta") or 0
    pasos: list[dict[str, Any]] = []

    base = cub * m2
    pasos.append({"label": "Base por superficie",
                  "detalle": f"{cub} m² × US$ {m2:,}/m²".replace(",", "."), "val": base})

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
        "fuentes": {"valuacion": "heurística (estimación)",
                    "comparables": "inventario propio",
                    "catastro": "pendiente de integración (ATM/IDE Mendoza)",
                    "portales": "pendiente de integración (scraping)"},
    }


def comparables(p: dict[str, Any], limite: int = 4) -> list[dict[str, Any]]:
    """Comparables tomados del inventario propio: mismo tipo y zona parecida."""
    _, zona = _zona_m2(p)
    out = []
    for q in inventory.load():
        if q.get("id") == p.get("id"):
            continue
        if _norm(q.get("tipo", "")) != _norm(p.get("tipo", "")):
            continue
        zq = _norm(f"{q.get('barrio','')} {q.get('departamento','')}")
        if zona not in zq and _norm(p.get("departamento", "")) not in zq:
            continue
        precio = q.get("precio_usd") or 0
        cub = q.get("sup_cubierta") or 0
        out.append({"id": q["id"], "titulo": q.get("titulo"), "precio_usd": precio,
                    "ppm": round(precio / cub) if cub else 0, "estado": q.get("estado")})
    return out[:limite]
