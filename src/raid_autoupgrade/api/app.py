from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from raid_autoupgrade.api.routes.adapters import router as adapters_router
from raid_autoupgrade.api.routes.count import router as count_router
from raid_autoupgrade.api.routes.regions import router as regions_router
from raid_autoupgrade.api.routes.settings import router as settings_router
from raid_autoupgrade.api.routes.spend import router as spend_router
from raid_autoupgrade.api.routes.status import router as status_router
from raid_autoupgrade.exceptions import (
    RaidAutoupgradeError,
    NetworkAdapterError,
    WindowNotFoundException,
    WorkflowValidationError,
)
from raid_autoupgrade.jobs.registry import JobRegistry

_EXCEPTION_STATUS: dict[type[RaidAutoupgradeError], int] = {
    WindowNotFoundException: 409,
    WorkflowValidationError: 422,
    NetworkAdapterError: 502,
}


def create_app(
    window_service: Any = None,
    network_manager: Any = None,
    job_registry: JobRegistry | None = None,
    count_runner: Any = None,
    spend_runner: Any = None,
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
        app.state.spend_runner = spend_runner
        app.state.settings_service = settings_service
        app.state.screenshot_service = screenshot_service
        app.state.cache_service = cache_service
        yield

    app = FastAPI(lifespan=lifespan)

    @app.exception_handler(RaidAutoupgradeError)
    async def _raid_autoupgrade_handler(
        request: Request, exc: RaidAutoupgradeError
    ) -> JSONResponse:
        status = _EXCEPTION_STATUS.get(type(exc), 500)
        return JSONResponse(
            status_code=status,
            content={"error": type(exc).__name__, "message": str(exc), "detail": None},
        )

    @app.exception_handler(Exception)
    async def _generic_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred.",
                "detail": None,
            },
        )

    app.include_router(status_router)
    app.include_router(count_router)
    app.include_router(spend_router)
    app.include_router(regions_router)
    app.include_router(settings_router)
    app.include_router(adapters_router)
    return app
