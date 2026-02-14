from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from commontrust_bot.services.mutual_credit import InsufficientCreditError, mutual_credit_service
from commontrust_bot.services.reputation import reputation_service

router = Router()


async def get_mc_group_for_chat(chat_id: int) -> dict | None:
    from commontrust_bot.pocketbase_client import pb_client

    group = await pb_client.group_get(chat_id)
    if not group:
        return None

    if not group.get("mc_enabled"):
        return None

    mc_group = await pb_client.mc_group_get(group.get("id"))
    return mc_group


@router.message(Command("pay"))
async def cmd_pay(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group with mutual credit enabled.")
        return

    if not message.reply_to_message:
        await message.answer("Reply to a user's message to send them credits.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Usage: /pay amount [description] (reply to user)")
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

    mc_group = await get_mc_group_for_chat(message.chat.id)
    if not mc_group:
        await message.answer(
            "Mutual credit is not enabled in this group. An admin can enable it with /enable_credit"
        )
        return

    try:
        payer_member = await reputation_service.get_or_create_member(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )
        payee_member = await reputation_service.get_or_create_member(
            payee.id,
            payee.username,
            payee.full_name,
        )

        result = await mutual_credit_service.create_payment(
            mc_group_id=mc_group.get("id"),
            payer_member_id=payer_member.get("id"),
            payee_member_id=payee_member.get("id"),
            amount=amount,
            description=description,
        )

        currency = mc_group.get("currency_symbol", "Cr")

        await message.answer(
            f"Payment successful!\n\n"
            f"<b>Amount:</b> {amount} {currency}\n"
            f"<b>To:</b> {html.bold(payee.full_name)}\n"
            f"<b>Your new balance:</b> {result['new_payer_balance']} {currency}\n"
            f"{f'<b>Note:</b> {description}' if description else ''}",
            parse_mode="HTML",
        )
    except InsufficientCreditError as e:
        await message.answer(f"Payment failed: {e}")
    except ValueError as e:
        await message.answer(f"Payment failed: {e}")
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group with mutual credit enabled.")
        return

    mc_group = await get_mc_group_for_chat(message.chat.id)
    if not mc_group:
        await message.answer("Mutual credit is not enabled in this group.")
        return

    try:
        member = await reputation_service.get_or_create_member(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )

        balance_info = await mutual_credit_service.get_account_balance(
            mc_group_id=mc_group.get("id"),
            member_id=member.get("id"),
        )

        currency = mc_group.get("currency_symbol", "Cr")
        currency_name = mc_group.get("currency_name", "Credit")

        await message.answer(
            f"<b>Your {currency_name} Balance</b>\n\n"
            f"<b>Balance:</b> {balance_info['balance']} {currency}\n"
            f"<b>Credit Limit:</b> {balance_info['credit_limit']} {currency}\n"
            f"<b>Available:</b> {balance_info['available']} {currency}",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("transactions"))
async def cmd_transactions(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group with mutual credit enabled.")
        return

    mc_group = await get_mc_group_for_chat(message.chat.id)
    if not mc_group:
        await message.answer("Mutual credit is not enabled in this group.")
        return

    try:
        member = await reputation_service.get_or_create_member(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )

        transactions = await mutual_credit_service.get_transaction_history(
            mc_group_id=mc_group.get("id"),
            member_id=member.get("id"),
            limit=10,
        )

        if not transactions:
            await message.answer("No transactions found.")
            return

        currency = mc_group.get("currency_symbol", "Cr")
        lines = ["<b>Recent Transactions</b>\n"]

        for tx in transactions:
            amount = tx.get("amount", 0)
            is_sender = tx.get("payer_id") == member.get("id")
            sign = "-" if is_sender else "+"
            tx_amount = sign + str(amount)
            other_id = tx.get("payee_id") if is_sender else tx.get("payer_id")

            lines.append(f"• {tx_amount} {currency} - {tx.get('created', 'N/A')[:10]}")

        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Error: {e}")
