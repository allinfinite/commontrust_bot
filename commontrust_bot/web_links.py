from __future__ import annotations

from urllib.parse import quote

from commontrust_bot.config import settings


def deal_reviews_url(deal_id: str) -> str | None:
    base = (settings.commontrust_web_url or "").strip()
    if not base:
        return None
    return f"{base.rstrip('/')}/deals/{deal_id}"


def user_reviews_url(username: str) -> str | None:
    base = (settings.commontrust_web_url or "").strip()
    if not base:
        return None
    u = (username or "").strip().lstrip("@")
    if not u:
        return None
    return f"{base.rstrip('/')}/user/{quote(u)}"


def user_reviews_url_by_telegram_id(telegram_id: int | None) -> str | None:
    base = (settings.commontrust_web_url or "").strip()
    if not base:
        return None
    if not telegram_id:
        return None
    return f"{base.rstrip('/')}/user/{telegram_id}"
