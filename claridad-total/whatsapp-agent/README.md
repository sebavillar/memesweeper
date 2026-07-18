# Agente de WhatsApp para compradores — Fase 0 + Fase 1

Agente de IA que atiende consultas de compradores por WhatsApp sobre el inventario
propio. Stack: **FastAPI + WhatsApp Cloud API (Meta) + Claude con tool use**.

- **Fase 0:** webhook, agente con tool use, inventario, CLI de prueba.
- **Fase 1:** envío de **fotos nativas**, **calificación de leads** (caliente/tibio/frío),
  **panel del corredor** (`/panel`), **plantillas de re-engagement** y **scripts de provisión de Meta**.

Para la configuración completa de Meta, ver **[`META_SETUP.md`](./META_SETUP.md)**.

## Qué hace

- Recibe mensajes por el webhook de la WhatsApp Cloud API.
- El agente (Claude) razona y usa herramientas para **consultar el inventario real**
  (`buscar_propiedades`, `ver_ficha`, `enviar_ficha`), **calificar** al comprador
  (`registrar_lead`), **agendar visitas** (`agendar_visita`) y **derivar al corredor**
  (`derivar_a_humano`).
- Nunca inventa datos: solo afirma lo que devuelven las herramientas.

## Estructura

```
whatsapp-agent/
├── app/
│   ├── main.py          # FastAPI: webhook GET/POST + /simulate
│   ├── agent.py         # loop de Claude con tool use + system prompt
│   ├── tools.py         # esquema y ejecución de las herramientas
│   ├── inventory.py     # búsqueda sobre el inventario (JSON en Fase 0)
│   ├── whatsapp.py      # cliente Cloud API (enviar mensajes)
│   ├── store.py         # persistencia JSON: conversaciones, leads, visitas
│   ├── models.py        # ficha/resumen de propiedad
│   └── config.py        # settings desde .env
│   ├── leadscoring.py   # calificación de leads (Fase 1)
│   └── panel.py         # panel del corredor: leads + visitas (Fase 1)
├── data/inventario.json # inventario de muestra (Mendoza)
├── meta/templates.py    # plantillas de mensaje para aprobar en Meta (Fase 1)
├── scripts/
│   ├── chat_cli.py            # probar el agente en la terminal (sin WhatsApp)
│   ├── meta_register_phone.py     # registrar el número (Cloud API)
│   ├── meta_subscribe_webhook.py  # suscribir la app a la WABA
│   ├── meta_create_templates.py   # crear/aprobar plantillas
│   ├── meta_send_template.py       # enviar una plantilla (re-engagement)
│   └── send_visit_reminders.py     # recordatorios de visita (cron)
├── META_SETUP.md        # runbook completo de Meta
├── requirements.txt
└── .env.example
```

## Panel del corredor (Fase 1)

Con el server levantado, abrí **`http://localhost:8000/panel`**: leads calificados por
temperatura (🔥 caliente / 🟡 tibio / ⚪ frío), visitas agendadas y estado del inventario.
APIs JSON: `/panel/api/leads` y `/panel/api/visitas`.
> En producción va detrás de autenticación.

## Puesta en marcha

```bash
cd claridad-total/whatsapp-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # completá las credenciales
```

### 1. Probar el "cerebro" sin WhatsApp (recomendado primero)

Solo necesitás `ANTHROPIC_API_KEY` en el `.env`:

```bash
python -m scripts.chat_cli
# o una sola consulta:
python -m scripts.chat_cli "hola, busco 3 ambientes en Godoy Cruz hasta 120 mil con cochera"
```

### 2. Levantar el webhook

```bash
uvicorn app.main:app --reload --port 8000
```

Probar el agente por HTTP sin WhatsApp:

```bash
curl -X POST localhost:8000/simulate \
  -H 'content-type: application/json' \
  -d '{"from":"5492610000000","text":"busco casa en Chacras con pileta"}'
```

### 3. Conectar WhatsApp (Meta Cloud API)

1. En [developers.facebook.com](https://developers.facebook.com) creá una app de tipo
   *Business* y agregá el producto **WhatsApp**. Obtené el **Phone Number ID** y un
   **access token** (para producción, un token de *System User* de larga duración).
2. Cargá en `.env`: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` y un
   `WHATSAPP_VERIFY_TOKEN` a tu elección.
3. Exponé el puerto local con un túnel HTTPS (ej. `cloudflared tunnel --url http://localhost:8000`
   o `ngrok http 8000`).
4. En el panel de WhatsApp → *Configuration* → *Webhook*, poné la URL
   `https://TU-TUNEL/webhook` y el mismo `verify_token`. Suscribite al campo `messages`.
5. Escribí al número de prueba desde tu WhatsApp: el agente responde.

> **Ventana de 24 h:** como el comprador escribe primero, las respuestas de texto del
> agente caen en la ventana de servicio gratuita. Las plantillas (para reabrir fuera de
> 24 h) se agregan en una fase posterior.

## Notas de diseño

- **Tool use, no memoria:** el inventario se consulta como función; los precios y la
  disponibilidad son siempre los reales. Es la defensa contra la alucinación.
- **La ficha `Propiedad` es la misma entidad `Inmueble`** que usará el Pasaporte del
  Inmueble: este agente siembra el inventario estructurado del resto de la plataforma.
- **Fase 0 usa JSON** para inventario/leads/conversaciones. La migración a
  PostgreSQL + pgvector no cambia las interfaces (`inventory.buscar`, `store.*`).

## Próximas fases

- **Fase 1:** envío de imágenes nativas, calificación más rica, panel de leads.
- **Fase 2:** carga de inventario por panel web y por WhatsApp; métricas.
- **Fase 3:** matching semántico con embeddings, plantillas de re-engagement.
