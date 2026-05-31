from fastapi import Request

from raid_autoupgrade.jobs.registry import JobRegistry
from raid_autoupgrade.protocols import (
    CacheProtocol,
    NetworkManagerProtocol,
    ScreenshotProtocol,
    WindowInteractionProtocol,
)
from raid_autoupgrade.services.count_target_screenshot import CountTargetScreenshot
from raid_autoupgrade.services.settings_service import SettingsService


def get_window_service(request: Request) -> WindowInteractionProtocol:
    return request.app.state.window_service


def get_screenshot_service(request: Request) -> ScreenshotProtocol:
    return request.app.state.screenshot_service


def get_cache_service(request: Request) -> CacheProtocol:
    return request.app.state.cache_service


def get_network_manager(request: Request) -> NetworkManagerProtocol:
    return request.app.state.network_manager


def get_job_registry(request: Request) -> JobRegistry:
    return request.app.state.job_registry


def get_count_runner(request: Request):
    """Return a factory: given adapter_ids, return a run_fn for the count workflow."""
    return request.app.state.count_runner


def get_spend_runner(request: Request):
    """Return a factory: given max_upgrade_attempts/continue_upgrade, return a run_fn for the spend workflow."""
    return request.app.state.spend_runner


def get_settings_service(request: Request) -> SettingsService:
    return request.app.state.settings_service


def get_count_screenshot_store(request: Request) -> CountTargetScreenshot:
    return request.app.state.count_screenshot_store
