from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from commontrust_bot.config import settings
from commontrust_bot.web_links import how_to_url

router = Router()


def _how_to_image_url() -> str | None:
    image_url = (settings.commontrust_howto_image_url or "").strip()
    return image_url or None


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    # Deep-links are handled in `handlers/dm.py` (CommandStart). This is the
    # default /start response when there is no payload.
    how_to = how_to_url()
    image_url = _how_to_image_url()

    primary_cta = "<b>First step (required):</b> DM me <code>/newdeal your deal description</code>."
    secondary_cta = "<b>Then:</b> send the invite link I generate to the other user so they can join the deal."

    if image_url:
        answer_photo = getattr(message, "answer_photo", None)
        if callable(answer_photo):
            caption = (
                f"Welcome to CommonTrust Bot, {html.bold(message.from_user.full_name)}.\n\n"
                f"{primary_cta}\n"
                f"{secondary_cta}"
            )
            if how_to:
                caption += f"\n\nStep-by-step guide: {html.quote(how_to)}"
            await answer_photo(photo=image_url, caption=caption, parse_mode="HTML")
            return

    text = (
        f"Welcome to CommonTrust Bot, {html.bold(message.from_user.full_name)}!\n\n"
        f"{primary_cta}\n"
        f"{secondary_cta}\n\n"
        "Use /help for all commands."
    )
    if how_to:
        text += f"\n\nStep-by-step guide: {html.quote(how_to)}"
    await message.answer(text, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    how_to = how_to_url()
    how_to_line = f"\nHow-to guide: {html.quote(how_to)}" if how_to else ""

    help_text = f"""
<b>CommonTrust Bot Commands</b>

<b>Do this first (required)</b>
1) /newdeal description - Create a private deal invite link in DM
2) Send the generated link to the other user so they can accept
{how_to_line}

<b>Basic</b>
/start - Start the bot
/help - Show this help message

<b>Deals</b>
/newdeal description - Create a private deal invite link (DM only; recommended)
/deal (reply) description - Create a new deal
/confirm deal_id - Confirm a pending deal
/complete deal_id - Mark a deal as completed
/review deal_id rating(1-5) [comment] - Review a completed deal

<b>Reports</b>
/report @username - Report a scammer (evidence collected in DM)
/report deal_id - Report linked to a specific deal

<b>Reputation</b>
/reputation - View your reputation stats
/mydeals - List your deals
"""
    await message.answer(help_text, parse_mode="HTML")
