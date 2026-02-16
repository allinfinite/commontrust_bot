from __future__ import annotations

from commontrust_api.config import api_settings
from commontrust_api.pocketbase_client import PocketBaseClient


def make_pb_client() -> PocketBaseClient:
    # Create an isolated PocketBase client for the API (do not rely on bot settings).
    return PocketBaseClient(
        base_url=api_settings.pocketbase_url,
        admin_token=api_settings.pocketbase_admin_token,
        admin_email=api_settings.pocketbase_admin_email,
        admin_password=api_settings.pocketbase_admin_password,
    )
