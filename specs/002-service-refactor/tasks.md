# Implementation Tasks: Service-Based Architecture Refactoring
**Design Pattern**: Nested command groups

**Branch**: `002-service-refactor` | **Date**: 2025-10-17
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Overview

This document provides detailed implementation tasks for refactoring AutoRaid into a service-based architecture with dependency injection. Tasks are organized by implementation phase, following the sequential order defined in the phase outline. Each phase leaves the codebase in a working state with passing tests.

**Testing Approach**: Smoke tests (not full TDD). Each service gets 1-2 concise smoke tests to verify basic functionality.

## Task Summary

- **Total Tasks**: 84
- **Phases**: 9 (Phase 0-8)
- **Estimated Time**: ~16 hours
- **Test Tasks**: 19 (12 smoke tests + 4 integration tests + 3 coverage validation tasks)
- **Parallel Opportunities**: Service extractions in Phases 2-5 could be parallelized if desired

## Dependencies & Execution Order

This refactoring follows a **strict sequential order** due to the nature of architectural refactoring:

```
Phase 0 (Setup)
    ↓
Phase 1 (State Machine) → Enables US1 (Core Testing)
    ↓
Phase 2 (CacheService) ─┐
    ↓                   │
Phase 3 (Screenshot) ───┼─→ Foundation for US4 (Unchanged Workflows)
    ↓                   │
Phase 4 (LocateRegion) ─┤
    ↓                   │
Phase 5 (WindowInteraction) ┘
    ↓
Phase 6 (Orchestrator) → Enables US3 (Mock Testing), Completes US4
    ↓
Phase 7 (CLI Refactor) → Enables US6 (Thin CLI), US2 (Debug Logging)
    ↓
Phase 8 (Cleanup) → Completes US5 (Phased Rollout)
```

**Key Dependencies**:
- Phase 6 (Orchestrator) depends on Phases 2-5 (all foundation services)
- Phase 7 (CLI) depends on Phase 6 (orchestrator available)
- US1 (Core Testing) delivered in Phase 1
- US4 (Unchanged Workflows) validated after Phase 6
- US2, US6 delivered in Phase 7
- US5 (Phased Rollout Safety) validated throughout all phases

## Phase 0: Setup Dependency Injection Infrastructure

**Goal**: Add dependency-injector library and create basic container structure.

**User Story Mapping**: Foundation for all user stories (US1-US6)

**Independent Test Criteria**: Container instantiates successfully, wiring configuration valid, existing CLI commands still work.

### Tasks

- [X] T001 Add dependency-injector to pyproject.toml dependencies section
- [X] T002 Run `uv sync` to install dependency-injector library
- [X] T003 Create new file src/autoraid/container.py with DeclarativeContainer class
- [X] T004 Define wiring configuration in Container class for autoraid.cli.upgrade_cli and autoraid.cli.network_cli modules
- [X] T005 Add configuration provider to Container class (cache_dir, debug flags)
- [X] T006 Create disk_cache provider (Singleton) wrapping diskcache.Cache in Container class
- [X] T007 Modify src/autoraid/cli/cli.py to create Container instance in cli() function
- [X] T008 Configure container from Click context (cache_dir, debug flag) in cli() function
- [X] T009 Store container in Click context object (ctx.obj) for potential manual access
- [X] T010 Run `uv run autoraid --help` to verify CLI still works
- [X] T011 Run `uv run autoraid upgrade count --help` to verify upgrade commands accessible
- [X] T012 Run existing tests with `uv run pytest` to ensure no regressions

**Checkpoint**: DI infrastructure ready. Container created. Existing functionality unchanged.

---

## Phase 1: Extract State Machine (US1 - Core Upgrade Logic Testing)

**Goal**: Separate pure state machine logic from I/O operations, making it testable with fixture images.

**User Story**: US1 (P1) - Core Upgrade Logic Testing

**Independent Test Criteria**:
- UpgradeStateMachine instantiates and processes fixture images without requiring Raid window
- State machine correctly counts fail states
- State machine detects stop conditions (4 consecutive standby/connection_error, max attempts)
- All acceptance scenarios from US1 pass

### Tasks

- [X] T013 [US1] Create new file src/autoraid/autoupgrade/state_machine.py
- [X] T014 [US1] Define ProgressBarState enum (FAIL, PROGRESS, STANDBY, CONNECTION_ERROR, UNKNOWN) in state_machine.py
- [X] T015 [US1] Define StopCountReason enum (UPGRADED, CONNECTION_ERROR, MAX_ATTEMPTS_REACHED) in state_machine.py
- [X] T016 [US1] Create UpgradeStateMachine class with __init__(max_attempts: int) in state_machine.py
- [X] T017 [US1] Initialize deque with maxlen=4 for recent_states in UpgradeStateMachine.__init__
- [X] T018 [US1] Implement process_frame(roi_image: np.ndarray) -> tuple[int, StopCountReason | None] method
- [X] T019 [US1] Implement _detect_state(roi_image: np.ndarray) -> ProgressBarState method using existing progress_bar.detect_progressbar_state()
- [X] T020 [US1] Implement _check_stop_condition() -> StopCountReason | None method checking deque for 4 consecutive states
- [X] T021 [US1] Update process_frame to track fail_count, append states to deque, check stop conditions
- [X] T022 [US1] Add state_machine Factory provider to Container class in src/autoraid/container.py
- [X] T023 [US1] Create new file test/test_state_machine.py for smoke tests
- [X] T024 [US1] Add smoke test: test_state_machine_instantiates() verifying UpgradeStateMachine(max_attempts=10) creates instance
- [X] T025 [US1] Add smoke test: test_state_machine_counts_fails() feeding 3 fail images and asserting fail_count=3
- [X] T026 [US1] Add smoke test: test_state_machine_stops_on_upgraded() feeding 4 consecutive standby images and asserting stop_reason=UPGRADED
- [X] T027 [US1] Add smoke test: test_state_machine_stops_on_max_attempts() feeding 10 fail images with max_attempts=10 and asserting stop_reason=MAX_ATTEMPTS_REACHED
- [X] T028 [US1] Modify src/autoraid/autoupgrade/autoupgrade.py count_upgrade_fails() to create state_machine instance from container
- [X] T029 [US1] Update count_upgrade_fails() to use state_machine.process_frame() instead of inline state detection
- [X] T030 Run `uv run pytest test/test_state_machine.py` to verify state machine smoke tests pass
- [X] T031 Run `uv run pytest` to ensure all existing tests still pass
- [X] T031a [US1] Install pytest-cov if not already installed: `uv add --dev pytest-cov`
- [X] T031b [US1] Run `uv run pytest --cov=autoraid.autoupgrade.state_machine --cov-report=term-missing test/test_state_machine.py` to measure coverage
- [X] T031c [US1] Verify code coverage for state_machine.py is ≥90% (SC-006), add tests if needed to reach threshold
- [X] T032 Run `uv run autoraid upgrade count --help` to verify CLI still works

**Checkpoint**: US1 delivered. State machine testable with fixture images. Existing workflows unchanged.

---

## Phase 2: Extract CacheService (Foundation for US4)

**Goal**: Centralize all caching operations in one service.

**User Story**: US4 (P1) - Unchanged User Workflows (foundation)

**Independent Test Criteria**:
- CacheService instantiates and generates correct cache keys
- get_regions/set_regions work with backward-compatible key format
- Existing cached regions from pre-refactor code load successfully

### Tasks

- [X] T033 [US4] Create directory src/autoraid/services/ if not exists
- [X] T034 [US4] Create new file src/autoraid/services/__init__.py (empty initially)
- [X] T035 [US4] Create new file src/autoraid/services/cache_service.py
- [X] T036 [US4] Define CacheService class with __init__(cache: diskcache.Cache) in cache_service.py
- [X] T037 [US4] Implement create_regions_key(window_size: tuple[int, int]) -> str method returning f"regions_{width}_{height}"
- [X] T038 [US4] Implement get_regions(window_size: tuple[int, int]) -> dict | None method
- [X] T039 [US4] Implement set_regions(window_size: tuple[int, int], regions: dict) -> None method
- [X] T040 [US4] Implement get_screenshot(window_size: tuple[int, int]) -> np.ndarray | None method
- [X] T041 [US4] Implement set_screenshot(window_size: tuple[int, int], screenshot: np.ndarray) -> None method
- [X] T042 [US4] Add cache_service Singleton provider to Container class in src/autoraid/container.py
- [X] T043 [US4] Create new file test/test_cache_service.py for smoke tests
- [X] T044 [US4] Add smoke test: test_cache_service_instantiates() verifying CacheService(mock_cache) creates instance
- [X] T045 [US4] Add smoke test: test_cache_service_generates_correct_key() asserting key format matches "regions_{width}_{height}"
- [X] T046 [US4] Update src/autoraid/autoupgrade/autoupgrade.py to inject and use cache_service
- [X] T047 [US4] Update src/autoraid/cli/upgrade_cli.py to inject and use cache_service if needed
- [X] T048 Run `uv run pytest test/test_cache_service.py` to verify cache service smoke tests pass
- [X] T049 Run `uv run pytest` to ensure all tests still pass
- [X] T050 Run `uv run autoraid upgrade count --help` to verify CLI still works

**Checkpoint**: CacheService extracted. All caching through one service. Backward-compatible cache keys maintained.

---

## Phase 3: Extract ScreenshotService (Foundation for US4)

**Goal**: All screenshot operations through one service.

**User Story**: US4 (P1) - Unchanged User Workflows (foundation)

**Independent Test Criteria**:
- ScreenshotService instantiates without dependencies
- extract_roi correctly extracts region from screenshot array
- window_exists check works (manual verification)

### Tasks

- [X] T051 [P] [US4] Create new file src/autoraid/services/screenshot_service.py
- [X] T052 [P] [US4] Define ScreenshotService class with __init__() (no dependencies) in screenshot_service.py
- [X] T053 [P] [US4] Move take_screenshot logic from interaction.py to ScreenshotService.take_screenshot(window_title: str) -> np.ndarray
- [X] T054 [P] [US4] Move window_exists logic from interaction.py to ScreenshotService.window_exists(window_title: str) -> bool
- [X] T055 [P] [US4] Implement extract_roi(screenshot: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray method
- [X] T056 [P] [US4] Add screenshot_service Singleton provider to Container class in src/autoraid/container.py
- [X] T057 Create new file test/test_screenshot_service.py for smoke tests
- [X] T058 Add smoke test: test_screenshot_service_instantiates() verifying ScreenshotService() creates instance
- [X] T059 Add smoke test: test_screenshot_service_extracts_roi() with fake numpy array verifying ROI extraction works
- [X] T060 Update src/autoraid/autoupgrade/autoupgrade.py to inject and use screenshot_service
- [X] T061 Update src/autoraid/cli/upgrade_cli.py to inject and use screenshot_service if needed
- [X] T062 Run `uv run pytest test/test_screenshot_service.py` to verify screenshot service smoke tests pass
- [X] T063 Run `uv run pytest` to ensure all tests still pass

**Checkpoint**: ScreenshotService extracted. Window operations centralized.

---

## Phase 4: Extract LocateRegionService (Foundation for US4)

**Goal**: One service handles all region detection and selection.

**User Story**: US4 (P1) - Unchanged User Workflows (foundation)

**Independent Test Criteria**:
- LocateRegionService instantiates with CacheService and ScreenshotService dependencies
- get_regions integrates with cache correctly
- Fallback from automatic to manual selection works

### Tasks

- [X] T064 [P] [US4] Create new file src/autoraid/services/locate_region_service.py
- [X] T065 [P] [US4] Define LocateRegionService class with __init__(cache_service: CacheService, screenshot_service: ScreenshotService)
- [X] T066 [P] [US4] Implement get_regions(screenshot: np.ndarray, window_size: tuple[int, int], manual: bool = False) -> dict method
- [X] T067 [P] [US4] Implement _try_automatic_detection(screenshot: np.ndarray) -> dict | None method using locate_upgrade_region module
- [X] T068 [P] [US4] Implement _manual_selection(screenshot: np.ndarray) -> dict method using existing selection logic
- [X] T069 [P] [US4] Integrate cache checks in get_regions: check cache → auto-detect → manual fallback → cache result
- [X] T070 [P] [US4] Add locate_region_service Singleton provider to Container class in src/autoraid/container.py
- [X] T071 [P] [US4] Inject cache_service and screenshot_service dependencies in provider registration
- [X] T072 Create new file test/test_locate_region_service.py for smoke tests
- [X] T073 Add smoke test: test_locate_region_service_instantiates() verifying LocateRegionService(mock_cache, mock_screenshot) creates instance
- [X] T074 Add smoke test: test_locate_region_service_uses_cache() with mocked cache_service.get_regions returning regions
- [X] T075 Update src/autoraid/autoupgrade/autoupgrade.py to inject and use locate_region_service
- [X] T076 Update src/autoraid/cli/upgrade_cli.py to inject and use locate_region_service if needed
- [X] T077 Run `uv run pytest test/test_locate_region_service.py` to verify locate region service smoke tests pass
- [X] T078 Run `uv run pytest` to ensure all tests still pass

**Checkpoint**: LocateRegionService extracted. Region management centralized and testable.

---

## Phase 5: Extract WindowInteractionService (Foundation for US4)

**Goal**: Separate clicking and window operations.

**User Story**: US4 (P1) - Unchanged User Workflows (foundation)

**Independent Test Criteria**:
- WindowInteractionService instantiates without dependencies
- click_region method exists and takes correct parameters
- activate_window method exists

### Tasks

- [X] T079 [P] [US4] Create new file src/autoraid/services/window_interaction_service.py
- [X] T080 [P] [US4] Define WindowInteractionService class with __init__() (no dependencies)
- [X] T081 [P] [US4] Move click_region_center logic from interaction.py to WindowInteractionService.click_region(window_title: str, region: tuple) -> None
- [X] T082 [P] [US4] Implement activate_window(window_title: str) -> None method if not already in ScreenshotService
- [X] T083 [P] [US4] Add window_interaction_service Singleton provider to Container class in src/autoraid/container.py
- [X] T084 Update src/autoraid/cli/upgrade_cli.py to inject and use window_interaction_service
- [X] T085 Run `uv run pytest` to ensure all tests still pass
- [X] T086 Run manual test: `uv run autoraid upgrade count -n 1` (requires live Raid window) to verify clicking still works

**Checkpoint**: WindowInteractionService extracted. All GUI interactions centralized.

---

## Phase 6: Create Orchestrator (US3, US4 completion)

**Goal**: Coordinate all services for workflows. Enable mocked testing.

**User Stories**:
- US3 (P2) - Unit Testing with Mocks
- US4 (P1) - Unchanged User Workflows (completion)

**Independent Test Criteria**:
- UpgradeOrchestrator instantiates with all service dependencies injected
- count_workflow executes successfully with mocked services
- spend_workflow executes successfully with mocked services
- Network adapters re-enabled in finally block even if workflow fails
- US4 acceptance criteria pass: CLI commands produce same output as before

### Tasks

- [ ] T087 [P] [US3] [US4] Create new file src/autoraid/services/upgrade_orchestrator.py
- [ ] T088 [P] [US3] [US4] Define UpgradeOrchestrator class with __init__ accepting all service dependencies
- [ ] T089 [P] [US3] [US4] Add constructor parameters: cache_service, screenshot_service, locate_region_service, window_interaction_service, state_machine (factory/provider)
- [ ] T090 [US3] [US4] Implement count_workflow(network_adapter_id: list[int] | None, max_attempts: int) -> tuple[int, StopCountReason] method
- [ ] T091 [US3] [US4] Move orchestration logic from CLI count command to count_workflow method
- [ ] T092 [US3] [US4] Add network disable/enable with finally block in count_workflow ensuring adapters re-enabled
- [ ] T093 [US3] [US4] Add INFO-level logging for workflow milestones: "Starting count workflow", "Captured screenshot", etc.
- [ ] T094 [US3] [US4] Add DEBUG-level logging for service entry/exit with [UpgradeOrchestrator] prefix
- [ ] T095 [US3] [US4] Implement spend_workflow(fail_count: int, max_attempts: int, continue_upgrade: bool) -> dict method
- [ ] T096 [US3] [US4] Move orchestration logic from CLI spend command to spend_workflow method
- [ ] T097 [US3] [US4] Add upgrade_orchestrator Factory provider to Container class in src/autoraid/container.py
- [ ] T098 [US3] [US4] Inject all service dependencies and state_machine.provider in orchestrator provider registration
- [ ] T099 [US3] Create new file test/test_upgrade_orchestrator.py for smoke tests
- [ ] T100 [US3] Create TestContainer class with mocked service providers in test_upgrade_orchestrator.py
- [ ] T101 [US3] Add smoke test: test_orchestrator_instantiates() verifying UpgradeOrchestrator creates with mocked dependencies
- [ ] T102 [US3] Add smoke test: test_orchestrator_count_workflow_calls_services() verifying orchestrator calls screenshot_service.take_screenshot
- [ ] T103 [US3] Add smoke test: test_orchestrator_count_workflow_re_enables_network() verifying finally block executes on exception
- [ ] T104 Run `uv run pytest test/test_upgrade_orchestrator.py` to verify orchestrator smoke tests pass
- [ ] T105 Run `uv run pytest` to ensure all tests still pass
- [ ] T105a [US4] Create integration test baseline by running `uv run autoraid upgrade count --help` and `uv run autoraid upgrade count -n 1 --dry-run` (if available) and capturing output to test/integration_baseline.txt
- [ ] T105b [US4] Create new file test/test_cli_integration.py with test_count_command_help_unchanged() comparing current help output to baseline
- [ ] T105c [US4] Add integration test test_cached_regions_load_successfully() verifying pre-refactor cached regions load without errors
- [ ] T105d [US4] Run `uv run pytest test/test_cli_integration.py` to verify US4 acceptance scenarios pass

**Checkpoint**: US3 delivered (mocked testing possible). US4 validated (integration tests pass - CLI behavior unchanged). Business logic separated from CLI.

---

## Phase 7: Simplify CLI with DI (US2, US6)

**Goal**: CLI becomes thin wrapper using @inject decorator. Logging properly configured.

**User Stories**:
- US2 (P2) - Service Isolation for Debugging
- US6 (P3) - Thin CLI Commands

**Independent Test Criteria**:
- CLI commands are <20 lines (excluding imports/docstrings)
- @inject decorator works correctly, orchestrator injected
- INFO logs show workflow milestones in normal mode
- DEBUG logs show service entry/exit when --debug flag enabled
- US2 acceptance criteria pass: logs show clear service boundaries
- US6 acceptance criteria pass: CLI is thin glue code

### Tasks

- [ ] T106 [US2] [US6] Add loguru logging configuration to src/autoraid/cli/cli.py in cli() function
- [ ] T107 [US2] Configure INFO level logging for normal mode (format without timestamps)
- [ ] T108 [US2] Configure DEBUG level logging for debug mode (format with timestamps, save to debug/ directory)
- [ ] T109 [US6] Add @inject decorator import to src/autoraid/cli/upgrade_cli.py
- [ ] T110 [US6] Add @inject decorator to count command in upgrade_cli.py
- [ ] T111 [US6] Add orchestrator parameter with Provide[Container.upgrade_orchestrator] to count command
- [ ] T112 [US6] Replace business logic in count command with orchestrator.count_workflow() call (target <20 lines)
- [ ] T113 [US6] Update count command to handle orchestrator result and display output using rich
- [ ] T114 [US6] Add @inject decorator to spend command in upgrade_cli.py
- [ ] T115 [US6] Add orchestrator parameter with Provide[Container.upgrade_orchestrator] to spend command
- [ ] T116 [US6] Replace business logic in spend command with orchestrator.spend_workflow() call (target <20 lines)
- [ ] T117 [US6] Update spend command to handle orchestrator result and display output using rich
- [ ] T118 [US6] Remove or deprecate business logic from CLI commands (move to orchestrator if not already done)
- [ ] T119 [US2] [US6] Verify wiring configuration in Container class includes autoraid.cli.upgrade_cli module
- [ ] T120 [US2] Run `uv run autoraid upgrade count --help` in normal mode and verify INFO logs show workflow milestones
- [ ] T121 [US2] Run `uv run autoraid --debug upgrade count --help` and verify DEBUG logs show service entry/exit with [ServiceName] prefixes
- [ ] T122 [US6] Measure LOC for count and spend commands (excluding imports/docstrings) and verify <20 lines each
- [ ] T123 Run `uv run pytest` to ensure all tests still pass
- [ ] T124 Run manual test: `uv run autoraid upgrade count -n 1` (requires live Raid window) to verify full workflow

**Checkpoint**: US2 delivered (debug logging). US6 delivered (thin CLI). Clean separation achieved.

---

## Phase 8: Cleanup and Documentation (US5 completion)

**Goal**: Remove duplicated code, update documentation, finalize refactoring.

**User Story**: US5 (P1) - Phased Rollout Safety (completion - all phases delivered working code)

**Independent Test Criteria**:
- No deprecated wrapper functions remain
- All tests pass
- CLAUDE.md documents new architecture
- US5 acceptance criteria pass: All 8 phases completed with working code at each checkpoint

### Tasks

- [ ] T125 [US5] Review src/autoraid/autoupgrade/autoupgrade.py for deprecated wrapper functions and mark for removal
- [ ] T126 [US5] Remove deprecated functions from autoupgrade.py if no longer called
- [ ] T127 [US5] Review src/autoraid/interaction.py and simplify or remove if logic moved to services
- [ ] T128 [US5] Update src/autoraid/services/__init__.py to export all service classes
- [ ] T129 [US5] Create exceptions.py file at src/autoraid/exceptions.py with custom exception classes
- [ ] T130 [US5] Define CacheInitializationError, WindowNotFoundException, RegionDetectionError, DependencyResolutionError in exceptions.py
- [ ] T131 [US5] Update services to raise custom exceptions instead of generic Exception where appropriate
- [ ] T132 [US5] Update CLAUDE.md Architecture section with service-based architecture overview
- [ ] T133 [US5] Add container dependency graph (ASCII art) to CLAUDE.md
- [ ] T134 [US5] Document service responsibilities and lifecycles (Singleton vs Factory) in CLAUDE.md
- [ ] T135 [US5] Update CLAUDE.md Testing section with mock testing patterns
- [ ] T136 [US5] Add troubleshooting section to CLAUDE.md for common DI container issues
- [ ] T137 [US5] Run `uv run ruff check .` to verify code quality
- [ ] T138 [US5] Run `uv run ruff format .` to format all code
- [ ] T139 [US5] Run `uv run pytest` to ensure all tests pass after cleanup
- [ ] T140 Run full integration test suite manually with live Raid window
- [ ] T141 Verify all US5 acceptance criteria: all phases completed, tests pass, workflows functional

**Checkpoint**: US5 delivered. Clean codebase. All user stories completed. Refactoring complete.

---

## Parallel Execution Opportunities

While this refactoring follows a sequential approach for safety, these tasks **could** be parallelized if desired:

**Phase 2-5 Service Extractions** (after Phase 1 complete):
- T033-T050 (CacheService)
- T051-T063 (ScreenshotService) - marked with [P]
- T064-T078 (LocateRegionService) - marked with [P]
- T079-T086 (WindowInteractionService) - marked with [P]

**Rationale for Parallel**: Each service extraction is independent (different files, minimal cross-dependencies during extraction phase).

**Caveat**: Orchestrator (Phase 6) MUST wait for all foundation services (Phases 2-5) to complete.

## Testing Strategy

**Smoke Tests Only** (per user guidance: "not following a full TDD approach, but will need smoke tests"):

1. **test_state_machine.py** (4 tests):
   - Instantiation
   - Fail counting
   - Stop on upgraded
   - Stop on max attempts

2. **test_cache_service.py** (2 tests):
   - Instantiation
   - Cache key generation

3. **test_screenshot_service.py** (2 tests):
   - Instantiation
   - ROI extraction

4. **test_locate_region_service.py** (2 tests):
   - Instantiation
   - Cache integration

5. **test_upgrade_orchestrator.py** (3 tests):
   - Instantiation with mocks
   - Service coordination
   - Finally block execution

6. **test_cli_integration.py** (4 tests):
   - CLI help output unchanged
   - Cached regions compatibility
   - Count command behavior
   - Spend command behavior

**Total**: 13 smoke tests + 4 integration tests + 3 coverage checks = 20 test-related tasks

**Manual Testing Checkpoints**:
- After Phase 0: CLI help commands
- After Phase 1: State machine with fixture images, verify ≥90% coverage
- After Phase 6: Full count workflow with live Raid window
- After Phase 7: Full count and spend workflows
- After Phase 8: Integration test suite

## Implementation Strategy

### MVP Scope

**Minimum Viable Product**: Phase 0-1 (US1 delivered)

At Phase 1 completion:
- ✅ DI infrastructure in place
- ✅ US1 delivered: State machine testable with fixture images
- ✅ Existing workflows unchanged
- ✅ Can stop here with valuable testability improvement

### Full Delivery Scope

**Complete Refactoring**: Phase 0-8 (all user stories delivered)

At Phase 8 completion:
- ✅ US1: Core logic testable
- ✅ US2: Debug logging with service boundaries
- ✅ US3: Mocked testing enabled
- ✅ US4: Backward compatibility maintained
- ✅ US5: Phased rollout completed safely
- ✅ US6: Thin CLI commands

### User Story Completion Order

1. **Phase 1**: US1 (Core Upgrade Logic Testing) - P1
2. **Phase 6**: US3 (Unit Testing with Mocks) - P2, US4 (Unchanged Workflows) - P1
3. **Phase 7**: US2 (Service Isolation for Debugging) - P2, US6 (Thin CLI) - P3
4. **Phase 8**: US5 (Phased Rollout Safety) - P1

## Success Criteria Validation

After Phase 8 completion, verify all success criteria from spec.md:

- [ ] SC-001: State machine tests execute in <1 second
- [ ] SC-002: Each service file <200 LOC
- [ ] SC-003: CLI commands <20 LOC each
- [ ] SC-004: Debug logs show service entry/exit points
- [ ] SC-005: All tests pass after each phase
- [ ] SC-006: State machine code coverage ≥90% (validated in T031b-c)
- [ ] SC-007: Fully mocked test exists and runs without external dependencies
- [ ] SC-008: Existing cached regions load successfully
- [ ] SC-009: CLI commands produce identical behavior vs pre-refactor (validated in T105a-d)
- [ ] SC-010: Container initialization <100ms (manual benchmark during T141)
- [ ] SC-011: Services have explicit constructor dependencies
- [ ] SC-012: Zero breaking changes to CLI or cache formats

## Commit Strategy

**Commit after each phase completes** with commit message format from service-refactor-phases.md:

- Phase 0: `refactor: setup dependency injection infrastructure`
- Phase 1: `refactor: extract UpgradeStateMachine from count_upgrade_fails`
- Phase 2: `refactor: extract CacheService`
- Phase 3: `refactor: extract ScreenshotService`
- Phase 4: `refactor: extract LocateRegionService`
- Phase 5: `refactor: extract WindowInteractionService`
- Phase 6: `refactor: create UpgradeOrchestrator`
- Phase 7: `refactor: simplify CLI with dependency injection`
- Phase 8: `refactor: cleanup and documentation`

Each commit includes the co-author line:
```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Next Steps

1. **Begin Phase 0**: Start with T001 (add dependency-injector to pyproject.toml)
2. **Follow sequential order**: Complete each phase before moving to next
3. **Commit after each phase**: Ensure working state at each checkpoint
4. **Validate US criteria**: Check user story acceptance scenarios at relevant phases
5. **Manual testing**: Perform manual smoke tests with live Raid window at key checkpoints
