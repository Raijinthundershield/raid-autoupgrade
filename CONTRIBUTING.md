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

## Capturing & labelling progress-bar samples (debug)

The progress-bar state detector is validated against real labelled ROI crops in
`test/fixtures/images/progress_bar_state/`. The debug-only **Label tab** is how
you grow that corpus from a live run — capture frames, correct the detector's
guesses, and export them as ready-to-commit fixtures. This matters most for
reproducing state misclassification at non-native window sizes, which synthetic
downscaling can't recreate.

Launch with `--debug` (or `-d`):

```bash
uv run raid-autoupgrade gui --debug
```

This does two things: Count/Spend runs write per-frame captures (full
screenshot + progress-bar ROI + the detector's recorded guess) under
`%PROGRAMDATA%\RaidAutoupgrade\debug\`, and the GUI shows the extra **Label**
tab. Without `--debug` neither is present.

The labelling pass is deliberate and post-hoc:

1. **Capture.** Run Count (and/or Spend) with `--debug` at the window size you
   want samples for, then stop.
2. **Review.** Open the Label tab and pick a session (it defaults to the most
   recent). Each frame shows its ROI, full screenshot, and a label dropdown
   pre-filled with the detector's guess (shown beside it as `guess: …`).
3. **Correct.** Change a dropdown to the true state (`fail` / `progress` /
   `standby` / `connection_error` / `unknown`, or `skip` for a genuinely
   ambiguous frame). Corrections persist to the session immediately, so they
   survive reopening it; the original detector guess is kept.
4. **Export.** Tick the **Export** checkbox on each frame to keep (off by
   default), then click **Export**. Each ticked frame's ROI is written to the
   session's `exports/` folder as `{label}_{w}x{h}_{n}.png` plus a
   `SampleAnnotation` JSON sidecar (label, window size, mean BGR/HSV, source).
   Re-exporting a frame overrides its previous file rather than duplicating it.
   Use **Copy path** to grab the `exports/` folder location.
5. **Commit.** Copy the `{png, json}` pairs from `exports/` into
   `test/fixtures/images/progress_bar_state/`. The detector test globs the
   sidecars, so the new samples are asserted automatically (a `skip` sample is
   kept for inspection but not asserted).

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
