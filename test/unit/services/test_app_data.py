from pathlib import Path
from autoraid.services.app_data import AppData


def test_app_data_initialization():
    """Verify AppData initializes with correct attributes."""
    cache_dir = Path("test-cache")
    app_data = AppData(cache_dir=cache_dir, debug_enabled=True)

    assert app_data.cache_dir == cache_dir
    assert app_data.debug_enabled is True


def test_debug_dir_when_enabled(tmp_path):
    """Verify debug_dir returns cache_dir/debug when debug enabled."""
    cache_dir = tmp_path / "cache"
    app_data = AppData(cache_dir=cache_dir, debug_enabled=True)

    assert app_data.debug_dir == cache_dir / "debug"


def test_debug_dir_when_disabled(tmp_path):
    """Verify debug_dir returns None when debug disabled."""
    cache_dir = tmp_path / "cache"
    app_data = AppData(cache_dir=cache_dir, debug_enabled=False)

    assert app_data.debug_dir is None


def test_ensure_directories_creates_cache(tmp_path):
    """Verify ensure_directories creates cache_dir."""
    cache_dir = tmp_path / "cache"
    app_data = AppData(cache_dir=cache_dir, debug_enabled=False)

    assert not cache_dir.exists()
    app_data.ensure_directories()
    assert cache_dir.exists()


def test_ensure_directories_creates_debug(tmp_path):
    """Verify ensure_directories creates debug_dir when enabled."""
    cache_dir = tmp_path / "cache"
    app_data = AppData(cache_dir=cache_dir, debug_enabled=True)

    assert not cache_dir.exists()
    assert app_data.debug_dir is not None
    assert not app_data.debug_dir.exists()

    app_data.ensure_directories()

    assert cache_dir.exists()
    assert app_data.debug_dir.exists()


def test_ensure_directories_idempotent(tmp_path):
    """Verify ensure_directories can be called multiple times safely."""
    cache_dir = tmp_path / "cache"
    app_data = AppData(cache_dir=cache_dir, debug_enabled=True)

    app_data.ensure_directories()
    assert cache_dir.exists()
    assert app_data.debug_dir is not None
    assert app_data.debug_dir.exists()

    # Call again - should not raise error
    app_data.ensure_directories()
    assert cache_dir.exists()
    assert app_data.debug_dir.exists()


def test_get_log_file_path_when_debug(tmp_path):
    """Verify get_log_file_path returns path when debug enabled."""
    cache_dir = tmp_path / "cache"
    app_data = AppData(cache_dir=cache_dir, debug_enabled=True)

    log_path = app_data.get_log_file_path()

    assert log_path is not None
    assert log_path == cache_dir / "debug" / "autoraid.log"


def test_get_log_file_path_when_no_debug(tmp_path):
    """Verify get_log_file_path returns None when debug disabled."""
    cache_dir = tmp_path / "cache"
    app_data = AppData(cache_dir=cache_dir, debug_enabled=False)

    log_path = app_data.get_log_file_path()

    assert log_path is None
