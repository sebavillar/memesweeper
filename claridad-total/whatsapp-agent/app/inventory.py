"""Inventario de propiedades. En Fase 0 vive en un JSON; en producción es
PostgreSQL + pgvector (búsqueda semántica). La interfaz de búsqueda se mantiene."""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "inventario.json"

# Sinónimos de zonas para tolerar cómo escribe la gente en el chat.
ZONA_ALIAS = {
    "godoy cruz": "Godoy Cruz",
    "ciudad": "Ciudad de Mendoza",
    "capital": "Ciudad de Mendoza",
    "mendoza ciudad": "Ciudad de Mendoza",
    "quinta seccion": "Ciudad de Mendoza",
    "chacras": "Luján de Cuyo",
    "chacras de coria": "Luján de Cuyo",
    "lujan": "Luján de Cuyo",
    "lujan de cuyo": "Luján de Cuyo",
    "maipu": "Maipú",
    "guaymallen": "Guaymallén",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def load() -> list[dict[str, Any]]:
    with open(DATA_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def get(prop_id: str) -> dict[str, Any] | None:
    return next((p for p in load() if p["id"] == prop_id), None)


def buscar(
    zona: str | None = None,
    precio_min: float | None = None,
    precio_max: float | None = None,
    ambientes_min: int | None = None,
    dormitorios_min: int | None = None,
    tipo: str | None = None,
    cochera: bool | None = None,
    caracteristicas: list[str] | None = None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Filtra el inventario disponible y rankea por relevancia.

    Devuelve solo propiedades reales y disponibles. Si un filtro no matchea
    exacto (p. ej. precio), se relaja levemente para poder sugerir alternativas,
    pero las mejores coincidencias quedan primero."""
    props = [p for p in load() if p.get("estado") == "disponible"]
    zona_norm = None
    if zona:
        zona_norm = ZONA_ALIAS.get(_norm(zona), zona)

    scored: list[tuple[float, dict[str, Any]]] = []
    for p in props:
        score = 0.0
        hard_fail = False

        if zona_norm and _norm(zona_norm) not in _norm(p["departamento"]) \
                and _norm(zona_norm) not in _norm(p.get("barrio", "")):
            score -= 3
        elif zona_norm:
            score += 3

        if precio_max is not None:
            if p["precio_usd"] <= precio_max:
                score += 2
            elif p["precio_usd"] <= precio_max * 1.1:
                score += 0.5  # apenas por encima: aún vale sugerirla
            else:
                hard_fail = True
        if precio_min is not None and p["precio_usd"] < precio_min * 0.9:
            hard_fail = True

        if ambientes_min is not None:
            if p["ambientes"] >= ambientes_min:
                score += 1.5
            else:
                score -= 2
        if dormitorios_min is not None and p.get("dormitorios") is not None:
            score += 1 if p["dormitorios"] >= dormitorios_min else -1.5

        if tipo and _norm(tipo) in _norm(p["tipo"]):
            score += 1
        if cochera is True:
            score += 1 if p.get("cochera") else -1.5
        if caracteristicas:
            tset = {_norm(c) for c in p.get("caracteristicas", [])}
            for c in caracteristicas:
                if _norm(c) in tset:
                    score += 0.7

        if not hard_fail:
            scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]
