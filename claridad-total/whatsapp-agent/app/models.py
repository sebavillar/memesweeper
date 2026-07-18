"""Modelos de dominio. En Fase 0 se persisten como JSON; la ficha `Propiedad`
es la misma entidad `Inmueble` que usará el Pasaporte del Inmueble más adelante."""
from __future__ import annotations

from typing import Any


def propiedad_resumen(p: dict[str, Any]) -> str:
    """Texto corto de una propiedad para que el agente lo muestre en el chat."""
    partes = [
        f"🏠 *{p['titulo']}*",
        f"US$ {p['precio_usd']:,}".replace(",", ".") + f" · {p['sup_cubierta']} m² · {p['ambientes']} amb",
    ]
    extras = []
    if p.get("cochera"):
        extras.append("cochera")
    if p.get("expensas_usd"):
        extras.append(f"expensas ~US$ {p['expensas_usd']}")
    if p.get("antiguedad") is not None:
        extras.append(f"{p['antiguedad']} años")
    if extras:
        partes.append(" · ".join(extras))
    return "\n".join(partes)


def propiedad_ficha(p: dict[str, Any]) -> dict[str, Any]:
    """Ficha completa (lo que 'sabe' el agente). Nada fuera de esto debe afirmarse."""
    return {
        "id": p["id"],
        "titulo": p["titulo"],
        "estado": p["estado"],
        "tipo": p["tipo"],
        "barrio": p["barrio"],
        "departamento": p["departamento"],
        "direccion_aprox": p.get("direccion_aprox"),
        "precio_usd": p["precio_usd"],
        "expensas_usd": p.get("expensas_usd"),
        "sup_cubierta": p["sup_cubierta"],
        "sup_total": p.get("sup_total"),
        "ambientes": p["ambientes"],
        "dormitorios": p.get("dormitorios"),
        "banos": p.get("banos"),
        "antiguedad": p.get("antiguedad"),
        "cochera": p.get("cochera", False),
        "caracteristicas": p.get("caracteristicas", []),
        "descripcion": p.get("descripcion"),
        "estado_legal_resumen": p.get("estado_legal_resumen"),
        "fotos": p.get("fotos", []),
        "asesor": p.get("asesor", {}),
    }
