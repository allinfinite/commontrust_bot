from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # HTTP API auth
    api_token: str = Field(default="", alias="COMMONTRUST_API_TOKEN")

    # PocketBase (used as ledger store and/or hub remote config store)
    pocketbase_url: str = Field(default="http://localhost:8090", alias="POCKETBASE_URL")
    pocketbase_admin_token: str | None = Field(default=None, alias="POCKETBASE_ADMIN_TOKEN")
    pocketbase_admin_email: str | None = Field(default=None, alias="POCKETBASE_ADMIN_EMAIL")
    pocketbase_admin_password: str | None = Field(default=None, alias="POCKETBASE_ADMIN_PASSWORD")

    # Credit policy (reputation-based by default)
    credit_base_limit: int = Field(default=100, alias="CREDIT_BASE_LIMIT")
    credit_per_deal: int = Field(default=50, alias="CREDIT_PER_DEAL")
    credit_limit_refresh_ttl_seconds: int = Field(default=300, alias="CREDIT_LIMIT_REFRESH_TTL_SECONDS")

    # Hub mode (optional): store and proxy per-chat remote ledger endpoints.
    ledger_mode: str = Field(default="local", alias="LEDGER_MODE")  # "local" | "hub"
    hub_remote_token_encryption_key: str | None = Field(
        default=None, alias="HUB_REMOTE_TOKEN_ENCRYPTION_KEY"
    )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token and self.api_token.strip())


api_settings = ApiSettings()

