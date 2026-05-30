from fastapi import APIRouter, Depends

from autoraid.api.deps import get_settings_service
from autoraid.services.settings_service import Settings, SettingsService

router = APIRouter()


@router.get("/api/settings")
def get_settings(svc: SettingsService = Depends(get_settings_service)) -> dict:
    s = svc.get_settings()
    return {
        "selected_adapters": s.selected_adapters,
        "last_count_result": s.last_count_result,
    }


@router.put("/api/settings")
def put_settings(
    body: Settings,
    svc: SettingsService = Depends(get_settings_service),
) -> dict:
    svc.save_settings(body)
    s = svc.get_settings()
    return {
        "selected_adapters": s.selected_adapters,
        "last_count_result": s.last_count_result,
    }
