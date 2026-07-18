# Provisión de Meta / WhatsApp Cloud API — runbook completo

Todo lo que hay que hacer del lado de Meta para poner el agente en producción.
Las partes que se pueden automatizar tienen su script (Graph API); las que requieren
tu login/verificación están marcadas como **manual**.

> Nada de esto expone secretos en el repo: las credenciales viven solo en tu `.env`
> local (que está en `.gitignore`).

---

## 0. Lo que vas a obtener (y dónde va en el .env)

| Dato | De dónde sale | Variable en `.env` |
|---|---|---|
| App ID / App Secret | Panel de la app en developers.facebook.com | (no requerido por el agente) |
| **WABA ID** (WhatsApp Business Account) | WhatsApp → API Setup | `WHATSAPP_BUSINESS_ACCOUNT_ID` |
| **Phone Number ID** | WhatsApp → API Setup | `WHATSAPP_PHONE_NUMBER_ID` |
| **Access token** (System User, permanente) | Business Settings → System Users | `WHATSAPP_ACCESS_TOKEN` |
| **Verify token** (lo elegís vos) | — | `WHATSAPP_VERIFY_TOKEN` |

---

## 1. Cuenta de negocio *(manual)*

1. Creá un **Meta Business Portfolio** en [business.facebook.com](https://business.facebook.com).
2. Tené a mano un **número de teléfono** que **no** esté registrado en la app de WhatsApp
   (o que puedas migrar). Es el número con el que la inmobiliaria va a atender.

## 2. App + producto WhatsApp *(manual)*

1. En [developers.facebook.com](https://developers.facebook.com) → **Create App** → tipo **Business**.
2. Dentro de la app, **Add Product → WhatsApp → Set up**.
   Esto crea automáticamente una **WABA de prueba** y un **número de prueba** para empezar ya.
3. En **WhatsApp → API Setup** vas a ver el **Phone Number ID** y el **WhatsApp Business Account ID (WABA ID)**.
   Copialos.

## 3. Access token permanente (System User) *(manual)*

El token que muestra "API Setup" dura 24 h. Para producción:

1. **Business Settings → Users → System Users → Add** (rol Admin).
2. **Generate new token** → elegí la app → permisos:
   `whatsapp_business_messaging` y `whatsapp_business_management`.
3. **Assign assets**: asignale la WABA al System User (control total).
4. Copiá el token (no vence) a `WHATSAPP_ACCESS_TOKEN`.

## 4. Completar el `.env`

```bash
cd claridad-total/whatsapp-agent
cp .env.example .env
```
Completá al menos:
```
WHATSAPP_VERIFY_TOKEN=claridad-total-verify      # lo elegís vos
WHATSAPP_ACCESS_TOKEN=EAAG...                     # token del System User
WHATSAPP_PHONE_NUMBER_ID=xxxxxxxxxxxxx
WHATSAPP_BUSINESS_ACCOUNT_ID=xxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-...
CORREDOR_NOTIFY_NUMBER=5492610000000              # opcional
```

## 5. Registrar el número en la Cloud API *(script)*

La Cloud API exige registrar el número con un PIN de verificación en dos pasos (6 dígitos, lo elegís vos):
```bash
python -m scripts.meta_register_phone 123456
```
(Si es el número de prueba de Meta, este paso puede no hacer falta.)

## 6. Configurar el webhook

**a. Exponé el backend por HTTPS** (Meta necesita una URL pública):
```bash
uvicorn app.main:app --port 8000 &
cloudflared tunnel --url http://localhost:8000     # o: ngrok http 8000
```
Te da una URL tipo `https://algo.trycloudflare.com`.

**b. Cargá el webhook** *(manual, una vez)*: en **WhatsApp → Configuration → Webhook → Edit**:
- **Callback URL**: `https://algo.trycloudflare.com/webhook`
- **Verify token**: el mismo `WHATSAPP_VERIFY_TOKEN` del `.env`
- Meta hace un GET de verificación; el endpoint `GET /webhook` responde el challenge automáticamente.
- **Subscribe** al campo **`messages`**.

**c. Suscribí la app a la WABA** *(script)*:
```bash
python -m scripts.meta_subscribe_webhook      # POST /{WABA_ID}/subscribed_apps -> {"success": true}
```

## 7. Crear las plantillas de mensaje *(script)*

Para reabrir conversación fuera de la ventana de 24 h (recordatorios, avisos de propiedad nueva):
```bash
python -m scripts.meta_create_templates
```
Crea las 3 plantillas de `meta/templates.py` (`recordatorio_visita`, `nueva_propiedad`,
`seguimiento_consulta`). Quedan **PENDING** hasta que Meta las aprueba (suele tardar de minutos a horas).
Enviarlas después:
```bash
python -m scripts.meta_send_template 5492610000000 recordatorio_visita \
    "Juan" "Depto en Godoy Cruz" "sábado 10 hs" "San Martín 1234"
```

## 8. Verificación de negocio *(manual, para escalar)*

Con el número de prueba y sin verificar, Meta limita a pocos destinatarios y baja volumen.
Para producción: **Business Settings → Security Center → Business Verification**. Al verificar
y subir de tier, el número puede escribir a más usuarios y sube el límite de mensajería.

## 9. Prueba de punta a punta

1. Escribí desde tu WhatsApp personal al número de la inmobiliaria.
2. El mensaje entra por `POST /webhook`, el agente responde y ves el diálogo.
3. Pedí ver una propiedad → deberías recibir las **fotos nativas**.
4. Agendá una visita → el corredor recibe el aviso y aparece en el **panel** (`/panel`).

---

## Checklist rápido

- [ ] Business Portfolio creado
- [ ] App Business + producto WhatsApp
- [ ] WABA ID y Phone Number ID copiados
- [ ] System User + token permanente con permisos `whatsapp_business_messaging` y `whatsapp_business_management`
- [ ] `.env` completo
- [ ] `meta_register_phone` OK
- [ ] Webhook cargado (callback + verify token) y suscripto a `messages`
- [ ] `meta_subscribe_webhook` → success
- [ ] `meta_create_templates` → plantillas en revisión
- [ ] (Producción) verificación de negocio

## Costos (recordatorio)

- **Entrantes / respuestas dentro de 24 h**: gratis (es el caso de este bot inbound).
- **Plantillas**: UTILITY dentro de la ventana de servicio suelen ser gratis; MARKETING se cobran
  por mensaje según país. Ver `04-plan-agente-whatsapp` para el detalle.
- **Claude**: centavos por conversación (tokens).

## Troubleshooting

- **GET /webhook devuelve 403**: el `verify_token` del panel no coincide con el `.env`.
- **No llegan mensajes**: falta suscribir la app (`meta_subscribe_webhook`) o el campo `messages`.
- **Las fotos no se ven**: las URLs de `data/inventario.json` deben ser públicas HTTPS reales (jpg/png).
- **Error al enviar plantilla**: todavía no está aprobada, o el nombre/idioma no coincide.
