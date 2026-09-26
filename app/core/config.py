from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EVE Healthcare Booking API"
    environment: str = "development"
    database_url: str = "sqlite:///./eve_healthcare.db"
    secret_key: str = "development-only-secret-change-me"
    access_token_expire_minutes: int = 60
    redis_url: str | None = None
    rate_limit_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
