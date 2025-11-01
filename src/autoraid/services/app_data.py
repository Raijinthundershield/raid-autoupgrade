from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppData:
    """Centralized application directory configuration.

    Manages cache_dir and debug_dir paths with single source of truth
    for all application directories.
    """

    DEFAULT_CACHE_DIR = Path("cache-raid-autoupgrade")
    DEFAULT_DEBUG_SUBDIR = "debug"

    cache_dir: Path
    debug_enabled: bool

    @property
    def debug_dir(self) -> Path | None:
        """Return debug directory path if debug enabled, else None."""
        if self.debug_enabled:
            return self.cache_dir / self.DEFAULT_DEBUG_SUBDIR
        return None

    def ensure_directories(self) -> None:
        """Create cache_dir and debug_dir (if enabled) if they don't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if self.debug_dir:
            self.debug_dir.mkdir(parents=True, exist_ok=True)

    def get_log_file_path(self) -> Path | None:
        """Return path to log file if debug enabled, else None."""
        if self.debug_dir:
            return self.debug_dir / "autoraid.log"
        return None
