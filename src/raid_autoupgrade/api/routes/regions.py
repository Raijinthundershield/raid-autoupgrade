import cv2
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, field_validator

from raid_autoupgrade.api.deps import (
    get_cache_service,
    get_screenshot_service,
    get_window_service,
)
from raid_autoupgrade.constants import RAID_WINDOW_TITLE
from raid_autoupgrade.exceptions import WindowNotFoundException
from raid_autoupgrade.protocols import (
    CacheProtocol,
    ScreenshotProtocol,
    WindowInteractionProtocol,
)

router = APIRouter()


@router.get("/api/screenshot")
def get_screenshot(
    screenshot_service: ScreenshotProtocol = Depends(get_screenshot_service),
):
    try:
        image = screenshot_service.take_screenshot(RAID_WINDOW_TITLE)
    except WindowNotFoundException:
        raise HTTPException(status_code=404, detail="Raid window not found")

    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode screenshot")
    return Response(content=buf.tobytes(), media_type="image/png")


class RegionsBody(BaseModel):
    upgrade_bar: list[int]
    upgrade_button: list[int]

    @field_validator("upgrade_bar", "upgrade_button")
    @classmethod
    def must_be_four_ints(cls, v: list[int]) -> list[int]:
        if len(v) != 4:
            raise ValueError("region must have exactly 4 values [l, t, w, h]")
        return v


@router.get("/api/regions")
def get_regions(
    window_service: WindowInteractionProtocol = Depends(get_window_service),
    cache_service: CacheProtocol = Depends(get_cache_service),
):
    try:
        current_size = window_service.get_window_size(RAID_WINDOW_TITLE)
    except WindowNotFoundException:
        any_entry = cache_service.find_regions_any_size()
        regions = any_entry[1] if any_entry else None
        return {"regions": regions, "window_size_mismatch": False}

    regions = cache_service.get_regions(current_size)
    if regions is not None:
        return {"regions": regions, "window_size_mismatch": False}

    stale = cache_service.find_regions_any_size() is not None
    return {"regions": None, "window_size_mismatch": stale}


@router.put("/api/regions")
def put_regions(
    body: RegionsBody,
    window_service: WindowInteractionProtocol = Depends(get_window_service),
    cache_service: CacheProtocol = Depends(get_cache_service),
):
    try:
        window_size = window_service.get_window_size(RAID_WINDOW_TITLE)
    except WindowNotFoundException:
        raise HTTPException(status_code=404, detail="Raid window not found")
    regions = {
        "upgrade_bar": tuple(body.upgrade_bar),
        "upgrade_button": tuple(body.upgrade_button),
    }
    cache_service.set_regions(window_size, regions)
    return {}
