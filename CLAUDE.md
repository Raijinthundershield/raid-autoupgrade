# CLAUDE.md

Guidance for Claude Code working in this repo.

## Project

**AutoRaid** — Windows-only automation tool for Raid: Shadow Legends. Uses OpenCV + pyautogui to count upgrade fails offline (airplane-mode trick), then spend attempts online to guarantee an upgrade.

Background on the trick: [docs/airplane-mode-trick.md](docs/airplane-mode-trick.md).

Use .scratch for temporary docs.

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

See [docs/architecture.md](docs/architecture.md) for the layer breakdown (React → FastAPI → jobs → workflows), the composition-root wiring, progress bar detection thresholds, and the upgrade flow.

## Constraints

- **Windows only**: WMI for adapter control, Win32 for window management.
- **Admin rights**: Required for WMI. Window activation uses ALT+SetForegroundWindow first (bypasses UIPI when Raid runs admin via RSLHelper), falls back to minimize/restore.
- **Window size**: Constant during a session — regions are cached per size. Resizing invalidates cache.
- **First-attempt success**: Not handled; tool assumes at least one fail before upgrade.

## Engineering Principles

Load [docs/engineering-principles.md](docs/engineering-principles.md) when making structural decisions: adding a module, splitting a class, wiring a dependency, or deciding where logic belongs.

## Testing

Load [docs/testing.md](docs/testing.md) when writing or reviewing tests.
Load [docs/testing_practical.md](docs/testing_practical.md) when writing test doubles or deciding where to inject them.

## Agent skills

### Issue tracker

Issues live in the repo's GitHub Issues, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary — `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
