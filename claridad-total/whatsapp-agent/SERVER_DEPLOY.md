# Desplegar en tu propio servidor (Ubuntu/Debian) con Docker + HTTPS

El bot queda 24/7 en tu servidor, con **certificado HTTPS automático** (Caddy +
Let's Encrypt). Todo corre en contenedores; no ensucia el sistema.

**Necesitás:** un servidor Linux con IP pública, acceso SSH (root o sudo), un
**subdominio** libre (ej. `bot.tudominio.com`) y los puertos **80 y 443** libres.

---

## 1. Apuntar el subdominio al servidor *(en tu proveedor de DNS)*

Creá un registro **A**:
```
bot.tudominio.com   A   <IP_PUBLICA_DE_TU_SERVIDOR>
```
Esperá unos minutos a que propague. Verificá desde tu compu:
```bash
ping bot.tudominio.com     # debe responder con la IP del servidor
```

## 2. Entrar al servidor e instalar Docker

```bash
ssh usuario@<IP>

# Docker + plugin compose (script oficial)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER      # para no usar sudo cada vez
# cerrá sesión y volvé a entrar (o: newgrp docker)
docker --version && docker compose version
```

## 3. Traer el código

```bash
git clone -b claude/ai-real-estate-platform-rivx96 \
  https://github.com/sebavillar/memesweeper.git
cd memesweeper/claridad-total/whatsapp-agent
```
*(Como el repo es privado, Git te va a pedir usuario y un token de GitHub. Si te
complica, avisame y lo resolvemos con una clave SSH o un token.)*

## 4. Crear el `.env`

```bash
cp .env.example .env
nano .env
```
Completá:
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
AGENT_DOMAIN=bot.tudominio.com
```
Guardá (en nano: Ctrl+O, Enter, Ctrl+X).

## 5. Abrir el firewall (si usás ufw)

```bash
sudo ufw allow 80
sudo ufw allow 443
```

## 6. Levantar todo

```bash
docker compose up -d --build
```
Caddy detecta el dominio y saca el certificado HTTPS solo (puede tardar ~1 min la
primera vez). Verificá:
```bash
curl https://bot.tudominio.com/health      # -> {"ok": true, ...}
```
Ver logs si algo falla:
```bash
docker compose logs -f app
docker compose logs -f caddy
```

## 7. Conectar el webhook en Meta

Panel de la app → **WhatsApp → Configuration → Webhook → Edit**:
- **Callback URL**: `https://bot.tudominio.com/webhook`
- **Verify token**: `claridad-total-verify`
- **Verify and save** (nuestro `GET /webhook` responde el handshake solo).
- **Subscribe** al campo **`messages`**.

## 8. Crear las plantillas (dentro del contenedor)

```bash
docker compose exec app python -m scripts.meta_subscribe_webhook
docker compose exec app python -m scripts.meta_create_templates
```

## 9. Probar de punta a punta

Desde tu celular (agregado como destinatario de prueba), escribí al **número de
prueba** (+1 555 172 3891):
- "hola, busco 3 ambientes en Godoy Cruz hasta 120 mil con cochera"
- pedí ver una → recibís la ficha
- agendá una visita → aparece en el panel y te llega el aviso.

Panel del corredor: **`https://bot.tudominio.com/panel`**

---

## Operación

| Acción | Comando |
|---|---|
| Ver logs | `docker compose logs -f app` |
| Reiniciar | `docker compose restart` |
| Actualizar código | `git pull && docker compose up -d --build` |
| Frenar | `docker compose down` |

## ⚠️ Antes de producción: token permanente

El token de prueba **dura 24 h**. Generá el **token permanente de System User**
(ver `META_SETUP.md` §3), reemplazá `WHATSAPP_ACCESS_TOKEN` en el `.env` y reiniciá:
```bash
docker compose restart app
```

## Notas

- **Puertos 80/443:** deben estar libres. Si el servidor ya corre otro sitio en
  esos puertos, avisame y adaptamos (Caddy puede convivir con lo existente).
- **Inventario:** se lee de `data/inventario.json`. Para cambiarlo: editás, `git pull`
  (o editás en el server) y `docker compose up -d --build`. La carga dinámica llega en Fase 2.
- **Datos** (conversaciones/leads/visitas): en el volumen `agent-data`, sobreviven reinicios.
