# Implementation Plan: AutoRaid GUI Desktop Application

**Branch**: `003-gui-desktop-app` | **Date**: 2025-10-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-gui-desktop-app/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a native desktop GUI for AutoRaid using NiceGUI framework. The GUI provides a single-page scrollable interface that replicates all CLI functionality through visual components while maintaining zero business logic duplication. Users can manage network adapters, select UI regions via OpenCV, and execute Count/Spend upgrade workflows with real-time feedback through log streaming and progress displays.

**Technical Approach**: Thin presentation layer pattern - GUI components inject existing services (UpgradeOrchestrator, CacheService, LocateRegionService) via dependency injection container. Async workflows run in threads to keep UI responsive. OpenCV windows remain external (not embedded). State persists across restarts using NiceGUI storage.

## Technical Context

**Language/Version**: Python 3.11+ (existing project constraint)
**Primary Dependencies**:
- NiceGUI[native] >=2.10.0 (native desktop GUI framework with FastAPI + WebSockets)
- dependency-injector (existing DI framework, already in use)
- pywebview (auto-installed with NiceGUI native extras for desktop window)
- All existing dependencies (opencv-python, pyautogui, loguru, click, diskcache, wmi)

**Storage**:
- NiceGUI app.storage.user for persistent GUI state (selected adapters, debug mode, last count result)
- Existing diskcache for region caching (no changes)

**Testing**:
- Manual testing per phase with acceptance criteria checklists (Principle III: Pragmatic Testing)
- Smoke tests for component instantiation
- Existing pytest suite for service layer (no changes)

**Target Platform**: Windows desktop (native application window, not browser)

**Project Type**: Single project with new GUI module alongside existing CLI

**Performance Goals**:
- Real-time log streaming with <500ms latency
- Count/spent display updates with <500ms latency
- GUI launch in <5 seconds
- Responsive UI during blocking workflows (async threading)

**Constraints**:
- Windows-only (existing project constraint)
- Admin rights required when Raid launched via RSLHelper (existing constraint)
- Zero business logic duplication (must use existing orchestrator and services)
- Native desktop window (not browser-based)

**Scale/Scope**:
- Single user (local desktop app)
- 3 main UI sections (Upgrade Workflows, Region Management, Network Adapters)
- 4 new Python modules (~600-800 LOC total for GUI layer)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle I: Simplicity Over Complexity

**Status**: PASS

- GUI is thin presentation layer with zero business logic duplication
- No new abstractions beyond NiceGUI's built-in components
- Straightforward async pattern: `asyncio.to_thread()` for blocking operations
- No deep inheritance (components are functions/modules, not classes)
- Explicit state management via `app.storage.user` (no magic)

### ✅ Principle II: Readability First

**Status**: PASS

- Component names match domain concepts: `UpgradePanel`, `RegionPanel`, `NetworkPanel`
- Module structure reflects GUI sections (components/, utils.py, app.py)
- Function names describe actions: `start_count()`, `show_regions()`, `refresh_adapters()`
- Magic numbers avoided: `POLL_INTERVAL = 5.0`, `LOG_RETENTION_LIMIT = 1000`

### ✅ Principle III: Pragmatic Testing

**Status**: PASS

- Manual testing per phase with documented acceptance criteria
- Smoke tests for component instantiation and key methods
- No GUI automation (per constitution: "GUI automation and simple utilities can rely on manual testing")
- Existing service layer tests remain unchanged (no duplication)

### ✅ Principle IV: Debug-Friendly Architecture

**Status**: PASS

- Preserves existing `--debug` flag via checkbox toggle
- Same debug artifacts as CLI (screenshots, metadata, ROIs saved to same directory)
- Real-time log streaming to UI with color-coded levels
- Error toasts show exception messages for rapid diagnosis
- Visual status indicators (Raid window, network) update every 5 seconds

### ✅ Principle V: Incremental Improvement Over Perfection

**Status**: PASS

- Minimum feature set: replicates CLI functionality, no extras
- Future enhancements explicitly deferred (workflow history, artifact viewer, hotkeys)
- 6 implementation phases, each deliverable independently
- YAGNI applied: no imagined features, no speculative complexity

### Gate Result: ✅ ALL GATES PASSED

No violations detected. No complexity tracking required.

## Project Structure

### Documentation (this feature)

```
specs/003-gui-desktop-app/
├── spec.md              # Feature specification (completed by /speckit.specify)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (technology validation)
├── data-model.md        # Phase 1 output (state and entities)
├── quickstart.md        # Phase 1 output (GUI developer guide)
├── contracts/           # Phase 1 output (component interfaces)
│   ├── upgrade_panel.md
│   ├── region_panel.md
│   └── network_panel.md
├── single-page-layout.svg  # UI layout diagram
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```
src/autoraid/
├── gui/                          # NEW: GUI layer
│   ├── __init__.py
│   ├── app.py                    # Main NiceGUI application & single-page layout
│   ├── components/               # UI sections
│   │   ├── __init__.py
│   │   ├── upgrade_panel.py      # Count + Spend workflows + Live Logs
│   │   ├── region_panel.py       # Region show/select (OpenCV integration)
│   │   └── network_panel.py      # Network adapter table & management
│   └── utils.py                  # GUI helpers (async wrappers, log capture)
├── cli/                          # EXISTING: CLI layer
│   ├── cli.py                    # MODIFY: Add 'gui' command
│   ├── upgrade_cli.py            # No changes
│   └── network_cli.py            # No changes
├── services/                     # EXISTING: No changes
│   ├── upgrade_orchestrator.py
│   ├── cache_service.py
│   ├── screenshot_service.py
│   ├── locate_region_service.py
│   └── window_interaction_service.py
├── core/                         # EXISTING: No changes
│   ├── state_machine.py
│   ├── progress_bar.py
│   ├── locate_region.py
│   └── artifact_icon.py
├── platform/                     # EXISTING: No changes
│   └── network.py
├── utils/                        # EXISTING: No changes
├── container.py                  # EXISTING: MODIFY wiring to include GUI modules
└── exceptions.py                 # EXISTING: No changes

test/
├── unit/
│   └── gui/                      # NEW: Smoke tests
│       ├── test_network_panel.py
│       ├── test_region_panel.py
│       └── test_upgrade_panel.py
├── integration/                  # EXISTING: No changes
└── fixtures/                     # EXISTING: No changes
```

**Structure Decision**: GUI lives as peer to CLI in `src/autoraid/gui/`. Both are thin presentation layers over shared services accessed via dependency injection. No code duplication - GUI calls same `UpgradeOrchestrator` and service methods as CLI.

## Complexity Tracking

*Not applicable - no Constitution violations detected.*

All principles pass without justification. GUI layer follows existing patterns:
- Thin presentation layer (same as CLI)
- Dependency injection for service access (same as CLI)
- No new abstractions or complexity
