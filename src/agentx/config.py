from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="AGENTX_")

    app_name: str = "AgentX"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///file:agentx?mode=memory&cache=shared&uri=true"
    checkpoint_url: str = "sqlite:///file:agentx?mode=memory&cache=shared&uri=true"
    confidence_gate: float = 0.98
    default_user: str = "SCB User"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"]


settings = Settings()
