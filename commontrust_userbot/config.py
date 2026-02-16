from __future__ import annotations

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class UserbotSettings(BaseSettings):
    # Keep consistent with the rest of this repo: allow local overrides in .env.local.
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # MTProto (user account) credentials from https://my.telegram.org/apps
    telegram_api_id: int = Field(default=0, alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(default="", alias="TELEGRAM_API_HASH")
    telegram_phone: str = Field(default="", alias="TELEGRAM_PHONE")

    # Telethon stores sessions as "<name>.session". Default is repo-local so it works out of the box.
    user_session_name: str = Field(
        default_factory=lambda: os.environ.get(
            "USER_SESSION_NAME",
            os.path.join(os.getcwd(), ".data", "commontrust_user"),
        )
    )

    # Optional: limit processing to a single chat/group.
    target_chat_id: int | None = Field(default=None, alias="TARGET_CHAT_ID")

    # Optional: allowlist for private (DM) admin commands.
    admin_user_ids: list[int] = Field(default_factory=list, alias="ADMIN_USER_IDS")
    # Accept either JSON (e.g. ["alice","bob"]) or a comma-separated string ("alice,bob").
    admin_usernames: list[str] | str = Field(default_factory=list, alias="ADMIN_USERNAMES")

    def admin_username_set(self) -> set[str]:
        v = self.admin_usernames
        if isinstance(v, list):
            return {str(x).strip().lower().lstrip("@") for x in v if str(x).strip()}
        raw = str(v or "").strip()
        if not raw:
            return set()
        # Best effort: allow "alice,bob" without requiring JSON list syntax.
        return {p.strip().lower().lstrip("@") for p in raw.split(",") if p.strip()}

    @property
    def is_configured(self) -> bool:
        return bool(self.telegram_api_id and self.telegram_api_hash and self.telegram_phone)


userbot_settings = UserbotSettings()
