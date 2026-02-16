from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from commontrust_credit_bot.api_client import api_client
from commontrust_credit_bot.config import credit_settings
from commontrust_credit_bot.handlers import router

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    me = await bot.get_me()
    logger.info(f"Credit bot started as @{me.username}")


async def on_shutdown(bot: Bot) -> None:
    await api_client.close()
    await bot.session.close()


async def main() -> None:
    if not credit_settings.is_configured:
        logger.error("Credit bot is not configured. Set CREDIT_TELEGRAM_BOT_TOKEN and COMMONTRUST_API_TOKEN.")
        sys.exit(1)

    bot = Bot(
        token=credit_settings.effective_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Credit bot stopped by user")


def run() -> None:
    with suppress(KeyboardInterrupt):
        asyncio.run(main())


if __name__ == "__main__":
    run()

