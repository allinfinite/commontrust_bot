from __future__ import annotations

from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"Mutual Credit Bot is active, {html.bold(message.from_user.full_name)}.\n\n"
        "Use /help to see available commands."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    help_text = """
<b>Mutual Credit Bot Commands</b>

<b>Credit</b>
/pay (reply) amount [description] - Send credits to user
/pay @username amount [description] - Send credits by username
/balance - Check your credit balance
/transactions - View recent transactions

<b>Admin</b>
/enable_credit [currency_name] [currency_symbol] - Enable mutual credit in group
/setcredit (reply) amount - Set user's credit limit
/freeze (reply) [reason] - Freeze user's credit account (sets limit to 0)
/checkzero - Verify zero-sum property for the group

<b>Federation (Hub)</b>
/setledger base_url token - Route this chat to a remote ledger API (hub mode)
/clearledger - Remove remote ledger routing for this chat
"""
    await message.answer(help_text, parse_mode="HTML")

