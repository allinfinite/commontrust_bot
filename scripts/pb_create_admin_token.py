#!/usr/bin/env python3
"""
Create a long-lived PocketBase admin/superuser token using only CLI (HTTP API calls).

How it works:
- Authenticates as a superuser (PocketBase >= v0.23) via:
    POST /api/collections/_superusers/auth-with-password
  (falls back to older admin endpoint if present)
- Mints an "impersonate" token for that superuser record with a long duration.
- Writes POCKETBASE_ADMIN_TOKEN into .env.local (gitignored by default).

Environment variables:
- POCKETBASE_URL (required)
- POCKETBASE_ADMIN_EMAIL (required)
- POCKETBASE_ADMIN_PASSWORD (required)

Optional:
- POCKETBASE_TOKEN_DURATION_SECONDS (default: 315360000 = 10 years)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import httpx


def _must_env(name: str) -> str:
    val = os.environ.get(name)
    if not val or not val.strip():
        raise SystemExit(f"Missing required env var: {name}")
    return val.strip()


def _write_env_local(pb_url: str, token: str) -> None:
    env_path = Path(".env.local")
    existing = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []

    def upsert(lines: list[str], key: str, value: str) -> list[str]:
        out: list[str] = []
        found = False
        for line in lines:
            if line.startswith(f"{key}="):
                out.append(f"{key}={value}")
                found = True
            else:
                out.append(line)
        if not found:
            if out and out[-1].strip():
                out.append("")
            out.append(f"{key}={value}")
        return out

    updated = existing
    updated = upsert(updated, "POCKETBASE_URL", pb_url)
    updated = upsert(updated, "POCKETBASE_ADMIN_TOKEN", token)

    env_path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    pb_url = _must_env("POCKETBASE_URL").rstrip("/")
    email = _must_env("POCKETBASE_ADMIN_EMAIL")
    password = _must_env("POCKETBASE_ADMIN_PASSWORD")
    duration = int(os.environ.get("POCKETBASE_TOKEN_DURATION_SECONDS", "315360000"))

    # PocketBase v0.23+: superusers are a system collection.
    auth_endpoints = [
        f"{pb_url}/api/collections/_superusers/auth-with-password",
        # PocketBase older versions:
        f"{pb_url}/api/admins/auth-with-password",
    ]

    with httpx.Client(timeout=30.0) as client:
        auth_data: dict[str, Any] | None = None
        used_endpoint: str | None = None
        for ep in auth_endpoints:
            r = client.post(ep, json={"identity": email, "password": password})
            if r.status_code == 200:
                auth_data = r.json()
                used_endpoint = ep
                break
            if r.status_code == 404:
                continue
            # Any other error means "endpoint exists but auth failed" etc.
            try:
                msg = r.json().get("message")
            except Exception:
                msg = r.text
            raise SystemExit(f"Auth failed at {ep} ({r.status_code}): {msg}")

        if not auth_data or not used_endpoint:
            raise SystemExit("No supported auth endpoint found on the server.")

        token = auth_data.get("token") or auth_data.get("data", {}).get("token")
        record = auth_data.get("record") or auth_data.get("admin") or auth_data.get("data", {}).get("record")
        record_id = record.get("id") if isinstance(record, dict) else None

        if not token or not record_id:
            raise SystemExit(f"Unexpected auth response shape from {used_endpoint}")

        # Mint long-lived impersonation token (available on the collection API).
        # This yields an API-key-like token that doesn't require storing the password.
        imp_ep = f"{pb_url}/api/collections/_superusers/impersonate/{record_id}"
        imp = client.post(imp_ep, headers={"Authorization": token}, json={"duration": duration})
        if imp.status_code != 200:
            try:
                msg = imp.json().get("message")
            except Exception:
                msg = imp.text
            raise SystemExit(f"Impersonate failed ({imp.status_code}): {msg}")

        imp_token = imp.json().get("token") or imp.json().get("data", {}).get("token")
        if not imp_token:
            raise SystemExit("Unexpected impersonate response shape (missing token).")

    _write_env_local(pb_url, imp_token)
    print("Wrote POCKETBASE_URL and POCKETBASE_ADMIN_TOKEN to .env.local")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

