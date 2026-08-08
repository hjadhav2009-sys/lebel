from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MMS Catalog API"
    database_url: str = "postgresql+psycopg://mms:mms@localhost:5432/mms"
    secret_key: str = "development-only-change-me"
    cors_origins: str = "http://localhost:5173"
    enable_print_simulation: bool = False
    print_transport_enabled: bool = False
    allow_unapproved_test_prints: bool = True
    print_artifact_root: str = "../runtime/print_artifacts"
    agent_pairing_ttl_seconds: int = 600
    agent_lease_seconds: int = 60
    max_labels_per_job: int = 5000
    max_print_artifact_bytes: int = 20_000_000
    max_preview_bytes: int = 2_000_000

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MMS_", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
