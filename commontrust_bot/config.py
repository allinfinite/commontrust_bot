from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(..., description="Telegram bot token from @BotFather")

    pocketbase_url: str = Field(
        default="http://localhost:8090", description="PocketBase server URL"
    )
    pocketbase_admin_email: str = Field(..., description="PocketBase admin email")
    pocketbase_admin_password: str = Field(..., description="PocketBase admin password")

    admin_user_ids: list[int] = Field(default_factory=list, description="Telegram user IDs of bot admins")

    credit_base_limit: int = Field(default=100, description="Base credit limit for new members")
    credit_per_deal: int = Field(default=50, description="Credit limit increase per verified deal")

    @property
    def is_configured(self) -> bool:
        return bool(self.telegram_bot_token and self.pocketbase_admin_email)


settings = Settings()
