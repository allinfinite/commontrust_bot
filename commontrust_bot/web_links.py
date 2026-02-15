from __future__ import annotations

from urllib.parse import quote

from commontrust_bot.config import settings


def _normalized_web_base() -> str | None:
    base = (settings.commontrust_web_url or "").strip()
    if not base:
        return None
    if not base.startswith(("http://", "https://")):
        base = f"https://{base}"
    return base.rstrip("/")


def deal_reviews_url(deal_id: str) -> str | None:
    base = _normalized_web_base()
    if not base:
        return None
    d = (deal_id or "").strip()
    if not d:
        return None
    return f"{base}/deals/{quote(d)}"


def user_reviews_url(username: str) -> str | None:
    base = _normalized_web_base()
    if not base:
        return None
    u = (username or "").strip().lstrip("@")
    if not u:
        return None
    return f"{base}/user/{quote(u)}"


def user_reviews_url_by_telegram_id(telegram_id: int | None) -> str | None:
    base = _normalized_web_base()
    if not base:
        return None
    if not telegram_id:
        return None
    return f"{base}/user/{telegram_id}"
