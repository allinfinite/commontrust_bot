from __future__ import annotations

from typing import Any

from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from commontrust_bot.services.deal import deal_service

router = Router()

# Very small in-memory state for "optional comment after rating".
# If the bot restarts, the user can just re-open the review link or run /review manually.
_PENDING_REVIEW_COMMENT: dict[int, tuple[str, int]] = {}


async def _bot_username(message: Message) -> str:
    me = await message.bot.get_me()
    if not me.username:
        raise ValueError("Bot username not available")
    return me.username


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
    result = await deal_service.create_invite_deal(
        initiator_telegram_id=message.from_user.id,
        description=description,
    )
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
        return

    payload = parts[1].strip()

    if payload.startswith("deal_"):
        deal_id = payload.removeprefix("deal_").strip()
        if not deal_id:
            return

        try:
            result = await deal_service.accept_invite_deal(deal_id, message.from_user.id)
            deal = result["deal"]
            await message.answer(
                "Deal accepted and confirmed.\n\n"
                f"<b>Deal ID:</b> <code>{html.quote(deal_id)}</code>\n"
                f"<b>Status:</b> Confirmed\n\n"
                f"Either party can complete it any time with:\n/complete {html.quote(deal_id)}",
                parse_mode="HTML",
            )

            # Notify initiator in DM as well (best-effort).
            initiator_tid, counterparty_tid = await deal_service.get_deal_participant_telegram_ids(deal_id)
            if message.from_user.id != initiator_tid:
                await message.bot.send_message(
                    initiator_tid,
                    "Your deal invite was accepted.\n\n"
                    f"<b>Deal ID:</b> <code>{html.quote(deal_id)}</code>\n"
                    f"Complete any time with /complete {html.quote(deal_id)}",
                    parse_mode="HTML",
                )
        except Exception as e:
            await message.answer(f"Failed to accept invite: {e}")
        return

    if payload.startswith("review_"):
        deal_id = payload.removeprefix("review_").strip()
        if not deal_id:
            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="1", callback_data=f"review:{deal_id}:1"),
                    InlineKeyboardButton(text="2", callback_data=f"review:{deal_id}:2"),
                    InlineKeyboardButton(text="3", callback_data=f"review:{deal_id}:3"),
                    InlineKeyboardButton(text="4", callback_data=f"review:{deal_id}:4"),
                    InlineKeyboardButton(text="5", callback_data=f"review:{deal_id}:5"),
                ]
            ]
        )
        await message.answer(
            "Leave a rating for this completed deal:\n\n"
            f"<b>Deal ID:</b> <code>{html.quote(deal_id)}</code>\n\n"
            "Tap a number (1-5). After that you can optionally send a comment.",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return


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

    await query.answer("Rating selected.")
    await query.message.answer(
        f"Got it: <b>{rating}</b>.\n\n"
        "Send an optional comment now, or type /skip to submit without a comment.",
        parse_mode="HTML",
    )


@router.message(F.chat.type == "private")
async def maybe_capture_review_comment(message: Message) -> None:
    if not message.from_user:
        return

    pending = _PENDING_REVIEW_COMMENT.get(message.from_user.id)
    if not pending:
        return

    deal_id, rating = pending
    text = (message.text or "").strip()

    if text.startswith("/skip"):
        comment: str | None = None
    else:
        # Avoid treating other commands as comments.
        if text.startswith("/"):
            await message.answer("Type a comment, or /skip.")
            return
        comment = text if text else None

    try:
        await deal_service.create_review(
            deal_id=deal_id,
            reviewer_telegram_id=message.from_user.id,
            rating=rating,
            comment=comment,
        )
        _PENDING_REVIEW_COMMENT.pop(message.from_user.id, None)
        await message.answer("Review submitted. Thanks!")
    except Exception as e:
        await message.answer(f"Failed to submit review: {e}")

