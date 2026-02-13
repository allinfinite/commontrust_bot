from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from commontrust_bot.config import settings
from commontrust_bot.pocketbase_client import pb_client
from commontrust_bot.services.mutual_credit import mutual_credit_service
from commontrust_bot.services.reputation import reputation_service

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids


@router.message(Command("enable_credit"))
async def cmd_enable_credit(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("This command can only be used in a group.")
        return

    if not is_admin(message.from_user.id):
        await message.answer("Only bot admins can use this command.")
        return

    args = message.text.split(maxsplit=2)
    currency_name = args[1] if len(args) > 1 else "Credit"
    currency_symbol = args[2] if len(args) > 2 else "Cr"

    try:
        group = await pb_client.group_get_or_create(
            message.chat.id,
            message.chat.title or "Group",
            mc_enabled=True,
        )

        mc_group = await mutual_credit_service.get_or_create_mc_group(
            group.get("id"),
            currency_name=currency_name,
            currency_symbol=currency_symbol,
        )

        await pb_client.update_record("groups", group.get("id"), {"mc_enabled": True})

        await message.answer(
            f"Mutual credit enabled for this group!\n\n"
            f"<b>Currency:</b> {currency_name} ({currency_symbol})\n"
            f"Members can now use /pay and /balance commands.",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("warn"))
async def cmd_warn(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Only bot admins can use this command.")
        return

    if not message.reply_to_message:
        await message.answer("Reply to a user's message to warn them.")
        return

    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "No reason provided"

    target = message.reply_to_message.from_user

    try:
        target_member = await reputation_service.get_or_create_member(
            target.id, target.username, target.full_name
        )

        group_id = None
        if message.chat.type != "private":
            group = await pb_client.group_get_or_create(
                message.chat.id, message.chat.title or "Group"
            )
            group_id = group.get("id")

        await pb_client.sanction_create(
            member_id=target_member.get("id"),
            group_id=group_id,
            sanction_type="warning",
            reason=reason,
        )

        await message.answer(
            f"⚠️ {html.bold(target.full_name)} has been warned.\n\n<b>Reason:</b> {reason}",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("mute"))
async def cmd_mute(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Only bot admins can use this command.")
        return

    if not message.reply_to_message:
        await message.answer("Reply to a user's message to mute them.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Usage: /mute <duration_hours> [reason]")
        return

    try:
        duration_hours = int(args[1])
    except ValueError:
        await message.answer("Duration must be a number (hours).")
        return

    reason = args[2] if len(args) > 2 else "No reason provided"
    target = message.reply_to_message.from_user

    try:
        target_member = await reputation_service.get_or_create_member(
            target.id, target.username, target.full_name
        )

        group_id = None
        if message.chat.type != "private":
            group = await pb_client.group_get_or_create(
                message.chat.id, message.chat.title or "Group"
            )
            group_id = group.get("id")

        from datetime import datetime, timedelta

        expires = (datetime.now() + timedelta(hours=duration_hours)).isoformat()

        await pb_client.sanction_create(
            member_id=target_member.get("id"),
            group_id=group_id,
            sanction_type="mute",
            reason=reason,
            expires_at=expires,
        )

        await message.answer(
            f"🔇 {html.bold(target.full_name)} has been muted for {duration_hours}h.\n\n<b>Reason:</b> {reason}",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("ban"))
async def cmd_ban(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Only bot admins can use this command.")
        return

    if not message.reply_to_message:
        await message.answer("Reply to a user's message to ban them.")
        return

    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "No reason provided"
    target = message.reply_to_message.from_user

    try:
        target_member = await reputation_service.get_or_create_member(
            target.id, target.username, target.full_name
        )

        group_id = None
        if message.chat.type != "private":
            group = await pb_client.group_get_or_create(
                message.chat.id, message.chat.title or "Group"
            )
            group_id = group.get("id")

        await pb_client.sanction_create(
            member_id=target_member.get("id"),
            group_id=group_id,
            sanction_type="ban",
            reason=reason,
        )

        await message.answer(
            f"🚫 {html.bold(target.full_name)} has been banned.\n\n<b>Reason:</b> {reason}",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("freeze"))
async def cmd_freeze(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Only bot admins can use this command.")
        return

    if message.chat.type == "private":
        await message.answer("This command can only be used in a group with mutual credit.")
        return

    if not message.reply_to_message:
        await message.answer("Reply to a user's message to freeze their credit account.")
        return

    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "No reason provided"
    target = message.reply_to_message.from_user

    try:
        target_member = await reputation_service.get_or_create_member(
            target.id, target.username, target.full_name
        )

        group = await pb_client.group_get(message.chat.id)
        if not group or not group.get("mc_enabled"):
            await message.answer("Mutual credit is not enabled in this group.")
            return

        mc_group = await pb_client.mc_group_get(group.get("id"))
        if not mc_group:
            await message.answer("Mutual credit group not found.")
            return

        account = await pb_client.mc_account_get(mc_group.get("id"), target_member.get("id"))
        if not account:
            await message.answer("User does not have a credit account in this group.")
            return

        await pb_client.update_record("mc_accounts", account.get("id"), {"credit_limit": 0})

        await pb_client.sanction_create(
            member_id=target_member.get("id"),
            group_id=group.get("id"),
            sanction_type="freeze",
            reason=reason,
        )

        await message.answer(
            f"❄️ {html.bold(target.full_name)}'s credit account has been frozen.\n\n<b>Reason:</b> {reason}",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("verify"))
async def cmd_verify(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Only bot admins can use this command.")
        return

    if not message.reply_to_message:
        await message.answer("Reply to a user's message to verify them.")
        return

    target = message.reply_to_message.from_user

    try:
        target_member = await reputation_service.get_or_create_member(
            target.id, target.username, target.full_name
        )

        success = await reputation_service.verify_member(target_member.get("id"))

        if success:
            await message.answer(
                f"✅ {html.bold(target.full_name)} has been verified.",
                parse_mode="HTML",
            )
        else:
            await message.answer("Failed to verify member.")
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("setcredit"))
async def cmd_setcredit(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Only bot admins can use this command.")
        return

    if message.chat.type == "private":
        await message.answer("This command can only be used in a group with mutual credit.")
        return

    if not message.reply_to_message:
        await message.answer("Reply to a user's message to set their credit limit.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /setcredit <amount>")
        return

    try:
        amount = int(args[1])
    except ValueError:
        await message.answer("Amount must be a number.")
        return

    target = message.reply_to_message.from_user

    try:
        target_member = await reputation_service.get_or_create_member(
            target.id, target.username, target.full_name
        )

        group = await pb_client.group_get(message.chat.id)
        if not group or not group.get("mc_enabled"):
            await message.answer("Mutual credit is not enabled in this group.")
            return

        mc_group = await pb_client.mc_group_get(group.get("id"))
        if not mc_group:
            await message.answer("Mutual credit group not found.")
            return

        await mutual_credit_service.update_credit_limit(
            mc_group.get("id"), target_member.get("id"), amount
        )

        currency = mc_group.get("currency_symbol", "Cr")

        await message.answer(
            f"💳 {html.bold(target.full_name)}'s credit limit set to {amount} {currency}.",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("checkzero"))
async def cmd_checkzero(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Only bot admins can use this command.")
        return

    if message.chat.type == "private":
        await message.answer("This command can only be used in a group with mutual credit.")
        return

    try:
        group = await pb_client.group_get(message.chat.id)
        if not group or not group.get("mc_enabled"):
            await message.answer("Mutual credit is not enabled in this group.")
            return

        mc_group = await pb_client.mc_group_get(group.get("id"))
        if not mc_group:
            await message.answer("Mutual credit group not found.")
            return

        result = await mutual_credit_service.verify_zero_sum(mc_group.get("id"))

        status = "✅ Valid" if result["is_zero_sum"] else "❌ Invalid"
        await message.answer(
            f"<b>Zero-Sum Verification</b>\n\n"
            f"<b>Status:</b> {status}\n"
            f"<b>Total Balance:</b> {result['total_balance']}\n"
            f"<b>Accounts:</b> {result['account_count']}",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")
