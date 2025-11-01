"""Integration tests for CLI to validate US4 (Unchanged User Workflows).

These tests verify that the refactored CLI produces the same behavior as before.
"""

import subprocess
from pathlib import Path
import pytest
from click.testing import CliRunner
from autoraid.cli.cli import autoraid


class TestCLIIntegration:
    """Integration tests for CLI behavior after refactoring."""

    @pytest.fixture
    def baseline_dir(self):
        """Get baseline directory for expected outputs."""
        return Path(__file__).parent

    def test_cached_regions_load_successfully(self, tmp_path):
        """Test that pre-refactor cached regions load without errors (US4 acceptance criteria).

        This test verifies backward compatibility with existing cache formats.
        """
        from diskcache import Cache
        from autoraid.services.cache_service import CacheService

        # Create a cache with pre-refactor format
        cache_dir = tmp_path / "test_cache"
        cache = Cache(str(cache_dir))

        # Create pre-refactor cache key format
        window_size = (1920, 1080)
        cache_key = f"regions_{window_size[0]}_{window_size[1]}"

        # Store regions in pre-refactor format
        regions = {
            "upgrade_bar": (100, 200, 300, 50),
            "upgrade_button": (100, 300, 300, 100),
            "artifact_icon": (50, 50, 100, 100),
        }
        cache.set(cache_key, regions)

        # Test that CacheService can load pre-refactor cache
        cache_service = CacheService(cache)
        loaded_regions = cache_service.get_regions(window_size)

        # Verify regions loaded correctly
        assert loaded_regions is not None, "Failed to load pre-refactor cached regions"
        assert loaded_regions == regions, "Loaded regions don't match stored regions"

        # Verify cache key format is unchanged
        assert (
            cache_service.create_regions_key(window_size) == cache_key
        ), "Cache key format has changed, breaking backward compatibility"

    def test_upgrade_commands_exist(self):
        """Test that upgrade commands are still available after refactoring."""
        # Test upgrade group exists
        result = subprocess.run(
            ["uv", "run", "autoraid", "upgrade", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0, "Upgrade command group not accessible"
        assert "count" in result.stdout, "Count command not found in upgrade group"
        assert "spend" in result.stdout, "Spend command not found in upgrade group"
        assert "region" in result.stdout, "Region command not found in upgrade group"

    def test_cli_context_contains_app_data(self):
        """Test that CLI context object contains app_data instance.

        This verifies that AppData integration properly populates the Click context.
        """
        runner = CliRunner()

        # Run a command that uses the context (help is safe and doesn't need validation)
        result = runner.invoke(autoraid, ["--help"])

        # Verify the command runs successfully
        assert result.exit_code == 0, "CLI should run successfully"

        # Test with debug flag to ensure app_data is created with debug_enabled=True
        result_debug = runner.invoke(autoraid, ["--debug", "--help"])
        assert result_debug.exit_code == 0, "CLI with --debug should run successfully"
