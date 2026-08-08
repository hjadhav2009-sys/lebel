from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MMS Catalog API"
    database_url: str = "postgresql+psycopg://mms:mms@localhost:5432/mms"
    secret_key: str = "development-only-change-me"
    cors_origins: str = "http://localhost:5173"
    enable_print_simulation: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MMS_", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
