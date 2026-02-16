from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CreditBotSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    telegram_bot_token: str = Field(
        default="",
        alias="CREDIT_TELEGRAM_BOT_TOKEN",
        description="Telegram bot token for the credit bot",
    )

    # Fallback for single-bot environments.
    telegram_bot_token_fallback: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")

    commontrust_api_base_url: str = Field(default="http://localhost:8000", alias="COMMONTRUST_API_BASE_URL")
    commontrust_api_token: str = Field(default="", alias="COMMONTRUST_API_TOKEN")

    super_admin_user_ids: list[int] = Field(default_factory=list, alias="SUPER_ADMIN_USER_IDS")

    @property
    def effective_bot_token(self) -> str:
        return self.telegram_bot_token.strip() or self.telegram_bot_token_fallback.strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.effective_bot_token and self.commontrust_api_token and self.commontrust_api_base_url)


credit_settings = CreditBotSettings()

