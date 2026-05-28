# CLAUDE.md

Guidance for Claude Code working in this repo.

## Project

**AutoRaid** — Windows-only automation tool for Raid: Shadow Legends. Uses OpenCV + pyautogui to count upgrade fails offline (airplane-mode trick), then spend attempts online to guarantee an upgrade.

Background on the trick: [docs/airplane-mode-trick.md](docs/airplane-mode-trick.md).

## Commands

Package manager is `uv`. All commands run from the `autoraid/` directory.

```bash
uv sync                       # install / refresh venv
uv run autoraid --help        # CLI
uv run autoraid gui           # native desktop GUI
uv run pytest                 # tests
uv run pytest test/unit/      # unit only
uv run ruff check --fix .     # lint
uv run ruff format .          # format
uv run pre-commit run --all-files
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for layer breakdown, DI container, progress bar detection thresholds, and the upgrade flow.

## Constraints

- **Windows only**: WMI for adapter control, Win32 for window management.
- **Admin rights**: Required for WMI. Window activation uses ALT+SetForegroundWindow first (bypasses UIPI when Raid runs admin via RSLHelper), falls back to minimize/restore.
- **Window size**: Constant during a session — regions are cached per size. Resizing invalidates cache.
- **First-attempt success**: Not handled; tool assumes at least one fail before upgrade.

## Testing

Smoke tests, not full TDD. Mock service dependencies — the DI seams are designed for it. See `test/unit/` (per-layer) and `test/integration/` (workflow + mocked orchestrator).
