from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from commontrust_api.config import api_settings

_bearer = HTTPBearer(auto_error=False)


def require_api_token(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    if not api_settings.is_configured:
        raise HTTPException(status_code=500, detail="API not configured (COMMONTRUST_API_TOKEN missing)")

    token = creds.credentials if creds else ""
    if not token or token != api_settings.api_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

