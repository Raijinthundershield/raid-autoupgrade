"""Utility functions for progress bar review GUI."""

import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from autoraid.workflows.progressbar_monitor_workflow import (
    ReviewedFrameMetadata,
)


def load_monitor_log(session_dir: Path) -> dict[str, Any]:
    """Load monitor_log.json from a session directory."""
    log_path = session_dir / "monitor_log.json"
    with open(log_path) as f:
        return json.load(f)


def create_review_folder(session_dir: Path) -> Path:
    """Create a review folder copy of the session directory.

    Returns:
        Path to review folder (e.g., "20251025_172020_review")
    """
    review_dir = session_dir.parent / f"{session_dir.name}_review"

    if not review_dir.exists():
        shutil.copytree(session_dir, review_dir)

    return review_dir


def load_reviewed_metadata(review_dir: Path) -> list[ReviewedFrameMetadata]:
    """Load reviewed metadata from review_log.json if it exists."""
    review_log_path = review_dir / "review_log.json"

    if not review_log_path.exists():
        # Create initial review log from monitor log
        monitor_log = load_monitor_log(review_dir)
        frames = monitor_log["frames"]

        # Convert to ReviewedFrameMetadata instances
        reviewed_frames = [
            ReviewedFrameMetadata(**frame, true_state=None) for frame in frames
        ]

        save_reviewed_metadata(review_dir, reviewed_frames, monitor_log)
        return reviewed_frames

    # Load existing review log
    with open(review_log_path) as f:
        data = json.load(f)

    return [ReviewedFrameMetadata(**frame) for frame in data["frames"]]


def save_reviewed_metadata(
    review_dir: Path,
    frames: list[ReviewedFrameMetadata],
    original_metadata: dict[str, Any] | None = None,
) -> None:
    """Save reviewed metadata to review_log.json."""
    review_log_path = review_dir / "review_log.json"

    # Load original metadata if not provided
    if original_metadata is None:
        monitor_log = load_monitor_log(review_dir)
        original_metadata = {
            "session_start": monitor_log["session_start"],
            "total_frames": monitor_log["total_frames"],
            "state_distribution": monitor_log["state_distribution"],
            "check_interval": monitor_log["check_interval"],
            "max_frames": monitor_log["max_frames"],
        }

    # Save with reviewed frames
    with open(review_log_path, "w") as f:
        json.dump(
            {
                **original_metadata,
                "frames": [asdict(frame) for frame in frames],
            },
            f,
            indent=2,
        )


def get_available_sessions(cache_dir: Path) -> list[Path]:
    """Get list of available monitoring session directories.

    Checks both possible locations:
    - cache_dir/progressbar_monitor/ (when run without --debug)
    - cache_dir/debug/progressbar_monitor/ (when run with --debug)

    Args:
        cache_dir: Root cache directory (e.g., cache-raid-autoupgrade)

    Returns:
        List of session directories, sorted by most recent first
    """
    sessions = []

    # Check both possible locations
    possible_locations = [
        cache_dir / "progressbar_monitor",  # Without --debug flag
        cache_dir / "debug" / "progressbar_monitor",  # With --debug flag
    ]

    for progressbar_monitor_dir in possible_locations:
        if progressbar_monitor_dir.exists():
            # Filter out review directories
            location_sessions = [
                d
                for d in progressbar_monitor_dir.iterdir()
                if d.is_dir() and not d.name.endswith("_review")
            ]
            sessions.extend(location_sessions)

    return sorted(sessions, reverse=True)  # Most recent first
