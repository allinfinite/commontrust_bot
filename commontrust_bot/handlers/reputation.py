from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from commontrust_bot.services.deal import deal_service
from commontrust_bot.services.reputation import reputation_service

router = Router()


@router.message(Command("reputation"))
async def cmd_reputation(message: Message) -> None:
    target_user = (
        message.reply_to_message.from_user if message.reply_to_message else message.from_user
    )

    try:
        member = await reputation_service.get_or_create_member(
            target_user.id,
            target_user.username,
            target_user.full_name,
        )

        if member.get("scammer"):
            scammer_at = member.get("scammer_at", "Unknown")
            await message.answer(
                f"<b>⛔ CONFIRMED SCAMMER</b>\n\n"
                f"<b>User:</b> {html.bold(target_user.full_name)}\n"
                f"This user has been confirmed as a scammer and is banned from trading.\n"
                f"<b>Flagged on:</b> {scammer_at}",
                parse_mode="HTML",
            )
            return

        stats = await reputation_service.get_member_stats(member.get("id"))
        rep = stats.get("reputation", {})

        rating = rep.get("avg_rating", 0)
        stars = "⭐" * int(rating) if rating else "No ratings"

        await message.answer(
            f"<b>Reputation Profile</b>\n\n"
            f"<b>User:</b> {html.bold(target_user.full_name)}\n"
            f"<b>Verified Deals:</b> {rep.get('verified_deals', 0)}\n"
            f"<b>Average Rating:</b> {stars} ({rating:.1f}/5)\n"
            f"<b>Total Reviews:</b> {rep.get('total_reviews', 0)}",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("mydeals"))
async def cmd_mydeals(message: Message) -> None:
    try:
        member = await reputation_service.get_or_create_member(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )

        deals = await reputation_service.get_member_deals(member.get("id"), limit=10)

        if not deals:
            await message.answer("You have no deals yet. Create one with /deal")
            return

        lines = ["<b>Your Deals</b>\n"]

        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "in_progress": "🔄",
            "completed": "✨",
            "cancelled": "❌",
            "disputed": "⚠️",
        }

        for deal in deals:
            emoji = status_emoji.get(deal.get("status", ""), "❓")
            description = deal.get("description", "No description")[:30]
            lines.append(f"{emoji} <b>{deal['id'][:8]}</b> - {description}")

        lines.append("\nUse /dealinfo deal_id for more details")

        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    try:
        member = await reputation_service.get_or_create_member(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )

        stats = await reputation_service.get_member_stats(member.get("id"))

        await message.answer(
            f"<b>Your Statistics</b>\n\n"
            f"<b>Total Deals:</b> {stats['total_deals']}\n"
            f"<b>Completed:</b> {stats['completed_deals']}\n"
            f"<b>Pending:</b> {stats['pending_deals']}\n"
            f"<b>Credit Limit:</b> {stats['credit_limit']} Cr",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("pending"))
async def cmd_pending(message: Message) -> None:
    try:
        pending = await deal_service.get_pending_deals_for_user(message.from_user.id)

        if not pending:
            await message.answer("You have no pending deals.")
            return

        lines = ["<b>Pending Deals</b>\n"]

        for deal in pending:
            description = deal.get("description", "No description")[:40]
            lines.append(f"⏳ <b>{deal['id'][:8]}</b> - {description}")

        lines.append("\nConfirm with /confirm deal_id")

        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("active"))
async def cmd_active(message: Message) -> None:
    try:
        active = await deal_service.get_active_deals_for_user(message.from_user.id)

        if not active:
            await message.answer("You have no active deals.")
            return

        lines = ["<b>Active Deals</b>\n"]

        for deal in active:
            status = deal.get("status", "unknown")
            emoji = "✅" if status == "confirmed" else "🔄"
            description = deal.get("description", "No description")[:40]
            lines.append(f"{emoji} <b>{deal['id'][:8]}</b> - {description}")

        lines.append("\nComplete with /complete deal_id")

        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Error: {e}")
