from __future__ import annotations

from commontrust_bot.config import settings


def deal_reviews_url(deal_id: str) -> str | None:
    base = (settings.commontrust_web_url or "").strip()
    if not base:
        return None
    return f"{base.rstrip('/')}/deals/{deal_id}"

