from __future__ import annotations

import logging

from fastapi import Depends, FastAPI

from commontrust_api.auth import require_api_token
from commontrust_api.hub.routes import router as hub_router
from commontrust_api.identity.routes import router as identity_router
from commontrust_api.ledger.routes import router as ledger_router
from commontrust_api.pb import make_pb_client
from commontrust_api.reputation.routes import router as reputation_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="CommonTrust API", version="1.0.0")

    # Auth gate: all routes require the API token.
    app.include_router(identity_router, dependencies=[Depends(require_api_token)])
    app.include_router(reputation_router, dependencies=[Depends(require_api_token)])
    app.include_router(ledger_router, dependencies=[Depends(require_api_token)])
    app.include_router(hub_router, dependencies=[Depends(require_api_token)])

    pb = make_pb_client()

    @app.on_event("startup")
    async def _startup() -> None:
        await pb.authenticate()
        logger.info("CommonTrust API authenticated with PocketBase")

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await pb.close()

    # Store on app state for handlers.
    app.state.pb = pb
    return app


app = create_app()
