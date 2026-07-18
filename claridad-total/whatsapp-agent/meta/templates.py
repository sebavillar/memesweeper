"""Plantillas de mensaje de WhatsApp para reabrir conversación fuera de la
ventana de 24 h. Se envían a Meta para aprobación con `scripts/meta_create_templates.py`.

Categorías (Meta las revisa y cobra distinto):
- UTILITY: seguimiento de algo que el usuario pidió/acordó (ej. recordar una visita).
- MARKETING: proactivo/promocional (ej. avisar de una propiedad nueva).

Los {{1}}, {{2}}, ... son variables que se completan al enviar, en orden.
`example` es obligatorio para la aprobación: son valores de muestra."""

TEMPLATES = [
    {
        "name": "recordatorio_visita",
        "language": "es_AR",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hola {{1}} 👋 Te recordamos tu visita a {{2}} el {{3}}.\n"
                    "Dirección: {{4}}. ¿La confirmás? Si necesitás reprogramar, "
                    "respondé por acá y lo vemos."
                ),
                "example": {
                    "body_text": [["Juan", "Depto 3 amb en Godoy Cruz", "sábado 26/07 a las 10 hs", "San Martín 1234"]]
                },
            }
        ],
    },
    {
        "name": "nueva_propiedad",
        "language": "es_AR",
        "category": "MARKETING",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hola {{1}} 🏠 Entró una propiedad que encaja con lo que buscabas: "
                    "{{2}} en {{3}}, US$ {{4}}. ¿Querés que te pase la ficha con fotos?"
                ),
                "example": {
                    "body_text": [["Juan", "Depto 3 amb con cochera", "Godoy Cruz", "119.000"]]
                },
            }
        ],
    },
    {
        "name": "seguimiento_consulta",
        "language": "es_AR",
        "category": "MARKETING",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hola {{1}} 🙂 ¿Seguís con la búsqueda en {{2}}? Tenemos novedades "
                    "que pueden interesarte. Escribinos y te muestro lo que tengo."
                ),
                "example": {"body_text": [["Juan", "Godoy Cruz"]]},
            }
        ],
    },
]
