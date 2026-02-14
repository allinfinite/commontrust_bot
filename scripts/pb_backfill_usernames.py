#!/usr/bin/env python3
"""
Backfill PocketBase member usernames/display names using Telegram Bot API,
then denormalize usernames into reviews for username-based display/search.

This is best-effort:
- Telegram getChat(user_id) only works if the user has interacted with the bot.

Required env vars (read from .env.local / .env):
- POCKETBASE_URL
- POCKETBASE_ADMIN_TOKEN
- TELEGRAM_BOT_TOKEN

Usage:
  python3 scripts/pb_backfill_usernames.py
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv


def _load_env() -> None:
    load_dotenv(".env.local", override=False)
    load_dotenv(".env", override=False)


def _must_env(name: str) -> str:
    v = os.environ.get(name)
    if not v or not v.strip():
        raise SystemExit(f"Missing required env var: {name}")
    return v.strip()


def _pb_headers(token: str) -> dict[str, str]:
    return {"Authorization": token}


def _tg_url(bot_token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{bot_token}/{method}"


def _norm_username(username: str | None) -> str | None:
    if not username:
        return None
    u = username.strip().lstrip("@").lower()
    return u or None


def _display_name(first: str | None, last: str | None) -> str | None:
    parts = [p for p in [(first or "").strip(), (last or "").strip()] if p]
    return " ".join(parts) if parts else None


def _pb_list_all(client: httpx.Client, base: str, token: str, collection: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        r = client.get(
            f"{base}/api/collections/{collection}/records",
            headers=_pb_headers(token),
            params={"page": page, "perPage": 200},
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        if not items:
            break
        out.extend(items)
        page += 1
    return out


def main() -> int:
    _load_env()
    pb_url = _must_env("POCKETBASE_URL").rstrip("/")
    pb_token = _must_env("POCKETBASE_ADMIN_TOKEN")
    tg_token = _must_env("TELEGRAM_BOT_TOKEN")

    # Keep this conservative to avoid Telegram API rate limits.
    tg_sleep_s = float(os.environ.get("TELEGRAM_API_SLEEP_SECONDS", "0.08"))

    updated_members = 0
    skipped_members = 0
    updated_reviews = 0

    with httpx.Client(timeout=30.0) as client:
        members = _pb_list_all(client, pb_url, pb_token, "members")
        for m in members:
            mid = m.get("id")
            tid = m.get("telegram_id")
            if not isinstance(mid, str) or not isinstance(tid, int):
                continue

            if _norm_username(m.get("username")):
                skipped_members += 1
                continue

            tg = client.get(_tg_url(tg_token, "getChat"), params={"chat_id": tid})
            time.sleep(tg_sleep_s)
            if tg.status_code != 200:
                continue
            payload = tg.json()
            if not payload.get("ok"):
                continue
            chat = payload.get("result") or {}

            username = _norm_username(chat.get("username"))
            if not username:
                continue

            dn = _display_name(chat.get("first_name"), chat.get("last_name"))
            patch: dict[str, Any] = {"username": username}
            if dn and not (m.get("display_name") or "").strip():
                patch["display_name"] = dn

            pr = client.patch(
                f"{pb_url}/api/collections/members/records/{mid}",
                headers=_pb_headers(pb_token),
                json=patch,
            )
            pr.raise_for_status()
            updated_members += 1

        # Denormalize usernames into existing reviews for display/search by username.
        page = 1
        while True:
            rr = client.get(
                f"{pb_url}/api/collections/reviews/records",
                headers=_pb_headers(pb_token),
                params={"page": page, "perPage": 200, "expand": "reviewer_id,reviewee_id"},
            )
            rr.raise_for_status()
            data = rr.json()
            items = data.get("items", [])
            if not items:
                break

            for r in items:
                rid = r.get("id")
                if not isinstance(rid, str):
                    continue

                cur_reviewer_u = _norm_username(r.get("reviewer_username"))
                cur_reviewee_u = _norm_username(r.get("reviewee_username"))

                exp = r.get("expand") or {}
                reviewer = exp.get("reviewer_id") or {}
                reviewee = exp.get("reviewee_id") or {}
                ru = _norm_username(reviewer.get("username"))
                eu = _norm_username(reviewee.get("username"))

                patch: dict[str, Any] = {}
                if not cur_reviewer_u and ru:
                    patch["reviewer_username"] = ru
                if not cur_reviewee_u and eu:
                    patch["reviewee_username"] = eu

                if patch:
                    pr = client.patch(
                        f"{pb_url}/api/collections/reviews/records/{rid}",
                        headers=_pb_headers(pb_token),
                        json=patch,
                    )
                    pr.raise_for_status()
                    updated_reviews += 1

            page += 1

    print(
        f"done: members_updated={updated_members} members_skipped={skipped_members} reviews_updated={updated_reviews}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

