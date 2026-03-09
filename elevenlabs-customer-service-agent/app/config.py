# Settings, environment variables
import os
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings from environment."""

    # Database (accept either env var)
    database_url: str = Field(
        default="postgresql://localhost:5432/customer_service",
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_CONNECTION_STRING"),
    )

    # Redis
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379") or 6379)
    redis_username: str | None = os.getenv("REDIS_USERNAME")
    redis_password: str | None = os.getenv("REDIS_PASSWORD")

    # App
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    environment: str = os.getenv("ENVIRONMENT", "development")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
