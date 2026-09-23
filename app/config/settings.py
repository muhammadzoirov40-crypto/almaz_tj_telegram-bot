from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    bot_token: str = Field(default="", alias="BOT_TOKEN")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/freefire",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")

    # Payment provider
    payment_api_url: str = Field(default="", alias="PAYMENT_API_URL")
    payment_api_key: str = Field(default="", alias="PAYMENT_API_KEY")
    payment_webhook_secret: str = Field(default="", alias="PAYMENT_WEBHOOK_SECRET")

    # Top-Up provider
    topup_api_url: str = Field(default="", alias="TOPUP_API_URL")
    topup_api_key: str = Field(default="", alias="TOPUP_API_KEY")

    # Free Fire real API (aliases for top-up provider)
    free_fire_api_url: str = Field(default="", alias="FREE_FIRE_API_URL")
    free_fire_api_key: str = Field(default="", alias="FREE_FIRE_API_KEY")

    @property
    def effective_topup_api_url(self) -> str:
        return self.free_fire_api_url or self.topup_api_url

    @property
    def effective_topup_api_key(self) -> str:
        return self.free_fire_api_key or self.topup_api_key

    # Manual card payment (shown to user; copy + pay + send receipt)
    payment_card_number: str = Field(default="", alias="PAYMENT_CARD_NUMBER")
    payment_card_holder: str = Field(default="", alias="PAYMENT_CARD_HOLDER")

    # Providers: "mock" (MVP/dev) or "real" (production)
    payment_provider: str = Field(default="mock", alias="PAYMENT_PROVIDER")
    topup_provider: str = Field(default="mock", alias="TOPUP_PROVIDER")

    # Force subscribe: user must join this channel before using the bot.
    # Empty value disables the check. Examples: "@my_channel" or "-1001234567890"
    force_subscribe_channel: str = Field(
        default="@_ff_almaz_tj_", alias="FORCE_SUBSCRIBE_CHANNEL"
    )

    # App
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    use_webhooks: bool = Field(default=False, alias="USE_WEBHOOKS")
    webhook_base_url: str = Field(default="", alias="WEBHOOK_BASE_URL")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _split_admin_ids(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip().strip("[]")
            return [
                int(v.strip())
                for v in cleaned.split(",")
                if v.strip().lstrip("-").isdigit()
            ]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def is_admin_id(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids

    @property
    def force_subscribe_enabled(self) -> bool:
        return bool(self.force_subscribe_channel.strip())

    @property
    def force_subscribe_url(self) -> str:
        channel = self.force_subscribe_channel.strip()
        if channel.startswith("@"):
            return f"https://t.me/{channel[1:]}"
        if channel.lstrip("-").isdigit():
            return ""
        return channel if channel.startswith("http") else ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
