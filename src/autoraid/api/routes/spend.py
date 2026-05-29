from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from autoraid.api.deps import get_job_registry, get_spend_runner
from autoraid.jobs.registry import ConflictError, JobRegistry

router = APIRouter()


class SpendRequest(BaseModel):
    max_upgrade_attempts: int
    continue_upgrade: bool = False


@router.post("/api/workflows/spend")
def post_spend(
    body: SpendRequest,
    registry: JobRegistry = Depends(get_job_registry),
    make_run_fn: Callable = Depends(get_spend_runner),
):
    run_fn = make_run_fn(body.max_upgrade_attempts, body.continue_upgrade)
    try:
        job_id = registry.start_job(run_fn)
    except ConflictError:
        raise HTTPException(status_code=409, detail="a workflow is already running")
    return {"job_id": job_id}
