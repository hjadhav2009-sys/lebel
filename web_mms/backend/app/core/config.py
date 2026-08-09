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
    auth_mode: str = "development"
    auth_cookie_secure: bool = False
    auth_session_minutes: int = 480

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MMS_", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

    def validate_transport_gate(self) -> None:
        if not self.print_transport_enabled:return
        if self.auth_mode!="local":raise ValueError("PRINT_TRANSPORT_REQUIRES_LOCAL_AUTH")
        if self.secret_key=="development-only-change-me" or len(self.secret_key)<32:raise ValueError("PRINT_TRANSPORT_REQUIRES_STRONG_SECRET")
        if not self.auth_cookie_secure:raise ValueError("PRINT_TRANSPORT_REQUIRES_SECURE_COOKIE")


@lru_cache
def get_settings() -> Settings:
    return Settings()
