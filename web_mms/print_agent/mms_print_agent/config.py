from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    server_url: str = "http://127.0.0.1:8000"
    agent_name: str = "MMS Windows Print Agent"
    poll_seconds: float = 3
    heartbeat_seconds: float = 20
    transport_enabled: bool = False
    dry_run: bool = True
    config_dir: Path = Path.home() / "AppData" / "Local" / "MMSPrintAgent"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_prefix="MMS_AGENT_", env_file=".env", extra="ignore")

    @property
    def real_transport_allowed(self) -> bool:
        return self.transport_enabled and not self.dry_run
