# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AutoRaid** is a Windows-only automation tool for Raid: Shadow Legends that helps with the "airplane mode trick" for gear upgrades. The tool uses computer vision (OpenCV) and GUI automation (pyautogui) to detect upgrade states and automate the upgrade process.

Key feature: The tool can count the number of upgrade fails needed before a successful upgrade (with internet off), then automatically spend those attempts (with internet on) to guarantee an upgrade at the right time.

## Development Commands

This project uses `uv` for package management and virtual environment management.

### Environment Setup
```bash
cd autoraid
uv sync  # Install dependencies and create virtual environment
```

### Running the Tool
```bash
cd autoraid
uv run autoraid --help
```

### Testing
```bash
cd autoraid
uv run pytest
```

### Linting and Formatting
```bash
cd autoraid
uv run ruff check .        # Lint code
uv run ruff check --fix .  # Fix linting issues
uv run ruff format .       # Format code
```

### Pre-commit Hooks
```bash
cd autoraid
uv run pre-commit install  # Install pre-commit hooks
uv run pre-commit run --all-files  # Run hooks manually
```

## Architecture

### Core Components

1. **CLI Layer** ([src/autoraid/cli/](autoraid/src/autoraid/cli/))
   - [cli.py](autoraid/src/autoraid/cli/cli.py): Main entry point with `autoraid` command group
   - [upgrade_cli.py](autoraid/src/autoraid/cli/upgrade_cli.py): Commands for counting/spending upgrade attempts
   - [network_cli.py](autoraid/src/autoraid/cli/network_cli.py): Commands for network adapter management
   - Uses Click for CLI framework with context passing for cache and debug settings

2. **Autoupgrade Module** ([src/autoraid/autoupgrade/](autoraid/src/autoraid/autoupgrade/))
   - [autoupgrade.py](autoraid/src/autoraid/autoupgrade/autoupgrade.py): Core upgrade counting logic
   - [progress_bar.py](autoraid/src/autoraid/autoupgrade/progress_bar.py): Computer vision for progress bar state detection (fail/standby/progress/connection_error)
   - [locate_upgrade_region.py](autoraid/src/autoraid/autoupgrade/locate_upgrade_region.py): Automatic detection of UI regions
   - [artifact_icon.py](autoraid/src/autoraid/autoupgrade/artifact_icon.py): Artifact icon handling
   - State machine tracks upgrade bar color changes (yellow → red → black) to count fails

3. **Interaction Layer** ([src/autoraid/interaction.py](autoraid/src/autoraid/interaction.py))
   - Window management using pygetwindow
   - Screenshot capture with pyautogui
   - Region selection with OpenCV GUI
   - Automated clicking on UI regions

4. **Network Management** ([src/autoraid/network.py](autoraid/src/autoraid/network.py))
   - Windows WMI-based network adapter control
   - Enables/disables network adapters for the airplane mode trick
   - Network connectivity checking

5. **Caching System**
   - Uses diskcache for persistent storage
   - Caches UI regions per window size (key format: `regions_{width}_{height}`)
   - Caches screenshots per window size
   - Cache directory: `cache-raid-autoupgrade/` in working directory

### Key Design Patterns

- **Region-based Detection**: All UI interactions use cached regions (left, top, width, height) relative to the Raid window
- **State Machine**: Progress bar monitoring uses a deque to track last N states and detect upgrades/errors
- **Window Size Dependency**: Regions are cached per window size, requiring re-selection if window is resized
- **Debug Mode**: Global `--debug` flag saves screenshots and metadata to `cache-raid-autoupgrade/debug/`

### Progress Bar State Detection

The core algorithm in [progress_bar.py](autoraid/src/autoraid/autoupgrade/progress_bar.py) uses average BGR color values to determine state:
- **fail**: Red (b<70, g<90, r>130)
- **progress**: Yellow (b<70, abs(r-g)<50)
- **standby**: Black (b<30, g<60, r<70)
- **connection_error**: Blue dominant (b>g, b>r, b>50)

### Upgrade Counting Flow

1. User navigates to upgrade screen in Raid
2. Tool disables network adapters (if specified)
3. Tool locates or prompts for UI regions (upgrade bar, button, artifact icon)
4. User clicks upgrade button programmatically
5. Tool monitors progress bar color changes every 0.25s
6. Counts transitions to "fail" state (red bar)
7. Stops on: max attempts reached, 4 consecutive "standby" states (upgraded), or 4 consecutive "connection_error" states
8. Re-enables network adapters

## Important Constraints

- **Windows Only**: Uses WMI for network adapter control and pywinauto for window management
- **Admin Rights**: Required when Raid is launched via RSLHelper (which runs as admin)
- **Window Size**: Must remain constant during operation; resizing invalidates cached regions
- **Foreground Window**: Raid window is activated before each screenshot/click
- **First-Attempt Success**: Tool does not handle upgrades that succeed on first try

## Project Structure

```
autoraid/
├── src/autoraid/
│   ├── cli/              # CLI commands
│   ├── autoupgrade/      # Core upgrade logic
│   ├── interaction.py    # Window/screenshot/click utilities
│   ├── network.py        # Network adapter management
│   ├── locate.py         # Region location utilities
│   ├── visualization.py  # Image display/annotation
│   ├── average_color.py  # Color analysis utilities
│   └── utils.py          # General utilities
├── test/                 # Tests
├── scripts/              # Helper scripts
├── docs/                 # Documentation
├── pyproject.toml        # Project config & dependencies
└── .pre-commit-config.yaml
```

## Dependencies

Key libraries:
- **opencv-python**: Computer vision for progress bar detection
- **pyautogui**: GUI automation (clicking, screenshots)
- **pygetwindow**: Window management
- **click**: CLI framework
- **diskcache**: Persistent caching
- **wmi**: Windows network adapter control
- **rich**: Terminal UI (tables, colors)
- **loguru**: Logging
- **pytesseract**: OCR (potential future use)

## Testing

Tests are in [test/](autoraid/test/):
- [test_progressbar_state.py](autoraid/test/test_progressbar_state.py): Progress bar color detection tests
- [test_locate.py](autoraid/test/test_locate.py): Region location tests

Test images and cache data are stored in `test/images/` and `test/cache-raid-autoupgrade/`.
