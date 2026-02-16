from __future__ import annotations

from aiogram import html
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from commontrust_bot.review_response_token import make_review_response_token
from commontrust_bot.web_links import review_respond_url, review_url, user_reviews_url, user_reviews_url_by_telegram_id


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

        token = make_review_response_token(review_id, reviewee_tid)
        respond = review_respond_url(token)
        view = review_url(review_id)
        if not respond:
            return

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
            "",
            f"<b>Respond on the ledger:</b> {html.quote(respond)}",
        ]
        if view:
            lines.append(f"<b>View filing:</b> {html.quote(view)}")
        if profile:
            lines.append(f"<b>Your ledger page:</b> {html.quote(profile)}")
        lines = [line for line in lines if line != ""]

        rows = [[InlineKeyboardButton(text="Public Response", url=respond)]]
        if view:
            rows.append([InlineKeyboardButton(text="Open Review", url=view)])
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

        # aiogram bot has send_message; tests may pass fakes that implement it.
        send_message = getattr(bot, "send_message", None)
        if not callable(send_message):
            return
        await send_message(reviewee_tid, "\n".join(lines), parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        return
