from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import suppress

from telethon import TelegramClient, events

from commontrust_userbot.config import userbot_settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _is_admin(sender) -> bool:
    if not sender:
        return False
    sender_id = getattr(sender, "id", None)
    if isinstance(sender_id, int) and sender_id in (userbot_settings.admin_user_ids or []):
        return True
    username = (getattr(sender, "username", None) or "").lower().lstrip("@")
    if username and username in userbot_settings.admin_username_set():
        return True
    return False


async def main() -> None:
    if not userbot_settings.is_configured:
        logger.error(
            "Userbot is not configured. Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE."
        )
        sys.exit(1)

    client = TelegramClient(
        userbot_settings.user_session_name,
        userbot_settings.telegram_api_id,
        userbot_settings.telegram_api_hash,
    )

    await client.start(phone=userbot_settings.telegram_phone)
    me = await client.get_me()
    my_id = int(getattr(me, "id"))
    logger.info("Userbot started as @%s (ID: %s)", getattr(me, "username", ""), my_id)

    @client.on(events.NewMessage(incoming=True))
    async def on_message(event: events.NewMessage.Event) -> None:
        # Ignore self and Telegram service notifications.
        if event.sender_id in (my_id, 777000):
            return

        if userbot_settings.target_chat_id and event.chat_id != userbot_settings.target_chat_id:
            return

        text = (event.raw_text or "").strip()
        sender = await event.get_sender()

        # Minimal admin-only DM smoke test.
        if event.is_private and text == "/ping":
            # If an allowlist is configured, enforce it. Otherwise allow /ping for smoke tests.
            if userbot_settings.admin_user_ids or userbot_settings.admin_username_set():
                if not _is_admin(sender):
                    return
            await event.reply("pong")
            return

        # Default behavior for now: just log.
        sender_label = getattr(sender, "username", None) or getattr(sender, "first_name", None) or "unknown"
        logger.info("msg chat_id=%s from=%s: %s", event.chat_id, sender_label, text[:400])

    try:
        await client.run_until_disconnected()
    finally:
        await client.disconnect()


def run() -> None:
    with suppress(KeyboardInterrupt):
        asyncio.run(main())


if __name__ == "__main__":
    run()
