"""Unit tests for AppData service."""

from pathlib import Path
from unittest.mock import patch

from raid_autoupgrade.services.app_data import AppData


class TestAppDataInitialization:
    """Unit tests for AppData initialization and configuration."""

    def test_app_data_with_default_root(self):
        """Verify AppData uses PROGRAMDATA default when no override specified."""
        with patch("os.getenv") as mock_getenv:
            # Mock PROGRAMDATA environment variable
            mock_getenv.side_effect = lambda key, default=None: (
                "C:\\ProgramData" if key == "PROGRAMDATA" else default
            )

            app_data = AppData(debug_enabled=False)

            assert app_data.root_dir == Path("C:\\ProgramData\\RaidAutoupgrade")
            assert app_data.debug_enabled is False

    def test_app_data_with_custom_root_parameter(self):
        """Verify AppData uses explicit root_dir parameter when provided."""
        custom_root = Path("C:\\custom\\data")

        app_data = AppData(root_dir=custom_root, debug_enabled=True)

        assert app_data.root_dir == custom_root
        assert app_data.debug_enabled is True

    def test_app_data_with_env_var_override(self):
        """Verify AppData uses RAID_AUTOUPGRADE_DATA_DIR env var when set."""
        with patch("os.getenv") as mock_getenv:
            # Mock environment variables
            def getenv_side_effect(key, default=None):
                if key == "PROGRAMDATA":
                    return "C:\\ProgramData"
                elif key == "RAID_AUTOUPGRADE_DATA_DIR":
                    return "C:\\env\\override"
                return default

            mock_getenv.side_effect = getenv_side_effect

            app_data = AppData(debug_enabled=False)

            assert app_data.root_dir == Path("C:\\env\\override")


class TestAppDataProperties:
    """Unit tests for AppData property accessors."""

    def test_cache_dir_property(self):
        """Verify cache_dir property returns root_dir/cache."""
        app_data = AppData(root_dir=Path("C:\\test"), debug_enabled=False)

        assert app_data.cache_dir == Path("C:\\test\\cache")

    def test_debug_dir_with_debug_enabled(self):
        """Verify debug_dir property returns root_dir/debug when enabled."""
        app_data = AppData(root_dir=Path("C:\\test"), debug_enabled=True)

        assert app_data.debug_dir == Path("C:\\test\\debug")

    def test_debug_dir_with_debug_disabled(self):
        """Verify debug_dir property returns None when disabled."""
        app_data = AppData(root_dir=Path("C:\\test"), debug_enabled=False)

        assert app_data.debug_dir is None

    def test_browser_data_dir_property(self):
        """Verify browser_data_dir property returns root_dir/browser_data."""
        app_data = AppData(root_dir=Path("C:\\test"), debug_enabled=False)

        assert app_data.browser_data_dir == Path("C:\\test\\browser_data")


class TestAppDataDirectoryCreation:
    """Unit tests for AppData directory creation."""

    def test_ensure_directories_creates_all_directories(self):
        """Verify ensure_directories() creates cache, debug, and browser_data dirs."""
        app_data = AppData(root_dir=Path("C:\\test"), debug_enabled=True)

        with patch.object(Path, "mkdir") as mock_mkdir:
            app_data.ensure_directories()

            # Verify mkdir called for cache_dir
            mock_mkdir.assert_any_call(parents=True, exist_ok=True)

            # Should be called 3 times: cache_dir, debug_dir, browser_data_dir
            assert mock_mkdir.call_count == 3

    def test_ensure_directories_skips_debug_when_disabled(self):
        """Verify ensure_directories() skips debug_dir when debug disabled."""
        app_data = AppData(root_dir=Path("C:\\test"), debug_enabled=False)

        with patch.object(Path, "mkdir") as mock_mkdir:
            app_data.ensure_directories()

            # Should be called 2 times: cache_dir, browser_data_dir (no debug_dir)
            assert mock_mkdir.call_count == 2


class TestAppDataLogFilePath:
    """Unit tests for AppData log file path generation."""

    def test_get_log_file_path_with_debug_enabled(self):
        """Verify get_log_file_path() returns log path when debug enabled."""
        app_data = AppData(root_dir=Path("C:\\test"), debug_enabled=True)

        log_path = app_data.get_log_file_path()

        assert log_path == Path("C:\\test\\debug\\raid_autoupgrade.log")

    def test_get_log_file_path_with_debug_disabled(self):
        """Verify get_log_file_path() returns None when debug disabled."""
        app_data = AppData(root_dir=Path("C:\\test"), debug_enabled=False)

        log_path = app_data.get_log_file_path()

        assert log_path is None
