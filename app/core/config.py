from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="api-gateway", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    cors_allow_origins: list[str] = Field(default=["*"], alias="CORS_ALLOW_ORIGINS")
    cors_allow_methods: list[str] = Field(default=["*"], alias="CORS_ALLOW_METHODS")
    cors_allow_headers: list[str] = Field(default=["*"], alias="CORS_ALLOW_HEADERS")
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")
    auth_service_base_url: str = Field(
        default="http://auth-service:8000", alias="AUTH_SERVICE_BASE_URL"
    )
    auth_service_validate_path: str = Field(
        default="/auth/validate", alias="AUTH_SERVICE_VALIDATE_PATH"
    )
    auth_service_authorize_path: str = Field(
        default="/auth/authorize", alias="AUTH_SERVICE_AUTHORIZE_PATH"
    )
    auth_service_timeout_seconds: float = Field(
        default=5.0, alias="AUTH_SERVICE_TIMEOUT_SECONDS"
    )
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60, alias="RATE_LIMIT_WINDOW_SECONDS"
    )
    rate_limit_exempt_paths: list[str] = Field(
        default=[], alias="RATE_LIMIT_EXEMPT_PATHS"
    )
    rate_limit_key_header: str = Field(
        default="X-Forwarded-For", alias="RATE_LIMIT_KEY_HEADER"
    )
    routes_config_path: str = Field(default="routes.yaml", alias="ROUTES_CONFIG_PATH")
    proxy_timeout_seconds: float = Field(default=10.0, alias="PROXY_TIMEOUT_SECONDS")
    routes_admin_permission: str = Field(
        default="gateway:routes:manage", alias="ROUTES_ADMIN_PERMISSION"
    )

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        case_sensitive=False,
        populate_by_name=True,
    )

    @field_validator(
        "cors_allow_origins",
        "cors_allow_methods",
        "cors_allow_headers",
        "rate_limit_exempt_paths",
        mode="before",
    )
    @classmethod
    def parse_list_settings(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                import json

                return json.loads(raw)
            return [item.strip() for item in raw.split(",") if item.strip()]
        return list(value)

    @property
    def debug(self) -> bool:
        return self.app_env.lower() != "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
