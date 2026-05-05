from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "sqlite:///./poster_engine.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_dir: str = "/data/storage"
    adobe_mode: str = "mock"
    adobe_api_key: str | None = None
    adobe_client_id: str | None = None
    canva_mode: str = "mock"
    canva_client_id: str | None = None
    canva_client_secret: str | None = None
    canva_access_token: str | None = None
    canva_api_base_url: str = "https://api.canva.com"
    adobe_api_base_url: str = "https://firefly-api.adobe.io"
    adobe_poll_interval_seconds: float = 1.0
    adobe_poll_max_attempts: int = 20
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    api_budget_per_project: int = 100
    idempotency_ttl_seconds: int = 3600
    request_log_level: str = "INFO"
    auth_jwt_secret: str = "change-me"
    auth_jwt_algorithm: str = "HS256"
    dev_internal_token_secret: str = "dev-internal-secret"
    storage_provider: str = "local"
    storage_bucket: str = "poster-engine"
    storage_region: str = "us-east-1"
    storage_endpoint_url: str | None = None
    storage_access_key_id: str | None = None
    storage_secret_access_key: str | None = None
    storage_signed_url_expiry_seconds: int = 86400
    billing_default_quota_per_month: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
