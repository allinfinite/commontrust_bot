from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def complete_kb(deal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Mark Completed", callback_data=f"deal_complete:{deal_id}")]
        ]
    )


def review_kb(deal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐", callback_data=f"review:{deal_id}:1"),
                InlineKeyboardButton(text="⭐⭐", callback_data=f"review:{deal_id}:2"),
                InlineKeyboardButton(text="⭐⭐⭐", callback_data=f"review:{deal_id}:3"),
                InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"review:{deal_id}:4"),
                InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"review:{deal_id}:5"),
            ]
        ]
    )


def report_confirm_kb(reporter_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Submit Report", callback_data=f"report_submit:{reporter_id}"),
                InlineKeyboardButton(text="Cancel", callback_data=f"report_cancel:{reporter_id}"),
            ]
        ]
    )


def report_admin_kb(report_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Confirm Scammer", callback_data=f"report_action:{report_id}:confirm_scammer"
                ),
                InlineKeyboardButton(text="Warn", callback_data=f"report_action:{report_id}:warn"),
            ],
            [
                InlineKeyboardButton(text="Dismiss", callback_data=f"report_action:{report_id}:dismiss"),
                InlineKeyboardButton(text="View Evidence", callback_data=f"report_evidence:{report_id}"),
            ],
        ]
    )

