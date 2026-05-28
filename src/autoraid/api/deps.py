from fastapi import Request

from autoraid.jobs.registry import JobRegistry
from autoraid.protocols import NetworkManagerProtocol, WindowInteractionProtocol


def get_window_service(request: Request) -> WindowInteractionProtocol:
    return request.app.state.window_service


def get_network_manager(request: Request) -> NetworkManagerProtocol:
    return request.app.state.network_manager


def get_job_registry(request: Request) -> JobRegistry:
    return request.app.state.job_registry


def get_count_runner(request: Request):
    """Return a factory: given adapter_ids, return a run_fn for the count workflow."""
    return request.app.state.count_runner
