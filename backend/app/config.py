from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "TallyToInsights"
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    DATABASE_URL: str = "sqlite:///./tallyinsights.db"

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 200

    REDIS_URL: str = "redis://localhost:6379/0"

    COMPANY_FINANCIAL_YEAR_START_MONTH: int = 4  # April

    model_config = {"env_file": ".env"}


settings = Settings()

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
