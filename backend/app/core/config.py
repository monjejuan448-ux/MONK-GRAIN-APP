"""Configuración de la aplicación cargada desde variables de entorno.

Si falta una variable obligatoria, la aplicación falla al arrancar con un
mensaje claro en vez de romperse más tarde en tiempo de ejecución.
"""

from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- Aplicación ----------
    app_name: str = "MONK GRAIN"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # ---------- Base de datos ----------
    database_url: str

    # ---------- Redis ----------
    redis_url: str = "redis://redis:6379/0"

    # ---------- Seguridad ----------
    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    password_min_length: int = 12
    email_verification_expire_hours: int = 24
    password_reset_expire_hours: int = 1

    # ---------- CORS ----------
    # `NoDecode` impide que pydantic-settings intente interpretar el valor como
    # JSON: sin él, una lista separada por comas falla antes de que el validador
    # de abajo llegue a ejecutarse.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # ---------- Límite de peticiones ----------
    rate_limit_login_per_minute: int = 5
    rate_limit_default_per_minute: int = 120

    # ---------- Almacenamiento ----------
    s3_endpoint_url: str = "http://minio:9000"
    s3_public_url: str = "http://localhost:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "monkgrain"
    s3_region: str = "us-east-1"
    max_upload_size_mb: int = 5
    max_document_size_mb: int = 10

    # ---------- Correo ----------
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = False
    mail_from: str = "no-reply@monkgrain.co"
    mail_from_name: str = "MONK GRAIN"

    # ---------- Negocio ----------
    default_currency: str = "COP"
    default_commission_rate: Decimal = Decimal("0.08")
    default_locale: str = "es-CO"
    low_stock_threshold: int = 5

    # ---------- Integraciones ----------
    payment_provider: Literal["simulated", "wompi", "mercadopago", "payu"] = "simulated"
    payment_webhook_secret: str = ""
    shipping_provider: Literal["simulated", "servientrega", "coordinadora", "interrapidisimo"] = (
        "simulated"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        """Permite declarar los orígenes separados por coma en el entorno."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("secret_key")
    @classmethod
    def reject_placeholder_secret(cls, value: str) -> str:
        """Impide que un valor de ejemplo llegue a un entorno real."""
        if "change_me" in value.lower():
            raise ValueError(
                "SECRET_KEY conserva el valor de ejemplo. "
                "Genera una clave real con: openssl rand -hex 32"
            )
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_document_size_bytes(self) -> int:
        return self.max_document_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración como singleton."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
