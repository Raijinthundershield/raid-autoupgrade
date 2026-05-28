from fastapi import Request

from autoraid.protocols import NetworkManagerProtocol, WindowInteractionProtocol


def get_window_service(request: Request) -> WindowInteractionProtocol:
    return request.app.state.window_service


def get_network_manager(request: Request) -> NetworkManagerProtocol:
    return request.app.state.network_manager
