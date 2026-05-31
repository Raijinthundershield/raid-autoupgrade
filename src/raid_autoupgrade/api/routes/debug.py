from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from raid_autoupgrade.api.deps import get_debug_session_store
from raid_autoupgrade.services.debug_session_store import DebugSessionStore

router = APIRouter()


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
