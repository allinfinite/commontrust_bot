from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from commontrust_bot.services.deal import deal_service
from commontrust_bot.review_notify import maybe_dm_reviewee_with_respond_link
from commontrust_bot.ui import review_kb
from commontrust_bot.web_links import deal_reviews_url, review_url, user_reviews_url, user_reviews_url_by_telegram_id

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
        await message.answer("Usage: /deal description")
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
        # Ensure usernames are stored so the web UI can show/search by @username.
        await deal_service.reputation.get_or_create_member(
            message.from_user.id, message.from_user.username, message.from_user.full_name
        )
        await deal_service.reputation.get_or_create_member(
            counterparty.id, counterparty.username, counterparty.full_name
        )

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
        await message.answer("Usage: /confirm deal_id")
        return

    deal_id = args[1].strip()

    try:
        await deal_service.reputation.get_or_create_member(
            message.from_user.id, message.from_user.username, message.from_user.full_name
        )
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
        await message.answer("Usage: /complete deal_id")
        return

    deal_id = args[1].strip()

    try:
        await deal_service.reputation.get_or_create_member(
            message.from_user.id, message.from_user.username, message.from_user.full_name
        )
        result = await deal_service.complete_deal(deal_id, message.from_user.id)
        await message.answer(
            f"Deal completed!\n\n"
            f"<b>Deal ID:</b> {deal_id}\n"
            f"<b>Status:</b> Completed\n\n"
            f"Both parties can now leave a review with /review {deal_id} rating(1-5) [comment]",
            parse_mode="HTML",
        )

        # DM-first UX: send each party a direct review deep-link in private messages.
        try:
            me = await message.bot.get_me()
            if me.username:
                link = f"https://t.me/{me.username}?start=review_{deal_id}"
                initiator_tid, counterparty_tid = await deal_service.get_deal_participant_telegram_ids(deal_id)
                review_msg = (
                    "Leave a review for your completed deal:\n\n"
                    f"<b>Deal ID:</b> <code>{deal_id}</code>\n\n"
                    "Tap a rating (1-5). After that you can optionally send a comment, or /skip.\n\n"
                    f"If you need it later, here is the review link:\n{link}"
                )
                for tid in {initiator_tid, counterparty_tid}:
                    await message.bot.send_message(
                        tid,
                        review_msg,
                        parse_mode="HTML",
                        reply_markup=review_kb(deal_id),
                    )
        except Exception:
            # Best-effort: don't fail /complete if DMing fails.
            pass
    except ValueError as e:
        await message.answer(f"Failed to complete deal: {e}")
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message) -> None:
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Usage: /cancel deal_id [reason]")
        return

    deal_id = args[1].strip()
    reason = args[2] if len(args) > 2 else None

    try:
        await deal_service.reputation.get_or_create_member(
            message.from_user.id, message.from_user.username, message.from_user.full_name
        )
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
        await message.answer("Usage: /review deal_id rating(1-5) [comment]")
        return

    deal_id = args[1].strip()
    try:
        rating = int(args[2])
    except ValueError:
        await message.answer("Rating must be a number between 1 and 5.")
        return

    comment = args[3] if len(args) > 3 else None

    try:
        await deal_service.reputation.get_or_create_member(
            message.from_user.id, message.from_user.username, message.from_user.full_name
        )
        result = await deal_service.create_review(
            deal_id=deal_id,
            reviewer_telegram_id=message.from_user.id,
            rating=rating,
            comment=comment,
        )
        review = result.get("review") if isinstance(result, dict) else None
        review_id = (review or {}).get("id") if isinstance(review, dict) else None
        filing_url = review_url(review_id) if isinstance(review_id, str) else deal_reviews_url(deal_id)
        reviewee = result.get("reviewee") if isinstance(result, dict) else None
        username = (reviewee or {}).get("username") if isinstance(reviewee, dict) else None
        telegram_id = (reviewee or {}).get("telegram_id") if isinstance(reviewee, dict) else None
        profile_url = (
            user_reviews_url_by_telegram_id(telegram_id if isinstance(telegram_id, int) else None)
            or (user_reviews_url(username) if isinstance(username, str) else None)
        )
        primary_url = profile_url or filing_url
        view_line = f"\n\n<b>View on web:</b> {html.quote(primary_url)}" if primary_url else ""
        filing_line = (
            f"\n\n<b>Filing URL (public after both reviews):</b> {html.quote(filing_url)}"
            if filing_url and filing_url != primary_url
            else ""
        )
        profile_line = f"\n\n<b>Reviewed user:</b> {html.quote(profile_url)}" if profile_url else ""
        await message.answer(
            f"Review submitted!\n\n"
            f"<b>Deal ID:</b> {deal_id}\n"
            f"<b>Rating:</b> {'⭐' * rating}\n"
            f"{f'<b>Comment:</b> {comment}' if comment else ''}"
            f"{view_line}"
            f"{filing_line}"
            f"{profile_line}",
            parse_mode="HTML",
        )
        # Best-effort DM to reviewee with a website response link.
        bot = getattr(message, "bot", None)
        if bot is not None:
            await maybe_dm_reviewee_with_respond_link(bot, result=result)
    except ValueError as e:
        await message.answer(f"Failed to submit review: {e}")
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("dealinfo"))
async def cmd_deal_info(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /dealinfo deal_id")
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
