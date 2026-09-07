from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All values come from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Gate Access Management System"
    company_name: str = "Acme Industries"

    # Database
    database_url: str = "postgresql+psycopg2://gate:gate@localhost:5432/gate"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 8

    # Public base URL used to build pass links embedded in QR codes.
    public_base_url: str = "http://localhost:5173"

    # Document storage
    storage_dir: str = "./storage"
    max_upload_bytes: int = 10 * 1024 * 1024
    allowed_mime_types: str = "application/pdf,image/jpeg,image/png"

    # Verification rate limiting (per gate token bucket)
    verify_rate_limit: int = 60
    verify_rate_window_seconds: int = 60

    # First-run bootstrap account
    bootstrap_email: str = "admin@company.com"
    bootstrap_password: str = "ChangeMe123!"

    @property
    def allowed_mime_list(self) -> list[str]:
        return [m.strip() for m in self.allowed_mime_types.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
