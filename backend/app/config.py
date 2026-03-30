from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "TallyToInsights"
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    DATABASE_URL: str = "sqlite:///./tallyinsights.db"

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 200

    # Comma-separated CORS origins — set via env var on Railway
    CORS_ORIGINS: str = "*"

    COMPANY_FINANCIAL_YEAR_START_MONTH: int = 4  # April

    @field_validator("DATABASE_URL")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    model_config = {"env_file": ".env"}


settings = Settings()

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
