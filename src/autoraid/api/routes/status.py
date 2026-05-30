from fastapi import APIRouter, Depends

from autoraid.api.deps import get_network_manager, get_window_service
from autoraid.protocols import NetworkManagerProtocol, WindowInteractionProtocol
from autoraid.services.network import NetworkState

RAID_WINDOW_TITLE = "Raid: Shadow Legends"

router = APIRouter()


@router.get("/api/status")
def get_status(
    window_service: WindowInteractionProtocol = Depends(get_window_service),
    network_manager: NetworkManagerProtocol = Depends(get_network_manager),
) -> dict:
    return {
        "raid_window_detected": window_service.window_exists(RAID_WINDOW_TITLE),
        "network_online": network_manager.check_network_access() == NetworkState.ONLINE,
    }
