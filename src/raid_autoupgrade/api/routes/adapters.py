from fastapi import APIRouter, Depends

from raid_autoupgrade.api.deps import get_network_manager
from raid_autoupgrade.protocols import NetworkManagerProtocol

router = APIRouter()


@router.get("/api/adapters")
def get_adapters(
    network_manager: NetworkManagerProtocol = Depends(get_network_manager),
) -> list[dict]:
    adapters = network_manager.get_adapters()
    return [{"id": a.id, "name": a.name, "enabled": a.enabled} for a in adapters]
