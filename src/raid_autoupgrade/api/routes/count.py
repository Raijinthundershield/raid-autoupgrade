import asyncio
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from fastapi.responses import Response
from pydantic import BaseModel

from raid_autoupgrade.api.deps import (
    get_count_runner,
    get_count_screenshot_store,
    get_job_registry,
)
from raid_autoupgrade.jobs.registry import ConflictError, JobRegistry
from raid_autoupgrade.services.count_target_screenshot import CountTargetScreenshot
from raid_autoupgrade.services.network import AdapterId

router = APIRouter()


@router.get("/api/last-count-screenshot")
def get_last_count_screenshot(
    store: CountTargetScreenshot = Depends(get_count_screenshot_store),
):
    """Return the counted Target's picture (staging if a Count is live, else the
    last committed one). 404 when no Count has kept a picture yet, so the panel
    can hide the element rather than show a broken image."""
    image_bytes = store.read()
    if image_bytes is None:
        raise HTTPException(status_code=404, detail="no count screenshot")
    return Response(content=image_bytes, media_type="image/png")


class CountRequest(BaseModel):
    adapter_ids: list[AdapterId] | None = None


@router.post("/api/workflows/count")
def post_count(
    body: CountRequest,
    registry: JobRegistry = Depends(get_job_registry),
    make_run_fn: Callable = Depends(get_count_runner),
):
    run_fn = make_run_fn(body.adapter_ids)
    try:
        job_id = registry.start_job(run_fn)
    except ConflictError:
        raise HTTPException(status_code=409, detail="a workflow is already running")
    return {"job_id": job_id}


@router.get("/api/workflows/{job_id}")
def get_job(
    job_id: str,
    registry: JobRegistry = Depends(get_job_registry),
):
    state = registry.get_job(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": state.job_id, "status": state.status, "result": state.result}


@router.post("/api/workflows/{job_id}/cancel", status_code=204)
def cancel_job(
    job_id: str,
    registry: JobRegistry = Depends(get_job_registry),
):
    registry.cancel(job_id)


@router.websocket("/ws/workflows/{job_id}")
async def ws_job(
    job_id: str,
    websocket: WebSocket,
):
    registry: JobRegistry = websocket.app.state.job_registry
    q = registry.get_queue(job_id)
    if q is None:
        await websocket.close(code=4004)
        return

    await websocket.accept()
    loop = asyncio.get_running_loop()

    while True:
        event = await loop.run_in_executor(None, q.get)
        await websocket.send_json(event)
        if event.get("type") in ("done", "error"):
            await websocket.close()
            return
