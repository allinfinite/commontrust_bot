from __future__ import annotations

import asyncio
import sys

from telethon import TelegramClient

from commontrust_userbot.config import userbot_settings


async def authenticate_user() -> None:
    if not userbot_settings.is_configured:
        raise RuntimeError(
            "Userbot is not configured. Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE."
        )

    client = TelegramClient(
        userbot_settings.user_session_name,
        userbot_settings.telegram_api_id,
        userbot_settings.telegram_api_hash,
    )
    try:
        await client.start(phone=userbot_settings.telegram_phone)
        me = await client.get_me()
        username = getattr(me, "username", None) or ""
        print(f"Authenticated as @{username} (ID: {me.id})")
        print(f"Session file: {userbot_settings.user_session_name}.session")
    finally:
        await client.disconnect()


def run() -> None:
    try:
        asyncio.run(authenticate_user())
    except KeyboardInterrupt:
        return
    except Exception as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    run()

