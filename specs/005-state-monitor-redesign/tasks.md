# Tasks: State Monitor Redesign

**Input**: Design documents from `/specs/005-state-monitor-redesign/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, quickstart.md

**Tests**: Tests are included for this feature as smoke tests to achieve ≥90% coverage requirement (SC-005).

**Organization**: This is a refactoring task organized by implementation phases to ensure runnable state after each phase.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Not applicable for this refactoring - organized by phase instead
- Include exact file paths in descriptions

## Path Conventions
- Single project structure: `src/autoraid/`, `test/` at repository root
- Test fixtures: `test/fixtures/images/`

---

## Phase 1: Create New Enums and Base Classes

**Purpose**: Add new enums and classes alongside existing code without breaking anything

**Runnable State After Phase**: Project compiles, all existing tests pass, new classes instantiable but unused

### Tasks

- [X] T001 Add ProgressBarState enum to src/autoraid/core/state_machine.py
- [X] T002 Rename StopCountReason to StopReason in src/autoraid/core/state_machine.py (keep alias StopCountReason = StopReason)
- [X] T003 Create src/autoraid/core/progress_bar_detector.py with ProgressBarStateDetector class and detect_state() method
- [X] T004 Implement input validation in ProgressBarStateDetector.detect_state() (raise ValueError for None/empty/invalid images)
- [X] T005 Implement state mapping in ProgressBarStateDetector.detect_state() (wrap existing progress_bar.get_progress_bar_state() function)
- [X] T006 Add DEBUG logging for UNKNOWN states in ProgressBarStateDetector
- [X] T007 Add UpgradeAttemptMonitor class to src/autoraid/core/state_machine.py with __init__(detector, max_attempts)
- [X] T008 Implement process_frame() method in UpgradeAttemptMonitor (calls detector, updates state)
- [X] T009 Implement fail counting logic in UpgradeAttemptMonitor (count transitions from non-FAIL to FAIL)
- [X] T010 Implement fail_count property in UpgradeAttemptMonitor (read-only)
- [X] T011 Implement stop_reason property in UpgradeAttemptMonitor (computed, checks all stop conditions)
- [X] T012 Implement current_state property in UpgradeAttemptMonitor (returns last state or None)
- [X] T013 Add DEBUG logging for state transitions in UpgradeAttemptMonitor.process_frame()
- [X] T014 Add DEBUG logging for stop conditions in UpgradeAttemptMonitor.stop_reason property
- [X] T015 Add validation for max_attempts > 0 in UpgradeAttemptMonitor.__init__()

**Verification Commands**:
```bash
# Smoke test: Import new classes
python -c "from autoraid.core.progress_bar_detector import ProgressBarStateDetector; print('Detector OK')"
python -c "from autoraid.core.state_machine import UpgradeAttemptMonitor, ProgressBarState, StopReason; print('Monitor OK')"

# Run existing tests (should all pass)
uv run pytest
```

**Checkpoint**: New classes exist, old UpgradeStateMachine untouched, all existing tests pass

---

## Phase 2: Update Dependency Injection Container

**Purpose**: Wire new classes into DI container without affecting workflows

**Runnable State After Phase**: Container builds successfully, new providers available, old providers still work

### Tasks

- [X] T016 Add progress_bar_detector Singleton provider to src/autoraid/container.py
- [X] T017 Add upgrade_attempt_monitor Factory provider to src/autoraid/container.py (injects detector)

**Verification Commands**:
```bash
# Smoke test: Get providers from container
python -c "from autoraid.container import Container; c = Container(); d = c.progress_bar_detector(); print('Detector provider OK')"
python -c "from autoraid.container import Container; c = Container(); m = c.upgrade_attempt_monitor(max_attempts=10); print('Monitor provider OK')"

# Run existing tests (should all pass)
uv run pytest
```

**Checkpoint**: DI container has new providers, old state_machine_provider coexists, all existing tests pass

---

## Phase 3: Write Tests for New Classes

**Purpose**: Achieve ≥90% coverage for detector and monitor before integration

**Runnable State After Phase**: New classes thoroughly tested, old implementation still in use

### Tasks: Detector Tests

- [X] T018 [P] Create test/unit/core/test_progress_bar_detector.py
- [X] T019 [P] Write test_detect_state_fail() using test/fixtures/images/fail_state.png
- [X] T020 [P] Write test_detect_state_progress() using test/fixtures/images/progress_state.png
- [X] T021 [P] Write test_detect_state_standby() using test/fixtures/images/standby_state.png
- [X] T022 [P] Write test_detect_state_connection_error() using test/fixtures/images/connection_error_state.png
- [X] T023 [P] Write test_detect_state_is_stateless() (verify same image returns same state 100 times)
- [X] T024 [P] Write test_detect_state_raises_on_none_image() (verify ValueError)
- [X] T025 [P] Write test_detect_state_raises_on_empty_image() (verify ValueError)
- [X] T026 [P] Write test_detect_state_raises_on_invalid_shape() (verify ValueError)

### Tasks: Monitor Tests

- [X] T027 [P] Create test/unit/core/test_upgrade_attempt_monitor.py
- [X] T028 [P] Write test_monitor_counts_fail_transitions() with mocked detector
- [X] T029 [P] Write test_monitor_ignores_consecutive_fails() with mocked detector
- [X] T030 [P] Write test_monitor_stops_on_max_attempts() (verify MAX_ATTEMPTS_REACHED)
- [X] T031 [P] Write test_monitor_stops_on_success() (verify SUCCESS after 4 STANDBY)
- [X] T032 [P] Write test_monitor_stops_on_connection_error() (verify CONNECTION_ERROR after 4 errors)
- [X] T033 [P] Write test_monitor_does_not_stop_early() (verify 3 STANDBY continues)
- [X] T034 [P] Write test_monitor_tracks_current_state() (verify current_state property)
- [X] T035 [P] Write test_monitor_validates_max_attempts() (verify ValueError for max_attempts <= 0)
- [X] T036 [P] Write test_monitor_fail_count_property_readonly() (verify property returns int)

### Tasks: Coverage Verification

- [X] T037 Run pytest --cov=autoraid.core.progress_bar_detector --cov-report=term-missing and verify ≥90%
- [X] T038 Run pytest --cov=autoraid.core.state_machine --cov-report=term-missing (UpgradeAttemptMonitor only) and verify ≥90%

**Verification Commands**:
```bash
# Run detector tests
uv run pytest test/unit/core/test_progress_bar_detector.py -v

# Run monitor tests
uv run pytest test/unit/core/test_upgrade_attempt_monitor.py -v

# Check coverage
uv run pytest --cov=autoraid.core.progress_bar_detector --cov=autoraid.core.state_machine --cov-report=term-missing test/unit/core/test_progress_bar_detector.py test/unit/core/test_upgrade_attempt_monitor.py

# All existing tests still pass
uv run pytest
```

**Checkpoint**: New classes have ≥90% coverage, all tests pass (new + existing)

---

## Phase 4: Integrate New Classes into Workflows

**Purpose**: Replace old UpgradeStateMachine with new monitor API in orchestrator

**Runnable State After Phase**: Workflows use new API, behavior identical, integration tests pass

### Tasks: Update Orchestrator

- [X] T039 Update UpgradeOrchestrator.__init__() in src/autoraid/services/upgrade_orchestrator.py (replace state_machine_provider with upgrade_attempt_monitor)
- [X] T040 Update UpgradeOrchestrator._count_upgrade_fails() to use monitor API (replace tuple unpacking with property access)
- [X] T041 Update loop condition in _count_upgrade_fails() to check monitor.stop_reason property
- [X] T042 Update fail count access in _count_upgrade_fails() to use monitor.fail_count property
- [X] T043 Update imports in src/autoraid/services/upgrade_orchestrator.py (use StopReason instead of StopCountReason)
- [X] T044 Update container wiring in src/autoraid/cli/cli.py (pass upgrade_attempt_monitor to orchestrator)

### Tasks: Update Integration Tests

- [X] T045 Update test/integration/test_upgrade_orchestrator.py to use new monitor API
- [X] T046 Add behavior parity test in test/integration/test_upgrade_orchestrator.py (verify same results as old implementation)

**Verification Commands**:
```bash
# Run integration tests
uv run pytest test/integration/test_upgrade_orchestrator.py -v

# Run full test suite
uv run pytest

# Manual CLI smoke test
uv run autoraid --help
uv run autoraid upgrade count --help
```

**Checkpoint**: Workflows use new API exclusively, all tests pass, CLI commands work

---

## Phase 5: Manual Workflow Testing

**Purpose**: Verify Count and Spend workflows in both CLI and GUI

**Runnable State After Phase**: Workflows verified to work identically to before refactoring

### Tasks

- [X] T047 Manual test: Run Count workflow in CLI with --debug flag (verify DEBUG logging)
- [X] T048 Manual test: Run Spend workflow in CLI (verify behavior unchanged)
- [X] T049 Manual test: Run Count workflow in GUI (verify UI updates correctly)
- [X] T050 Manual test: Run Spend workflow in GUI (verify UI updates correctly)
- [X] T051 Verify all success criteria SC-001 through SC-007 met per plan.md

**Verification Commands**:
```bash
# CLI manual tests (requires Raid game running)
uv run autoraid upgrade count --debug

# GUI manual test
uv run autoraid gui
# Then click Count workflow button

# Success criteria verification
# SC-001: Detector tested independently with fixture images ✓ (Phase 3)
# SC-002: Monitor tested independently with mocked detector ✓ (Phase 3)
# SC-003: 100% repeatability verified ✓ (T023)
# SC-004: Zero functional changes ✓ (T046 + manual tests)
# SC-005: ≥90% test coverage ✓ (T037, T038)
# SC-006: Detector changes isolated ✓ (architecture review)
# SC-007: Monitor changes isolated ✓ (architecture review)
```

**Checkpoint**: Manual verification complete, all workflows work identically

---

## Phase 6: Clean Up Old Code

**Purpose**: Remove deprecated UpgradeStateMachine class and old provider

**Runnable State After Phase**: Old code removed, tests updated, all tests pass

### Tasks: Remove Old Implementation

- [X] T052 Remove UpgradeStateMachine class from src/autoraid/core/state_machine.py
- [X] T053 Remove StopCountReason alias from src/autoraid/core/state_machine.py
- [X] T054 Remove state_machine_provider from src/autoraid/container.py
- [X] T055 Remove old state machine tests from test/unit/core/test_state_machine.py (keep enum tests if any)
- [X] T056 Remove behavior parity test from test/integration/test_upgrade_orchestrator.py (no longer needed)

### Tasks: Verify Cleanup

- [X] T057 Run grep -r "UpgradeStateMachine" src/autoraid/ and verify no matches
- [X] T058 Run grep -r "StopCountReason" src/autoraid/ and verify no matches
- [X] T059 Run grep -r "state_machine_provider" src/autoraid/ and verify no matches

**Verification Commands**:
```bash
# Check for old references
grep -r "UpgradeStateMachine" src/autoraid/
grep -r "StopCountReason" src/autoraid/
grep -r "state_machine_provider" src/autoraid/

# Run all tests
uv run pytest

# Lint check
uv run ruff check .

# Format check
uv run ruff format --check .
```

**Checkpoint**: Old implementation removed, no references remain, all tests pass

---

## Phase 7: Update Documentation

**Purpose**: Update CLAUDE.md to reflect new architecture

**Runnable State After Phase**: Documentation accurate and complete

### Tasks

- [X] T060 [P] Update "Core Components" section in CLAUDE.md (add ProgressBarStateDetector description)
- [X] T061 [P] Update "Core Components" section in CLAUDE.md (add UpgradeAttemptMonitor description)
- [X] T062 [P] Remove UpgradeStateMachine reference from CLAUDE.md
- [X] T063 [P] Update "Service Responsibilities" table in CLAUDE.md (add detector and monitor rows)
- [X] T064 Update "Dependency Injection Container" diagram in CLAUDE.md (show detector singleton and monitor factory)
- [X] T065 Update "Testing" section in CLAUDE.md (add detector and monitor testing examples)

**Verification Commands**:
```bash
# Verify documentation accuracy
cat CLAUDE.md | grep -A5 "ProgressBarStateDetector"
cat CLAUDE.md | grep -A5 "UpgradeAttemptMonitor"
cat CLAUDE.md | grep "UpgradeStateMachine"  # Should return nothing

# Lint and format
uv run ruff check .
uv run ruff format .

# Final test run
uv run pytest
```

**Checkpoint**: Documentation updated and accurate

---

## Phase 8: Final Verification and Code Quality

**Purpose**: Run all quality checks and verify constitutional compliance

**Runnable State After Phase**: Feature complete, all checks pass, ready to merge

### Tasks

- [ ] T066 Run uv run ruff check . and verify no warnings
- [ ] T067 Run uv run ruff format . and verify no changes needed
- [ ] T068 Run uv run pytest --cov=autoraid.core --cov-report=term-missing and verify ≥90% core coverage
- [ ] T069 Run uv run pre-commit run --all-files and verify all hooks pass
- [ ] T070 Verify Constitution Principle I: Simplicity (2 focused classes, 0 inheritance levels) ✓
- [ ] T071 Verify Constitution Principle II: DRY & Separation (CV=detector, Logic=monitor) ✓
- [ ] T072 Verify Constitution Principle III: Readability (clear names, type hints, properties) ✓
- [ ] T073 Verify Constitution Principle IV: Pragmatic Testing (90% coverage achieved) ✓
- [ ] T074 Verify Constitution Principle V: Debug-Friendly (DEBUG logging added) ✓
- [ ] T075 Verify Constitution Principle VI: Incremental Improvement (atomic replacement) ✓

**Verification Commands**:
```bash
# Code quality checks
uv run ruff check .
uv run ruff format .
uv run pytest --cov=autoraid.core --cov-report=term-missing
uv run pre-commit run --all-files

# Final smoke tests
uv run autoraid --help
uv run autoraid gui

# Test counts
uv run pytest --collect-only | grep "test session starts"
```

**Checkpoint**: All checks pass, feature complete and ready to merge

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Create Classes)**: No dependencies - can start immediately
- **Phase 2 (DI Container)**: Depends on Phase 1 completion
- **Phase 3 (Write Tests)**: Depends on Phases 1-2 completion (classes must exist to test)
- **Phase 4 (Integration)**: Depends on Phases 1-3 completion (tests gate integration)
- **Phase 5 (Manual Testing)**: Depends on Phase 4 completion (workflows must be integrated)
- **Phase 6 (Cleanup)**: Depends on Phase 5 completion (manual verification gates deletion)
- **Phase 7 (Documentation)**: Can start after Phase 4, but should complete after Phase 6
- **Phase 8 (Final Verification)**: Depends on all previous phases

### Task Dependencies Within Phases

**Phase 1 (Sequential implementation)**:
- T001-T002: Enums first (required by other classes)
- T003-T006: Detector implementation
- T007-T015: Monitor implementation (depends on T001-T006 for ProgressBarState enum)

**Phase 2 (Sequential)**:
- T016: Detector provider first
- T017: Monitor provider second (depends on detector provider)

**Phase 3 (Highly parallel)**:
- T018-T026: Detector tests (can all run in parallel after T018 creates file)
- T027-T036: Monitor tests (can all run in parallel after T027 creates file)
- T037-T038: Coverage checks (depends on all tests written)

**Phase 4 (Sequential updates)**:
- T039-T043: Orchestrator updates (sequential)
- T044: Container wiring update
- T045-T046: Integration tests (depends on T039-T044)

**Phase 5 (Sequential manual tests)**:
- T047-T051: Must be done in order to verify each workflow

**Phase 6 (Parallel removals)**:
- T052-T056: Can be done in parallel (different sections)
- T057-T059: Verification (depends on T052-T056)

**Phase 7 (Parallel doc updates)**:
- T060-T065: All parallel (different sections of CLAUDE.md)

**Phase 8 (Sequential checks)**:
- T066-T075: Must be sequential (some checks depend on previous)

### Parallel Opportunities

**Phase 1**: None (sequential class building)

**Phase 3**: Maximum parallelism
```bash
# All detector tests in parallel (after T018):
T019, T020, T021, T022, T023, T024, T025, T026

# All monitor tests in parallel (after T027):
T028, T029, T030, T031, T032, T033, T034, T035, T036
```

**Phase 6**: Parallel removals
```bash
# All cleanup tasks in parallel:
T052, T053, T054, T055, T056
```

**Phase 7**: Parallel documentation
```bash
# All doc updates in parallel:
T060, T061, T062, T063, T064, T065
```

---

## Implementation Strategy

### Atomic Replacement Approach

This refactoring uses **atomic replacement** (not gradual migration):

1. **Phases 1-3**: Build and test new implementation in parallel with old
2. **Phase 4**: Single-phase integration (swap old for new)
3. **Phases 5-6**: Verify and remove old implementation
4. **Phases 7-8**: Documentation and final checks

### Runnable State Checkpoints

After each phase, the project is in a runnable state:

- **After Phase 1**: Old implementation works, new classes exist but unused
- **After Phase 2**: Old implementation works, new providers available but unused
- **After Phase 3**: Old implementation works, new classes fully tested
- **After Phase 4**: New implementation works, old code still present (rollback possible)
- **After Phase 5**: New implementation verified manually
- **After Phase 6**: New implementation only, old code removed
- **After Phase 7**: Documentation matches implementation
- **After Phase 8**: Feature complete, all quality gates passed

### Rollback Points

Each phase can be reverted:
- **Before Phase 4**: Remove new code, no impact on workflows
- **After Phase 4**: Revert orchestrator changes, use old state_machine_provider
- **After Phase 6**: Restore old implementation from git history

---

## Summary

**Total Tasks**: 75 tasks across 8 phases

**Task Breakdown by Phase**:
- Phase 1 (Create Classes): 15 tasks
- Phase 2 (DI Container): 2 tasks
- Phase 3 (Write Tests): 21 tasks
- Phase 4 (Integration): 8 tasks
- Phase 5 (Manual Testing): 5 tasks
- Phase 6 (Cleanup): 8 tasks
- Phase 7 (Documentation): 6 tasks
- Phase 8 (Final Verification): 10 tasks

**Parallel Opportunities**:
- Phase 3: Up to 18 test tasks in parallel (9 detector + 9 monitor)
- Phase 6: 5 cleanup tasks in parallel
- Phase 7: 6 documentation tasks in parallel

**Independent Test Criteria per Phase**:
- Phase 1: New classes instantiate, existing tests pass
- Phase 2: Providers work, existing tests pass
- Phase 3: ≥90% coverage achieved, all tests pass
- Phase 4: Integration tests pass, behavior parity verified
- Phase 5: Manual workflows work identically
- Phase 6: Old code removed, all tests pass
- Phase 7: Documentation accurate
- Phase 8: All quality checks pass

**Suggested Execution**: Sequential phases with parallelism within Phase 3 (tests), Phase 6 (cleanup), and Phase 7 (docs)

---

## Notes

- This is a pure refactoring - no functional changes to workflows (FR-016)
- Each phase maintains runnable state with passing tests
- Tests written in Phase 3 gate integration in Phase 4
- Manual verification in Phase 5 gates cleanup in Phase 6
- Atomic replacement ensures no dual-implementation maintenance period
- All tasks include exact file paths for clarity
- Coverage target: ≥90% for detector and monitor (SC-005)
