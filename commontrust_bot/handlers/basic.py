from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    # Deep-links are handled in `handlers/dm.py` (CommandStart). This is the
    # default /start response when there is no payload.
    await message.answer(
        f"Welcome to CommonTrust Bot, {html.bold(message.from_user.full_name)}!\n\n"
        "This bot helps you build reputation through verified deals and participate "
        "in verified deals within your Telegram groups.\n\n"
        "Use /help to see available commands."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    help_text = """
<b>CommonTrust Bot Commands</b>

<b>Basic</b>
/start - Start the bot
/help - Show this help message

<b>Deals</b>
/newdeal description - Create a private deal invite link (DM only; recommended)
/deal (reply) description - Create a new deal
/confirm deal_id - Confirm a pending deal
/complete deal_id - Mark a deal as completed
/review deal_id rating(1-5) [comment] - Review a completed deal

<b>Credit</b>
Mutual credit commands are handled by the separate Mutual Credit Bot.

<b>Reputation</b>
/reputation - View your reputation stats
/mydeals - List your deals

<b>Admin</b>
/warn (reply) reason - Warn a user
/mute (reply) duration_hours [reason] - Mute a user
/ban (reply) reason - Ban a user
/verify @user - Verify a member
"""
    await message.answer(help_text, parse_mode="HTML")
