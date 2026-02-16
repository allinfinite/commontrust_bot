from __future__ import annotations

import os

import uvicorn


def run() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("commontrust_api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()

