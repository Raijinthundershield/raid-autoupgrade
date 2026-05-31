from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from raid_autoupgrade.api.deps import get_debug_session_store
from raid_autoupgrade.services.debug_session_store import DebugSessionStore

router = APIRouter()


class FrameLabel(BaseModel):
    """One frame the reviewer chose to export, with its corrected label."""

    frame_number: int
    label: str


class ExportRequest(BaseModel):
    """A request to export the reviewer's corrected labels as fixture samples."""

    session: str
    labels: list[FrameLabel]


class LabelUpdate(BaseModel):
    """A request to persist one frame's corrected label for a session."""

    session: str
    frame_number: int
    label: str


@router.get("/api/debug/status")
def get_debug_status(
    store: DebugSessionStore = Depends(get_debug_session_store),
) -> dict:
    """Report whether debug capture is enabled, so the frontend can decide
    whether to render the Label tab."""
    return {"enabled": store.enabled}


@router.get("/api/debug/sessions")
def list_debug_sessions(
    store: DebugSessionStore = Depends(get_debug_session_store),
) -> dict:
    """List captured sessions, most-recent-first. 404 when debug is disabled,
    so the endpoint is absent without ``--debug``."""
    if not store.enabled:
        raise HTTPException(status_code=404, detail="debug capture disabled")
    return {"sessions": [asdict(s) for s in store.list_sessions()]}


@router.get("/api/debug/frames")
def get_session_frames(
    session: str,
    store: DebugSessionStore = Depends(get_debug_session_store),
) -> dict:
    """Return a session's captured frames, each carrying the detector's
    recorded state guess and its ROI/screenshot filenames. ``session`` is the
    id from the sessions list (a slash-bearing relative path, so it travels as
    a query parameter)."""
    if not store.enabled:
        raise HTTPException(status_code=404, detail="debug capture disabled")
    frames = store.read_frames(session)
    if frames is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {"frames": frames}


@router.get("/api/debug/image")
def get_session_image(
    session: str,
    file: str,
    store: DebugSessionStore = Depends(get_debug_session_store),
) -> Response:
    """Serve a frame's ROI or screenshot PNG (``file``) from a session."""
    if not store.enabled:
        raise HTTPException(status_code=404, detail="debug capture disabled")
    data = store.read_image(session, file)
    if data is None:
        raise HTTPException(status_code=404, detail="image not found")
    return Response(content=data, media_type="image/png")


@router.post("/api/debug/export")
def export_labeled_samples(
    request: ExportRequest,
    store: DebugSessionStore = Depends(get_debug_session_store),
) -> dict:
    """Write the reviewer's corrected labels back into the session as
    ``{label}_{w}x{h}_{n}.png`` + ``SampleAnnotation`` sidecar pairs, ready to
    copy into ``test/fixtures/images/``. Returns the written PNG filenames. 404
    when debug is disabled or the session is unknown."""
    if not store.enabled:
        raise HTTPException(status_code=404, detail="debug capture disabled")
    written = store.export_labeled_samples(
        request.session,
        [label.model_dump() for label in request.labels],
    )
    if written is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "exported": written,
        "directory": store.export_directory(request.session),
    }


@router.post("/api/debug/labels")
def set_frame_label(
    request: LabelUpdate,
    store: DebugSessionStore = Depends(get_debug_session_store),
) -> dict:
    """Persist one frame's corrected label so it survives reloading the session.
    The detector's original guess is left intact. 404 when debug is disabled or
    the session is unknown."""
    if not store.enabled:
        raise HTTPException(status_code=404, detail="debug capture disabled")
    if not store.set_label(request.session, request.frame_number, request.label):
        raise HTTPException(status_code=404, detail="session not found")
    return {"ok": True}
