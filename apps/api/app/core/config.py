from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Procuratio API"
    app_version: str = "0.1.0"

    database_url: str
    redis_url: str
    jwt_access_secret: str = "change_me"
    jwt_refresh_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_access_expires_minutes: int = 30
    jwt_refresh_expires_minutes: int = 60 * 24 * 7
    payment_webhook_token: str = "change_me"
    stripe_secret_key: str = ""
    stripe_checkout_currency: str = "eur"
    cors_allow_origins: str = "*"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
