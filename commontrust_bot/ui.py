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
                InlineKeyboardButton(text="1", callback_data=f"review:{deal_id}:1"),
                InlineKeyboardButton(text="2", callback_data=f"review:{deal_id}:2"),
                InlineKeyboardButton(text="3", callback_data=f"review:{deal_id}:3"),
                InlineKeyboardButton(text="4", callback_data=f"review:{deal_id}:4"),
                InlineKeyboardButton(text="5", callback_data=f"review:{deal_id}:5"),
            ]
        ]
    )

