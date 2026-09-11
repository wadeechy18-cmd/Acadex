from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg2://acadex:acadex@localhost:5432/acadex"

    secret_key: str = "change-me-to-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    cors_origins: str = "http://localhost:3000"

    # Used to turn locally-stored file keys into absolute URLs the frontend (a
    # separate origin) can actually load.
    public_base_url: str = "http://localhost:8000"

    storage_backend: str = "local"
    storage_local_path: str = "./uploads"
    storage_s3_bucket: str | None = None
    storage_s3_region: str | None = None
    storage_s3_access_key: str | None = None
    storage_s3_secret_key: str | None = None
    storage_s3_endpoint_url: str | None = None

    # AI is entirely optional -- leave anthropic_api_key unset and every AI
    # endpoint responds 503 rather than the app failing to start. See
    # docs/LESSON_PLANNER_ARCHITECTURE.md section 10.
    anthropic_api_key: str | None = None
    ai_model: str = "claude-opus-5"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
