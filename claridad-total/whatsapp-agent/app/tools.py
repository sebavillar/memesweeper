"""Definición y ejecución de las herramientas que usa el agente (tool use).

Principio central: el modelo NO guarda el inventario en su memoria. Consulta
`buscar_propiedades`/`ver_ficha` como funciones, y solo puede afirmar lo que
estas devuelven. Así los precios y la disponibilidad son siempre los reales."""
from __future__ import annotations

import logging
from typing import Any

from . import inventory, leadscoring, store, whatsapp
from .models import propiedad_ficha, propiedad_resumen

log = logging.getLogger("tools")

# ---- Esquemas expuestos al modelo (Anthropic tool use) ----
TOOLS: list[dict[str, Any]] = [
    {
        "name": "buscar_propiedades",
        "description": (
            "Busca propiedades disponibles del inventario propio según los criterios "
            "del comprador. Devuelve solo propiedades reales y disponibles. Usala "
            "siempre que el comprador describa qué busca; no inventes propiedades."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "zona": {"type": "string", "description": "Barrio o departamento (ej. 'Godoy Cruz', 'Chacras')."},
                "precio_max": {"type": "number", "description": "Presupuesto máximo en dólares."},
                "precio_min": {"type": "number", "description": "Precio mínimo en dólares (opcional)."},
                "ambientes_min": {"type": "integer", "description": "Cantidad mínima de ambientes."},
                "dormitorios_min": {"type": "integer", "description": "Cantidad mínima de dormitorios."},
                "tipo": {"type": "string", "description": "'departamento' o 'casa'."},
                "cochera": {"type": "boolean", "description": "true si necesita cochera."},
                "caracteristicas": {"type": "array", "items": {"type": "string"}, "description": "Ej. ['pileta','patio']."},
            },
        },
    },
    {
        "name": "ver_ficha",
        "description": "Devuelve la ficha completa de una propiedad por su id, para dar detalles o enviarla.",
        "input_schema": {
            "type": "object",
            "properties": {"propiedad_id": {"type": "string"}},
            "required": ["propiedad_id"],
        },
    },
    {
        "name": "enviar_ficha",
        "description": "Envía al comprador la ficha con fotos y datos de una propiedad. Usala cuando pida ver una en detalle.",
        "input_schema": {
            "type": "object",
            "properties": {"propiedad_id": {"type": "string"}},
            "required": ["propiedad_id"],
        },
    },
    {
        "name": "agendar_visita",
        "description": "Reserva una visita y avisa al corredor. Confirmá antes fecha/horario con el comprador.",
        "input_schema": {
            "type": "object",
            "properties": {
                "propiedad_id": {"type": "string"},
                "fecha_hora": {"type": "string", "description": "Ej. 'sábado 10 hs' o '2026-07-25 10:00'."},
                "nombre": {"type": "string"},
                "telefono": {"type": "string"},
            },
            "required": ["propiedad_id", "fecha_hora"],
        },
    },
    {
        "name": "registrar_lead",
        "description": "Guarda o actualiza el perfil y la calificación del comprador (presupuesto, zona, tipo, urgencia, crédito).",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string"},
                "telefono": {"type": "string"},
                "presupuesto_usd": {"type": "number"},
                "zona": {"type": "string"},
                "tipo": {"type": "string"},
                "ambientes": {"type": "integer"},
                "necesita_credito": {"type": "boolean"},
                "urgencia": {"type": "string", "description": "Ej. 'esta semana', 'explorando'."},
                "notas": {"type": "string"},
            },
        },
    },
    {
        "name": "derivar_a_humano",
        "description": "Escala la conversación al corredor con un resumen. Usala ante negociación, reclamos o dudas fuera de tu alcance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "motivo": {"type": "string"},
                "resumen": {"type": "string"},
            },
            "required": ["motivo", "resumen"],
        },
    },
]


def dispatch(name: str, args: dict[str, Any], wa_id: str) -> dict[str, Any]:
    """Ejecuta una herramienta y devuelve un resultado JSON-serializable."""
    log.info("tool %s(%s)", name, args)

    if name == "buscar_propiedades":
        matches = inventory.buscar(
            zona=args.get("zona"),
            precio_min=args.get("precio_min"),
            precio_max=args.get("precio_max"),
            ambientes_min=args.get("ambientes_min"),
            dormitorios_min=args.get("dormitorios_min"),
            tipo=args.get("tipo"),
            cochera=args.get("cochera"),
            caracteristicas=args.get("caracteristicas"),
        )
        return {
            "cantidad": len(matches),
            "propiedades": [
                {
                    "id": p["id"], "titulo": p["titulo"], "barrio": p["barrio"],
                    "departamento": p["departamento"], "precio_usd": p["precio_usd"],
                    "ambientes": p["ambientes"], "sup_cubierta": p["sup_cubierta"],
                    "cochera": p.get("cochera", False), "resumen": propiedad_resumen(p),
                }
                for p in matches
            ],
        }

    if name == "ver_ficha":
        p = inventory.get(args["propiedad_id"])
        return {"ficha": propiedad_ficha(p)} if p else {"error": "No existe esa propiedad."}

    if name == "enviar_ficha":
        p = inventory.get(args["propiedad_id"])
        if not p:
            return {"error": "No existe esa propiedad."}
        # Fase 1: envío de fotos nativas de WhatsApp. La primera lleva el resumen
        # como caption; las demás van a continuación. Requiere URLs públicas HTTPS.
        ficha = propiedad_ficha(p)
        fotos = ficha.get("fotos") or []
        caption = propiedad_resumen(p)
        if p.get("descripcion"):
            caption += f"\n\n{p['descripcion']}"
        if fotos:
            whatsapp.send_images(wa_id, fotos, caption=caption)
        else:
            whatsapp.send_text(wa_id, caption)
        return {"enviada": True, "fotos": len(fotos), "ficha": ficha}

    if name == "agendar_visita":
        p = inventory.get(args["propiedad_id"])
        visita = {
            "wa_id": wa_id,
            "propiedad_id": args["propiedad_id"],
            "propiedad": p["titulo"] if p else args["propiedad_id"],
            "fecha_hora": args["fecha_hora"],
            "nombre": args.get("nombre"),
            "telefono": args.get("telefono", wa_id),
        }
        store.add_visita(visita)
        # Agendar una visita califica fuerte al lead.
        lead = store.upsert_lead(wa_id, {"visita_agendada": True,
                                          "nombre": args.get("nombre"),
                                          "telefono": args.get("telefono")})
        calif = leadscoring.calificar(lead)
        store.upsert_lead(wa_id, {"temperatura": calif["temperatura"], "score": calif["score"]})
        whatsapp.notify_corredor(
            f"🗓️ Visita agendada [{calif['temperatura'].upper()}]: {visita['propiedad']} — "
            f"{visita['fecha_hora']} — {visita.get('nombre') or 'comprador'} ({visita['telefono']})"
        )
        return {"agendada": True, "visita": visita, "calificacion": calif}

    if name == "registrar_lead":
        lead = store.upsert_lead(wa_id, args)
        calif = leadscoring.calificar(lead)
        lead = store.upsert_lead(wa_id, {"temperatura": calif["temperatura"], "score": calif["score"]})
        return {"registrado": True, "lead": lead, "calificacion": calif}

    if name == "derivar_a_humano":
        store.upsert_lead(wa_id, {"handoff": True, "handoff_motivo": args["motivo"]})
        whatsapp.notify_corredor(
            f"🙋 Handoff ({args['motivo']}) — {wa_id}\nResumen: {args['resumen']}"
        )
        return {"derivado": True}

    return {"error": f"Herramienta desconocida: {name}"}
