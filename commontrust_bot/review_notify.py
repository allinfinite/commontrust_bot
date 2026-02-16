from __future__ import annotations

from aiogram import html
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from commontrust_bot.review_response_token import make_review_response_token
from commontrust_bot.web_links import review_respond_url, review_url, user_reviews_url, user_reviews_url_by_telegram_id

# In-memory cache: (telegram_user_id, message_id) -> review_id
# This allows us to detect when users reply to their review notification.
_REVIEW_NOTIFICATION_MESSAGES: dict[tuple[int, int], str] = {}


async def maybe_dm_reviewee_with_respond_link(bot: object, *, result: dict) -> None:
    """
    Best-effort: if the reviewee hasn't started the bot, Telegram DM may fail.
    Also requires COMMONTRUST_WEB_URL and REVIEW_RESPONSE_SECRET to be configured.
    """
    try:
        review = result.get("review") if isinstance(result, dict) else None
        reviewer = result.get("reviewer") if isinstance(result, dict) else None
        reviewee = result.get("reviewee") if isinstance(result, dict) else None

        review_id = (review or {}).get("id") if isinstance(review, dict) else None
        if not isinstance(review_id, str) or not review_id.strip():
            return

        reviewee_tid = (reviewee or {}).get("telegram_id") if isinstance(reviewee, dict) else None
        if not isinstance(reviewee_tid, int) or reviewee_tid <= 0:
            return

        reviewer_name = (reviewer or {}).get("display_name") if isinstance(reviewer, dict) else None
        if not isinstance(reviewer_name, str) or not reviewer_name.strip():
            reviewer_name = (reviewer or {}).get("username") if isinstance(reviewer, dict) else None
        reviewer_name = reviewer_name.strip() if isinstance(reviewer_name, str) and reviewer_name.strip() else "Someone"
        rating = (review or {}).get("rating") if isinstance(review, dict) else None
        comment = (review or {}).get("comment") if isinstance(review, dict) else None
        outcome = (review or {}).get("outcome") if isinstance(review, dict) else None
        deal_id = (review or {}).get("deal_id") if isinstance(review, dict) else None

        view = review_url(review_id)
        respond: str | None = None
        try:
            token = make_review_response_token(review_id, reviewee_tid)
            respond = review_respond_url(token)
        except Exception:
            respond = None

        username = (reviewee or {}).get("username") if isinstance(reviewee, dict) else None
        profile = user_reviews_url_by_telegram_id(reviewee_tid) or (user_reviews_url(username) if isinstance(username, str) else None)

        stars = ""
        if isinstance(rating, int) and 1 <= rating <= 5:
            stars = "⭐" * rating
        comment_line = (
            f"<b>Comment:</b> {html.quote(comment)}"
            if isinstance(comment, str) and comment.strip()
            else "<b>Comment:</b> (none)"
        )

        lines = [
            f"You received a new review from <b>{html.quote(reviewer_name)}</b>.",
            "",
            f"<b>Rating:</b> {html.quote(stars)}" if stars else "<b>Rating:</b> (not provided)",
            comment_line,
            f"<b>Outcome:</b> {html.quote(str(outcome))}" if outcome else "",
            f"<b>Deal ID:</b> <code>{html.quote(str(deal_id))}</code>" if deal_id else "",
        ]
        if respond:
            lines.extend([
                "",
                "💬 <b>To post a public response:</b>",
                "Simply reply to this message with your response text.",
                "It will be published on the ledger for everyone to see.",
            ])
        if view:
            lines.append(f"<b>View filing:</b> {html.quote(view)}")
        if profile:
            lines.append(f"<b>Your ledger page:</b> {html.quote(profile)}")
        lines = [line for line in lines if line != ""]

        rows: list[list[InlineKeyboardButton]] = []
        # Only show "Open Review" button - users should reply to message for responses
        if view:
            rows.append([InlineKeyboardButton(text="Open Review", url=view)])
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows) if rows else None

        # aiogram bot has send_message; tests may pass fakes that implement it.
        send_message = getattr(bot, "send_message", None)
        if not callable(send_message):
            return
        kwargs = {"parse_mode": "HTML"}
        if keyboard is not None:
            kwargs["reply_markup"] = keyboard
        sent_message = await send_message(reviewee_tid, "\n".join(lines), **kwargs)

        # Store the message ID so we can detect replies to it.
        if sent_message and hasattr(sent_message, "message_id"):
            _REVIEW_NOTIFICATION_MESSAGES[(reviewee_tid, sent_message.message_id)] = review_id
    except Exception:
        return


def get_review_id_from_reply(user_id: int, reply_to_message_id: int) -> str | None:
    """
    Check if a message is a reply to a review notification.
    Returns the review_id if it is, None otherwise.
    """
    return _REVIEW_NOTIFICATION_MESSAGES.get((user_id, reply_to_message_id))
