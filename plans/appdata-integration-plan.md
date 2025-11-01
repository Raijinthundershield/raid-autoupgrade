# AppData Integration - Implementation Plan

## Overview

### Purpose
Integrate the existing `AppData` service into AutoRaid to replace hardcoded directory paths with centralized, testable configuration. This enables proper debug mode support in the GUI and establishes a single source of truth for all application directories.

### Scope
**In Scope:**
- Integration of existing `AppData` service into dependency injection container
- Replacement of all hardcoded `Path("cache-raid-autoupgrade")` references
- GUI debug mode support (replacing `debug_dir=None` pattern)
- CLI context object migration from `debug_dir` to `app_data`
- Test updates to reflect new AppData usage
- Documentation updates

**Out of Scope:**
- Changes to AppData class implementation (already well-designed)
- User-configurable cache directory locations
- Migration scripts (directory structure remains unchanged)
- New directory types beyond cache_dir and debug_dir

### Success Criteria
- ✅ All hardcoded directory paths removed from src/
- ✅ GUI workflows properly pass debug_dir when debug mode enabled
- ✅ CLI and GUI use identical AppData configuration mechanism
- ✅ All tests pass with new AppData integration
- ✅ Manual testing confirms debug artifacts created in both CLI and GUI
- ✅ Documentation reflects new centralized configuration approach

---

## Architecture & Design

### Current State Analysis

**Planned AppData Implementation** (`src/autoraid/services/app_data.py`):
```python
@dataclass(frozen=True)
class AppData:
    DEFAULT_CACHE_DIR = Path("cache-raid-autoupgrade")
    DEFAULT_DEBUG_SUBDIR = "debug"

    cache_dir: Path
    debug_enabled: bool

    @property
    def debug_dir(self) -> Path | None

    def ensure_directories(self) -> None

    def get_log_file_path(self) -> Path | None
```

**Status:** **Does not exist yet.** Will be created in Phase 0.5 with immutable dataclass, proper type hints, and directory management methods before container integration.

### Hardcoded Path Inventory

| Location | Line | Current Code | Impact |
|----------|------|--------------|--------|
| `cli/cli.py` | 30 | `Path("cache-raid-autoupgrade")` | CLI entry point |
| `cli/cli.py` | 68-71 | `debug_dir / "autoraid.log"` | Log file path |
| `workflows/debug_monitor_workflow.py` | 131 | Fallback `Path("cache-raid-autoupgrade") / "debug"` | Default debug directory |
| `gui/components/upgrade_panel.py` | 220, 339 | `debug_dir=None` | GUI workflows never pass debug_dir |
| `debug/app.py` | 10, 16 | `cache_dir: Path \| str = "cache-raid-autoupgrade"` | Debug GUI default |

### Project Structure

```
src/autoraid/
├── services/
│   └── app_data.py                              ✨ CREATE - AppData dataclass
├── container.py                                  🔧 MODIFY - Add app_data provider
├── cli/
│   ├── cli.py                                    🔧 MODIFY - Use AppData
│   ├── upgrade_cli.py                            🔧 MODIFY - Context object changes
│   └── debug_cli.py                              🔧 MODIFY - Context object changes
├── gui/
│   ├── app.py                                    🔧 MODIFY - Create container
│   └── components/
│       └── upgrade_panel.py                      🔧 MODIFY - Inject app_data
├── workflows/
│   ├── count_workflow.py                         ✅ COMPATIBLE
│   ├── spend_workflow.py                         ✅ COMPATIBLE
│   └── debug_monitor_workflow.py                 🔧 MODIFY - Remove fallback
└── debug/
    └── app.py                                    🔧 MODIFY - Use constant

test/
├── unit/
│   ├── services/
│   │   ├── test_app_data.py                      ✨ CREATE - Unit tests
│   │   └── test_upgrade_orchestrator.py          🔧 MODIFY - Update references
│   └── workflows/
│       ├── test_count_workflow.py                🔧 MODIFY - Test fixtures
│       ├── test_spend_workflow.py                🔧 MODIFY - Test fixtures
│       └── test_debug_monitor_workflow.py        🔧 MODIFY - Path assertions
└── integration/
    ├── test_cli_integration.py                   🔧 MODIFY - CLI behavior
    └── test_count_workflow_integration.py        🔧 MODIFY - debug_dir references

docs/
├── README.md                                     📝 UPDATE - Cache directory
└── CLAUDE.md                                     📝 UPDATE - Architecture

Legend:
✅ No changes needed
🔧 Modifications required
✨ New file
📝 Documentation update
```

### Design Decisions

#### 1. AppData as Singleton Provider
**Decision:** Register AppData as Singleton in DI container

**Rationale:**
- Single application configuration per run (one cache_dir, one debug state)
- Avoids confusion from multiple AppData instances with different settings
- Matches pattern of other configuration services (CacheService, NetworkManager)
- Simplifies testing with consistent configuration

**Alternative Considered:** Factory provider - rejected because per-request configuration makes no sense for application-wide directories

#### 2. CLI Context Object Migration
**Decision:** Change `ctx.obj["debug_dir"]` to `ctx.obj["app_data"].debug_dir`

**Rationale:**
- Provides access to full AppData capabilities (not just debug_dir)
- Future-proof for additional directory types (export_dir, template_dir, etc.)
- Maintains single source of truth principle
- Consistent with AppData ownership of directory configuration

**Impact:** Requires updates to upgrade_cli.py and debug_cli.py

#### 3. GUI Debug Mode Propagation
**Decision:** Create AppData in GUI app.py, inject into upgrade_panel.py

**Rationale:**
- GUI and CLI use identical configuration mechanism (DRY principle)
- Enables debug mode in GUI (currently broken with `debug_dir=None`)
- Maintains zero business logic duplication in GUI layer
- Follows existing DI pattern in GUI components

**Implementation:** AppData created from `--debug` flag in GUI launcher

#### 4. Remove Hardcoded Fallback Paths
**Decision:** Remove `Path("cache-raid-autoupgrade") / "debug"` fallback in debug_monitor_workflow.py

**Rationale:**
- Violates single source of truth principle
- Makes testing harder (hidden defaults)
- Can mask configuration errors
- AppData always available via DI, so fallback unnecessary

**Migration:** Workflows receive debug_dir via constructor injection, fail early if None when debug required

### Data Flow

#### CLI Flow (with AppData)
```
User runs: autoraid --debug gui
    ↓
cli.py creates Container with config:
    container.config.cache_dir.from_value("cache-raid-autoupgrade")
    container.config.debug.from_value(True)
    ↓
Container creates AppData (Singleton):
    AppData(cache_dir=Path("cache-raid-autoupgrade"), debug_enabled=True)
    ↓
CLI stores in context:
    ctx.obj["app_data"] = container.app_data()
    ↓
Commands access via:
    app_data = ctx.obj["app_data"]
    workflow_factory(debug_dir=app_data.debug_dir)
    ↓
Workflow receives: debug_dir = Path("cache-raid-autoupgrade/debug")
```

#### GUI Flow (with AppData)
```
User launches GUI with: autoraid --debug gui
    ↓
gui/app.py creates Container with config:
    container.config.cache_dir.from_value("cache-raid-autoupgrade")
    container.config.debug.from_value(True)
    ↓
Container creates AppData (Singleton):
    AppData(cache_dir=Path("cache-raid-autoupgrade"), debug_enabled=True)
    ↓
GUI stores in app.storage.general:
    app.storage.general["app_data"] = container.app_data()
    ↓
upgrade_panel.py injects app_data:
    @inject
    def create_panel(app_data=Provide[Container.app_data]):
        workflow_factory(debug_dir=app_data.debug_dir)
    ↓
Workflow receives: debug_dir = Path("cache-raid-autoupgrade/debug")
```

---

## Technical Approach

### Dependencies

**Existing Dependencies (no additions needed):**
- `dependency-injector`: DI container (already used)
- `pathlib`: Path handling (standard library)
- `dataclasses`: AppData implementation (standard library)

**Service Dependencies:**
```
AppData (Singleton)
    ↓ injected into
Workflows (Factory)
    ↓ use
debug_dir property
    ↓ creates
Debug artifacts in cache_dir/debug/
```

### Integration Points

#### Container Wiring
**File:** `src/autoraid/container.py`

**Changes:**
1. Add `app_data` as Singleton provider:
```python
app_data = providers.Singleton(
    AppData,
    cache_dir=config.cache_dir,
    debug_enabled=config.debug,
)
```

2. Add to wiring config:
```python
wiring_config = containers.WiringConfiguration(
    modules=[
        "autoraid.cli.cli",
        "autoraid.cli.upgrade_cli",
        "autoraid.cli.debug_cli",
        "autoraid.gui.app",
        "autoraid.gui.components.upgrade_panel",
        # ... existing modules
    ]
)
```

#### CLI Integration
**Files:** `cli/cli.py`, `cli/upgrade_cli.py`, `cli/debug_cli.py`

**Changes:**
- Remove hardcoded `Path("cache-raid-autoupgrade")`
- Store `app_data` in Click context instead of `debug_dir`
- Update logging configuration to use `app_data.get_log_file_path()`

#### GUI Integration
**Files:** `gui/app.py`, `gui/components/upgrade_panel.py`

**Changes:**
- Create and configure Container in `gui/app.py`
- Wire container modules for GUI components
- Inject `app_data` into upgrade_panel.py
- Replace `debug_dir=None` with `debug_dir=app_data.debug_dir`

#### Workflow Integration
**File:** `workflows/debug_monitor_workflow.py`

**Changes:**
- Remove hardcoded fallback `Path("cache-raid-autoupgrade") / "debug"`
- Use injected `debug_dir` parameter (via workflow factory)
- Workflows already accept `debug_dir` parameter, so minimal changes

### Error Handling

#### Directory Creation Failures
**Scenario:** Insufficient permissions to create cache/debug directories

**Handling:**
- Call `app_data.ensure_directories()` at CLI/GUI entry point
- Catch `OSError` and display user-friendly error message
- Fail fast with clear guidance (e.g., "Cannot create cache directory: permission denied")

#### Missing Debug Directory
**Scenario:** Workflow requires debug_dir but it's None

**Current State:** Hardcoded fallback masks the issue
**New Behavior:** Workflow raises `ValueError` with clear message
**Best Practice:** Validate debug_dir at workflow factory level, not in orchestrator

#### Container Configuration Errors
**Scenario:** Container initialized with invalid cache_dir

**Handling:**
- Validate cache_dir at container configuration time
- Use Path.resolve() to handle relative paths
- Log configuration details at DEBUG level for troubleshooting

---

## Implementation Strategy

### Phase Breakdown

#### Phase 0: Branch Setup
**Goal:** Create isolated feature branch
**Duration:** 2 minutes

#### Phase 0.5: Create AppData Service
**Goal:** Implement the AppData dataclass for centralized directory management
**Duration:** 30-45 minutes
**Deliverable:** Working AppData class ready for container integration

**Key Files:**
- `src/autoraid/services/app_data.py`: New file with dataclass implementation

**Key Implementation:**
- Frozen dataclass with cache_dir and debug_enabled attributes
- debug_dir property (returns cache_dir/debug or None)
- ensure_directories() method for directory creation
- get_log_file_path() method for log file path resolution

**Checkpoint:** AppData service implemented, ready for DI container integration

#### Phase 1: Container Foundation (Core Infrastructure)
**Goal:** Integrate AppData into DI container and CLI entry point
**Duration:** 45-60 minutes
**Deliverable:** Container provides AppData singleton, CLI uses app_data

**Key Files:**
- `container.py`: Add app_data provider + wiring
- `cli/cli.py`: Use AppData, update context object

**Checkpoint:** CLI can create and access AppData via container

#### Phase 2: CLI Layer Integration
**Goal:** Update CLI commands to use app_data from context
**Duration:** 30-45 minutes
**Deliverable:** All CLI commands access app_data.debug_dir

**Key Files:**
- `cli/upgrade_cli.py`: Update count/spend commands
- `cli/debug_cli.py`: Update debug commands

**Checkpoint:** CLI workflows receive correct debug_dir from app_data

#### Phase 3: Workflow Layer Cleanup
**Goal:** Remove hardcoded fallback paths from workflows
**Duration:** 30 minutes
**Deliverable:** Workflows use injected debug_dir exclusively

**Key Files:**
- `workflows/debug_monitor_workflow.py`: Remove fallback
- `debug/app.py`: Use AppData constant

**Checkpoint:** No hardcoded paths remain in workflow layer

#### Phase 4: GUI Integration
**Goal:** Enable debug mode support in GUI
**Duration:** 60-75 minutes
**Deliverable:** GUI creates container, workflows receive debug_dir

**Key Files:**
- `gui/app.py`: Create container, store app_data
- `gui/components/upgrade_panel.py`: Inject and use app_data

**Checkpoint:** GUI debug mode creates debug artifacts correctly

#### Phase 5: Testing
**Goal:** Comprehensive test coverage for AppData integration
**Duration:** 90-120 minutes
**Deliverable:** All tests pass, 80%+ coverage for new code

**Key Files:**
- Create `test/unit/services/test_app_data.py`
- Update workflow tests with new fixtures
- Update CLI integration tests

**Checkpoint:** Full test suite passes

#### Phase 6: Documentation
**Goal:** Update documentation to reflect new architecture
**Duration:** 30-45 minutes
**Deliverable:** README and CLAUDE.md updated

**Key Files:**
- `README.md`: Cache directory documentation
- `CLAUDE.md`: Architecture section updates

**Checkpoint:** Documentation accurately describes AppData integration

### Testing Approach

#### Unit Tests
**New Test File:** `test/unit/services/test_app_data.py`

**Test Coverage:**
- `test_app_data_initialization()`: Verify cache_dir and debug_enabled
- `test_debug_dir_when_enabled()`: Returns cache_dir/debug
- `test_debug_dir_when_disabled()`: Returns None
- `test_ensure_directories_creates_cache()`: Creates cache directory
- `test_ensure_directories_creates_debug()`: Creates debug when enabled
- `test_ensure_directories_idempotent()`: Safe to call multiple times
- `test_get_log_file_path_when_debug()`: Returns correct log path
- `test_get_log_file_path_when_no_debug()`: Returns None

**Target Coverage:** ≥90% for AppData class

#### Integration Tests
**Files to Update:**
- `test/integration/test_cli_integration.py`: Verify CLI context object
- `test/integration/test_count_workflow_integration.py`: Update debug_dir references

**Test Scenarios:**
- CLI with `--debug` flag creates debug directory
- CLI without `--debug` flag skips debug directory
- GUI with debug mode creates debug artifacts
- Workflows receive correct debug_dir via DI

#### Manual Testing Checklist
- [ ] CLI count workflow with `--debug` creates count/ subdirectory
- [ ] CLI spend workflow with `--debug` creates spend/ subdirectories
- [ ] GUI count workflow with debug mode creates debug artifacts
- [ ] GUI spend workflow with debug mode creates debug artifacts
- [ ] Log files written to correct location when debug enabled
- [ ] No errors when debug mode disabled

### Deployment Notes

**Backward Compatibility:**
- Directory structure unchanged (`cache-raid-autoupgrade/`)
- Existing caches remain valid (no migration needed)
- CLI flags and commands unchanged (transparent upgrade)

**Rollback Strategy:**
- Single atomic feature branch
- Revert branch if issues found in testing
- No database migrations or data transformations required

**Verification Steps:**
1. Run full test suite: `uv run pytest`
2. Manual CLI test: `uv run autoraid --debug count`
3. Manual GUI test: `uv run autoraid --debug gui`
4. Check debug artifacts created in `cache-raid-autoupgrade/debug/`
5. Verify logs written to correct location

---

## Risks & Considerations

### Technical Challenges

#### 1. Test Brittleness
**Risk:** Tests with hardcoded path expectations will break

**Mitigation:**
- Identify all hardcoded path assertions before implementation
- Update test fixtures to use AppData.DEFAULT_CACHE_DIR constant
- Use temporary directories in tests where possible
- Comprehensive test plan in Phase 5

**Likelihood:** High | **Impact:** Medium | **Priority:** High

#### 2. GUI Container Lifecycle
**Risk:** GUI creates multiple containers, causing configuration inconsistency

**Mitigation:**
- Create container once in `gui/app.py` startup
- Store container (not just app_data) in app.storage.general
- Use single container instance for all GUI components
- Document container lifecycle in GUI architecture section

**Likelihood:** Low | **Impact:** High | **Priority:** High

#### 3. Context Object Migration Errors
**Risk:** Missing updates to `ctx.obj["debug_dir"]` access patterns

**Mitigation:**
- Grep for all `ctx.obj["debug_dir"]` occurrences before implementation
- Update all access points in single phase (Phase 2)
- Test CLI integration thoroughly
- Add integration test for context object structure

**Likelihood:** Medium | **Impact:** Medium | **Priority:** High

### Performance Considerations

**Directory Creation Overhead:**
- `ensure_directories()` called at startup (one-time cost)
- Minimal impact: ~1ms for directory creation
- No performance degradation during runtime

**Singleton vs Factory:**
- Singleton provides better performance (single instance)
- No per-request configuration overhead
- Memory footprint negligible (one AppData instance)

### Security Considerations

**Path Traversal:**
- AppData uses absolute paths (Path.resolve())
- No user input for cache_dir location (hardcoded default)
- Debug artifacts stored within cache_dir (no arbitrary writes)

**Permission Issues:**
- Early validation with `ensure_directories()`
- Clear error messages for permission failures
- No privilege escalation attempts

### Technical Debt

**Addressed:**
- ✅ Removes hardcoded paths (improves maintainability)
- ✅ Enables GUI debug mode (removes feature gap)
- ✅ Centralizes configuration (reduces duplication)

**Introduced:**
- ⚠️ AppData class remains basic (no user customization)
- ⚠️ Still assumes single cache directory (not multi-profile)

**Future Enhancements:**
- User-configurable cache directory location
- Per-profile cache directories (advanced use case)
- Additional directory types (export, templates, etc.)

---

## Appendix

### File Modification Summary

| File | Changes | Lines Affected | Test Impact |
|------|---------|----------------|-------------|
| `services/app_data.py` | **NEW** - Create AppData dataclass | +30 | New test file |
| `container.py` | Add app_data provider | +10 | None |
| `cli/cli.py` | Use AppData, context object | ~15 | Integration tests |
| `cli/upgrade_cli.py` | Context object access | ~5 | Integration tests |
| `cli/debug_cli.py` | Context object access | ~3 | Integration tests |
| `gui/app.py` | Create container | +20 | Smoke tests |
| `gui/components/upgrade_panel.py` | Inject app_data | ~10 | Smoke tests |
| `workflows/debug_monitor_workflow.py` | Remove fallback | -3 | Unit tests |
| `debug/app.py` | Use constant | ~2 | None |
| **Total** | **9 files (1 new + 8 modified)** | **~95 lines** | **7 test files** |

### Testing File Summary

| Test File | New/Modified | Test Cases |
|-----------|--------------|------------|
| `test/unit/services/test_app_data.py` | NEW | 8 cases |
| `test/unit/services/test_upgrade_orchestrator.py` | MODIFY | Update fixtures |
| `test/unit/workflows/test_count_workflow.py` | MODIFY | Update fixtures |
| `test/unit/workflows/test_spend_workflow.py` | MODIFY | Update fixtures |
| `test/unit/workflows/test_debug_monitor_workflow.py` | MODIFY | Path assertions |
| `test/integration/test_cli_integration.py` | MODIFY | Context object tests |
| `test/integration/test_count_workflow_integration.py` | MODIFY | debug_dir references |
| **Total** | **1 new + 6 modified** | **~8 new + updates** |

### Grep Patterns for Verification

**Before Implementation:**
```bash
# Find all hardcoded cache paths
grep -r "cache-raid-autoupgrade" src/

# Find all debug_dir=None patterns
grep -r "debug_dir=None" src/

# Find all ctx.obj["debug_dir"] access
grep -r 'ctx.obj\["debug_dir"\]' src/
```

**After Implementation:**
```bash
# Should return 0 results in src/ (only in tests/fixtures)
grep -r "cache-raid-autoupgrade" src/

# Should return 0 results in GUI components
grep -r "debug_dir=None" src/gui/

# Should return 0 results (replaced with app_data)
grep -r 'ctx.obj\["debug_dir"\]' src/
```

### References

- **DI Container Pattern:** [dependency-injector docs](https://python-dependency-injector.ets-labs.org/)
- **Dataclass Design:** PEP 557 - Data Classes
- **Path Handling:** pathlib module documentation
- **AutoRaid Architecture:** CLAUDE.md sections on DI and service layer
