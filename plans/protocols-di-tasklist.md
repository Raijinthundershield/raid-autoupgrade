# Protocol-Based Dependency Injection - Implementation Tasklist

> **Using This Tasklist**
> - Each task is designed to take 15-30 minutes
> - Complete all tasks in a phase before moving to the next
> - Code must be runnable after each phase
> - Refer to `protocols-di-plan.md` for architectural context

---

## Phase 0: Branch Setup

**Goal:** Create feature branch for isolated development

**Tasks:**
- [x] [P0.1] Create feature branch `feat-protocols-di`
  ```bash
  git checkout -b feat-protocols-di
  ```

---

## Phase 1: Protocol Definitions

**Goal:** Create protocol definitions for all 7 infrastructure services

**Deliverable:** Complete `protocols.py` file with all protocol interfaces defined

**Tasks:**
- [x] [P1.1] Create `src/autoraid/protocols.py` with module docstring and imports
  - Import `Protocol`, `runtime_checkable` from `typing`
  - Import `Path` from `pathlib`
  - Import `numpy as np`
  - Import `ProgressBarState` from `autoraid.detection.progress_bar_detector`
  - Import `NetworkAdapter`, `NetworkState` from `autoraid.services.network`

- [x] [P1.2] Define `ProgressBarDetectorProtocol` with single method
  - Add `@runtime_checkable` decorator
  - Define `detect_state(progress_bar_image: np.ndarray) -> ProgressBarState`
  - Add docstring: "Protocol for progress bar state detection."

- [x] [P1.3] Define `WindowInteractionProtocol` with 4 methods
  - Add `@runtime_checkable` decorator
  - Define `window_exists(window_title: str) -> bool`
  - Define `get_window_size(window_title: str) -> tuple[int, int]`
  - Define `click_region(window_title: str, region: tuple[int, int, int, int]) -> None`
  - Define `activate_window(window_title: str) -> None`
  - Add docstring: "Protocol for window operations."

- [x] [P1.4] Define `NetworkManagerProtocol` with 4 methods
  - Add `@runtime_checkable` decorator
  - Define `check_network_access(timeout: float = 5.0) -> NetworkState`
  - Define `toggle_adapters(adapter_ids: list[str], target_state: NetworkState, wait: bool = False, timeout: float | None = None) -> bool`
  - Define `get_adapters() -> list[NetworkAdapter]`
  - Define `wait_for_network_state(target_state: NetworkState, timeout: float) -> None`
  - Add docstring: "Protocol for network adapter management."

- [x] [P1.5] Define `CacheProtocol` with 4 methods
  - Add `@runtime_checkable` decorator
  - Define `get_regions(window_size: tuple[int, int]) -> dict | None`
  - Define `set_regions(window_size: tuple[int, int], regions: dict) -> None`
  - Define `get_screenshot(window_size: tuple[int, int]) -> np.ndarray | None`
  - Define `set_screenshot(window_size: tuple[int, int], screenshot: np.ndarray) -> None`
  - Add docstring: "Protocol for region/screenshot caching operations."

- [x] [P1.6] Define `ScreenshotProtocol` with 2 methods
  - Add `@runtime_checkable` decorator
  - Define `take_screenshot(window_title: str) -> np.ndarray`
  - Define `extract_roi(screenshot: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray`
  - Add docstring: "Protocol for screenshot capture and ROI extraction."

- [x] [P1.7] Define `LocateRegionProtocol` with 1 method
  - Add `@runtime_checkable` decorator
  - Define `get_regions(screenshot: np.ndarray, manual: bool = False, override_cache: bool = False) -> dict[str, tuple[int, int, int, int]]`
  - Add docstring: "Protocol for UI region detection."

- [x] [P1.8] Define `AppDataProtocol` with properties and methods
  - Add `@runtime_checkable` decorator
  - Define property `cache_dir: Path`
  - Define property `debug_enabled: bool`
  - Define property method `debug_dir() -> Path | None` with `@property` decorator
  - Define method `ensure_directories() -> None`
  - Define method `get_log_file_path() -> Path | None`
  - Add docstring: "Protocol for application directory configuration."

- [x] [P1.9] Verify protocols.py imports successfully
  ```bash
  uv run python -c "from autoraid.protocols import *; print('All protocols imported successfully')"
  ```

**Phase 1 Checkpoint:** Protocol definitions complete and importable

---

## Phase 2: Service Layer Updates

**Goal:** Update services to use protocol type hints for internal dependencies

**Deliverable:** Services with protocol-based internal dependencies verified

**Tasks:**
- [x] [P2.1] Update `services/screenshot_service.py` constructor
  - Change parameter type from `WindowInteractionService` to `WindowInteractionProtocol`
  - Add import: `from autoraid.protocols import WindowInteractionProtocol`
  - Verify type hint: `def __init__(self, window_service: WindowInteractionProtocol):`

- [x] [P2.2] Update `services/locate_region_service.py` constructor
  - Change `cache_service` parameter from `CacheService` to `CacheProtocol`
  - Change `screenshot_service` parameter from `ScreenshotService` to `ScreenshotProtocol`
  - Add import: `from autoraid.protocols import CacheProtocol, ScreenshotProtocol`
  - Verify type hints in `__init__` method

- [x] [P2.3] Verify concrete services satisfy protocols (optional runtime check)
  - Run Python script to verify isinstance checks:
  ```python
  from autoraid.container import Container
  from autoraid.protocols import *

  container = Container()
  container.config.cache_dir.from_value("./test_cache")
  container.config.debug.from_value(False)

  # Verify protocol compliance
  assert isinstance(container.progress_bar_detector(), ProgressBarDetectorProtocol)
  assert isinstance(container.window_interaction_service(), WindowInteractionProtocol)
  assert isinstance(container.network_manager(), NetworkManagerProtocol)
  assert isinstance(container.cache_service(), CacheProtocol)
  assert isinstance(container.screenshot_service(), ScreenshotProtocol)
  print("All services satisfy their protocols!")
  ```

- [x] [P2.4] Run unit tests for services to verify no regressions
  ```bash
  uv run pytest test/unit/services/ -v
  ```

**Phase 2 Checkpoint:** Services use protocol type hints, all service tests pass

---

## Phase 3: Orchestration Layer Updates

**Goal:** Update orchestration components to accept protocol parameters

**Deliverable:** Orchestration layer using protocol type hints with tests passing

**Tasks:**
- [x] [P3.1] Update `orchestration/progress_bar_monitor.py` constructor
  - Change parameter from `ProgressBarStateDetector` to `ProgressBarDetectorProtocol`
  - Add import: `from autoraid.protocols import ProgressBarDetectorProtocol`
  - Verify type hint: `def __init__(self, detector: ProgressBarDetectorProtocol):`

- [x] [P3.2] Update `orchestration/upgrade_orchestrator.py` constructor (part 1)
  - Add import: `from autoraid.protocols import ScreenshotProtocol, WindowInteractionProtocol, CacheProtocol`
  - Change `screenshot_service` parameter to `ScreenshotProtocol`
  - Change `window_interaction_service` parameter to `WindowInteractionProtocol`
  - Change `cache_service` parameter to `CacheProtocol`

- [x] [P3.3] Update `orchestration/upgrade_orchestrator.py` constructor (part 2)
  - Add to import: `NetworkManagerProtocol, ProgressBarDetectorProtocol`
  - Change `network_manager` parameter to `NetworkManagerProtocol`
  - Change `detector` parameter to `ProgressBarDetectorProtocol`

- [x] [P3.4] Run unit tests for orchestration layer
  ```bash
  uv run pytest test/unit/orchestration/test_progress_bar_monitor.py -v
  uv run pytest test/unit/orchestration/test_upgrade_orchestrator.py -v
  ```

**Phase 3 Checkpoint:** Orchestration layer uses protocol type hints, orchestration tests pass

---

## Phase 4: Workflow Layer Updates

**Goal:** Update all workflow constructors to use protocol parameters

**Deliverable:** Workflows with protocol-based constructors, workflow tests passing

**Tasks:**
- [x] [P4.1] Update `workflows/count_workflow.py` constructor
  - Add import: `from autoraid.protocols import CacheProtocol, WindowInteractionProtocol, NetworkManagerProtocol, ScreenshotProtocol, ProgressBarDetectorProtocol`
  - Change `cache_service` parameter to `CacheProtocol`
  - Change `window_interaction_service` parameter to `WindowInteractionProtocol`
  - Change `network_manager` parameter to `NetworkManagerProtocol`
  - Change `screenshot_service` parameter to `ScreenshotProtocol`
  - Change `detector` parameter to `ProgressBarDetectorProtocol`

- [x] [P4.2] Update `workflows/spend_workflow.py` constructor
  - Add same import as P4.1
  - Change all 5 service parameters to protocol types (same as P4.1)

- [x] [P4.3] Update `workflows/debug_monitor_workflow.py` constructor
  - Add same import as P4.1
  - Change all 5 service parameters to protocol types (same as P4.1)

- [x] [P4.4] Run unit tests for workflows
  ```bash
  uv run pytest test/unit/workflows/ -v
  ```

**Phase 4 Checkpoint:** Workflows use protocol type hints, workflow unit tests pass

---

## Phase 5: Entry Point Updates

**Goal:** Update CLI and GUI entry points to use protocol type annotations

**Deliverable:** All entry points using protocol type hints, application runs successfully

**Tasks:**
- [x] [P5.1] Update `cli/upgrade_cli.py` - count command
  - Add import: `from autoraid.protocols import CacheProtocol, WindowInteractionProtocol, NetworkManagerProtocol, ScreenshotProtocol, ProgressBarDetectorProtocol`
  - Update `count()` function signature (line ~57-63)
  - Change `cache_service: CacheService` to `cache_service: CacheProtocol`
  - Change `window_interaction_service: WindowInteractionService` to `WindowInteractionProtocol`
  - Change `network_manager: NetworkManager` to `NetworkManagerProtocol`
  - Change `screenshot_service: ScreenshotService` to `ScreenshotProtocol`
  - Change `detector: ProgressBarStateDetector` to `ProgressBarDetectorProtocol`

- [x] [P5.2] Update `cli/upgrade_cli.py` - spend command
  - Update `spend()` function signature (line ~136-142)
  - Change all 5 service parameters to protocol types (same as P5.1)

- [x] [P5.3] Update `cli/upgrade_cli.py` - region commands
  - Update `region_show()` function signature (line ~206-210)
  - Change parameters to `CacheProtocol`, `WindowInteractionProtocol`, `ScreenshotProtocol`
  - Update `region_select()` function signature (line ~300-306)
  - Change parameters to `CacheProtocol`, `WindowInteractionProtocol`, `ScreenshotProtocol`

- [x] [P5.4] Update `cli/debug_cli.py` - monitor command
  - Add same import as P5.1
  - Update `monitor()` function signature (line ~67-73)
  - Change all 5 service parameters to protocol types

- [x] [P5.5] Update `cli/network_cli.py` - network commands
  - Add import: `from autoraid.protocols import NetworkManagerProtocol`
  - Update `list_adapters()` function (line ~101) - change to `NetworkManagerProtocol`
  - Update `disable_adapters()` function (line ~118) - change to `NetworkManagerProtocol`
  - Update `enable_adapters()` function (line ~165) - change to `NetworkManagerProtocol`

- [x] [P5.6] Update `gui/app.py` - header component
  - Add import: `from autoraid.protocols import WindowInteractionProtocol, NetworkManagerProtocol`
  - Update `create_header()` function signature (line ~20-24)
  - Change parameters to protocol types

- [x] [P5.7] Update `gui/components/upgrade_panel.py`
  - Add import: `from autoraid.protocols import CacheProtocol, WindowInteractionProtocol, NetworkManagerProtocol, ScreenshotProtocol, ProgressBarDetectorProtocol, AppDataProtocol`
  - Update `create_upgrade_panel()` function signature (line ~133-139)
  - Change all service parameters to protocol types
  - Change `app_data: AppData | None` to `app_data: AppDataProtocol | None`

- [x] [P5.8] Update `gui/components/region_panel.py`
  - Add import: `from autoraid.protocols import LocateRegionProtocol, ScreenshotProtocol, CacheProtocol`
  - Update `create_region_panel()` function signature (line ~26-30)
  - Change parameters to protocol types

- [x] [P5.9] Update `gui/components/network_panel.py`
  - Add import: `from autoraid.protocols import NetworkManagerProtocol`
  - Update `create_network_panel()` function signature (line ~13)
  - Change parameter to `NetworkManagerProtocol`

- [x] [P5.10] Test CLI commands manually
  ```bash
  uv run autoraid --help
  uv run autoraid count --help
  uv run autoraid spend --help
  uv run autoraid network list
  ```

- [x] [P5.11] Test GUI launches without errors
  ```bash
  uv run autoraid gui
  # Verify GUI opens and displays panels correctly, then close
  ```

**Phase 5 Checkpoint:** All entry points use protocol type hints, CLI/GUI run successfully

---

## Phase 6: Test Updates

**Goal:** Update test mocks to use protocols instead of concrete classes

**Deliverable:** All tests pass with protocol-based mocks

**Tasks:**
- [x] [P6.1] Update `test/unit/orchestration/test_progress_bar_monitor.py`
  - Add import: `from autoraid.protocols import ProgressBarDetectorProtocol`
  - Replace `Mock(spec=ProgressBarStateDetector)` with `Mock(spec=ProgressBarDetectorProtocol)`
  - Verify all tests still pass

- [x] [P6.2] Update `test/unit/orchestration/test_upgrade_orchestrator.py`
  - Add import: `from autoraid.protocols import ScreenshotProtocol, WindowInteractionProtocol, CacheProtocol, NetworkManagerProtocol, ProgressBarDetectorProtocol`
  - Replace all `Mock(spec=ConcreteClass)` with `Mock(spec=Protocol)`
  - Update mock specs for all 5 services
  - Verify all tests still pass

- [x] [P6.3] Update `test/unit/workflows/test_count_workflow.py`
  - Add import for all 5 protocols
  - Replace all mock specs with protocol specs
  - Verify all tests still pass

- [x] [P6.4] Update `test/unit/workflows/test_spend_workflow.py`
  - Add import for all 5 protocols
  - Replace all mock specs with protocol specs
  - Verify all tests still pass

- [x] [P6.5] Update `test/unit/workflows/test_debug_monitor_workflow.py`
  - Add import for all 5 protocols
  - Replace all mock specs with protocol specs
  - Verify all tests still pass

- [x] [P6.6] Update `test/integration/test_count_workflow_integration.py`
  - Add import for relevant protocols
  - Replace mock specs with protocol specs where applicable
  - Verify integration test still passes

- [x] [P6.7] Update `test/integration/test_spend_workflow_integration.py`
  - Add import for relevant protocols
  - Replace mock specs with protocol specs where applicable
  - Verify integration test still passes

- [x] [P6.8] Run full test suite
  ```bash
  uv run pytest -v
  ```

**Phase 6 Checkpoint:** All tests pass with protocol-based mocks

---

## Phase 7: Verification & Documentation

**Goal:** Verify complete implementation and update documentation

**Deliverable:** Fully verified protocol-based DI system with updated docs

**Tasks:**
- [x] [P7.1] Run full test suite with coverage
  ```bash
  uv run pytest --cov=src/autoraid --cov-report=term-missing
  ```

- [x] [P7.2] Verify no import errors across all modules
  ```bash
  uv run python -c "import autoraid.cli.cli; import autoraid.gui.app; import autoraid.workflows.count_workflow; print('All imports successful')"
  ```

- [x] [P7.3] Run linting checks
  ```bash
  uv run ruff check src/autoraid/protocols.py
  uv run ruff format --check src/autoraid/protocols.py
  ```

- [x] [P7.4] Optional: Run mypy type checker (if configured)
  ```bash
  uv run mypy src/autoraid/protocols.py --strict
  ```

- [x] [P7.5] Update `CLAUDE.md` - Architecture section
  - Add subsection "Protocol-Based Dependency Injection"
  - Document that services have corresponding protocol interfaces
  - Explain protocol location (`src/autoraid/protocols.py`)
  - Add example of protocol usage in type annotations
  - Note that protocols are `@runtime_checkable`

- [x] [P7.6] Update `CLAUDE.md` - Service Responsibilities table
  - Add "Protocol" column showing corresponding protocol for each service
  - Example: `CacheService` → `CacheProtocol`

- [x] [P7.7] Update `CLAUDE.md` - Testing section
  - Update mock testing pattern examples to use protocols
  - Show before/after comparison: `Mock(spec=ConcreteClass)` vs `Mock(spec=Protocol)`

- [x] [P7.8] Manual smoke test: Run count workflow end-to-end (if Raid available)
  ```bash
  uv run autoraid count --help
  # If Raid is running, test: uv run autoraid count
  ```

- [x] [P7.9] Manual smoke test: Launch GUI and verify all panels load
  ```bash
  uv run autoraid gui
  # Verify: Upgrade panel, Region panel, Network panel all display correctly
  ```

- [x] [P7.10] Review git diff to ensure no unintended changes
  ```bash
  git diff main --stat
  git diff main src/autoraid/protocols.py  # Review new file
  ```

**Phase 7 Checkpoint:** Protocol-based DI system fully verified and documented

---

## Completion Checklist

Before merging `feat-protocols-di` branch:

- [ ] All 7 protocols defined in `src/autoraid/protocols.py`
- [ ] All services use protocol type hints for dependencies
- [ ] All orchestration components use protocol parameters
- [ ] All workflows use protocol parameters
- [ ] All CLI commands use protocol type annotations
- [ ] All GUI components use protocol type annotations
- [ ] All tests use protocol-based mocks
- [ ] Full test suite passes (`uv run pytest`)
- [ ] Linting passes (`uv run ruff check .`)
- [ ] CLI runs without errors (`uv run autoraid --help`)
- [ ] GUI launches successfully (`uv run autoraid gui`)
- [ ] `CLAUDE.md` updated with protocol documentation
- [ ] Zero runtime behavior changes verified

---

## Notes

- **Estimated total time:** 4-6 hours (assuming 15-30 min per task)
- **Safe to pause:** After any completed phase (code remains runnable)
- **Rollback point:** Each phase completion is a stable checkpoint
- **Testing frequency:** After each phase to catch issues early
