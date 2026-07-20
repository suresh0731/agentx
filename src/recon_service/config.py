from pydantic_settings import BaseSettings, SettingsConfigDict


class ReconSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RECON_")

    app_name: str = "AgentX Reconciliation Service"
    host: str = "127.0.0.1"
    port: int = 8002
    debug: bool = True


settings = ReconSettings()
