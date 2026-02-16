from __future__ import annotations

from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from commontrust_credit_bot.api_client import ApiError, api_client
from commontrust_credit_bot.config import credit_settings


router = Router()


async def _is_group_admin(message: Message) -> bool:
    # Super-admin override (useful for testing and emergency ops).
    if message.from_user.id in credit_settings.super_admin_user_ids:
        return True
    # If aiogram Message has a bot instance, check Telegram admin roles.
    bot = getattr(message, "bot", None)
    if bot is None:
        return False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    except Exception:
        return False
    status = getattr(member, "status", None)
    return status in ("administrator", "creator")


@router.message(Command("enable_credit"))
async def cmd_enable_credit(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group.")
        return
    if not await _is_group_admin(message):
        await message.answer("Only group admins can use this command.")
        return

    args = (message.text or "").split(maxsplit=2)
    currency_name = args[1] if len(args) > 1 else "Credit"
    currency_symbol = args[2] if len(args) > 2 else "Cr"

    try:
        await api_client.enable_credit(message.chat.id, message.chat.title, currency_name, currency_symbol)
        await message.answer(
            f"Mutual credit enabled for this group!\n\n"
            f"<b>Currency:</b> {currency_name} ({currency_symbol})\n"
            f"Members can now use /pay and /balance commands.",
            parse_mode="HTML",
        )
    except ApiError as e:
        await message.answer(f"Error: {e.detail}")


@router.message(Command("freeze"))
async def cmd_freeze(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group.")
        return
    if not await _is_group_admin(message):
        await message.answer("Only group admins can use this command.")
        return
    if not message.reply_to_message:
        await message.answer("Reply to a user's message to freeze their credit account.")
        return

    target = message.reply_to_message.from_user
    try:
        await api_client.set_credit_limit(message.chat.id, target.id, credit_limit=0)
        await message.answer(
            f"{html.bold(target.full_name)}'s credit account has been frozen (limit set to 0).",
            parse_mode="HTML",
        )
    except ApiError as e:
        await message.answer(f"Error: {e.detail}")


@router.message(Command("setcredit"))
async def cmd_setcredit(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group.")
        return
    if not await _is_group_admin(message):
        await message.answer("Only group admins can use this command.")
        return
    if not message.reply_to_message:
        await message.answer("Reply to a user's message to set their credit limit.")
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /setcredit amount")
        return
    try:
        amount = int(args[1])
    except ValueError:
        await message.answer("Amount must be a number.")
        return

    target = message.reply_to_message.from_user
    try:
        await api_client.set_credit_limit(message.chat.id, target.id, credit_limit=amount)
        await message.answer(
            f"{html.bold(target.full_name)}'s credit limit set to {amount}.",
            parse_mode="HTML",
        )
    except ApiError as e:
        await message.answer(f"Error: {e.detail}")


@router.message(Command("checkzero"))
async def cmd_checkzero(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group.")
        return
    if not await _is_group_admin(message):
        await message.answer("Only group admins can use this command.")
        return
    try:
        result = await api_client.verify_zero_sum(message.chat.id)
        status = "Valid" if result.get("is_zero_sum") else "Invalid"
        await message.answer(
            f"<b>Zero-Sum Verification</b>\n\n"
            f"<b>Status:</b> {status}\n"
            f"<b>Total Balance:</b> {result.get('total_balance')}\n"
            f"<b>Accounts:</b> {result.get('account_count')}",
            parse_mode="HTML",
        )
    except ApiError as e:
        await message.answer(f"Error: {e.detail}")


@router.message(Command("setledger"))
async def cmd_setledger(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group.")
        return
    if not await _is_group_admin(message):
        await message.answer("Only group admins can use this command.")
        return

    args = (message.text or "").split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /setledger base_url token")
        return
    base_url = args[1]
    token = args[2]
    try:
        await api_client.set_remote_ledger(message.chat.id, base_url=base_url, token=token)
        await message.answer(f"Remote ledger set for this chat: {base_url}")
    except ApiError as e:
        await message.answer(f"Error: {e.detail}")


@router.message(Command("clearledger"))
async def cmd_clearledger(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group.")
        return
    if not await _is_group_admin(message):
        await message.answer("Only group admins can use this command.")
        return
    try:
        await api_client.clear_remote_ledger(message.chat.id)
        await message.answer("Remote ledger cleared for this chat.")
    except ApiError as e:
        await message.answer(f"Error: {e.detail}")

