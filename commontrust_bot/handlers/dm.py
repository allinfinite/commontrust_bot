from __future__ import annotations

from typing import Any

from aiogram import F, Router, html
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from commontrust_bot.services.deal import deal_service
from commontrust_bot.ui import complete_kb, review_kb
from commontrust_bot.web_links import deal_reviews_url, user_reviews_url, user_reviews_url_by_telegram_id

router = Router()

# Very small in-memory state for "optional comment after rating".
# If the bot restarts, the user can just re-open the review link or run /review manually.
_PENDING_REVIEW_COMMENT: dict[int, tuple[str, int]] = {}


async def _bot_username(message: Message) -> str:
    me = await message.bot.get_me()
    if not me.username:
        raise ValueError("Bot username not available")
    return me.username


async def _send_review_prompt(message: Message, deal_id: str) -> None:
    me = await message.bot.get_me()
    if not me.username:
        return
    link = f"https://t.me/{me.username}?start=review_{deal_id}"
    initiator_tid, counterparty_tid = await deal_service.get_deal_participant_telegram_ids(deal_id)
    review_msg = (
        "Leave a review for your completed deal:\n\n"
        f"<b>Deal ID:</b> <code>{html.quote(deal_id)}</code>\n\n"
        "Tap a rating (1-5). After that you can optionally send a comment, or /skip.\n\n"
        f"If you need it later, here is the review link:\n{html.quote(link)}"
    )
    for tid in {initiator_tid, counterparty_tid}:
        await message.bot.send_message(
            tid,
            review_msg,
            parse_mode="HTML",
            reply_markup=review_kb(deal_id),
        )


@router.message(Command("newdeal"))
async def cmd_newdeal(message: Message) -> None:
    if message.chat.type != "private":
        await message.answer("DM me to create a private deal invite (recommended).")
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /newdeal description")
        return

    description = args[1].strip()
    try:
        # Ensure usernames are stored so the web UI can show/search by @username.
        await deal_service.reputation.get_or_create_member(
            message.from_user.id, message.from_user.username, message.from_user.full_name
        )
        result = await deal_service.create_invite_deal(
            initiator_telegram_id=message.from_user.id,
            description=description,
        )
    except Exception as e:
        await message.answer(f"Failed to create deal invite: {e}")
        return
    deal = result["deal"]
    deal_id = deal.get("id")
    if not isinstance(deal_id, str):
        await message.answer("Failed to create invite (missing deal id).")
        return

    username = await _bot_username(message)
    link = f"https://t.me/{username}?start=deal_{deal_id}"

    await message.answer(
        "Deal invite created.\n\n"
        f"<b>Deal ID:</b> <code>{html.quote(deal_id)}</code>\n"
        f"<b>Description:</b> {html.quote(description)}\n\n"
        "Send this link to the other person to accept:\n"
        f"{html.quote(link)}",
        parse_mode="HTML",
    )


@router.message(CommandStart())
async def cmd_start_deeplink(message: Message) -> None:
    # If no payload, let the normal /start handler respond (basic router).
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        raise SkipHandler

    payload = parts[1].strip()

    if payload.startswith("deal_"):
        deal_id = payload.removeprefix("deal_").strip()
        if not deal_id:
            return

        try:
            await deal_service.reputation.get_or_create_member(
                message.from_user.id, message.from_user.username, message.from_user.full_name
            )
            result = await deal_service.accept_invite_deal(deal_id, message.from_user.id)
            deal = result["deal"]
            await message.answer(
                "Deal accepted and confirmed.\n\n"
                f"<b>Deal ID:</b> <code>{html.quote(deal_id)}</code>\n"
                f"<b>Status:</b> Confirmed\n\n"
                "Either party can complete it any time:",
                parse_mode="HTML",
                reply_markup=complete_kb(deal_id),
            )

            # Notify initiator in DM as well (best-effort).
            initiator_tid, counterparty_tid = await deal_service.get_deal_participant_telegram_ids(deal_id)
            if message.from_user.id != initiator_tid:
                await message.bot.send_message(
                    initiator_tid,
                    "Your deal invite was accepted.\n\n"
                    f"<b>Deal ID:</b> <code>{html.quote(deal_id)}</code>\n"
                    "Tap to complete any time:",
                    parse_mode="HTML",
                    reply_markup=complete_kb(deal_id),
                )
        except Exception as e:
            await message.answer(f"Failed to accept invite: {e}")
        return

    if payload.startswith("review_"):
        deal_id = payload.removeprefix("review_").strip()
        if not deal_id:
            return

        await message.answer(
            "Leave a rating for this completed deal:\n\n"
            f"<b>Deal ID:</b> <code>{html.quote(deal_id)}</code>\n\n"
            "Tap a number (1-5). After that you can optionally send a comment.",
            parse_mode="HTML",
            reply_markup=review_kb(deal_id),
        )
        return

    # Unknown payload: allow other handlers (or future features) to respond.
    raise SkipHandler


@router.callback_query(F.data.startswith("review:"))
async def cb_review_rating(query: CallbackQuery) -> None:
    data = query.data or ""
    # review:<deal_id>:<rating>
    parts = data.split(":", 2)
    if len(parts) != 3:
        await query.answer("Invalid review action.", show_alert=True)
        return

    deal_id = parts[1].strip()
    try:
        rating = int(parts[2])
    except ValueError:
        await query.answer("Invalid rating.", show_alert=True)
        return

    if not (1 <= rating <= 5):
        await query.answer("Rating must be 1-5.", show_alert=True)
        return

    user_id = query.from_user.id
    _PENDING_REVIEW_COMMENT[user_id] = (deal_id, rating)
    await deal_service.reputation.get_or_create_member(
        query.from_user.id, query.from_user.username, query.from_user.full_name
    )

    await query.answer("Rating selected.")
    await query.message.answer(
        f"Got it: <b>{rating}</b>.\n\n"
        "Send an optional comment now, or type /skip to submit without a comment.",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("deal_complete:"))
async def cb_deal_complete(query: CallbackQuery) -> None:
    data = query.data or ""
    parts = data.split(":", 1)
    if len(parts) != 2:
        await query.answer("Invalid action.", show_alert=True)
        return

    deal_id = parts[1].strip()
    if not deal_id:
        await query.answer("Invalid deal id.", show_alert=True)
        return

    try:
        await deal_service.reputation.get_or_create_member(
            query.from_user.id, query.from_user.username, query.from_user.full_name
        )
        await deal_service.complete_deal(deal_id, query.from_user.id)
        await query.answer("Completed.")
        await query.message.answer(
            "Deal completed.\n\n"
            f"<b>Deal ID:</b> <code>{html.quote(deal_id)}</code>\n\n"
            "Reviews are private until both parties submit them.",
            parse_mode="HTML",
        )
        try:
            await _send_review_prompt(query.message, deal_id)
        except Exception:
            pass
    except Exception as e:
        await query.answer("Failed.", show_alert=False)
        await query.message.answer(f"Failed to complete deal: {e}")


@router.message(
    F.chat.type == "private",
    lambda m: bool(getattr(m, "from_user", None))
    and getattr(m.from_user, "id", None) in _PENDING_REVIEW_COMMENT,  # type: ignore[attr-defined]
)
async def maybe_capture_review_comment(message: Message) -> None:
    if not message.from_user:
        raise SkipHandler

    pending = _PENDING_REVIEW_COMMENT.get(message.from_user.id)
    if not pending:
        raise SkipHandler

    deal_id, rating = pending
    text = (message.text or "").strip()

    if text.startswith("/skip"):
        comment: str | None = None
    else:
        # Avoid treating other commands as comments.
        if text.startswith("/"):
            # Let real command handlers run (e.g. /help).
            raise SkipHandler
        comment = text if text else None

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
        _PENDING_REVIEW_COMMENT.pop(message.from_user.id, None)
        url = deal_reviews_url(deal_id)
        reviewee = result.get("reviewee") if isinstance(result, dict) else None
        username = (reviewee or {}).get("username") if isinstance(reviewee, dict) else None
        telegram_id = (reviewee or {}).get("telegram_id") if isinstance(reviewee, dict) else None
        profile_url = (
            user_reviews_url_by_telegram_id(telegram_id if isinstance(telegram_id, int) else None)
            or (user_reviews_url(username) if isinstance(username, str) else None)
        )
        if url:
            profile_block = f"\n\nReviewed user:\n{html.quote(profile_url)}" if profile_url else ""
            await message.answer(
                "Review submitted. Thanks!\n\n"
                f"View on web:\n{html.quote(url)}"
                f"{profile_block}",
                parse_mode="HTML",
            )
        else:
            view = f"\n\nReviewed user:\n{html.quote(profile_url)}" if profile_url else ""
            await message.answer("Review submitted. Thanks!" + view, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Failed to submit review: {e}")
