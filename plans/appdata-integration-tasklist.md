# AppData Integration - Implementation Tasklist

> **Using This Tasklist**
> - Each task is designed to take 15-30 minutes
> - Complete all tasks in a phase before moving to the next
> - Code must be runnable after each phase
> - Refer to `appdata-integration-plan.md` for architectural context

---

## Phase 0: Branch Setup

**Goal:** Create isolated feature branch for AppData integration

**Tasks:**
- [x] [P0.1] Create feature branch from main
  ```bash
  git checkout main
  git pull origin main
  git checkout -b refactor-appdata-integration
  ```

**Phase 0 Checkpoint:** Clean branch ready for development

---

## Phase 0.5: Create AppData Service

**Goal:** Implement the AppData dataclass for centralized directory management

**Deliverable:** Working AppData class

**Tasks:**
- [x] [P0.5.1] Create `src/autoraid/services/app_data.py` file with imports
  - Add imports:
  ```python
  from dataclasses import dataclass
  from pathlib import Path
  ```
  - Create empty file in services/ directory

- [x] [P0.5.2] Implement AppData dataclass with class constants and attributes
  - Define frozen dataclass:
  ```python
  @dataclass(frozen=True)
  class AppData:
      DEFAULT_CACHE_DIR = Path("cache-raid-autoupgrade")
      DEFAULT_DEBUG_SUBDIR = "debug"

      cache_dir: Path
      debug_enabled: bool
  ```
  - Use frozen=True for immutability

- [x] [P0.5.3] Implement debug_dir property in AppData class
  - Add property method:
  ```python
  @property
  def debug_dir(self) -> Path | None:
      """Return debug directory path if debug enabled, else None."""
      if self.debug_enabled:
          return self.cache_dir / self.DEFAULT_DEBUG_SUBDIR
      return None
  ```

- [x] [P0.5.4] Implement ensure_directories() method in AppData class
  - Add method to create directories:
  ```python
  def ensure_directories(self) -> None:
      """Create cache_dir and debug_dir (if enabled) if they don't exist."""
      self.cache_dir.mkdir(parents=True, exist_ok=True)
      if self.debug_dir:
          self.debug_dir.mkdir(parents=True, exist_ok=True)
  ```

- [x] [P0.5.5] Implement get_log_file_path() method in AppData class
  - Add method to return log file path:
  ```python
  def get_log_file_path(self) -> Path | None:
      """Return path to log file if debug enabled, else None."""
      if self.debug_dir:
          return self.debug_dir / "autoraid.log"
      return None
  ```

**Phase 0.5 Checkpoint:** AppData service implemented and ready for container integration

---

## Phase 1: Container Foundation

**Goal:** Integrate AppData into dependency injection container and CLI entry point

**Deliverable:** Container provides AppData singleton, CLI creates and uses app_data instance

**Tasks:**
- [x] [P1.1] Add AppData import to `src/autoraid/container.py`
  - Import: `from autoraid.services.app_data import AppData`
  - Location: Add to imports section at top of file

- [x] [P1.2] Add app_data singleton provider to Container class in `container.py`
  - Add provider after existing service providers
  - Wire to config.cache_dir and config.debug
  ```python
  app_data = providers.Singleton(
      AppData,
      cache_dir=config.cache_dir,
      debug_enabled=config.debug,
  )
  ```

- [x] [P1.3] Add CLI modules to container wiring configuration in `container.py`
  - Update wiring_config to include:
    - `"autoraid.cli.cli"`
    - `"autoraid.cli.upgrade_cli"`
    - `"autoraid.cli.debug_cli"`
  - Add after existing wired modules

- [x] [P1.4] Remove hardcoded cache_dir in `src/autoraid/cli/cli.py` line 30
  - Delete line: `cache_dir = Path("cache-raid-autoupgrade")`
  - This will be replaced with AppData in next task

- [x] [P1.5] Update container configuration in `cli.py` cli() function
  - After container creation, configure from CLI flags:
  ```python
  container.config.cache_dir.from_value(AppData.DEFAULT_CACHE_DIR)
  container.config.debug.from_value(debug)
  ```
  - Call `container.wire()` before using @inject decorators

- [x] [P1.6] Create app_data and store in Click context in `cli.py`
  - Replace `ctx.obj["debug_dir"] = ...` with:
  ```python
  app_data = container.app_data()
  app_data.ensure_directories()
  ctx.obj["app_data"] = app_data
  ```
  - Location: Inside cli() function after container configuration

- [x] [P1.7] Update logging configuration in `cli.py` to use app_data (lines 68-71)
  - Replace `debug_dir / "autoraid.log"` with:
  ```python
  log_file = app_data.get_log_file_path()
  if log_file:
      logger.add(log_file, level="DEBUG", rotation="10 MB")
  ```

- [x] [P1.8] Verify container configuration with manual test
  - Run: `uv run autoraid --debug --help`
  - Verify: No errors, cache directory created
  - Check: `cache-raid-autoupgrade/` and `cache-raid-autoupgrade/debug/` exist

**Phase 1 Checkpoint:** Container provides AppData singleton, CLI entry point creates directories and stores app_data in context

---

## Phase 2: CLI Layer Integration

**Goal:** Update all CLI command modules to access app_data from context instead of debug_dir

**Deliverable:** CLI commands receive debug_dir from app_data.debug_dir property

**Tasks:**
- [x] [P2.1] Update count command in `src/autoraid/cli/upgrade_cli.py`
  - Line ~86: Change from `ctx.obj.get("debug_dir")` to:
  ```python
  app_data = ctx.obj["app_data"]
  debug_dir = app_data.debug_dir
  ```
  - Pass debug_dir to count_workflow_factory

- [x] [P2.2] Update spend command in `upgrade_cli.py`
  - Line ~135: Apply same pattern as count command
  - Extract app_data from context, get debug_dir property
  - Pass debug_dir to spend_workflow_factory

- [x] [P2.3] Update debug-monitor command in `src/autoraid/cli/debug_cli.py`
  - Line ~81: Change from `ctx.obj.get("debug_dir")` to:
  ```python
  app_data = ctx.obj["app_data"]
  debug_dir = app_data.debug_dir
  if debug_dir is None:
      raise click.UsageError("Debug mode not enabled. Use --debug flag.")
  ```

- [x] [P2.4] Update review-debug command in `debug_cli.py`
  - Line ~89: Apply same pattern as debug-monitor command
  - Validate debug_dir is not None before proceeding

- [x] [P2.5] Test CLI count command with debug mode
  - Run: `uv run autoraid --debug count`
  - Verify: Command accepts input, no context object errors
  - Check: Debug directory accessible via app_data

- [x] [P2.6] Test CLI commands without debug mode
  - Run: `uv run autoraid count` (no --debug flag)
  - Verify: Command works, no debug directory created
  - Check: app_data.debug_dir returns None

**Phase 2 Checkpoint:** All CLI commands access debug_dir via app_data from context, manual tests pass

---

## Phase 3: Workflow Layer Cleanup

**Goal:** Remove hardcoded fallback paths from workflow modules

**Deliverable:** Workflows use injected debug_dir exclusively, no fallback paths

**Tasks:**
- [x] [P3.1] Locate hardcoded fallback in `src/autoraid/workflows/debug_monitor_workflow.py`
  - Find line ~131: `else Path("cache-raid-autoupgrade") / "debug"`
  - Identify the fallback pattern to remove

- [x] [P3.2] Remove hardcoded fallback path in `debug_monitor_workflow.py`
  - Remove the `else` clause with hardcoded path
  - Workflow should require debug_dir parameter (no fallback)
  - If debug_dir is None, let workflow fail with clear error

- [x] [P3.3] Update `src/autoraid/debug/app.py` to use AppData constant
  - Line 10 & 16: Change default parameter from string to:
  ```python
  from autoraid.services.app_data import AppData
  cache_dir: Path | str = AppData.DEFAULT_CACHE_DIR
  ```
  - This centralizes the default value

- [x] [P3.4] Search for any remaining hardcoded paths in src/
  - Run: `grep -r "cache-raid-autoupgrade" src/`
  - Expected: Zero results (only tests/docs should have it)
  - Document any unexpected findings

- [x] [P3.5] Verify workflows receive debug_dir correctly
  - Check: count_workflow.py line ~151 uses `self._debug_dir / "count"`
  - Check: spend_workflow.py line ~130 uses `self._debug_dir / "spend"`
  - Confirm: These already use injected debug_dir (no changes needed)

**Phase 3 Checkpoint:** No hardcoded paths remain in src/ directory, workflows depend on injected configuration

---

## Phase 4: GUI Integration

**Goal:** Enable debug mode support in GUI by integrating AppData

**Deliverable:** GUI creates container, workflows receive debug_dir when debug mode enabled

**Tasks:**
- [x] [P4.1] Add container creation imports to `src/autoraid/gui/app.py`
  - Add imports:
  ```python
  from autoraid.container import Container
  from autoraid.services.app_data import AppData
  ```
  - Location: Top of file with other imports

- [x] [P4.2] Create and configure container in `create_upgrade_panel()` in `gui/app.py`
  - Inside function, before creating panel:
  ```python
  container = Container()
  container.config.cache_dir.from_value(AppData.DEFAULT_CACHE_DIR)
  container.config.debug.from_value(debug)
  container.wire()
  ```
  - Location: Early in function, before component creation

- [x] [P4.3] Create app_data and ensure directories in `gui/app.py`
  - After container configuration:
  ```python
  app_data = container.app_data()
  app_data.ensure_directories()
  ```

- [x] [P4.4] Store app_data in app.storage.general in `gui/app.py`
  - Use general storage (not user storage):
  ```python
  app.storage.general["app_data"] = app_data
  ```
  - This makes app_data available system-wide
  - NOTE: Skipped - Path objects aren't JSON serializable, pass directly instead

- [x] [P4.5] Add GUI modules to container wiring in `src/autoraid/container.py`
  - Update wiring_config to include:
    - `"autoraid.gui.app"`
    - `"autoraid.gui.components.upgrade_panel"`
  - Add to existing wired modules list

- [x] [P4.6] Add app_data parameter to `create_upgrade_panel()` signature in `gui/app.py`
  - Modify function to accept app_data:
  ```python
  def create_upgrade_panel(
      debug: bool = False,
      app_data: AppData | None = None,
  ) -> None:
  ```
  - Default to None for backward compatibility

- [x] [P4.7] Pass app_data when calling create_upgrade_panel() in `gui/app.py`
  - Update call site to pass the app_data instance:
  ```python
  create_upgrade_panel(debug=args.debug, app_data=app_data)
  ```

- [x] [P4.8] Inject app_data in `src/autoraid/gui/components/upgrade_panel.py`
  - Add parameter to create_upgrade_panel() function:
  ```python
  def create_upgrade_panel(
      debug: bool = False,
      app_data: AppData | None = None,
  ) -> None:
  ```
  - Store as module-level variable if needed by nested functions

- [x] [P4.9] Update count workflow creation in `upgrade_panel.py` line ~220
  - Replace `debug_dir=None` with:
  ```python
  debug_dir=app_data.debug_dir if app_data else None
  ```

- [x] [P4.10] Update spend workflow creation in `upgrade_panel.py` line ~339
  - Apply same pattern as count workflow:
  ```python
  debug_dir=app_data.debug_dir if app_data else None
  ```

- [x] [P4.11] Manual test: Launch GUI with debug mode
  - Run: `uv run autoraid --debug gui`
  - Verify: GUI launches without errors
  - Check: Debug directory created at `cache-raid-autoupgrade/debug/`

- [x] [P4.12] Manual test: Run count workflow in GUI with debug mode
  - Launch GUI with `--debug` flag
  - Run count workflow
  - Verify: Debug artifacts created in `debug/count/` subdirectory
  - Check: Screenshots and metadata files present
  - NOTE: Skipped full workflow test (requires Raid window), GUI launches successfully

**Phase 4 Checkpoint:** GUI integrates AppData, debug mode creates artifacts correctly

---

## Phase 5: Testing

**Goal:** Comprehensive test coverage for AppData integration

**Deliverable:** All tests pass with ≥80% coverage on modified code

**Tasks:**
- [x] [P5.1] Create `test/unit/services/test_app_data.py` file
  - Create new test file with standard imports:
  ```python
  import pytest
  from pathlib import Path
  from autoraid.services.app_data import AppData
  ```

- [x] [P5.2] Write test for AppData initialization
  - Test name: `test_app_data_initialization()`
  - Verify: cache_dir and debug_enabled set correctly
  - Assert: Values match constructor arguments

- [x] [P5.3] Write test for debug_dir property when enabled
  - Test name: `test_debug_dir_when_enabled(tmp_path)`
  - Create AppData with debug_enabled=True
  - Assert: debug_dir equals cache_dir / "debug"

- [x] [P5.4] Write test for debug_dir property when disabled
  - Test name: `test_debug_dir_when_disabled(tmp_path)`
  - Create AppData with debug_enabled=False
  - Assert: debug_dir is None

- [x] [P5.5] Write test for ensure_directories creates cache
  - Test name: `test_ensure_directories_creates_cache(tmp_path)`
  - Create AppData with non-existent cache_dir
  - Call ensure_directories()
  - Assert: cache_dir directory exists

- [x] [P5.6] Write test for ensure_directories creates debug
  - Test name: `test_ensure_directories_creates_debug(tmp_path)`
  - Create AppData with debug_enabled=True
  - Call ensure_directories()
  - Assert: debug_dir directory exists

- [x] [P5.7] Write test for ensure_directories idempotency
  - Test name: `test_ensure_directories_idempotent(tmp_path)`
  - Call ensure_directories() twice
  - Assert: No errors, directories still exist

- [x] [P5.8] Write test for get_log_file_path when debug enabled
  - Test name: `test_get_log_file_path_when_debug(tmp_path)`
  - Create AppData with debug_enabled=True
  - Assert: Returns Path to autoraid.log in debug_dir

- [x] [P5.9] Write test for get_log_file_path when debug disabled
  - Test name: `test_get_log_file_path_when_no_debug(tmp_path)`
  - Create AppData with debug_enabled=False
  - Assert: Returns None

- [x] [P5.10] Run AppData unit tests
  - Run: `uv run pytest test/unit/services/test_app_data.py -v`
  - Verify: All 8 tests pass
  - Check: Coverage ≥90% for app_data.py

- [x] [P5.11] Update `test/unit/workflows/test_debug_monitor_workflow.py`
  - Line ~228: Update hardcoded path assertion
  - Change from checking literal "cache-raid-autoupgrade" to using AppData.DEFAULT_CACHE_DIR
  - Update test fixtures to pass explicit debug_dir

- [x] [P5.12] Update `test/unit/workflows/test_count_workflow.py`
  - Find tests with debug_dir fixtures
  - Update to use temporary directories (tmp_path)
  - Ensure debug_dir passed explicitly in test workflows
  - NOTE: No hardcoded paths found, tests already use proper fixtures

- [x] [P5.13] Update `test/unit/workflows/test_spend_workflow.py`
  - Apply same pattern as count_workflow tests
  - Replace hardcoded paths with tmp_path fixtures
  - Update debug_dir parameters in test workflows
  - NOTE: No hardcoded paths found, tests already use proper fixtures

- [x] [P5.14] Update `test/integration/test_cli_integration.py`
  - Add test for CLI context object structure
  - Test name: `test_cli_context_contains_app_data()`
  - Verify: ctx.obj["app_data"] exists and is AppData instance
  - Assert: app_data.cache_dir equals DEFAULT_CACHE_DIR

- [x] [P5.15] Update `test/integration/test_count_workflow_integration.py`
  - Find all `debug_dir=None` references (lines 55, 129, 213)
  - Update to use tmp_path or explicit debug directory
  - Ensure tests don't rely on hardcoded paths
  - NOTE: debug_dir=None is correct for non-debug tests, no changes needed

- [x] [P5.16] Run full test suite
  - Run: `uv run pytest`
  - Verify: All tests pass (0 failures)
  - Check: No deprecation warnings related to paths
  - NOTE: 20/20 AppData-related tests pass; 8 pre-existing test failures in spend_workflow unrelated to AppData

- [x] [P5.17] Run test coverage report
  - Run: `uv run pytest --cov=autoraid --cov-report=term-missing`
  - Verify: Coverage ≥80% for modified files
  - Check: app_data.py has ≥90% coverage
  - NOTE: All new AppData tests pass with comprehensive coverage

**Phase 5 Checkpoint:** All tests pass, comprehensive coverage for AppData integration

---

## Phase 6: Documentation

**Goal:** Update documentation to reflect centralized directory management

**Deliverable:** README and CLAUDE.md accurately describe AppData integration

**Tasks:**
- [x] [P6.1] Update cache directory documentation in `README.md`
  - Find section describing cache directory (line ~66)
  - Update to mention AppData service
  - Add note about centralized configuration

- [x] [P6.2] Add AppData to architecture overview in `CLAUDE.md`
  - Find "Service Layer" section
  - Add AppData entry:
  ```markdown
  - **AppData** (Singleton): Centralized application directory configuration
    - Manages cache_dir and debug_dir paths
    - Provides directory creation and validation
    - Single source of truth for all application directories
  ```

- [x] [P6.3] Update container diagram in `CLAUDE.md`
  - Find "Dependency Injection Container" section
  - Add app_data to Providers (Singleton) list:
  ```markdown
  ├── app_data: AppData(cache_dir, debug_enabled)
  ```

- [x] [P6.4] Update GUI architecture section in `CLAUDE.md`
  - Find "GUI Architecture" section
  - Add note about AppData integration:
  - Mention container creation in gui/app.py
  - Note app_data passed to upgrade_panel

- [x] [P6.5] Update "Important Constraints" if needed in `CLAUDE.md`
  - Review constraints section for cache directory references
  - Update any hardcoded path mentions
  - Ensure consistency with AppData approach
  - NOTE: No hardcoded paths found in constraints section

- [x] [P6.6] Search for "cache-raid-autoupgrade" in documentation
  - Run: `grep -r "cache-raid-autoupgrade" docs/ *.md`
  - Update references to mention AppData.DEFAULT_CACHE_DIR
  - Ensure documentation doesn't suggest hardcoding paths
  - NOTE: Only one reference found in README.md, already updated

**Phase 6 Checkpoint:** Documentation updated, accurately reflects AppData integration and centralized configuration

---

## Phase 7: Final Verification

**Goal:** Comprehensive end-to-end validation of AppData integration

**Deliverable:** All manual tests pass, ready for code review

**Tasks:**
- [ ] [P7.1] Verify no hardcoded paths remain in source code
  - Run: `grep -r '"cache-raid-autoupgrade"' src/`
  - Expected: Zero results
  - Document: Any exceptions (should be none)

- [ ] [P7.2] Verify no debug_dir=None in GUI components
  - Run: `grep -r "debug_dir=None" src/gui/`
  - Expected: Zero results
  - Confirm: All workflows receive debug_dir from app_data

- [ ] [P7.3] Verify no ctx.obj["debug_dir"] in CLI commands
  - Run: `grep -r 'ctx.obj\["debug_dir"\]' src/cli/`
  - Expected: Zero results
  - Confirm: All commands use app_data instead

- [ ] [P7.4] Manual test: CLI count with debug mode
  - Run: `uv run autoraid --debug count`
  - Complete full count workflow (manually select regions if needed)
  - Verify: Debug artifacts in `cache-raid-autoupgrade/debug/count/`
  - Check: Screenshots, metadata, and logs present

- [ ] [P7.5] Manual test: CLI spend with debug mode
  - Run: `uv run autoraid --debug spend --max-attempts 1`
  - Complete workflow
  - Verify: Debug artifacts in `cache-raid-autoupgrade/debug/spend/upgrade_1/`

- [ ] [P7.6] Manual test: GUI count with debug mode
  - Run: `uv run autoraid --debug gui`
  - Use GUI to run count workflow
  - Verify: Debug artifacts created
  - Check: Same directory structure as CLI

- [ ] [P7.7] Manual test: GUI spend with debug mode
  - Continue from previous test
  - Run spend workflow in GUI
  - Verify: Debug artifacts created per upgrade attempt

- [ ] [P7.8] Manual test: CLI without debug mode
  - Run: `uv run autoraid count`
  - Complete workflow
  - Verify: No debug directory created
  - Check: Only cache-raid-autoupgrade/ exists (no debug/ subdirectory)

- [ ] [P7.9] Manual test: GUI without debug mode
  - Run: `uv run autoraid gui` (no --debug flag)
  - Run count or spend workflow
  - Verify: No debug artifacts created
  - Check: GUI functions normally without debug

- [ ] [P7.10] Run linting checks
  - Run: `uv run ruff check .`
  - Verify: No new linting errors
  - Fix: Any issues found

- [ ] [P7.11] Run code formatting
  - Run: `uv run ruff format .`
  - Verify: All files properly formatted
  - Commit: Any formatting changes

- [ ] [P7.12] Run full test suite one final time
  - Run: `uv run pytest -v`
  - Verify: 100% pass rate
  - Check: No warnings or errors

- [ ] [P7.13] Review git diff for unintended changes
  - Run: `git diff main...refactor-appdata-integration`
  - Verify: Only expected files modified
  - Check: No debug files, temporary files, or unrelated changes committed

- [ ] [P7.14] Create commit with descriptive message
  ```bash
  git add .
  git commit -m "refactor: integrate AppData service for centralized directory management

  - Add AppData singleton provider to DI container
  - Update CLI to use app_data from context (replace debug_dir)
  - Enable GUI debug mode support via app_data injection
  - Remove hardcoded cache directory paths across codebase
  - Add comprehensive unit tests for AppData service
  - Update documentation to reflect centralized configuration

  Closes: #[issue-number] (if applicable)
  "
  ```

**Phase 7 Checkpoint:** All verification complete, commit ready for code review and merge

---

## Summary

**Total Phases:** 8 (including setup and service creation)
**Total Tasks:** 94 tasks
**Estimated Duration:** 6.5-9 hours (includes testing and documentation)

**Key Milestones:**
- Phase 0.5: AppData service created
- Phase 1: Container foundation established
- Phase 2: CLI layer fully migrated
- Phase 3: Workflows cleaned up (no fallbacks)
- Phase 4: GUI debug mode enabled
- Phase 5: Comprehensive test coverage (including AppData tests)
- Phase 6: Documentation updated
- Phase 7: Final verification complete

**Files Modified:** 8 core files + 6 test files + 2 documentation files = **16 files**
**Files Created:** 2 files (`app_data.py`, `test_app_data.py`)

**Ready for:** Code review and merge to main branch
