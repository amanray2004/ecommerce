import os
from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

# Auto-load root .env when python-dotenv is available.
if load_dotenv:
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=False)


class Settings:
    """Application settings loaded from environment variables."""

    app_name: str = os.getenv("APP_NAME", "Multi-Tenant Ecommerce API")
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "")
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/ecommerce"
    )

    keycloak_issuer: str = os.getenv("KEYCLOAK_ISSUER", "")
    keycloak_audience: str = os.getenv("KEYCLOAK_AUDIENCE", "account")
    keycloak_public_key: str = os.getenv("KEYCLOAK_PUBLIC_KEY", "")
    keycloak_client_id: str = os.getenv("KEYCLOAK_CLIENT_ID", "")

    firebase_bucket: str = os.getenv("FIREBASE_BUCKET", "")
    firebase_credentials_path: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")

    default_page_limit: int = int(os.getenv("DEFAULT_PAGE_LIMIT", "20"))
    max_page_limit: int = int(os.getenv("MAX_PAGE_LIMIT", "100"))
    auto_create_tables: bool = os.getenv("AUTO_CREATE_TABLES", "false").lower() in {"1", "true", "yes"}
    seed_roles_on_startup: bool = os.getenv("SEED_ROLES_ON_STARTUP", "true").lower() in {"1", "true", "yes"}
    run_startup_tasks: bool = os.getenv("RUN_STARTUP_TASKS", "true").lower() in {"1", "true", "yes"}
    cors_allow_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ]
    cors_allow_origin_regex: str = os.getenv("CORS_ALLOW_ORIGIN_REGEX", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
