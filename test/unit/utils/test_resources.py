"""Unit tests for the frozen-aware resource path resolver."""

from pathlib import Path

from raid_autoupgrade.utils.resources import resource_path


class TestResourcePath:
    """Contract: resolve bundled-asset paths in both source and frozen layouts."""

    def test_returns_source_relative_path_when_not_frozen(self, monkeypatch):
        """When not frozen, the path is anchored at the repo root next to src/."""
        monkeypatch.delattr("sys.frozen", raising=False)

        result = resource_path("frontend", "dist")

        # Repo root is three parents above the package (utils -> raid_autoupgrade
        # -> src -> root), which is where frontend/dist lives in a source checkout.
        expected = Path(__file__).resolve().parents[3] / "frontend" / "dist"
        assert result == expected

    def test_returns_meipass_relative_path_when_frozen(self, monkeypatch, tmp_path):
        """When frozen, the path is anchored under PyInstaller's sys._MEIPASS."""
        monkeypatch.setattr("sys.frozen", True, raising=False)
        monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)

        result = resource_path("frontend", "dist")

        assert result == tmp_path / "frontend" / "dist"
