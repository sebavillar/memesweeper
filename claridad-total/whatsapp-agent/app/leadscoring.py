"""Calificación de leads (Fase 1). A partir de lo que sabemos del comprador,
calcula un puntaje y una 'temperatura' para que el corredor priorice.

No es un modelo entrenado: es una heurística transparente y ajustable —el mismo
criterio que el motor de valuación del Pasaporte. Cada punto tiene su porqué."""
from __future__ import annotations

from typing import Any

# Palabras que sugieren urgencia alta en texto libre.
_URGENTE = ("urg", "esta semana", "ya", "cuanto antes", "inmediat", "mudar")


def calificar(lead: dict[str, Any]) -> dict[str, Any]:
    score = 0
    factores: list[str] = []

    if lead.get("presupuesto_usd"):
        score += 2
        factores.append("presupuesto definido")
    if lead.get("zona"):
        score += 1
        factores.append("zona clara")
    if lead.get("tipo"):
        score += 1
    if lead.get("ambientes"):
        score += 1

    urg = (lead.get("urgencia") or "").lower()
    if any(w in urg for w in _URGENTE):
        score += 3
        factores.append("urgencia alta")

    if lead.get("necesita_credito") is False:
        score += 2
        factores.append("compra al contado")
    elif lead.get("necesita_credito") is True:
        score += 1
        factores.append("requiere crédito")

    if lead.get("visita_agendada"):
        score += 4
        factores.append("visita agendada")
    if lead.get("nombre") and lead.get("telefono"):
        score += 1
        factores.append("datos de contacto")

    if score >= 8:
        estado = "caliente"
    elif score >= 4:
        estado = "tibio"
    else:
        estado = "frio"

    return {"score": score, "temperatura": estado, "factores": factores}
