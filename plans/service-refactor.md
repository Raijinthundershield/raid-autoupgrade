# Service-Based Architecture Refactoring Plan

## Current Architecture Issues

**Problems identified**:
1. **Mixed responsibilities**: `count_upgrade_fails()` combines state machine logic, screenshot capture, caching, and debug output (273-line file)
2. **Hard to test**: Core upgrade counting requires actual Raid window and GUI interaction
3. **Tight coupling**: CLI directly orchestrates all components with business logic embedded
4. **Code duplication**: Cache key generation, screenshot→ROI patterns repeated

## Proposed Services (Simple & Focused)

Following **Constitution Principle I (Simplicity)** and **Principle II (Readability)**:

### 1. **UpgradeStateMachine** (NEW)
- **Purpose**: Pure state machine for upgrade counting logic
- **Input**: Takes ROI images (BGR numpy arrays)
- **Output**: State transitions, fail count, stop reason
- **Why**: Makes core logic testable with fixture images (no GUI needed)
- **File**: `src/autoraid/autoupgrade/state_machine.py`

### 2. **CacheService** (NEW)
- **Purpose**: Centralize all caching operations
- **Responsibility**: Window-size-based keys, get/set regions and screenshots
- **Why**: Caching logic currently scattered across 3+ functions
- **File**: `src/autoraid/services/cache_service.py`

### 3. **ScreenshotService** (NEW)
- **Purpose**: Window screenshot capture + ROI extraction
- **Why**: Consolidates interaction with pyautogui/pygetwindow
- **File**: `src/autoraid/services/screenshot_service.py`

### 4. **RegionService** (NEW)
- **Purpose**: Automatic detection + manual selection + caching
- **Consolidates**: `select_upgrade_regions()` + cache integration
- **File**: `src/autoraid/services/region_service.py`

### 5. **ClickService** (NEW)
- **Purpose**: Region clicking and window activation
- **Why**: Isolates pyautogui interaction
- **File**: `src/autoraid/services/click_service.py`

### 6. **UpgradeOrchestrator** (NEW)
- **Purpose**: Coordinates services for count/spend workflows
- **Why**: Moves business logic out of CLI
- **File**: `src/autoraid/services/upgrade_orchestrator.py`

### 7. **ProgressBarStateDetector** (KEEP AS IS)
- Already pure functions, well-tested ✅

## Phased Refactoring (Each Phase = Runnable State)

### **Phase 1: Extract State Machine** (Core Logic Testable)
**Goal**: Separate pure state machine from I/O operations

**Changes**:
- Create `UpgradeStateMachine` class in `state_machine.py`
- Extract state transition logic from `count_upgrade_fails()`
- `count_upgrade_fails()` becomes thin wrapper calling state machine
- Add comprehensive tests with fixture images

**Files modified**:
- NEW: `src/autoraid/autoupgrade/state_machine.py`
- NEW: `test/test_state_machine.py`
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py` (make it use state machine)

**Result**: State machine testable without GUI. Original code still works.

---

### **Phase 2: Extract Cache Service** (Centralized Caching)
**Goal**: One place for all caching operations

**Changes**:
- Create `CacheService` class
- Move cache key generation functions
- Move get/set operations
- Update callers: `autoupgrade.py`, `upgrade_cli.py`

**Files modified**:
- NEW: `src/autoraid/services/cache_service.py`
- NEW: `test/test_cache_service.py`
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`

**Result**: All caching through one service. No scattered cache logic.

---

### **Phase 3: Extract Screenshot Service** (Consolidated Window I/O)
**Goal**: All screenshot operations through one service

**Changes**:
- Create `ScreenshotService` class
- Move `take_screenshot_of_window()`, `window_exists()` from `interaction.py`
- Add ROI extraction method (from `visualization.py`)
- Update callers

**Files modified**:
- NEW: `src/autoraid/services/screenshot_service.py`
- NEW: `test/test_screenshot_service.py` (mock-based)
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`

**Result**: Single point for all window screenshot operations.

---

### **Phase 4: Extract Region Service** (Unified Region Management)
**Goal**: One service handles all region detection and selection

**Changes**:
- Create `RegionService` class
- Consolidate automatic detection + manual fallback
- Integrate with `CacheService`
- Move `select_upgrade_regions()`, `get_regions()` logic

**Files modified**:
- NEW: `src/autoraid/services/region_service.py`
- NEW: `test/test_region_service.py`
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`

**Result**: Region management in one place, testable.

---

### **Phase 5: Extract Click Service** (Isolated Click Operations)
**Goal**: Separate clicking from other interaction logic

**Changes**:
- Create `ClickService` class
- Move `click_region_center()` from `interaction.py`
- Add window activation logic

**Files modified**:
- NEW: `src/autoraid/services/click_service.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`

**Result**: All clicking through one service.

---

### **Phase 6: Create Orchestrator** (Business Logic Layer)
**Goal**: Coordinate all services for workflows

**Changes**:
- Create `UpgradeOrchestrator` class
- Implement `count_workflow()` and `spend_workflow()` methods
- Move orchestration logic from CLI commands
- Integrate network management, debug output coordination

**Files modified**:
- NEW: `src/autoraid/services/upgrade_orchestrator.py`
- NEW: `test/test_upgrade_orchestrator.py` (integration tests)

**Result**: Business logic separated from CLI presentation.

---

### **Phase 7: Simplify CLI** (Thin Presentation Layer)
**Goal**: CLI becomes thin wrapper calling orchestrator

**Changes**:
- Update `count()` command to call `orchestrator.count_workflow()`
- Update `spend()` command to call `orchestrator.spend_workflow()`
- Remove business logic from CLI
- CLI only handles: argument parsing, context setup, output formatting

**Files modified**:
- MODIFY: `src/autoraid/cli/upgrade_cli.py` (major simplification)

**Result**: Clean separation. CLI is thin, testable business logic in orchestrator.

---

### **Phase 8: Cleanup** (Optional Refinement)
**Goal**: Remove duplicated code, consolidate utilities

**Changes**:
- Deprecate/remove old functions in `autoupgrade.py` if no longer needed
- Update `interaction.py` (may become simpler or merge into services)
- Documentation updates

**Files modified**:
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/interaction.py`
- MODIFY: `CLAUDE.md` (architecture section)

**Result**: Clean codebase with no dead code.

---

## Testing Strategy (Constitution Principle III: Pragmatic Testing)

**MUST test**:
- ✅ `UpgradeStateMachine`: State transitions with fixture images
- ✅ `CacheService`: Key generation, get/set operations
- ✅ `RegionService`: Automatic detection fallback logic

**SHOULD test**:
- `UpgradeOrchestrator`: Integration tests with mocked services
- Error handling in services

**CAN skip** (manual testing):
- GUI interactions in `ScreenshotService`, `ClickService` (hard to automate Windows GUI)
- CLI argument parsing (simple Click decorators)

## Benefits Aligned with Constitution

✅ **Simplicity** (Principle I): Flat services, no deep hierarchies, clear single responsibilities
✅ **Readability** (Principle II): Service names describe exactly what they do
✅ **Pragmatic Testing** (Principle III): Core logic testable, GUI parts manually tested
✅ **Debug-Friendly** (Principle IV): Services can log at entry/exit, clear data flow
✅ **Incremental** (Principle V): Each phase is shippable, iterative improvement

## Estimated Lines of Code per Service

- `UpgradeStateMachine`: ~100 lines (extracted from 273-line file)
- `CacheService`: ~50 lines
- `ScreenshotService`: ~60 lines
- `RegionService`: ~80 lines
- `ClickService`: ~40 lines
- `UpgradeOrchestrator`: ~150 lines

**Total**: ~480 lines across 6 services vs. current 273 lines in one file + 360 in CLI

## Risks & Mitigation

**Risk**: Over-engineering for a one-person project
**Mitigation**: Each service is simple (<150 lines), provides clear value, improves testability

**Risk**: Breaking existing functionality
**Mitigation**: Each phase keeps code runnable, incremental refactoring, tests guard against regressions

**Risk**: More files to navigate
**Mitigation**: Clear naming convention (`*_service.py`), grouped in `services/` directory
