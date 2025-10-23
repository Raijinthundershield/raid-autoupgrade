# Tasks: NetworkManager Service Redesign

**Feature Branch**: `004-network-manager-redesign`
**Input**: Design documents from `/specs/004-network-manager-redesign/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/network-manager-service.md

**Organization**: This is a focused service refactoring, so tasks are organized by implementation phase rather than user stories.

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

---

## Phase 1: Core Service Refactoring

**Purpose**: Implement new waiting logic and update NetworkManager service

- [X] T001 [P] Add timeout constants to NetworkManager in src/autoraid/platform/network.py (DEFAULT_DISABLE_TIMEOUT=5.0, DEFAULT_ENABLE_TIMEOUT=10.0, CHECK_INTERVAL=0.5)
- [X] T002 Implement wait_for_network_state() method in src/autoraid/platform/network.py with 2-consecutive-check stability logic
- [X] T003 Enhance toggle_adapters() method in src/autoraid/platform/network.py to accept wait and timeout parameters
- [X] T004 Add invalid adapter ID validation and warning logging in toggle_adapters() in src/autoraid/platform/network.py
- [X] T005 Add "internet still accessible" warning detection after disable operations in src/autoraid/platform/network.py
- [X] T006 Remove display_adapters(), find_adapter(), select_adapters(), and toggle_selected_adapters() methods from src/autoraid/platform/network.py

**Checkpoint**: NetworkManager service layer complete with encapsulated waiting logic

---

## Phase 2: Service Layer Integration

**Purpose**: Update orchestrator and other services to use new wait=True pattern

- [X] T007 Update UpgradeOrchestrator count_workflow() in src/autoraid/services/upgrade_orchestrator.py to use toggle_adapters(wait=True) for disable operations
- [X] T008 Update UpgradeOrchestrator count_workflow() in src/autoraid/services/upgrade_orchestrator.py to use toggle_adapters(wait=False) for enable operations in finally block
- [X] T009 Update UpgradeOrchestrator spend_workflow() in src/autoraid/services/upgrade_orchestrator.py to use toggle_adapters(wait=True) for enable operations in finally block (N/A - spend_workflow doesn't disable network)
- [X] T010 Remove manual waiting loops and timeout logic from UpgradeOrchestrator workflows in src/autoraid/services/upgrade_orchestrator.py

**Checkpoint**: All workflows use unified toggle_adapters() with automatic waiting

---

## Phase 3: Dependency Injection & CLI Updates

**Purpose**: Wire NetworkManager singleton and migrate display logic to CLI layer

- [X] T011 Register network_manager as Singleton provider in src/autoraid/container.py
- [X] T012 Add wiring for autoraid.cli.network_cli module in src/autoraid/container.py (Already wired)
- [X] T013 [P] Migrate display_adapters() logic to network_cli.py using Rich tables in src/autoraid/cli/network_cli.py
- [X] T014 [P] Migrate find_adapter() logic to network_cli.py in src/autoraid/cli/network_cli.py
- [X] T015 [P] Migrate select_adapters() interactive prompts to network_cli.py in src/autoraid/cli/network_cli.py
- [X] T016 Update list command in src/autoraid/cli/network_cli.py to use @inject decorator and Provide[Container.network_manager]
- [X] T017 Update enable/disable commands in src/autoraid/cli/network_cli.py to use injected NetworkManager and new CLI-layer display logic

**Checkpoint**: CLI layer handles all display/interaction, service layer is pure logic

---

## Phase 4: GUI Integration

**Purpose**: Update GUI components to use dependency injection

- [X] T018 Add wiring for autoraid.gui.components.network_panel module in src/autoraid/container.py (Already wired)
- [X] T019 Update create_network_panel() in src/autoraid/gui/components/network_panel.py to use @inject decorator and Provide[Container.network_manager]
- [X] T020 Replace direct NetworkManager() instantiation with injected parameter in src/autoraid/gui/components/network_panel.py

**Checkpoint**: GUI uses injected NetworkManager singleton

---

## Phase 5: Testing

**Purpose**: Validate new service methods with smoke tests

- [X] T021 [P] Create test/unit/platform/test_network_manager.py test file
- [X] T022 [P] Implement test_toggle_adapters_without_wait in test/unit/platform/test_network_manager.py (verify immediate return when wait=False)
- [X] T023 [P] Implement test_toggle_adapters_with_wait_success in test/unit/platform/test_network_manager.py (verify wait_for_network_state called when wait=True)
- [X] T024 [P] Implement test_toggle_adapters_uses_default_timeout_disable in test/unit/platform/test_network_manager.py (verify 5s timeout for disable)
- [X] T025 [P] Implement test_toggle_adapters_uses_default_timeout_enable in test/unit/platform/test_network_manager.py (verify 10s timeout for enable)
- [X] T026 [P] Implement test_wait_for_network_state_immediate_success in test/unit/platform/test_network_manager.py (verify return when state matches after 2 checks)
- [X] T027 [P] Implement test_wait_for_network_state_timeout in test/unit/platform/test_network_manager.py (verify NetworkAdapterError raised on timeout)
- [X] T028 [P] Implement test_toggle_adapters_invalid_ids in test/unit/platform/test_network_manager.py (verify graceful degradation with warning logs)
- [X] T029 Update integration test test_upgrade_orchestrator.py to verify new wait=True pattern in workflows
- [X] T030 Run all existing tests to verify backward compatibility (uv run pytest) - 15/15 tests passed

**Checkpoint**: All smoke tests passing, backward compatibility confirmed

---

## Phase 6: Documentation & Cleanup

**Purpose**: Update documentation and finalize refactoring

- [X] T031 [P] Update CLAUDE.md to document NetworkManager as singleton service in container with display logic in CLI layer
- [X] T032 [P] Remove Rich import from src/autoraid/platform/network.py (no longer needed in service layer)
- [X] T033 [P] Remove Console instance from NetworkManager.__init__() in src/autoraid/platform/network.py
- [ ] T034 Verify all CLI commands function identically to pre-refactor behavior (manual testing)
- [ ] T035 Verify GUI network panel functions identically to pre-refactor behavior (manual testing)

**Checkpoint**: Documentation updated, zero breaking changes for end users

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Core Service Refactoring)**: No dependencies - start immediately
  - Tasks T001-T006 must complete before Phase 2
  - T001 (constants) should complete before T002-T003 (use constants)
  - T002-T005 are parallelizable if working on different methods

- **Phase 2 (Service Layer Integration)**: Depends on Phase 1 completion
  - Tasks T007-T010 can proceed once NetworkManager refactor is done
  - T007-T009 update different workflows (parallelizable by workflow)
  - T010 cleanup happens after T007-T009

- **Phase 3 (DI & CLI)**: Depends on Phase 1 completion (NetworkManager API finalized)
  - T011-T012 (DI wiring) should complete before T013-T017
  - T013-T015 migrate different methods (parallelizable)
  - T016-T017 update CLI commands after display logic migration

- **Phase 4 (GUI Integration)**: Depends on T011-T012 (DI container setup)
  - T018-T020 can proceed once container wiring exists
  - Parallelizable with Phase 2 if desired

- **Phase 5 (Testing)**: Depends on Phase 1 completion (service methods exist)
  - T021 (create test file) before T022-T028
  - T022-T028 are individual test functions (fully parallelizable)
  - T029-T030 integration/regression tests after smoke tests

- **Phase 6 (Documentation)**: Depends on all implementation phases complete
  - T031-T033 documentation/cleanup (parallelizable)
  - T034-T035 manual validation (sequential, after all code changes)

### Parallel Opportunities

**Within Phase 1**: T002, T003, T004, T005 can be developed in parallel (different methods/logic branches)

**Within Phase 2**: T007, T008, T009 can be updated in parallel (different workflows in same file - careful merge)

**Within Phase 3**: T013, T014, T015 migrate different functions (parallelizable); T016 and T017 update different commands (parallelizable)

**Within Phase 5**: T022-T028 are independent test functions (launch all 7 tests together)

**Within Phase 6**: T031, T032, T033 are documentation/cleanup tasks (parallelizable)

**Across Phases**: Phase 3 (CLI) and Phase 4 (GUI) can proceed in parallel after Phase 1 completes

---

## Implementation Strategy

### Recommended Sequential Flow

1. **Phase 1**: Refactor NetworkManager service (T001-T006) - Foundation for everything
2. **Phase 2**: Update orchestrator workflows (T007-T010) - Validate new API works
3. **Phase 3 + Phase 4 in parallel**: CLI updates (T011-T017) + GUI updates (T018-T020)
4. **Phase 5**: Write and run tests (T021-T030) - Validate correctness
5. **Phase 6**: Documentation and final validation (T031-T035) - Polish

### Incremental Validation Points

- After Phase 1: Test NetworkManager methods manually in Python REPL
- After Phase 2: Run upgrade workflow with debug logging to verify waiting logic
- After Phase 3: Test CLI commands (list, enable, disable) to verify display/interaction
- After Phase 4: Launch GUI and verify network panel still works
- After Phase 5: All automated tests green
- After Phase 6: Full manual regression test of both CLI and GUI

---

## Summary

**Total Tasks**: 35
**Parallelization Opportunities**:
- Phase 1: 4 tasks (T002-T005)
- Phase 3: 5 tasks (T013-T015, T016-T017 in 2 groups)
- Phase 5: 7 tests (T022-T028)
- Phase 6: 3 tasks (T031-T033)

**Critical Path**: Phase 1 → Phase 2 → Phase 5 → Phase 6 (must be sequential)

**MVP Scope**: Phases 1-2 deliver the core value (encapsulated waiting logic), remaining phases ensure no regressions

**Estimated Effort**:
- Phase 1: 3-4 hours (core service logic)
- Phase 2: 1-2 hours (workflow updates)
- Phase 3: 2-3 hours (CLI migration)
- Phase 4: 30 minutes (GUI injection)
- Phase 5: 2-3 hours (test writing)
- Phase 6: 1 hour (documentation)
- **Total**: ~10-14 hours for complete refactoring

---

## Notes

- All tasks include exact file paths for clarity
- [P] markers indicate true parallelization opportunities (different files or independent functions)
- Backward compatibility is critical: existing CLI/GUI behavior must remain unchanged
- Tests use mocking to avoid requiring real network adapters or admin rights
- Constitution principles satisfied: simplicity (remove duplication), readability (clear method names), pragmatic testing (smoke tests only), debug-friendly (logging preserved), incremental (opt-in wait parameter)
