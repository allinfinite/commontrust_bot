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


def review_url(review_id: str) -> str | None:
    base = (settings.commontrust_web_url or "").strip()
    if not base:
        return None
    rid = (review_id or "").strip()
    if not rid:
        return None
    return f"{base.rstrip('/')}/reviews/{quote(rid)}"


def review_respond_url(token: str) -> str | None:
    base = (settings.commontrust_web_url or "").strip()
    if not base:
        return None
    t = (token or "").strip()
    if not t:
        return None
    return f"{base.rstrip('/')}/respond/{quote(t)}"
