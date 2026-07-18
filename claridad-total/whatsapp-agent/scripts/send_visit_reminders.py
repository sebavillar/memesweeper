#!/usr/bin/env python3
"""Envía recordatorios de visita (plantilla `recordatorio_visita`) a las visitas
agendadas. Pensado para correr una vez por día (cron) el día previo.

Uso:  python -m scripts.send_visit_reminders
En Fase 1 recorre todas las visitas guardadas; en producción se filtra por fecha."""
from __future__ import annotations

from app import inventory, store
from app.whatsapp import send_template


def main() -> None:
    visitas = store.list_visitas()
    if not visitas:
        print("No hay visitas agendadas.")
        return
    for v in visitas:
        prop = inventory.get(v.get("propiedad_id", "")) or {}
        direccion = prop.get("direccion_aprox") or "te confirmamos la dirección exacta"
        variables = [
            v.get("nombre") or "hola",
            v.get("propiedad") or "la propiedad",
            v.get("fecha_hora") or "el horario acordado",
            direccion,
        ]
        res = send_template(v.get("telefono") or v.get("wa_id"), "recordatorio_visita", variables)
        print(f"→ {v.get('telefono') or v.get('wa_id')}: {res}")


if __name__ == "__main__":
    main()
