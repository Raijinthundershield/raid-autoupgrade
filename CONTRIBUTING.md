# Contributing — running Raid Autoupgrade from source

This guide covers building and running the app from a source checkout.

## Prerequisites

- **Windows 10/11** — the tool uses WMI and Win32 APIs and is Windows-only.
- **Administrator rights** — required for WMI network-adapter control; the app
  prompts for elevation on launch.
- [**uv**](https://docs.astral.sh/uv/) — manages the Python side.
- [**Node.js**](https://nodejs.org/) 20+ — builds the React frontend.

## Setup

The desktop window renders the **built** React frontend served by the in-process
FastAPI backend, so the frontend must be built before the first launch (and after
any frontend change — unless you use the dev server, below).

```bash
# 1. Install Python dependencies
uv sync

# 2. Build the frontend (produces frontend/dist/, which FastAPI serves)
cd frontend
npm install
npm run build
cd ..
```

## Running

With the frontend built (above), launch the GUI — the FastAPI backend serves the
built frontend from `frontend/dist/`:

```bash
uv run raid-autoupgrade gui
```

On launch the app checks for admin rights and, if missing, prompts a UAC dialog
to relaunch elevated.

### Frontend hot reload

While iterating on the UI, skip the rebuild-per-change. Run the Vite dev server
in one terminal and point the GUI at it in another:

```bash
cd frontend && npm run dev          # terminal 1: Vite dev server
uv run raid-autoupgrade gui --dev   # terminal 2: window points at the dev server
```

The window loads from the dev server, which proxies `/api` and `/ws` to the
backend, so frontend edits hot-reload without a rebuild.

## Quality checks

```bash
uv run pytest                 # tests (uv run pytest test/unit/ for unit only)
uv run ruff check --fix .     # lint
uv run ruff format .          # format
uv run pre-commit run --all-files
```

## Building the Windows exe

See [CLAUDE.md](CLAUDE.md) for the local one-file `.exe` build steps; release
builds are produced by `.github/workflows/release.yml` on every `v*` tag.
