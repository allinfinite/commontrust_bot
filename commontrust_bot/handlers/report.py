"""Report handler: /report command, DM evidence collection, and admin review callbacks."""

from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime

from aiogram import F, Router, html
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from commontrust_bot.config import settings
from commontrust_bot.pocketbase_client import pb_client
from commontrust_bot.services.report import report_service
from commontrust_bot.ui import report_admin_kb, report_confirm_kb

logger = logging.getLogger(__name__)
router = Router()


# ---------------------------------------------------------------------------
# In-memory DM conversation state for evidence collection
# ---------------------------------------------------------------------------

@dataclass
class ReportDraft:
    reported_member_id: str
    reported_telegram_id: int
    reported_display: str
    deal_id: str | None = None
    description: str | None = None
    photo_file_ids: list[str] = field(default_factory=list)
    forwarded_messages: list[dict] = field(default_factory=list)
    step: str = "description"  # "description" | "evidence" | "confirm"


_PENDING_REPORT: dict[int, ReportDraft] = {}


def get_pending_report(user_id: int) -> ReportDraft | None:
    return _PENDING_REPORT.get(user_id)


def clear_pending_report(user_id: int) -> None:
    _PENDING_REPORT.pop(user_id, None)


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids


# ---------------------------------------------------------------------------
# /report command — entry point
# ---------------------------------------------------------------------------

@router.message(Command("report"))
async def cmd_report(message: Message) -> None:
    if not message.from_user:
        return

    args = (message.text or "").split(maxsplit=1)
    arg = args[1].strip() if len(args) > 1 else ""

    reported_user = None
    deal_id: str | None = None

    # Case 1: reply to a message in a group
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        if target.id == message.from_user.id:
            await message.answer("You cannot report yourself.")
            return
        if target.is_bot:
            await message.answer("You cannot report a bot.")
            return
        reported_user = await pb_client.member_get_or_create(
            target.id, target.username, target.full_name
        )

    # Case 2: /report @username
    elif arg.startswith("@"):
        username = arg.lstrip("@").strip()
        if not username:
            await message.answer("Usage: /report @username or reply to a message with /report")
            return
        reported_user = await pb_client.member_get_by_username(username)
        if not reported_user:
            await message.answer(f"User @{username} not found in the system.")
            return
        if reported_user.get("telegram_id") == message.from_user.id:
            await message.answer("You cannot report yourself.")
            return

    # Case 3: /report deal_id (in DM)
    elif arg and not arg.startswith("@"):
        deal_id = arg.strip()
        try:
            deal = await pb_client.deal_get(deal_id)
            if not deal:
                await message.answer("Deal not found.")
                return
            reporter = await pb_client.member_get(message.from_user.id)
            if not reporter:
                await message.answer("You are not registered. Use /start first.")
                return
            initiator_id = deal.get("initiator_id")
            counterparty_id = deal.get("counterparty_id")
            reporter_id = reporter.get("id")
            if reporter_id not in (initiator_id, counterparty_id):
                await message.answer("You can only report deals you participated in.")
                return
            reported_member_id = counterparty_id if reporter_id == initiator_id else initiator_id
            reported_user = await pb_client.get_record("members", reported_member_id)
        except Exception as e:
            await message.answer(f"Error looking up deal: {e}")
            return

    else:
        await message.answer(
            "Usage:\n"
            "• Reply to a message with /report\n"
            "• /report @username\n"
            "• /report deal_id"
        )
        return

    # Ensure reporter is registered.
    await pb_client.member_get_or_create(
        message.from_user.id, message.from_user.username, message.from_user.full_name
    )

    reported_display = reported_user.get("display_name") or reported_user.get("username") or "Unknown"
    reported_tid = reported_user.get("telegram_id", 0)

    draft = ReportDraft(
        reported_member_id=reported_user["id"],
        reported_telegram_id=reported_tid,
        reported_display=reported_display,
        deal_id=deal_id,
        step="description",
    )
    _PENDING_REPORT[message.from_user.id] = draft

    # If in a group, move to DM.
    if message.chat.type != "private":
        try:
            await message.bot.send_message(
                message.from_user.id,
                f"Starting report against <b>{html.quote(reported_display)}</b>.\n\n"
                "Please describe what happened. Be specific about the scam or violation.",
                parse_mode="HTML",
            )
            await message.answer("Check your DMs — I'll collect the report there.")
        except Exception:
            me = await message.bot.get_me()
            link = f"https://t.me/{me.username}?start=report"
            await message.answer(f"I couldn't DM you. Please start the bot first: {link}")
            clear_pending_report(message.from_user.id)
        return

    # Already in DM.
    await message.answer(
        f"Starting report against <b>{html.quote(reported_display)}</b>.\n\n"
        "Please describe what happened. Be specific about the scam or violation.",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# DM evidence capture — multi-step conversation
# ---------------------------------------------------------------------------

@router.message(
    F.chat.type == "private",
    lambda m: bool(getattr(m, "from_user", None))
    and getattr(m.from_user, "id", None) in _PENDING_REPORT,
)
async def capture_report_evidence(message: Message) -> None:
    if not message.from_user:
        raise SkipHandler

    draft = _PENDING_REPORT.get(message.from_user.id)
    if not draft:
        raise SkipHandler

    text = (message.text or "").strip()

    # Allow /cancel at any step.
    if text.lower() == "/cancel":
        clear_pending_report(message.from_user.id)
        await message.answer("Report cancelled.")
        return

    # Let other commands pass through (except /done, /skip which we handle).
    if text.startswith("/") and text.lower() not in ("/done", "/skip"):
        raise SkipHandler

    # --- Step: description ---
    if draft.step == "description":
        if message.photo:
            await message.answer("Please send your description as text first, then you can add photos.")
            return
        if not text:
            await message.answer("Please describe the issue in text.")
            return
        if len(text) > 4000:
            await message.answer("Description too long. Please keep it under 4000 characters.")
            return
        draft.description = text
        draft.step = "evidence"
        await message.answer(
            "Got it. Now send any evidence:\n\n"
            "• Screenshots or photos\n"
            "• Forward messages from the scammer\n\n"
            "Type /done when finished, or /skip to submit without additional evidence.",
        )
        return

    # --- Step: evidence ---
    if draft.step == "evidence":
        if text.lower() in ("/done", "/skip"):
            draft.step = "confirm"
            await _show_confirmation(message, draft)
            return

        # Capture photos.
        if message.photo:
            if len(draft.photo_file_ids) >= 10:
                await message.answer("Maximum 10 photos per report. Type /done to finish.")
                return
            draft.photo_file_ids.append(message.photo[-1].file_id)
            await message.answer(
                f"Photo received ({len(draft.photo_file_ids)}/10). "
                "Send more, forward messages, or type /done."
            )
            return

        # Capture forwarded messages.
        if message.forward_date or message.forward_from or message.forward_sender_name:
            fwd: dict = {
                "text": (message.text or message.caption or "(no text)").strip(),
                "from_name": (
                    message.forward_from.full_name
                    if message.forward_from
                    else message.forward_sender_name or "Hidden user"
                ),
                "date": message.forward_date.isoformat() if message.forward_date else "Unknown",
            }
            draft.forwarded_messages.append(fwd)
            # Also capture photos from forwarded messages.
            if message.photo:
                if len(draft.photo_file_ids) < 10:
                    draft.photo_file_ids.append(message.photo[-1].file_id)
            await message.answer(
                f"Forwarded message captured ({len(draft.forwarded_messages)} total). "
                "Send more or type /done."
            )
            return

        # Plain text during evidence step — treat as additional forwarded text.
        if text:
            draft.forwarded_messages.append({
                "text": text,
                "from_name": "Reporter note",
                "date": datetime.now().isoformat(),
            })
            await message.answer("Note captured. Send more evidence or type /done.")
            return

        await message.answer("Send photos, forward messages, or type /done to finish.")
        return

    # --- Step: confirm (handled by callback) ---
    if draft.step == "confirm":
        await message.answer("Please use the buttons above to submit or cancel.")
        return


async def _show_confirmation(message: Message, draft: ReportDraft) -> None:
    desc_preview = (draft.description or "")[:200]
    if len(draft.description or "") > 200:
        desc_preview += "..."
    deal_line = f"Deal: <code>{html.quote(draft.deal_id)}</code>" if draft.deal_id else "Open report (no linked deal)"

    await message.answer(
        f"<b>Report Summary</b>\n\n"
        f"<b>Reported user:</b> {html.quote(draft.reported_display)}\n"
        f"<b>{deal_line}</b>\n"
        f"<b>Description:</b> {html.quote(desc_preview)}\n"
        f"<b>Evidence:</b> {len(draft.photo_file_ids)} photo(s), "
        f"{len(draft.forwarded_messages)} forwarded message(s)\n\n"
        "Confirm submission?",
        parse_mode="HTML",
        reply_markup=report_confirm_kb(message.from_user.id),
    )


# ---------------------------------------------------------------------------
# Confirmation callbacks (Submit / Cancel)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("report_submit:"))
async def cb_report_submit(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    draft = _PENDING_REPORT.get(user_id)
    if not draft:
        await query.answer("No pending report found.", show_alert=True)
        return

    await query.answer("Submitting...")

    # Download photos from Telegram.
    photo_data: list[tuple[str, bytes, str]] = []
    for i, file_id in enumerate(draft.photo_file_ids):
        try:
            file = await query.bot.get_file(file_id)
            buf = io.BytesIO()
            await query.bot.download_file(file.file_path, buf)
            photo_data.append((f"evidence_{i}.jpg", buf.getvalue(), "image/jpeg"))
        except Exception as e:
            logger.warning("Failed to download photo %s: %s", file_id, e)

    try:
        record = await report_service.create_report(
            reporter_telegram_id=user_id,
            reported_telegram_id=draft.reported_telegram_id,
            description=draft.description or "",
            photo_data=photo_data,
            forwarded_messages=draft.forwarded_messages,
            deal_id=draft.deal_id,
        )
        clear_pending_report(user_id)

        await query.message.edit_text(
            "Your report has been submitted and is being reviewed.\n\n"
            f"<b>Report ID:</b> <code>{html.quote(record['id'][:8])}</code>",
            parse_mode="HTML",
        )

        # Trigger AI review asynchronously, then notify admins.
        asyncio.create_task(_run_ai_and_notify(query.bot, record["id"], user_id))
    except Exception as e:
        clear_pending_report(user_id)
        await query.message.answer(f"Failed to submit report: {e}")


@router.callback_query(F.data.startswith("report_cancel:"))
async def cb_report_cancel(query: CallbackQuery) -> None:
    clear_pending_report(query.from_user.id)
    await query.answer("Report cancelled.")
    await query.message.edit_text("Report cancelled.")


# ---------------------------------------------------------------------------
# AI review + admin notification (runs as background task)
# ---------------------------------------------------------------------------

async def _run_ai_and_notify(bot: object, report_id: str, reporter_tid: int) -> None:
    try:
        report = await report_service.trigger_ai_review(report_id)
    except Exception as e:
        logger.error("AI review failed for report %s: %s", report_id, e)
        # Still proceed — mark as pending_admin so admins can review manually.
        try:
            report = await pb_client.update_record(
                "reports", report_id, {"status": "pending_admin", "ai_summary": f"AI analysis failed: {e}"}
            )
        except Exception:
            return

    await _notify_admins(bot, report)


async def _notify_admins(bot: object, report: dict) -> None:
    send_message = getattr(bot, "send_message", None)
    if not callable(send_message):
        return

    reporter = await pb_client.get_record("members", report["reporter_id"])
    reported = await pb_client.get_record("members", report["reported_id"])

    reporter_name = reporter.get("display_name") or reporter.get("username") or "Unknown"
    reported_name = reported.get("display_name") or reported.get("username") or "Unknown"

    severity = report.get("ai_severity", "?")
    recommendation = report.get("ai_recommendation", "?")
    summary = report.get("ai_summary", "No AI summary")
    reasoning = report.get("ai_reasoning", "")
    deal_line = f"Deal: <code>{html.quote(str(report.get('deal_id', '')))}</code>" if report.get("deal_id") else "Open report (no linked deal)"

    red_flags_text = ""
    # ai_reasoning contains the detailed assessment; red_flags are in the summary.

    text = (
        f"<b>NEW REPORT (#{html.quote(report['id'][:8])})</b>\n\n"
        f"<b>Reporter:</b> {html.quote(reporter_name)}\n"
        f"<b>Reported:</b> {html.quote(reported_name)}\n"
        f"<b>{deal_line}</b>\n\n"
        f"<b>Description:</b>\n{html.quote((report.get('description') or '')[:500])}\n\n"
        f"<b>AI Assessment:</b>\n"
        f"  Severity: {severity}/10\n"
        f"  Recommendation: {recommendation}\n"
        f"  Summary: {html.quote(str(summary)[:300])}\n\n"
        f"<b>Evidence:</b> {len(report.get('evidence_photos') or [])} photo(s), "
        f"{len(report.get('forwarded_messages') or [])} forwarded msg(s)"
    )

    for admin_id in settings.admin_user_ids:
        try:
            await send_message(
                admin_id,
                text,
                parse_mode="HTML",
                reply_markup=report_admin_kb(report["id"]),
            )
        except Exception as e:
            logger.warning("Could not notify admin %s: %s", admin_id, e)


# ---------------------------------------------------------------------------
# Admin action callbacks
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("report_action:"))
async def cb_report_action(query: CallbackQuery) -> None:
    if not _is_admin(query.from_user.id):
        await query.answer("Admin only.", show_alert=True)
        return

    parts = (query.data or "").split(":", 2)
    if len(parts) != 3:
        await query.answer("Invalid action.", show_alert=True)
        return

    report_id, action = parts[1], parts[2]

    # Race condition guard: check report is still pending.
    try:
        report = await report_service.get_report(report_id)
    except Exception:
        await query.answer("Report not found.", show_alert=True)
        return

    if report.get("status") != "pending_admin":
        await query.answer("This report has already been resolved.", show_alert=True)
        return

    if action not in ("confirm_scammer", "warn", "dismiss"):
        await query.answer("Unknown action.", show_alert=True)
        return

    try:
        updated = await report_service.resolve_report(
            report_id, query.from_user.id, action
        )
    except Exception as e:
        await query.answer(f"Failed: {e}", show_alert=True)
        return

    labels = {
        "confirm_scammer": "CONFIRMED SCAMMER",
        "warn": "WARNING ISSUED",
        "dismiss": "DISMISSED",
    }
    label = labels.get(action, action.upper())
    await query.answer(f"Report resolved: {label}")

    try:
        await query.message.edit_text(
            query.message.text + f"\n\n<b>[RESOLVED: {label}]</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    # Notify reporter.
    try:
        reporter = await pb_client.get_record("members", report["reporter_id"])
        reporter_tid = reporter.get("telegram_id")
        if isinstance(reporter_tid, int) and reporter_tid > 0:
            reported = await pb_client.get_record("members", report["reported_id"])
            reported_name = reported.get("display_name") or reported.get("username") or "Unknown"
            if action == "confirm_scammer":
                msg = f"Your report against {reported_name} has been reviewed. Action: confirmed as scammer and banned."
            elif action == "warn":
                msg = f"Your report against {reported_name} has been reviewed. The user has been warned."
            else:
                msg = f"Your report against {reported_name} has been reviewed. No action was taken at this time."
            send_message = getattr(query.bot, "send_message", None)
            if callable(send_message):
                await send_message(reporter_tid, msg)
    except Exception as e:
        logger.warning("Could not notify reporter: %s", e)


# ---------------------------------------------------------------------------
# View Evidence callback (admin)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("report_evidence:"))
async def cb_report_evidence(query: CallbackQuery) -> None:
    if not _is_admin(query.from_user.id):
        await query.answer("Admin only.", show_alert=True)
        return

    report_id = (query.data or "").split(":", 1)[1] if ":" in (query.data or "") else ""
    if not report_id:
        await query.answer("Invalid report.", show_alert=True)
        return

    try:
        report = await report_service.get_report(report_id)
    except Exception:
        await query.answer("Report not found.", show_alert=True)
        return

    await query.answer("Sending evidence...")

    # Send photos from PocketBase file storage.
    photos = report.get("evidence_photos") or []
    collection_id = report.get("collectionId", "reports")
    for filename in photos:
        url = f"{settings.pocketbase_url}/api/files/{collection_id}/{report_id}/{filename}"
        try:
            send_photo = getattr(query.bot, "send_photo", None)
            if callable(send_photo):
                await send_photo(query.from_user.id, photo=url, caption=f"Evidence: {filename}")
        except Exception as e:
            logger.warning("Failed to send evidence photo: %s", e)

    # Send forwarded message texts.
    forwarded = report.get("forwarded_messages") or []
    for msg in forwarded:
        text = (
            f"<b>Forwarded from:</b> {html.quote(str(msg.get('from_name', 'Unknown')))}\n"
            f"<b>Date:</b> {html.quote(str(msg.get('date', 'Unknown')))}\n\n"
            f"{html.quote(str(msg.get('text', '(no text)')))}"
        )
        send_message = getattr(query.bot, "send_message", None)
        if callable(send_message):
            try:
                await send_message(query.from_user.id, text, parse_mode="HTML")
            except Exception as e:
                logger.warning("Failed to send forwarded message evidence: %s", e)

    if not photos and not forwarded:
        send_message = getattr(query.bot, "send_message", None)
        if callable(send_message):
            await send_message(query.from_user.id, "No additional evidence attached to this report.")
