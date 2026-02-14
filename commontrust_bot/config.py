from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Allow local overrides without touching .env (both are gitignored by default here).
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # Keep this optional at import-time so tooling/tests can import modules without
    # having to provision secrets. Runtime checks should use `is_configured`.
    telegram_bot_token: str = Field(default="", description="Telegram bot token from @BotFather")

    pocketbase_url: str = Field(
        default="http://localhost:8090", description="PocketBase server URL"
    )
    # Prefer a long-lived admin/superuser token (API key) instead of storing a password.
    pocketbase_admin_token: str | None = Field(
        default=None,
        description="PocketBase admin/superuser API token (preferred; sent as Authorization header)",
    )
    pocketbase_admin_email: str | None = Field(default=None, description="PocketBase admin/superuser email")
    pocketbase_admin_password: str | None = Field(
        default=None, description="PocketBase admin/superuser password"
    )

    admin_user_ids: list[int] = Field(default_factory=list, description="Telegram user IDs of bot admins")

    credit_base_limit: int = Field(default=100, description="Base credit limit for new members")
    credit_per_deal: int = Field(default=50, description="Credit limit increase per verified deal")

    commontrust_web_url: str = Field(
        default="",
        description="Optional public website base URL (e.g. https://commontrust.example.com)",
    )

    @property
    def is_configured(self) -> bool:
        has_pb_auth = bool(
            (self.pocketbase_admin_token and self.pocketbase_admin_token.strip())
            or (self.pocketbase_admin_email and self.pocketbase_admin_password)
        )
        return bool(self.telegram_bot_token and has_pb_auth)


settings = Settings()
