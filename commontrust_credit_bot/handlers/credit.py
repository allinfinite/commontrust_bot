from __future__ import annotations

from types import SimpleNamespace

from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from commontrust_credit_bot.api_client import ApiError, api_client


router = Router()


def _normalize_username(username: str | None) -> str | None:
    if not username:
        return None
    value = username.strip().lstrip("@").lower()
    return value or None


@router.message(Command("pay"))
async def cmd_pay(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group with mutual credit enabled.")
        return

    args = (message.text or "").split(maxsplit=3)
    if len(args) < 2:
        await message.answer("Usage: /pay <amount> [description] OR /pay @username <amount> [description]")
        return

    payee = None
    amount = None
    description = None

    if args[1].startswith("@"):
        if len(args) < 3:
            await message.answer("Usage: /pay @username <amount> [description]")
            return
        mention = args[1]
        try:
            amount = int(args[2])
        except ValueError:
            await message.answer("Amount must be a number.")
            return
        description = args[3] if len(args) > 3 else None

        try:
            payee_member = await api_client.member_by_username(mention)
        except ApiError:
            await message.answer(
                f"User {mention} was not found. Ask them to send a message first so I can register their username."
            )
            return
        payee = SimpleNamespace(
            id=payee_member.get("telegram_user_id"),
            username=payee_member.get("username"),
            full_name=payee_member.get("display_name") or f"@{payee_member.get('username')}",
        )
    else:
        if not message.reply_to_message:
            await message.answer("Reply to a user's message or use /pay @username <amount> [description].")
            return
        try:
            amount = int(args[1])
        except ValueError:
            await message.answer("Amount must be a number.")
            return
        description = args[2] if len(args) > 2 else None
        payee = message.reply_to_message.from_user

    if payee.id == message.from_user.id:
        await message.answer("You cannot send credits to yourself.")
        return

    # Keep identity mapping fresh for username-based payments.
    await api_client.upsert_member(
        telegram_user_id=message.from_user.id,
        username=_normalize_username(message.from_user.username),
        display_name=message.from_user.full_name,
    )
    await api_client.upsert_member(
        telegram_user_id=payee.id,
        username=_normalize_username(getattr(payee, "username", None)),
        display_name=getattr(payee, "full_name", None),
    )

    idempotency_key = f"{message.chat.id}:{getattr(message, 'message_id', 0)}"

    try:
        result = await api_client.pay(
            telegram_chat_id=message.chat.id,
            payer_telegram_user_id=message.from_user.id,
            payee_telegram_user_id=payee.id,
            amount=amount,
            description=description,
            idempotency_key=idempotency_key,
        )

        currency = result.get("symbol", "Cr")
        await message.answer(
            f"Payment successful!\n\n"
            f"<b>Amount:</b> {amount} {currency}\n"
            f"<b>To:</b> {html.bold(payee.full_name)}\n"
            f"<b>Your new balance:</b> {result.get('new_payer_balance')} {currency}\n"
            f"{f'<b>Note:</b> {description}' if description else ''}",
            parse_mode="HTML",
        )
    except ApiError as e:
        await message.answer(f"Payment failed: {e.detail}")


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group with mutual credit enabled.")
        return

    await api_client.upsert_member(
        telegram_user_id=message.from_user.id,
        username=_normalize_username(message.from_user.username),
        display_name=message.from_user.full_name,
    )

    try:
        info = await api_client.balance(message.chat.id, message.from_user.id)
        await message.answer(
            f"<b>Your Balance</b>\n\n"
            f"<b>Balance:</b> {info['balance']} {info['symbol']}\n"
            f"<b>Credit Limit:</b> {info['credit_limit']} {info['symbol']}\n"
            f"<b>Available:</b> {info['available']} {info['symbol']}",
            parse_mode="HTML",
        )
    except ApiError as e:
        await message.answer(f"Error: {e.detail}")


@router.message(Command("transactions"))
async def cmd_transactions(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group with mutual credit enabled.")
        return

    try:
        result = await api_client.transactions(message.chat.id, message.from_user.id, limit=10)
        items = result.get("items", [])
        if not items:
            await message.answer("No transactions found.")
            return

        lines = ["<b>Recent Transactions</b>\n"]
        for tx in items:
            amount = int(tx.get("amount", 0) or 0)
            direction = tx.get("direction")
            sign = "-" if direction == "sent" else "+"
            other = tx.get("other_display_name") or (
                f"@{tx.get('other_username')}" if tx.get("other_username") else "unknown"
            )
            created = str(tx.get("created", ""))[:10]
            desc = tx.get("description")
            lines.append(
                f"• {sign}{amount} - {html.quote(other)} - {created}{f' - {html.quote(str(desc))}' if desc else ''}"
            )
        await message.answer("\n".join(lines), parse_mode="HTML")
    except ApiError as e:
        await message.answer(f"Error: {e.detail}")
