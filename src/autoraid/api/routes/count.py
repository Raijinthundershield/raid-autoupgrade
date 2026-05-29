import asyncio
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from pydantic import BaseModel

from autoraid.api.deps import get_count_runner, get_job_registry
from autoraid.jobs.registry import ConflictError, JobRegistry

router = APIRouter()


class CountRequest(BaseModel):
    adapter_ids: list[int] | None = None
    debug: bool = False
    log_debug: bool = False


@router.post("/api/workflows/count")
def post_count(
    body: CountRequest,
    registry: JobRegistry = Depends(get_job_registry),
    make_run_fn: Callable = Depends(get_count_runner),
):
    run_fn = make_run_fn(body.adapter_ids, body.debug, body.log_debug)
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
