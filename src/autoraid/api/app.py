from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from autoraid.api.routes.count import router as count_router
from autoraid.api.routes.status import router as status_router
from autoraid.jobs.registry import JobRegistry


def create_app(
    window_service: Any = None,
    network_manager: Any = None,
    job_registry: JobRegistry | None = None,
    count_runner: Any = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.window_service = window_service
        app.state.network_manager = network_manager
        app.state.job_registry = (
            job_registry if job_registry is not None else JobRegistry()
        )
        app.state.count_runner = count_runner
        yield

    app = FastAPI(lifespan=lifespan)
    app.include_router(status_router)
    app.include_router(count_router)
    return app
