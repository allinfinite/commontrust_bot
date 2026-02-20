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
    commontrust_howto_image_url: str = Field(
        default="",
        description="Optional public image URL sent to new users on /start",
    )
    review_response_secret: str = Field(
        default="",
        description="HMAC secret for signing review response links (shared with web app)",
    )

    venice_api_key: str = Field(default="", description="Venice.ai API key for report analysis")
    ai_model: str = Field(
        default="llama-3.3-70b",
        description="Venice.ai model for report analysis (e.g. llama-3.3-70b, deepseek-ai-DeepSeek-R1)",
    )

    @property
    def is_configured(self) -> bool:
        has_pb_auth = bool(
            (self.pocketbase_admin_token and self.pocketbase_admin_token.strip())
            or (self.pocketbase_admin_email and self.pocketbase_admin_password)
        )
        return bool(self.telegram_bot_token and has_pb_auth)


settings = Settings()
