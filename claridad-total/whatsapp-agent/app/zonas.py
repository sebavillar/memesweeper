"""Normalización de departamentos de Mendoza (única fuente de verdad).

Los portales escriben la zona de mil formas ("Capital", "Ciudad de Mendoza",
"Capital Mendoza", "Villa Marini, Godoy Cruz", "Lujan de Cuyo"...). Acá las
llevamos a los 18 departamentos oficiales para poder agrupar, filtrar y buscar
comparables con sentido. Lo usan el dashboard de mercado (api.py) Y la
valuación (analysis.py), así que la lógica es una sola."""
from __future__ import annotations

import unicodedata
from typing import Any

# clave normalizada (sin acentos, minúsculas) → nombre para mostrar.
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
# Matcheo por claves más largas primero ("lujan de cuyo" antes que "lujan").
_KEYS = sorted(_DEPTOS, key=len, reverse=True)


def norm(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def departamento(*textos: str | None) -> str | None:
    """Devuelve el departamento canónico de Mendoza a partir de uno o más textos
    (departamento, barrio, título...). None si no reconoce ninguno."""
    t = norm(" ".join(x or "" for x in textos))
    for k in _KEYS:
        if k in t:
            return _DEPTOS[k]
    return None


def de_row(row: dict[str, Any]) -> str | None:
    """Departamento canónico de un aviso/propiedad (mira departamento, barrio y título)."""
    return departamento(row.get("departamento"), row.get("barrio"), row.get("titulo"))
