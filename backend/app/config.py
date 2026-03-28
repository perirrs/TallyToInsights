from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "TallyToInsights"
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Render provides DATABASE_URL as "postgres://..." — SQLAlchemy needs "postgresql://"
    DATABASE_URL: str = "sqlite:///./tallyinsights.db"

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 200

    # Comma-separated list of allowed CORS origins (add your GitHub Pages URL here)
    CORS_ORIGINS: str = "*"

    COMPANY_FINANCIAL_YEAR_START_MONTH: int = 4  # April

    @field_validator("DATABASE_URL")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        # Render / Heroku legacy format uses postgres:// which SQLAlchemy 2.x rejects
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    model_config = {"env_file": ".env"}


settings = Settings()

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

