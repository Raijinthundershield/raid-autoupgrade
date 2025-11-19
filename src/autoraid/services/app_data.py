import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppData:
    """Centralized application directory configuration.

    Manages root_dir, cache_dir, debug_dir, and browser_data_dir paths with
    single source of truth for all application directories.

    The root directory defaults to C:\\ProgramData\\AutoRaid but can be overridden
    via AUTORAID_DATA_DIR environment variable or explicit root_dir parameter.
    """

    DEFAULT_ROOT = Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "AutoRaid"
    DEFAULT_DEBUG_SUBDIR = "debug"

    root_dir: Path
    debug_enabled: bool

    def __init__(
        self, root_dir: Path | None = None, debug_enabled: bool = False
    ) -> None:
        """Initialize AppData with optional root directory override.

        Args:
            root_dir: Override application data root directory.
                     If None, resolves from env var or PROGRAMDATA default.
            debug_enabled: Whether debug mode is enabled.
        """
        self.root_dir = (
            root_dir if root_dir is not None else self._get_configured_root()
        )
        self.debug_enabled = debug_enabled

    def _get_configured_root(self) -> Path:
        """Get configured root directory from environment or default.

        Resolution order:
        1. AUTORAID_DATA_DIR environment variable
        2. DEFAULT_ROOT (C:\\ProgramData\\AutoRaid)

        Returns:
            Path to application data root directory.
        """
        env_data_dir = os.getenv("AUTORAID_DATA_DIR")
        if env_data_dir:
            return Path(env_data_dir)
        return self.DEFAULT_ROOT

    @property
    def cache_dir(self) -> Path:
        """Return cache directory path (root_dir/cache)."""
        return self.root_dir / "cache"

    @property
    def debug_dir(self) -> Path | None:
        """Return debug directory path if debug enabled, else None."""
        if self.debug_enabled:
            return self.root_dir / self.DEFAULT_DEBUG_SUBDIR
        return None

    @property
    def browser_data_dir(self) -> Path:
        """Return Edge user data directory (used when Edge is active browser)."""
        return self.root_dir / "browser_data"

    def ensure_directories(self) -> None:
        """Create cache_dir, debug_dir, and browser_data_dir if they don't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if self.debug_dir:
            self.debug_dir.mkdir(parents=True, exist_ok=True)
        self.browser_data_dir.mkdir(parents=True, exist_ok=True)

    def get_log_file_path(self) -> Path | None:
        """Return path to log file if debug enabled, else None."""
        if self.debug_dir:
            return self.debug_dir / "autoraid.log"
        return None
