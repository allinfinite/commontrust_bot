from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from commontrust_bot.services.deal import deal_service

router = Router()


def parse_mention(text: str) -> int | None:
    if text.startswith("@"):
        return text[1:]
    if text.startswith("[") and "]" in text:
        start = text.index("]") + 1
        if text[start:].startswith("(") and ")" in text[start:]:
            return text[start + 1 : text.index(")", start)]
    return None


@router.message(Command("deal"))
async def cmd_deal(message: Message) -> None:
    if not message.reply_to_message:
        await message.answer("Reply to a user's message to create a deal with them.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Usage: /deal <description>")
        return

    description = args[1] if len(args) == 2 else args[1] + " " + args[2]

    counterparty = message.reply_to_message.from_user
    if counterparty.id == message.from_user.id:
        await message.answer("You cannot create a deal with yourself.")
        return

    if not message.chat.id:
        await message.answer("This command can only be used in a group.")
        return

    try:
        result = await deal_service.create_deal(
            initiator_telegram_id=message.from_user.id,
            counterparty_telegram_id=counterparty.id,
            group_telegram_id=message.chat.id,
            description=description,
        )

        deal = result["deal"]
        await message.answer(
            f"Deal created!\n\n"
            f"<b>Deal ID:</b> {deal['id']}\n"
            f"<b>Description:</b> {description}\n"
            f"<b>Status:</b> Pending\n\n"
            f"{html.bold(counterparty.full_name)} can confirm with /confirm {deal['id']}",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Failed to create deal: {e}")


@router.message(Command("confirm"))
async def cmd_confirm(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /confirm <deal_id>")
        return

    deal_id = args[1].strip()

    try:
        result = await deal_service.confirm_deal(deal_id, message.from_user.id)
        await message.answer(
            f"Deal confirmed!\n\n"
            f"<b>Deal ID:</b> {deal_id}\n"
            f"<b>Status:</b> Confirmed\n\n"
            f"Both parties can now mark it as completed with /complete {deal_id}",
            parse_mode="HTML",
        )
    except ValueError as e:
        await message.answer(f"Failed to confirm deal: {e}")
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("complete"))
async def cmd_complete(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /complete <deal_id>")
        return

    deal_id = args[1].strip()

    try:
        result = await deal_service.complete_deal(deal_id, message.from_user.id)
        await message.answer(
            f"Deal completed!\n\n"
            f"<b>Deal ID:</b> {deal_id}\n"
            f"<b>Status:</b> Completed\n\n"
            f"Both parties can now leave a review with /review {deal_id} <rating> [comment]",
            parse_mode="HTML",
        )
    except ValueError as e:
        await message.answer(f"Failed to complete deal: {e}")
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message) -> None:
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Usage: /cancel <deal_id> [reason]")
        return

    deal_id = args[1].strip()
    reason = args[2] if len(args) > 2 else None

    try:
        result = await deal_service.cancel_deal(deal_id, message.from_user.id, reason)
        await message.answer(
            f"Deal cancelled.\n\n<b>Deal ID:</b> {deal_id}",
            parse_mode="HTML",
        )
    except ValueError as e:
        await message.answer(f"Failed to cancel deal: {e}")
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("review"))
async def cmd_review(message: Message) -> None:
    args = message.text.split(maxsplit=3)
    if len(args) < 3:
        await message.answer("Usage: /review <deal_id> <rating 1-5> [comment]")
        return

    deal_id = args[1].strip()
    try:
        rating = int(args[2])
    except ValueError:
        await message.answer("Rating must be a number between 1 and 5.")
        return

    comment = args[3] if len(args) > 3 else None

    try:
        result = await deal_service.create_review(
            deal_id=deal_id,
            reviewer_telegram_id=message.from_user.id,
            rating=rating,
            comment=comment,
        )
        await message.answer(
            f"Review submitted!\n\n"
            f"<b>Deal ID:</b> {deal_id}\n"
            f"<b>Rating:</b> {'⭐' * rating}\n"
            f"{f'<b>Comment:</b> {comment}' if comment else ''}",
            parse_mode="HTML",
        )
    except ValueError as e:
        await message.answer(f"Failed to submit review: {e}")
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("dealinfo"))
async def cmd_deal_info(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /dealinfo <deal_id>")
        return

    deal_id = args[1].strip()

    try:
        deal = await deal_service.get_deal(deal_id)
        if not deal:
            await message.answer("Deal not found.")
            return

        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "in_progress": "🔄",
            "completed": "✨",
            "cancelled": "❌",
            "disputed": "⚠️",
        }.get(deal.get("status", ""), "❓")

        await message.answer(
            f"<b>Deal Information</b>\n\n"
            f"<b>ID:</b> {deal['id']}\n"
            f"<b>Status:</b> {status_emoji} {deal.get('status')}\n"
            f"<b>Description:</b> {deal.get('description', 'N/A')}\n"
            f"<b>Created:</b> {deal.get('created', 'N/A')}",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Error: {e}")
