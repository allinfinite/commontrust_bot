import asyncio
import logging
import sys
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from commontrust_bot.config import settings
from commontrust_bot.handlers import router
from commontrust_bot.pocketbase_client import pb_client

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    logger.info("Starting bot...")

    try:
        await pb_client.authenticate()
        logger.info("Successfully authenticated with PocketBase")
    except Exception as e:
        logger.error(f"Failed to authenticate with PocketBase: {e}")
        sys.exit(1)

    me = await bot.get_me()
    logger.info(f"Bot started as @{me.username}")


async def on_shutdown(bot: Bot) -> None:
    logger.info("Shutting down bot...")
    await pb_client.close()


async def main() -> None:
    if not settings.is_configured:
        logger.error("Bot is not configured. Please set required environment variables.")
        sys.exit(1)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.session.close()


def run() -> None:
    with suppress(KeyboardInterrupt):
        asyncio.run(main())


if __name__ == "__main__":
    run()
