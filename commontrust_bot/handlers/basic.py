from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"Welcome to CommonTrust Bot, {html.bold(message.from_user.full_name)}!\n\n"
        "This bot helps you build reputation through verified deals and participate "
        "in mutual credit systems within your Telegram groups.\n\n"
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
/deal @user <description> - Create a new deal
/confirm <deal_id> - Confirm a pending deal
/complete <deal_id> - Mark a deal as completed
/review <deal_id> <rating 1-5> [comment] - Review a completed deal

<b>Credit</b>
/pay @user <amount> [description] - Send credits to user
/balance - Check your credit balance

<b>Reputation</b>
/reputation - View your reputation stats
/mydeals - List your deals

<b>Admin</b>
/enable_credit - Enable mutual credit in group
/warn @user <reason> - Warn a user
/mute @user <duration> <reason> - Mute a user
/ban @user <reason> - Ban a user
/freeze @user <reason> - Freeze user's credit account
/verify @user - Verify a member
"""
    await message.answer(help_text, parse_mode="HTML")
