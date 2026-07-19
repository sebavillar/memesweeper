"""Configuración cargada desde variables de entorno (.env)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # WhatsApp Cloud API
    whatsapp_verify_token: str = "claridad-total-verify"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""  # WABA ID (para webhooks y plantillas)
    graph_api_version: str = "v21.0"
    template_lang: str = "es_AR"  # idioma por defecto de las plantillas
    whatsapp_ar_15: bool = False  # número de PRUEBA con celulares AR en formato viejo (15)

    # Claude
    anthropic_api_key: str = ""
    agent_model: str = "claude-sonnet-5"

    # Negocio
    corredor_notify_number: str = ""
    panel_password: str = ""  # si se define, el panel pide esta clave (usuario libre)
    agent_domain: str = ""    # dominio público (para URLs de fotos servidas por el server)

    # MercadoLibre (datos de oferta reales)
    meli_client_id: str = ""
    meli_client_secret: str = ""
    meli_access_token: str = ""  # opcional: token manual en vez de client_credentials

    # RE/MAX (scraping de su API JSON). URL base obtenida desde DevTools del navegador.
    remax_api_url: str = ""

    @property
    def graph_base(self) -> str:
        return f"https://graph.facebook.com/{self.graph_api_version}"

    @property
    def graph_url(self) -> str:
        return f"{self.graph_base}/{self.whatsapp_phone_number_id}/messages"

    @property
    def whatsapp_ready(self) -> bool:
        return bool(self.whatsapp_access_token and self.whatsapp_phone_number_id)


settings = Settings()
