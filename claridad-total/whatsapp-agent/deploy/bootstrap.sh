#!/usr/bin/env bash
# Arranque automático del agente de WhatsApp en un servidor nuevo (Ubuntu/Debian).
# Uso (dentro de claridad-total/whatsapp-agent):  sudo bash deploy/bootstrap.sh
set -euo pipefail

echo "======================================================"
echo "  Claridad Total · Bootstrap del agente de WhatsApp"
echo "======================================================"
echo

# 1) Docker (si falta)
if ! command -v docker >/dev/null 2>&1; then
  echo ">> Instalando Docker..."
  curl -fsSL https://get.docker.com | sh
else
  echo ">> Docker ya está instalado."
fi

# 2) Configuración (interactiva)
echo
echo ">> Cargá los datos del bot:"
read -rp "   Dominio del bot (ej. bot.tudominio.com): " AGENT_DOMAIN
read -rp "   Token de WhatsApp: " WHATSAPP_ACCESS_TOKEN
read -rp "   API key de Anthropic (sk-ant-...): " ANTHROPIC_API_KEY
read -rp "   Celular para avisos (549261..., Enter para omitir): " CORREDOR_NOTIFY_NUMBER

if [ -z "${AGENT_DOMAIN}" ] || [ -z "${WHATSAPP_ACCESS_TOKEN}" ] || [ -z "${ANTHROPIC_API_KEY}" ]; then
  echo "!! Faltan datos obligatorios (dominio, token o API key). Volvé a correr el script."
  exit 1
fi

# 3) Escribir .env (los IDs ya vienen prellenados; se pueden editar luego)
cat > .env <<EOF
WHATSAPP_VERIFY_TOKEN=claridad-total-verify
WHATSAPP_ACCESS_TOKEN=${WHATSAPP_ACCESS_TOKEN}
WHATSAPP_PHONE_NUMBER_ID=1209516492249572
WHATSAPP_BUSINESS_ACCOUNT_ID=26903216089352293
GRAPH_API_VERSION=v21.0
TEMPLATE_LANG=es_AR
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
AGENT_MODEL=claude-sonnet-5
CORREDOR_NOTIFY_NUMBER=${CORREDOR_NOTIFY_NUMBER}
AGENT_DOMAIN=${AGENT_DOMAIN}
EOF
chmod 600 .env
echo ">> .env creado."

# 4) Levantar los contenedores (app + Caddy con HTTPS automático)
echo ">> Levantando contenedores (esto compila la imagen la primera vez)..."
docker compose up -d --build

echo
echo "======================================================"
echo "  Listo ✅"
echo "  Salud:   https://${AGENT_DOMAIN}/health"
echo "  Webhook: https://${AGENT_DOMAIN}/webhook"
echo "  Verify token: claridad-total-verify"
echo "  Panel:   https://${AGENT_DOMAIN}/panel"
echo
echo "  Caddy puede tardar ~1 min en sacar el certificado HTTPS."
echo "  Ver logs:  docker compose logs -f app"
echo "======================================================"
