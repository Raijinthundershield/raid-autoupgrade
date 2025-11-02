# Services Refactoring - Implementation Tasklist

> **Using This Tasklist**
> - Each task is designed to take 15-30 minutes
> - Complete all tasks in a phase before moving to the next
> - Code must be runnable after each phase
> - Refer to `refactor-services-plan.md` for architectural context

---

## Phase 0: Branch Setup

**Goal**: Create feature branch and establish baseline

**Tasks**:
- [x] [P0.1] Create feature branch `refactor-services`
  ```bash
  git checkout -b refactor-services
  ```
- [x] [P0.2] Run full test suite to establish baseline
  ```bash
  uv run pytest
  ```
- [x] [P0.3] Verify CLI and GUI launch without errors
  ```bash
  uv run autoraid --help
  uv run autoraid gui  # Launch and immediately close
  ```

**Phase 0 Checkpoint**: Feature branch created, baseline tests passing

---

## Phase 1: Create New Folder Structure

**Goal**: Establish new directory structure for infrastructure vs application separation

**Deliverable**: New `/orchestration` and `/detection` folders created with proper `__init__.py` files

**Tasks**:
- [x] [P1.1] Create `src/autoraid/orchestration/` directory
  ```bash
  mkdir src/autoraid/orchestration
  ```
- [x] [P1.2] Create `src/autoraid/orchestration/__init__.py` with empty exports
  ```python
  """Application-layer coordination logic."""
  ```
- [x] [P1.3] Create `src/autoraid/detection/` directory
  ```bash
  mkdir src/autoraid/detection
  ```
- [x] [P1.4] Create `src/autoraid/detection/__init__.py` with empty exports
  ```python
  """Computer vision detection algorithms."""
  ```

**Phase 1 Checkpoint**: New folder structure created, ready for file moves

---

## Phase 2: Move Files to New Locations

**Goal**: Relocate files from `/core` and `/services` to new folders

**Deliverable**: Files moved to correct locations, old directories cleaned up

**Tasks**:
- [x] [P2.1] Move `src/autoraid/core/progress_bar_detector.py` to `src/autoraid/detection/progress_bar_detector.py`
  ```bash
  git mv src/autoraid/core/progress_bar_detector.py src/autoraid/detection/progress_bar_detector.py
  ```
- [x] [P2.2] Move `src/autoraid/core/locate_region.py` to `src/autoraid/detection/locate_region.py`
  ```bash
  git mv src/autoraid/core/locate_region.py src/autoraid/detection/locate_region.py
  ```
- [x] [P2.3] Move `src/autoraid/core/progress_bar_monitor.py` to `src/autoraid/orchestration/progress_bar_monitor.py`
  ```bash
  git mv src/autoraid/core/progress_bar_monitor.py src/autoraid/orchestration/progress_bar_monitor.py
  ```
- [x] [P2.4] Move `src/autoraid/core/stop_conditions.py` to `src/autoraid/orchestration/stop_conditions.py`
  ```bash
  git mv src/autoraid/core/stop_conditions.py src/autoraid/orchestration/stop_conditions.py
  ```
- [x] [P2.5] Move `src/autoraid/core/debug_frame_logger.py` to `src/autoraid/orchestration/debug_frame_logger.py`
  ```bash
  git mv src/autoraid/core/debug_frame_logger.py src/autoraid/orchestration/debug_frame_logger.py
  ```
- [x] [P2.6] Move `src/autoraid/services/upgrade_orchestrator.py` to `src/autoraid/orchestration/upgrade_orchestrator.py`
  ```bash
  git mv src/autoraid/services/upgrade_orchestrator.py src/autoraid/orchestration/upgrade_orchestrator.py
  ```
- [x] [P2.7] Delete `src/autoraid/core/` directory (should be empty except __init__.py)
  ```bash
  rm -rf src/autoraid/core
  ```
- [x] [P2.8] Commit file moves with descriptive message
  ```bash
  git add -A
  git commit -m "refactor: reorganize files into orchestration/ and detection/ folders"
  ```

**Phase 2 Checkpoint**: All files moved to new locations, /core deleted, changes committed

---

## Phase 3: Update Module __init__.py Files

**Goal**: Update public exports in new modules to expose moved components

**Deliverable**: Proper exports in `orchestration/__init__.py` and `detection/__init__.py`

**Tasks**:
- [x] [P3.1] Update `src/autoraid/detection/__init__.py` with exports
  ```python
  """Computer vision detection algorithms."""
  from autoraid.detection.progress_bar_detector import (
      ProgressBarStateDetector,
      ProgressBarState,
  )
  from autoraid.detection.locate_region import (
      locate_regions,
      locate_upgrade_button_region,
      locate_progress_bar_region,
      locate_artifact_icon_region,
  )

  __all__ = [
      "ProgressBarStateDetector",
      "ProgressBarState",
      "locate_regions",
      "locate_upgrade_button_region",
      "locate_progress_bar_region",
      "locate_artifact_icon_region",
  ]
  ```
- [x] [P3.2] Update `src/autoraid/orchestration/__init__.py` with exports
  ```python
  """Application-layer coordination logic."""
  from autoraid.orchestration.upgrade_orchestrator import (
      UpgradeOrchestrator,
      UpgradeResult,
      UpgradeSessionConfig,
  )
  from autoraid.orchestration.progress_bar_monitor import (
      ProgressBarMonitor,
      ProgressBarMonitorState,
  )
  from autoraid.orchestration.stop_conditions import (
      StopCondition,
      MaxAttemptsCondition,
      MaxFramesCondition,
      UpgradedCondition,
      ConnectionErrorCondition,
      StopConditionChain,
  )
  from autoraid.orchestration.debug_frame_logger import (
      DebugFrameLogger,
  )

  __all__ = [
      "UpgradeOrchestrator",
      "UpgradeResult",
      "UpgradeSessionConfig",
      "ProgressBarMonitor",
      "ProgressBarMonitorState",
      "StopCondition",
      "MaxAttemptsCondition",
      "MaxFramesCondition",
      "UpgradedCondition",
      "ConnectionErrorCondition",
      "StopConditionChain",
      "DebugFrameLogger",
  ]
  ```
- [x] [P3.3] Update `src/autoraid/services/__init__.py` to remove upgrade_orchestrator export

**Phase 3 Checkpoint**: Module exports updated, public APIs defined

---

## Phase 4: Update Import Statements - Services Layer

**Goal**: Update all import statements in services layer to use new paths

**Deliverable**: All services importing from correct new locations

**Tasks**:
- [x] [P4.1] Update imports in `src/autoraid/services/locate_region_service.py`
  - Change `from autoraid.core.locate_region import` to `from autoraid.detection.locate_region import`
- [x] [P4.2] Update imports in `src/autoraid/container.py`
  - Change `from autoraid.core.progress_bar_detector import` to `from autoraid.detection.progress_bar_detector import`
  - Change `from autoraid.core.progress_bar_monitor import` to `from autoraid.orchestration.progress_bar_monitor import`
  - Change `from autoraid.services.upgrade_orchestrator import` to `from autoraid.orchestration.upgrade_orchestrator import`
- [x] [P4.3] Run tests to verify service layer still works
  ```bash
  uv run pytest test/unit/services/
  ```

**Phase 4 Checkpoint**: Services layer imports updated, tests passing

---

## Phase 5: Update Import Statements - Workflows Layer

**Goal**: Update all import statements in workflows to use new paths

**Deliverable**: All workflows importing from correct new locations

**Tasks**:
- [x] [P5.1] Update imports in `src/autoraid/workflows/count_workflow.py`
  - Change `from autoraid.services.upgrade_orchestrator import` to `from autoraid.orchestration.upgrade_orchestrator import`
- [x] [P5.2] Update imports in `src/autoraid/workflows/spend_workflow.py`
  - Change `from autoraid.services.upgrade_orchestrator import` to `from autoraid.orchestration.upgrade_orchestrator import`
- [x] [P5.3] Update imports in `src/autoraid/workflows/debug_monitor_workflow.py`
  - Change `from autoraid.services.upgrade_orchestrator import` to `from autoraid.orchestration.upgrade_orchestrator import`
  - Change `from autoraid.core.debug_frame_logger import` to `from autoraid.orchestration.debug_frame_logger import`
- [x] [P5.4] Update `src/autoraid/workflows/__init__.py` if it exports anything

**Phase 5 Checkpoint**: Workflows layer imports updated

---

## Phase 6: Update Import Statements - Utils Layer

**Goal**: Update all import statements in utils to use new paths

**Deliverable**: All utils importing from correct new locations

**Tasks**:
- [x] [P6.1] Update imports in `src/autoraid/utils/interaction.py`
  - Check for any imports from `autoraid.core.locate_region` and change to `autoraid.detection.locate_region`
- [x] [P6.2] Verify no other utils files import from old paths
  ```bash
  grep -r "from autoraid.core" src/autoraid/utils/
  grep -r "from autoraid.services.upgrade_orchestrator" src/autoraid/utils/
  ```

**Phase 6 Checkpoint**: Utils layer imports updated

---

## Phase 7: Update Import Statements - CLI Layer

**Goal**: Update all import statements in CLI to use new paths

**Deliverable**: All CLI commands importing from correct new locations

**Tasks**:
- [x] [P7.1] Update imports in `src/autoraid/cli/upgrade_cli.py`
  - Change `from autoraid.services.upgrade_orchestrator import` to `from autoraid.orchestration.upgrade_orchestrator import` (if present)
- [x] [P7.2] Update imports in `src/autoraid/cli/debug_cli.py`
  - Change `from autoraid.core` imports to `from autoraid.detection` or `from autoraid.orchestration`
- [x] [P7.3] Update imports in `src/autoraid/cli/cli.py` if needed
- [x] [P7.4] Verify CLI still launches
  ```bash
  uv run autoraid --help
  ```

**Phase 7 Checkpoint**: CLI layer imports updated, commands functional

---

## Phase 8: Update Import Statements - GUI Layer

**Goal**: Update all import statements in GUI to use new paths

**Deliverable**: All GUI components importing from correct new locations

**Tasks**:
- [x] [P8.1] Update imports in `src/autoraid/gui/components/upgrade_panel.py`
  - Change any `from autoraid.core` or `from autoraid.services.upgrade_orchestrator` imports
- [x] [P8.2] Update imports in `src/autoraid/gui/components/region_panel.py`
  - Change any `from autoraid.core.locate_region` to `from autoraid.detection.locate_region`
- [x] [P8.3] Update imports in `src/autoraid/gui/app.py` if needed
- [x] [P8.4] Verify GUI still launches
  ```bash
  uv run autoraid gui  # Launch and immediately close
  ```

**Phase 8 Checkpoint**: GUI layer imports updated, application functional

---

## Phase 9: Update Import Statements - Debug Tools

**Goal**: Update all import statements in debug tools to use new paths

**Deliverable**: Debug tools importing from correct new locations

**Tasks**:
- [x] [P9.1] Update imports in `src/autoraid/debug/app.py`
  - Change `from autoraid.core` imports to appropriate new paths
- [x] [P9.2] Update imports in `src/autoraid/debug/progressbar_review_gui.py`
  - Change `from autoraid.core.progress_bar_detector` to `from autoraid.detection.progress_bar_detector`
- [x] [P9.3] Update imports in `src/autoraid/debug/utils.py`
- [x] [P9.4] Update imports in all debug component files (`src/autoraid/debug/components/*.py`)

**Phase 9 Checkpoint**: Debug tools imports updated

---

## Phase 10: Update Import Statements - Test Files

**Goal**: Update all import statements in test files to use new paths

**Deliverable**: All tests importing from correct new locations

**Tasks**:
- [x] [P10.1] Update imports in `test/unit/core/test_progress_bar_detector.py`
  - Change `from autoraid.core.progress_bar_detector` to `from autoraid.detection.progress_bar_detector`
  - Move file to `test/unit/detection/test_progress_bar_detector.py`
- [x] [P10.2] Update imports in `test/unit/core/test_progress_bar_monitor.py`
  - Change `from autoraid.core.progress_bar_monitor` to `from autoraid.orchestration.progress_bar_monitor`
  - Change `from autoraid.core.progress_bar_detector` to `from autoraid.detection.progress_bar_detector`
  - Move file to `test/unit/orchestration/test_progress_bar_monitor.py`
- [x] [P10.3] Update imports in `test/unit/core/test_stop_conditions.py`
  - Change `from autoraid.core.stop_conditions` to `from autoraid.orchestration.stop_conditions`
  - Change `from autoraid.core.progress_bar_monitor` to `from autoraid.orchestration.progress_bar_monitor`
  - Move file to `test/unit/orchestration/test_stop_conditions.py`
- [x] [P10.4] Update imports in `test/unit/core/test_debug_frame_logger.py`
  - Change `from autoraid.core.debug_frame_logger` to `from autoraid.orchestration.debug_frame_logger`
  - Move file to `test/unit/orchestration/test_debug_frame_logger.py`
- [x] [P10.5] Update imports in `test/unit/services/test_upgrade_orchestrator.py`
  - Change `from autoraid.services.upgrade_orchestrator` to `from autoraid.orchestration.upgrade_orchestrator`
  - Change `from autoraid.core` imports to appropriate new paths
  - Move file to `test/unit/orchestration/test_upgrade_orchestrator.py`
- [x] [P10.6] Update imports in `test/unit/services/test_locate_region_service.py`
  - Change any `from autoraid.core.locate_region` to `from autoraid.detection.locate_region`
- [x] [P10.7] Create `test/unit/orchestration/` directory
  ```bash
  mkdir -p test/unit/orchestration
  ```
- [x] [P10.8] Create `test/unit/detection/` directory
  ```bash
  mkdir -p test/unit/detection
  ```
- [x] [P10.9] Delete `test/unit/core/` directory (should be empty)
  ```bash
  rm -rf test/unit/core
  ```
- [x] [P10.10] Update imports in integration tests (`test/integration/test_*.py`)
  - Search for `from autoraid.core` and `from autoraid.services.upgrade_orchestrator` imports
  - Update to new paths
- [x] [P10.11] Run full test suite to verify all imports work
  ```bash
  uv run pytest
  ```

**Phase 10 Checkpoint**: All test imports updated, test directory structure reorganized, tests passing

---

## Phase 11: Commit Folder Structure Changes

**Goal**: Commit all import updates as atomic change

**Deliverable**: Clean git history with folder refactoring complete

**Tasks**:
- [ ] [P11.1] Stage all import changes
  ```bash
  git add -A
  ```
- [ ] [P11.2] Commit with descriptive message
  ```bash
  git commit -m "refactor: update all imports to use new orchestration/ and detection/ paths"
  ```
- [ ] [P11.3] Run full test suite to verify stability
  ```bash
  uv run pytest
  ```
- [ ] [P11.4] Manual smoke test CLI
  ```bash
  uv run autoraid --help
  uv run autoraid list-adapters
  ```
- [ ] [P11.5] Manual smoke test GUI
  ```bash
  uv run autoraid gui  # Launch, verify panels load, then close
  ```

**Phase 11 Checkpoint**: Folder structure refactoring complete and committed, all tests passing

---

## Phase 12: Remove Workflows from DI Container

**Goal**: Remove workflow factory providers from container and update callers

**Deliverable**: Workflows constructed directly, container has 10 providers (3 factories remaining)

**Tasks**:
- [x] [P12.1] Update `src/autoraid/container.py` - Remove workflow factory providers
  - Delete `count_workflow_factory = providers.Factory(CountWorkflow, ...)`
  - Delete `spend_workflow_factory = providers.Factory(SpendWorkflow, ...)`
  - Delete `debug_monitor_workflow_factory = providers.Factory(DebugMonitorWorkflow, ...)`
- [x] [P12.2] Update `src/autoraid/container.py` - Remove workflow module wiring
  - Remove `container.wire(modules=["autoraid.workflows.count_workflow"])` (if present)
  - Remove `container.wire(modules=["autoraid.workflows.spend_workflow"])` (if present)
  - Remove `container.wire(modules=["autoraid.workflows.debug_monitor_workflow"])` (if present)
- [x] [P12.3] Update `src/autoraid/workflows/count_workflow.py`
  - Remove `@inject` decorator from `__init__` if present
  - Update constructor to accept all services directly (no DI)
  - Keep orchestrator as parameter for now (will be removed in Phase 13)
- [x] [P12.4] Update `src/autoraid/workflows/spend_workflow.py`
  - Remove `@inject` decorator from `__init__` if present
  - Update constructor to accept all services directly
  - Keep orchestrator as parameter for now
- [x] [P12.5] Update `src/autoraid/workflows/debug_monitor_workflow.py`
  - Remove `@inject` decorator from `__init__` if present
  - Update constructor to accept all services directly
  - Keep orchestrator as parameter for now

**Phase 12 Checkpoint**: Workflow providers removed from container, workflows ready for direct construction

---

## Phase 13: Update CLI to Construct Workflows Directly

**Goal**: Update CLI commands to inject services and construct workflows

**Deliverable**: CLI commands inject services, construct workflows with explicit parameters

**Tasks**:
- [x] [P13.1] Update `src/autoraid/cli/upgrade_cli.py` - count command
  - Change from `@inject count_workflow_factory: Callable = Provide[...]`
  - To: `@inject cache_service, screenshot_service, window_service, network_manager, orchestrator_factory`
  - Construct `CountWorkflow(cache_service=..., orchestrator=orchestrator_factory(), ...)`
  - Pass runtime params directly (network_adapter_ids, max_attempts, debug_dir)
- [x] [P13.2] Update `src/autoraid/cli/upgrade_cli.py` - spend command
  - Same pattern as count command
  - Construct `SpendWorkflow(...)` directly with injected services
- [x] [P13.3] Update `src/autoraid/cli/debug_cli.py` - debug monitor command
  - Same pattern as count/spend
  - Construct `DebugMonitorWorkflow(...)` directly
- [x] [P13.4] Test CLI commands
  ```bash
  uv run autoraid count --help
  uv run autoraid spend --help
  ```

**Phase 13 Checkpoint**: CLI commands construct workflows directly, functional

---

## Phase 14: Update GUI to Construct Workflows Directly

**Goal**: Update GUI components to inject services and construct workflows

**Deliverable**: GUI panels inject services, construct workflows with explicit parameters

**Tasks**:
- [x] [P14.1] Update `src/autoraid/gui/components/upgrade_panel.py` - count workflow
  - Change from `@inject count_workflow_factory: Callable`
  - To: `@inject cache_service, screenshot_service, window_service, network_manager, orchestrator_factory, app_data`
  - Update `start_count_workflow()` to construct `CountWorkflow(...)` directly
- [x] [P14.2] Update `src/autoraid/gui/components/upgrade_panel.py` - spend workflow
  - Same pattern as count workflow
  - Update `start_spend_workflow()` to construct `SpendWorkflow(...)` directly
- [x] [P14.3] Update GUI to inject debug monitor workflow dependencies (if used in GUI)
- [x] [P14.4] Test GUI functionality
  ```bash
  uv run autoraid gui  # Launch, verify upgrade panel loads
  ```

**Phase 14 Checkpoint**: GUI components construct workflows directly, functional

---

## Phase 15: Update Workflow Tests

**Goal**: Update workflow tests to construct workflows directly with mocked services

**Deliverable**: Workflow tests construct directly, no factory mocking

**Tasks**:
- [ ] [P15.1] Update `test/unit/workflows/test_count_workflow.py` (if exists)
  - Remove factory mocking
  - Construct workflow directly with `Mock()` services
- [ ] [P15.2] Update `test/unit/workflows/test_spend_workflow.py` (if exists)
  - Same pattern as count workflow tests
- [ ] [P15.3] Update `test/unit/workflows/test_debug_monitor_workflow.py` (if exists)
  - Same pattern as count workflow tests
- [ ] [P15.4] Update `test/integration/test_count_workflow_integration.py`
  - Update to construct workflow with mocked orchestrator
- [ ] [P15.5] Update `test/integration/test_spend_workflow_integration.py`
  - Same pattern as count workflow integration tests
- [ ] [P15.6] Run workflow tests
  ```bash
  uv run pytest test/unit/workflows/
  uv run pytest test/integration/
  ```

**Phase 15 Checkpoint**: Workflow tests updated and passing, workflows fully removed from DI

---

## Phase 16: Commit Workflow DI Removal

**Goal**: Commit workflow removal from DI as atomic change

**Deliverable**: Clean git history with workflows removed from container

**Tasks**:
- [ ] [P16.1] Stage all workflow DI changes
  ```bash
  git add -A
  ```
- [ ] [P16.2] Commit with descriptive message
  ```bash
  git commit -m "refactor: remove workflows from DI container, construct directly in CLI/GUI"
  ```
- [ ] [P16.3] Run full test suite
  ```bash
  uv run pytest
  ```
- [ ] [P16.4] Verify container now has 10 providers (7 singletons, 3 factories)

**Phase 16 Checkpoint**: Workflows removed from DI, container down to 10 providers

---

## Phase 17: Remove Monitor from DI Container

**Goal**: Remove monitor factory from container, update orchestrator to create monitor internally

**Deliverable**: Monitor created by orchestrator per session, container has 9 providers

**Tasks**:
- [x] [P17.1] Update `src/autoraid/orchestration/upgrade_orchestrator.py` constructor
  - Change from accepting `monitor: ProgressBarMonitor` parameter
  - To: accepting `detector: ProgressBarStateDetector` parameter
  - Store `self._detector = detector`
- [x] [P17.2] Update `src/autoraid/orchestration/upgrade_orchestrator.py` - `run_upgrade_session()` method
  - At start of method, create fresh monitor: `monitor = ProgressBarMonitor(self._detector)`
  - Replace all `self._monitor` references with `monitor` local variable
- [x] [P17.3] Update `src/autoraid/container.py` - Remove monitor factory provider
  - Delete `progress_bar_monitor = providers.Factory(ProgressBarMonitor, ...)`
- [x] [P17.4] Update `src/autoraid/container.py` - Update orchestrator factory
  - Change `upgrade_orchestrator = providers.Factory(UpgradeOrchestrator, monitor=progress_bar_monitor, ...)`
  - To: `upgrade_orchestrator = providers.Factory(UpgradeOrchestrator, detector=progress_bar_detector, ...)`

**Phase 17 Checkpoint**: Monitor removed from container, created internally by orchestrator

---

## Phase 18: Update Orchestrator Tests

**Goal**: Update orchestrator tests to provide detector instead of monitor

**Deliverable**: Orchestrator tests construct with mocked detector, test real monitor

**Tasks**:
- [ ] [P18.1] Update `test/unit/orchestration/test_upgrade_orchestrator.py`
  - Change mocks from `Mock(spec=ProgressBarMonitor)` to `Mock(spec=ProgressBarStateDetector)`
  - Update orchestrator construction to pass `detector=mock_detector` instead of `monitor=mock_monitor`
  - Verify tests still pass (orchestrator creates monitor internally now)
- [ ] [P18.2] Run orchestrator tests
  ```bash
  uv run pytest test/unit/orchestration/test_upgrade_orchestrator.py
  ```

**Phase 18 Checkpoint**: Orchestrator tests updated and passing, monitor fully removed from DI

---

## Phase 19: Commit Monitor DI Removal

**Goal**: Commit monitor removal from DI as atomic change

**Deliverable**: Clean git history with monitor removed from container

**Tasks**:
- [ ] [P19.1] Stage all monitor DI changes
  ```bash
  git add -A
  ```
- [ ] [P19.2] Commit with descriptive message
  ```bash
  git commit -m "refactor: remove monitor from DI, created internally by orchestrator per session"
  ```
- [ ] [P19.3] Run full test suite
  ```bash
  uv run pytest
  ```
- [ ] [P19.4] Verify container now has 9 providers (7 singletons, 2 factories: orchestrator + disk_cache wrapper)

**Phase 19 Checkpoint**: Monitor removed from DI, container down to 9 providers

---

## Phase 20: Remove Orchestrator from DI Container

**Goal**: Remove orchestrator factory from container, update workflows to construct directly

**Deliverable**: Orchestrator constructed by workflows, container has 8 providers (zero factories except disk_cache)

**Tasks**:
- [x] [P20.1] Update `src/autoraid/workflows/count_workflow.py`
  - Remove `orchestrator` parameter from constructor
  - Add all orchestrator dependencies as parameters: `detector, screenshot_service, window_service, cache_service, network_manager`
  - In `run()` method, construct orchestrator: `orchestrator = UpgradeOrchestrator(detector=self._detector, ...)`
- [x] [P20.2] Update `src/autoraid/workflows/spend_workflow.py`
  - Same pattern as count workflow
- [x] [P20.3] Update `src/autoraid/workflows/debug_monitor_workflow.py`
  - Same pattern as count workflow
- [x] [P20.4] Update `src/autoraid/container.py` - Remove orchestrator factory provider
  - Delete `upgrade_orchestrator = providers.Factory(UpgradeOrchestrator, ...)`

**Phase 20 Checkpoint**: Orchestrator provider removed from container, workflows ready to construct directly

---

## Phase 21: Update CLI to Inject Detector Instead of Orchestrator

**Goal**: Update CLI commands to inject detector and let workflows construct orchestrator

**Deliverable**: CLI injects detector, workflows construct orchestrator internally

**Tasks**:
- [x] [P21.1] Update `src/autoraid/cli/upgrade_cli.py` - count command
  - Remove `orchestrator_factory` from injected params
  - Add `detector: ProgressBarStateDetector = Provide[Container.progress_bar_detector]`
  - Update `CountWorkflow(...)` construction to pass all services including detector
- [x] [P21.2] Update `src/autoraid/cli/upgrade_cli.py` - spend command
  - Same pattern as count command
  - Pass detector to `SpendWorkflow(...)`
- [x] [P21.3] Update `src/autoraid/cli/debug_cli.py` - debug monitor command
  - Same pattern as count/spend
  - Pass detector to `DebugMonitorWorkflow(...)`
- [x] [P21.4] Test CLI commands
  ```bash
  uv run autoraid count --help
  uv run autoraid spend --help
  ```

**Phase 21 Checkpoint**: CLI constructs workflows with detector, workflows create orchestrator

---

## Phase 22: Update GUI to Inject Detector Instead of Orchestrator

**Goal**: Update GUI components to inject detector and let workflows construct orchestrator

**Deliverable**: GUI injects detector, workflows construct orchestrator internally

**Tasks**:
- [x] [P22.1] Update `src/autoraid/gui/components/upgrade_panel.py`
  - Remove `orchestrator_factory` from injected params
  - Add `detector: ProgressBarStateDetector = Provide[Container.progress_bar_detector]`
  - Update workflow constructions in `start_count_workflow()` and `start_spend_workflow()`
  - Pass all services including detector to workflow constructors
- [x] [P22.2] Test GUI functionality
  ```bash
  uv run autoraid gui  # Launch, verify upgrade panel loads
  ```

**Phase 22 Checkpoint**: GUI constructs workflows with detector, workflows create orchestrator

---

## Phase 23: Update Integration Tests for Orchestrator Removal

**Goal**: Update integration tests to construct orchestrator directly with mocked services

**Deliverable**: Integration tests construct orchestrator, no factory mocking

**Tasks**:
- [x] [P23.1] Update `test/integration/test_count_workflow_integration.py`
  - Remove orchestrator factory mocking
  - Create mocked services (screenshot, window, cache, network, detector)
  - Workflow constructs orchestrator internally with these mocked services
- [x] [P23.2] Update `test/integration/test_spend_workflow_integration.py`
  - Same pattern as count workflow integration tests
- [x] [P23.3] Run integration tests
  ```bash
  uv run pytest test/integration/
  ```

**Phase 23 Checkpoint**: Integration tests updated and passing, orchestrator fully removed from DI

---

## Phase 24: Commit Orchestrator DI Removal

**Goal**: Commit orchestrator removal from DI as atomic change

**Deliverable**: Clean git history with orchestrator removed from container

**Tasks**:
- [ ] [P24.1] Stage all orchestrator DI changes
  ```bash
  git add -A
  ```
- [ ] [P24.2] Commit with descriptive message
  ```bash
  git commit -m "refactor: remove orchestrator from DI, constructed directly by workflows"
  ```
- [ ] [P24.3] Run full test suite
  ```bash
  uv run pytest
  ```
- [ ] [P24.4] Verify container now has 8 providers (8 singletons, 0 application factories)
  - Should only have: app_data, disk_cache, cache_service, screenshot_service, window_interaction_service, locate_region_service, network_manager, progress_bar_detector

**Phase 24 Checkpoint**: Orchestrator removed from DI, container down to 8 infrastructure singletons only

---

## Phase 25: Update CLAUDE.md Documentation

**Goal**: Update project documentation to reflect new architecture

**Deliverable**: CLAUDE.md accurately describes new folder structure and DI container

**Tasks**:
- [x] [P25.1] Update CLAUDE.md - Architecture section
  - Update Component Hierarchy diagram to show new folder structure
  - Update to show workflows/orchestrator/monitor constructed directly (not from DI)
- [x] [P25.2] Update CLAUDE.md - Project Structure section
  - Replace `/core` references with `/orchestration` and `/detection`
  - Update file tree to show new folder organization
- [x] [P25.3] Update CLAUDE.md - Dependency Injection Container section
  - Update container diagram to show 8 singletons only
  - Remove factory providers from documentation
  - Update wiring documentation
- [x] [P25.4] Update CLAUDE.md - Service Responsibilities table
  - Update lifecycle column (remove Factory entries for monitor/orchestrator)
  - Update file paths to reference new locations
- [x] [P25.5] Update CLAUDE.md - Workflow Usage Examples
  - Show direct construction pattern instead of factory injection
  - Update code examples to reflect new constructor signatures

**Phase 25 Checkpoint**: CLAUDE.md updated with new architecture

---

## Phase 26: Final Validation and Cleanup

**Goal**: Comprehensive testing and cleanup before merge

**Deliverable**: All tests passing, no regressions, clean codebase

**Tasks**:
- [ ] [P26.1] Run full test suite with coverage
  ```bash
  uv run pytest --cov=autoraid --cov-report=term-missing
  ```
- [ ] [P26.2] Verify no coverage decrease from baseline
- [ ] [P26.3] Run linting checks
  ```bash
  uv run ruff check .
  ```
- [ ] [P26.4] Run formatting checks
  ```bash
  uv run ruff format --check .
  ```
- [ ] [P26.5] Manual testing - CLI count workflow
  ```bash
  # (Don't actually run, just verify command syntax works)
  uv run autoraid count --help
  ```
- [ ] [P26.6] Manual testing - CLI spend workflow
  ```bash
  uv run autoraid spend --help
  ```
- [ ] [P26.7] Manual testing - GUI launch and navigation
  ```bash
  uv run autoraid gui
  # Verify all panels load without errors, then close
  ```
- [ ] [P26.8] Search for any remaining references to old paths
  ```bash
  grep -r "autoraid.core" src/autoraid/ test/
  grep -r "services.upgrade_orchestrator" src/autoraid/ test/
  ```
- [ ] [P26.9] Clean up any unused imports across codebase
- [ ] [P26.10] Verify container configuration in `container.py`
  - Exactly 8 singleton providers
  - Zero factory providers (except disk_cache wrapper)
  - Wiring only for CLI and GUI modules (not workflows)

**Phase 26 Checkpoint**: All tests passing, no regressions, codebase clean and ready for merge

---

## Phase 27: Final Commit and Merge Preparation

**Goal**: Finalize refactoring and prepare for merge

**Deliverable**: Feature branch ready to merge to main

**Tasks**:
- [ ] [P27.1] Stage documentation changes
  ```bash
  git add CLAUDE.md
  ```
- [ ] [P27.2] Commit documentation updates
  ```bash
  git commit -m "docs: update CLAUDE.md with new architecture and folder structure"
  ```
- [ ] [P27.3] Review full git log for clean history
  ```bash
  git log --oneline refactor-services
  ```
- [ ] [P27.4] Verify all commits are atomic and well-described
- [ ] [P27.5] Create summary of changes for PR/merge notes
  - Folder structure changes (orchestration/, detection/ created)
  - DI container simplification (13 → 8 providers, 62% factory reduction)
  - Constitutional alignment (YAGNI, Simplicity, Explicit Over Implicit)
- [ ] [P27.6] Final test run before merge
  ```bash
  uv run pytest
  ```

**Phase 27 Checkpoint**: Feature branch complete, ready to merge to main

---

## Completion Checklist

Before merging `refactor-services` to `main`:

- [ ] All 27 phases completed
- [ ] Full test suite passing (`pytest` shows 100% pass)
- [ ] No import errors in CLI or GUI
- [ ] Manual smoke tests successful (count, spend, GUI launch)
- [ ] Container has exactly 8 singleton providers, 0 application factory providers
- [ ] Folder structure matches target state (orchestration/, detection/ exist, core/ deleted)
- [ ] CLAUDE.md documentation updated
- [ ] No decrease in test coverage
- [ ] All constitutional violations addressed (YAGNI, Simplicity, Explicit Over Implicit)
- [ ] Git history clean with atomic commits

---

## Rollback Plan

If critical issues discovered after starting:

1. **Early phases (0-11)**: Revert folder moves
   ```bash
   git reset --hard origin/main
   ```

2. **Mid phases (12-19)**: Revert DI changes for workflows/monitor
   ```bash
   git revert <commit-hash>  # Revert specific DI commits
   ```

3. **Late phases (20-27)**: Complete refactoring or pause at stable checkpoint
   - Each phase leaves code in runnable state
   - Can pause between phases and deploy if needed

4. **Post-merge issues**: Revert merge commit
   ```bash
   git revert -m 1 <merge-commit-hash>
   ```
