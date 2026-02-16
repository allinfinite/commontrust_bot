from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from commontrust_bot.config import settings
from commontrust_bot.pocketbase_client import pb_client
from commontrust_bot.services.reputation import reputation_service

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids

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
        await message.answer("Usage: /mute duration_hours [reason]")
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
