"""Configuración cargada desde variables de entorno (.env)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # WhatsApp Cloud API
    whatsapp_verify_token: str = "claridad-total-verify"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    graph_api_version: str = "v21.0"

    # Claude
    anthropic_api_key: str = ""
    agent_model: str = "claude-sonnet-5"

    # Negocio
    corredor_notify_number: str = ""

    @property
    def graph_url(self) -> str:
        return (
            f"https://graph.facebook.com/{self.graph_api_version}"
            f"/{self.whatsapp_phone_number_id}/messages"
        )

    @property
    def whatsapp_ready(self) -> bool:
        return bool(self.whatsapp_access_token and self.whatsapp_phone_number_id)


settings = Settings()
