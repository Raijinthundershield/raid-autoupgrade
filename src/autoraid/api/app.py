from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from autoraid.api.routes.status import router as status_router


def create_app(
    window_service: Any = None,
    network_manager: Any = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.window_service = window_service
        app.state.network_manager = network_manager
        yield

    app = FastAPI(lifespan=lifespan)
    app.include_router(status_router)
    return app
