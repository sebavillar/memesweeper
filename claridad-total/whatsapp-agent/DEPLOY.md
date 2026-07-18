# Desplegar el agente en la nube (Render) — 24/7

Guía para poner el bot en un servidor siempre prendido y conectar el webhook de
WhatsApp. Usamos **Render** porque despliega directo desde GitHub y da una URL
HTTPS estable. Tiempo estimado: ~20 min.

> **Costo:** el plan **Starter (~US$7/mes)** mantiene el servicio siempre activo
> (necesario para un webhook). El plan Free se "duerme" tras 15 min de inactividad
> y perdería mensajes, así que no sirve para esto.

---

## 1. Crear la cuenta y conectar el repo

1. Entrá a **[render.com](https://render.com)** y registrate **con GitHub**.
2. **New + → Web Service**.
3. **Connect a repository** → autorizá a Render en GitHub y elegí **`sebavillar/memesweeper`**.
   (Si no aparece, "Configure account" y dale acceso a ese repo.)

## 2. Configurar el servicio

| Campo | Valor |
|---|---|
| **Name** | `claridad-total-whatsapp` |
| **Branch** | `claude/ai-real-estate-platform-rivx96` |
| **Root Directory** | `claridad-total/whatsapp-agent` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | **Starter** (siempre activo) |

## 3. Variables de entorno

En **Environment / Environment Variables**, agregá (las mismas del `.env`):

```
WHATSAPP_VERIFY_TOKEN=claridad-total-verify
WHATSAPP_ACCESS_TOKEN=<token de WhatsApp>
WHATSAPP_PHONE_NUMBER_ID=1209516492249572
WHATSAPP_BUSINESS_ACCOUNT_ID=26903216089352293
GRAPH_API_VERSION=v21.0
TEMPLATE_LANG=es_AR
ANTHROPIC_API_KEY=<tu API key de Claude>
AGENT_MODEL=claude-sonnet-5
CORREDOR_NOTIFY_NUMBER=<tu celular 549261XXXXXXX>
DATA_DIR=/var/data
PYTHON_VERSION=3.12.6
```

## 4. Disco persistente (para no perder leads al reiniciar)

En **Advanced → Add Disk**:
- **Name**: `data`
- **Mount Path**: `/var/data`
- **Size**: `1 GB`

## 5. Crear y esperar el deploy

**Create Web Service**. Render compila y despliega (unos minutos). Cuando esté
"Live", vas a tener una URL tipo:
```
https://claridad-total-whatsapp.onrender.com
```
Verificá que anda: abrí **`https://…onrender.com/health`** → debe responder
`{"ok": true, ...}`.

## 6. Conectar el webhook en Meta

En el panel de la app → **WhatsApp → Configuration** (o *Configuración*) → **Webhook → Edit**:
- **Callback URL**: `https://claridad-total-whatsapp.onrender.com/webhook`
- **Verify token**: `claridad-total-verify` (el mismo del `.env`)
- **Verify and save** → Meta hace el handshake (nuestro `GET /webhook` responde solo).
- En **Webhook fields**, **Subscribe** al campo **`messages`**.

## 7. Crear las plantillas (desde la nube)

En Render, pestaña **Shell** del servicio, corré:
```bash
python -m scripts.meta_subscribe_webhook     # asegura la suscripción de la app
python -m scripts.meta_create_templates      # sube las 3 plantillas a aprobación
```

## 8. Probar de punta a punta

Desde tu celular (el que agregaste como destinatario de prueba), escribí al
**número de prueba** (+1 555 172 3891). El agente debería responder. Probá:
- "hola, busco 3 ambientes en Godoy Cruz hasta 120 mil con cochera"
- pedí ver una → deberías recibir la ficha
- agendá una visita → aparece en el panel **`/panel`** y te llega el aviso.

El panel del corredor queda en:
```
https://claridad-total-whatsapp.onrender.com/panel
```

---

## ⚠️ Antes de dejarlo en producción: token permanente

El token de "Paso 1. Pruébalo" **dura solo 24 h**. Para que el bot funcione sin
cortarse, generá un **token permanente de System User** (ver `META_SETUP.md` §3) y
reemplazá `WHATSAPP_ACCESS_TOKEN` en las variables de entorno de Render. Render
redepliega solo al guardar.

## Notas

- **Inventario:** en esta fase se lee de `data/inventario.json` (en el repo). Para
  cambiarlo, se edita y se commitea (Render redepliega). La carga dinámica llega en Fase 2.
- **Datos mutables** (conversaciones, leads, visitas) viven en el disco `/var/data`
  y sobreviven reinicios y deploys.
- **Auto-deploy:** cada push a la rama redepliega el servicio automáticamente.
