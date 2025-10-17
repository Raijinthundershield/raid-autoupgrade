# Service-Based Architecture Refactoring - Implementation Phases

## Phase 0: Setup Dependency Injection Infrastructure

**Goal**: Add dependency-injector and create basic container structure

**Changes**:
- Add `dependency-injector` to `pyproject.toml`
- Create `src/autoraid/container.py` with basic container
- Wire container in CLI entry point (`cli.py`)
- Add container to Click context object

**Files modified**:
- MODIFY: `pyproject.toml` (add dependency-injector)
- NEW: `src/autoraid/container.py`
- MODIFY: `src/autoraid/cli/cli.py` (create container, wire modules)

**Result**: DI infrastructure ready. Existing code unchanged but container available.

---

## Phase 1: Extract State Machine

**Goal**: Separate pure state machine from I/O operations

**Changes**:
- Create `UpgradeStateMachine` class in `state_machine.py`
- Extract state transition logic from `count_upgrade_fails()`
- `count_upgrade_fails()` becomes thin wrapper calling state machine
- Add comprehensive tests with fixture images
- Add state_machine provider to container

**Files modified**:
- NEW: `src/autoraid/autoupgrade/state_machine.py`
- NEW: `test/test_state_machine.py`
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py` (make it use state machine)
- MODIFY: `src/autoraid/container.py` (add state_machine provider)

**Result**: State machine testable without GUI. Original code still works.

---

## Phase 2: Extract Cache Service

**Goal**: One place for all caching operations

**Changes**:
- Create `CacheService` class
- Move cache key generation functions
- Move get/set operations
- Update callers: `autoupgrade.py`, `upgrade_cli.py`
- Add cache_service provider to container (Singleton)
- Inject via DI where needed

**Files modified**:
- NEW: `src/autoraid/services/cache_service.py`
- NEW: `test/test_cache_service.py`
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`
- MODIFY: `src/autoraid/container.py` (add cache_service provider)

**Result**: All caching through one service. No scattered cache logic.

---

## Phase 3: Extract Screenshot Service

**Goal**: All screenshot operations through one service

**Changes**:
- Create `ScreenshotService` class
- Move `take_screenshot_of_window()`, `window_exists()` from `interaction.py`
- Add ROI extraction method (from `visualization.py`)
- Update callers
- Add screenshot_service provider to container (Singleton)
- Inject via DI

**Files modified**:
- NEW: `src/autoraid/services/screenshot_service.py`
- NEW: `test/test_screenshot_service.py` (mock-based)
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`
- MODIFY: `src/autoraid/container.py` (add screenshot_service provider)

**Result**: Single point for all window screenshot operations.

---

## Phase 4: Extract LocateRegion Service

**Goal**: One service handles all region detection and selection

**Changes**:
- Create `LocateRegionService` class
- Consolidate automatic detection + manual fallback
- Integrate with `CacheService` via DI
- Move `select_upgrade_regions()`, `get_regions()` logic
- Add locate_region_service provider to container (Singleton)
- Inject cache_service and screenshot_service

**Files modified**:
- NEW: `src/autoraid/services/locate_region_service.py`
- NEW: `test/test_locate_region_service.py`
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`
- MODIFY: `src/autoraid/container.py` (add locate_region_service provider)

**Result**: Region management in one place, testable.

---

## Phase 5: Extract WindowInteraction Service

**Goal**: Separate clicking and window operations from other interaction logic

**Changes**:
- Create `WindowInteractionService` class
- Move `click_region_center()` from `interaction.py`
- Add window activation, `window_exists()` if not in ScreenshotService
- Add window_interaction_service provider to container (Singleton)

**Files modified**:
- NEW: `src/autoraid/services/window_interaction_service.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`
- MODIFY: `src/autoraid/container.py` (add window_interaction_service provider)

**Result**: All clicking and window interaction through one service.

---

## Phase 6: Create Orchestrator

**Goal**: Coordinate all services for workflows

**Changes**:
- Create `UpgradeOrchestrator` class
- Implement `count_workflow()` and `spend_workflow()` methods
- Move orchestration logic from CLI commands
- Integrate network management, debug output coordination
- Add upgrade_orchestrator provider to container (Factory)
- Inject all required services via constructor

**Files modified**:
- NEW: `src/autoraid/services/upgrade_orchestrator.py`
- NEW: `test/test_upgrade_orchestrator.py` (integration tests)
- MODIFY: `src/autoraid/container.py` (add upgrade_orchestrator provider)

**Result**: Business logic separated from CLI presentation.

---

## Phase 7: Simplify CLI with DI

**Goal**: CLI becomes thin wrapper using @inject decorator

**Changes**:
- Use `@inject` decorator on CLI commands
- Inject `UpgradeOrchestrator` via `Provide[Container.upgrade_orchestrator]`
- Update `count()` command to call `orchestrator.count_workflow()`
- Update `spend()` command to call `orchestrator.spend_workflow()`
- Remove business logic from CLI
- CLI only handles: argument parsing, context setup, output formatting

**Files modified**:
- MODIFY: `src/autoraid/cli/upgrade_cli.py` (major simplification, add @inject)
- MODIFY: `src/autoraid/cli/cli.py` (ensure wiring configuration)

**Result**: Clean separation. CLI is thin, testable business logic in orchestrator.

---

## Phase 8: Cleanup

**Goal**: Remove duplicated code, consolidate utilities

**Changes**:
- Deprecate/remove old functions in `autoupgrade.py` if no longer needed
- Update `interaction.py` (may become simpler or merge into services)
- Documentation updates
- Add container diagram to CLAUDE.md

**Files modified**:
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/interaction.py`
- MODIFY: `CLAUDE.md` (architecture section with DI container info)

**Result**: Clean codebase with no dead code.

---

## Summary: Phase Dependencies

```
Phase 0: Setup DI
    ↓
Phase 1: State Machine ──┐
    ↓                    │
Phase 2: Cache Service ──┼─→ Foundation Services
    ↓                    │
Phase 3: Screenshot ─────┤
    ↓                    │
Phase 4: LocateRegion ───┤
    ↓                    │
Phase 5: WindowInteraction ┘
    ↓
Phase 6: Orchestrator (uses all foundation services)
    ↓
Phase 7: Simplify CLI (uses orchestrator)
    ↓
Phase 8: Cleanup
```

## Testing Checkpoints

After each phase, verify:
1. ✅ All existing tests pass
2. ✅ New tests added for new components
3. ✅ CLI commands work as before
4. ✅ `autoraid upgrade count` functional
5. ✅ `autoraid upgrade spend` functional
6. ✅ Region caching still works
7. ✅ Debug mode still saves artifacts

## Rollback Strategy

Each phase is a separate git commit. If issues arise:
1. Identify problematic phase
2. `git revert` the phase commit
3. Fix issues in isolation
4. Re-apply phase

## Estimated Time per Phase

- **Phase 0**: 30 minutes (setup)
- **Phase 1**: 2 hours (extract state machine + tests)
- **Phase 2**: 1.5 hours (cache service + tests)
- **Phase 3**: 1.5 hours (screenshot service + tests)
- **Phase 4**: 2 hours (locate region service + tests)
- **Phase 5**: 1 hour (window interaction service)
- **Phase 6**: 3 hours (orchestrator + integration tests)
- **Phase 7**: 2 hours (CLI simplification)
- **Phase 8**: 1.5 hours (cleanup + documentation)

**Total**: ~15 hours of focused work

## Commit Message Templates

**Phase 0**:
```
refactor: setup dependency injection infrastructure

- Add dependency-injector to dependencies
- Create container with wiring configuration
- Integrate container in CLI entry point
```

**Phase 1**:
```
refactor: extract UpgradeStateMachine from count_upgrade_fails

- Create state_machine.py with pure state logic
- Add tests with fixture images
- Wire into container as Factory provider
```

**Phase 2**:
```
refactor: extract CacheService

- Centralize all caching operations
- Move cache key generation
- Wire as Singleton provider
- Update callers to use service
```

**Phase 3**:
```
refactor: extract ScreenshotService

- Consolidate window screenshot operations
- Move take_screenshot and window_exists
- Add ROI extraction method
- Wire as Singleton provider
```

**Phase 4**:
```
refactor: extract LocateRegionService

- Unify region detection and selection
- Integrate with CacheService and ScreenshotService
- Wire as Singleton provider
```

**Phase 5**:
```
refactor: extract WindowInteractionService

- Isolate GUI clicking operations
- Wire as Singleton provider
```

**Phase 6**:
```
refactor: create UpgradeOrchestrator

- Move workflow orchestration from CLI
- Implement count_workflow and spend_workflow
- Wire as Factory provider with all dependencies
```

**Phase 7**:
```
refactor: simplify CLI with dependency injection

- Add @inject decorators to commands
- Inject UpgradeOrchestrator
- Remove business logic from CLI
```

**Phase 8**:
```
refactor: cleanup and documentation

- Remove deprecated functions
- Update CLAUDE.md with new architecture
- Clean up unused code
```
