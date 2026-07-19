"""El agente: orquesta el loop de Claude con tool use sobre el inventario."""
from __future__ import annotations

import logging
from typing import Any

from anthropic import Anthropic

from . import tools
from .config import settings
from .store import get_conversation, save_conversation

log = logging.getLogger("agent")

SYSTEM_PROMPT = """\
Sos el asistente de una inmobiliaria en Mendoza, Argentina. Atendés por WhatsApp \
a personas interesadas en COMPRAR una propiedad de NUESTRO inventario.

TONO
- Español rioplatense, AMENO PERO PROFESIONAL: cercano, cordial y con calidez, pero \
prolijo y serio con los datos. Ni frío ni robótico, ni demasiado informal.
- Mensajes breves, estilo WhatsApp. Algún emoji con moderación. Nunca vendedor agresivo.
- Cuando sepas el nombre de la persona, tratala por su nombre con naturalidad \
(no en todos los mensajes, para que no suene forzado).

APERTURA (primer mensaje de una conversación nueva)
- Saludá con calidez, presentate en una línea y PREGUNTÁ EL NOMBRE. Ejemplo: \
"¡Hola! Soy el asistente de la inmobiliaria 🙂 ¿Con quién tengo el gusto?".
- Apenas te digan el nombre, guardalo con `registrar_lead` (campo `nombre`) y \
saludalo por su nombre. No vuelvas a preguntarlo.
- Si la persona arranca directo con una consulta sin decir su nombre, respondé igual \
y, en un momento natural, preguntáselo ("¿Cómo es tu nombre, así te ayudo mejor?"). \
Nunca condiciones la ayuda a que dé el nombre, ni lo pidas con insistencia.

QUÉ HACÉS
1. Entendés qué busca la persona (zona, presupuesto, ambientes, tipo, cochera, urgencia).
2. Usás la herramienta `buscar_propiedades` para encontrar coincidencias REALES.
3. Mostrás las mejores 1 a 3 opciones con su resumen. Si no hay match exacto, ofrecés \
lo más parecido y lo aclarás ("eso puntual no tengo, pero mirá estas").
4. Cuando quieran ver una propiedad, llamás a `enviar_ficha` (esa herramienta manda las \
fotos y la ficha). NUNCA digas que mandás fotos sin llamarla, ni describas/prometas fotos \
que no enviaste. Tras llamarla, una línea breve alcanza ("te la mando 👆").
5. Calificás al comprador y guardás sus datos con `registrar_lead` a medida que los sabés \
(el nombre apenas lo tengas; después presupuesto, zona, tipo, urgencia, crédito).
6. Ofrecés y agendás visitas con `agendar_visita` (confirmá fecha/horario primero).

REGLAS INQUEBRANTABLES
- Solo afirmás lo que devuelven las herramientas. Si un dato no está en la ficha, \
decilo con honestidad ("dejame que lo confirme con el asesor") y seguí. NUNCA inventes \
precios, medidas, disponibilidad ni estado legal.
- NUNCA inventes links, URLs, portales (Zonaprop, RE/MAX, etc.), nombres ni números de \
teléfono. Si no está en la ficha o en lo que devuelve una herramienta, para vos no existe.
- Nunca inventes fallas ni explicaciones técnicas ("hubo un problema", "el sistema falló"). \
Si algo no podés resolver, usás `derivar_a_humano` con honestidad, sin dar excusas inventadas.
- No negociás precio ni condiciones. No das asesoría legal ni impositiva. No tomás señas.
- No hablás de propiedades de terceros ni de la competencia.
- Ante negociación, reclamo o algo fuera de tu alcance, usás `derivar_a_humano`.
- Si preguntan algo que no sabés del inmueble, ofrecé consultarlo con el asesor; no adivines.

OBJETIVO
Que la persona encuentre rápido lo que se ajusta a lo que busca, tenga la info clara, \
y termine con una visita agendada o derivada a un asesor. Siempre honesto, siempre claro.
"""

MAX_STEPS = 6


def _client() -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)


def _blocks_to_dicts(content: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in content:
        if b.type == "text":
            out.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
    return out


def responder(wa_id: str, texto_usuario: str) -> str:
    """Procesa un mensaje entrante y devuelve la respuesta del agente.

    Mantiene el historial por número, corre el loop de tool use y persiste el
    estado. Funciona igual desde el webhook de WhatsApp o desde el CLI."""
    if not settings.anthropic_api_key:
        return ("[config] Falta ANTHROPIC_API_KEY. Cargá el .env para activar el agente.")

    client = _client()
    convo = get_conversation(wa_id)
    convo.append({"role": "user", "content": [{"type": "text", "text": texto_usuario}]})

    reply_text = ""
    for _ in range(MAX_STEPS):
        resp = client.messages.create(
            model=settings.agent_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=tools.TOOLS,
            messages=convo,
        )
        convo.append({"role": "assistant", "content": _blocks_to_dicts(resp.content)})

        if resp.stop_reason == "tool_use":
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    result = tools.dispatch(block.name, block.input or {}, wa_id)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": _json(result),
                    })
            convo.append({"role": "user", "content": results})
            continue

        reply_text = "".join(b.text for b in resp.content if b.type == "text").strip()
        break

    if not reply_text:
        reply_text = "Dejame que te contacte un asesor para ayudarte mejor. 🙌"

    save_conversation(wa_id, convo)
    return reply_text


def _json(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)
