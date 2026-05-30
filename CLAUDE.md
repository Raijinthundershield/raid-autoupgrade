# CLAUDE.md

Guidance for Claude Code working in this repo.

## Project

**Raid Autoupgrade** — Windows-only automation tool for Raid: Shadow Legends. Uses OpenCV + pyautogui to count upgrade fails offline (airplane-mode trick), then spend attempts online to guarantee an upgrade.

Background on the trick: [docs/airplane-mode-trick.md](docs/airplane-mode-trick.md).

Use .scratch for temporary docs.

## Commands

Package manager is `uv`. All commands run from the `autoraid/` directory.

```bash
uv sync                       # install / refresh venv
uv run raid-autoupgrade --help        # CLI
uv run raid-autoupgrade gui           # native desktop GUI
uv run pytest                 # tests
uv run pytest test/unit/      # unit only
uv run ruff check --fix .     # lint
uv run ruff format .          # format
uv run pre-commit run --all-files
```

### Building the one-file Windows .exe locally

Mirrors the `release.yml` CI steps. Run from the `autoraid/` directory:

```powershell
cd frontend; npm run build    # tsc -b && vite build → frontend/dist (bundled into the exe)
cd ..
uv sync                       # installs deps incl. pyinstaller (dev group)
uv run pyinstaller raid-autoupgrade.spec --noconfirm   # → dist/RaidAutoupgrade.exe
```

All build config (one-file, windowed, UAC-admin manifest, `frontend/dist` bundling,
version info read from `pyproject.toml`, `upx=False` for AV) lives in
`raid-autoupgrade.spec` — not in CLI flags. `--noconfirm` just overwrites a prior
`dist/`/`build/`; CI omits it (fresh runner). CI additionally renames the artifact
to `RaidAutoupgrade-v{version}-win64.exe` and guards the tag against the pyproject
version. The frontend build is mandatory first — a stale/missing `frontend/dist`
bundles stale UI.

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
