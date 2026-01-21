from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "api-gateway"
    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_allow_origins: list[str] = ["*"]
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    cors_allow_credentials: bool = False
    auth_service_base_url: str = "http://auth-service:8000"
    auth_service_validate_path: str = "/auth/validate"
    auth_service_authorize_path: str = "/auth/authorize"
    auth_service_timeout_seconds: float = 5.0

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator(
        "cors_allow_origins", "cors_allow_methods", "cors_allow_headers", mode="before"
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
