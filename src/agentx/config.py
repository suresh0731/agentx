from pathlib import Path

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

    # Folder ingest poller
    ingest_poll_enabled: bool = True
    ingest_poll_interval_seconds: int = 120
    ingest_watch_folder: str = "data/incoming"
    ingest_success_folder: str = "data/processed"
    ingest_failed_folder: str = "data/failed"
    ingest_review_folder: str = "data/review"

    # Enterprise IDP
    idp_token_url: str = (
        "https://sit-authn.idp.global.standardchartered.com"
        "/ns03/realms/internal-system/protocol/openid-connect/token"
    )
    idp_api_url: str = (
        "https://apigw.sea.dev.azure.scbdev.net"
        "/serving-endpoints/idp_inference_idp_poc_endpoint_v1/invocations"
    )
    idp_token_client_id: str = "sstm-ai-gbl-sys"
    idp_token_host: str = "hkis7m14522d602.hk.standardchartered.com"
    idp_client_id: str = "fee_agreement_extraction"
    idp_doc_type: str = "contract"
    idp_ocr_model: str = "ocr_mineru_v1"
    idp_cert_dir: str = ""
    idp_token_jar: str = "token-tool-candidate_20241105.4.jar"
    idp_keystore: str = "keystore.jks"
    idp_truststore: str = "sstm_rt_np.jks"
    idp_keystore_password: str = "scb@123"
    idp_truststore_password: str = ""
    idp_verify_ssl: bool = False
    idp_request_timeout_seconds: int = 360

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]


settings = Settings()
