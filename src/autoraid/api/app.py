from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from autoraid.api.routes.adapters import router as adapters_router
from autoraid.api.routes.count import router as count_router
from autoraid.api.routes.regions import router as regions_router
from autoraid.api.routes.settings import router as settings_router
from autoraid.api.routes.status import router as status_router
from autoraid.jobs.registry import JobRegistry


def create_app(
    window_service: Any = None,
    network_manager: Any = None,
    job_registry: JobRegistry | None = None,
    count_runner: Any = None,
    settings_service: Any = None,
    screenshot_service: Any = None,
    cache_service: Any = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.window_service = window_service
        app.state.network_manager = network_manager
        app.state.job_registry = (
            job_registry if job_registry is not None else JobRegistry()
        )
        app.state.count_runner = count_runner
        app.state.settings_service = settings_service
        app.state.screenshot_service = screenshot_service
        app.state.cache_service = cache_service
        yield

    app = FastAPI(lifespan=lifespan)
    app.include_router(status_router)
    app.include_router(count_router)
    app.include_router(regions_router)
    app.include_router(settings_router)
    app.include_router(adapters_router)
    return app
