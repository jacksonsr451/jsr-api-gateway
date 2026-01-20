from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "api-gateway"
    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def debug(self) -> bool:
        return self.app_env.lower() != "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
