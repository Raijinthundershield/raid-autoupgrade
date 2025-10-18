# Implementation Tasks: AutoRaid GUI Desktop Application

**Feature**: AutoRaid GUI Desktop Application
**Branch**: `003-gui-desktop-app`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Baseline**: `plans/gui-phases.md`

---

## Task Summary

**Total Tasks**: 44
**Estimated Time**: ~13.5 hours

### Tasks by Phase
- **Phase 1 (Setup)**: 6 tasks (30 min)
- **Phase 2 (Foundational - US4, P2)**: 6 tasks (2.5 hrs) - Network Adapter Management
- **Phase 3 (US3, P1)**: 6 tasks (2 hrs) - Select UI Regions
- **Phase 4 (US1, P1)**: 8 tasks (2 hrs) - Count Upgrade Fails
- **Phase 5 (US2, P2 + US5, P3)**: 7 tasks (2 hrs) - Spend Workflow + Real-Time Logs
- **Phase 6 (US6, US7, P3)**: 7 tasks (3 hrs) - Polish, Debug, Status Display
- **Phase 7 (Documentation)**: 4 tasks (1.5 hrs)

### MVP Scope
**Recommended MVP**: Phase 1-4 (Setup + US4 + US3 + US1)
- ~7 hours total
- Delivers core Count workflow with network adapter management and region selection
- Independently testable and deployable

---

## Implementation Strategy

### Parallel Execution Opportunities

Tasks marked with **[P]** can be executed in parallel with other [P] tasks in the same phase, as they modify different files or have no dependencies on incomplete tasks.

### Testing Approach

Per feature specification: **Smoke tests only** (not strict TDD)
- Smoke tests verify component instantiation and key method calls
- Manual testing per acceptance criteria after each phase
- No GUI automation tests (per Constitution Principle III)

---

## Dependencies

### Story Completion Order

```
Phase 1: Setup
  ↓
Phase 2: US4 (P2) - Network Adapter Management
  ↓ (blocks Count workflow)
Phase 3: US3 (P1) - Select UI Regions
  ↓ (blocks all workflows)
Phase 4: US1 (P1) - Count Upgrade Fails
  ↓ (Count populates Spend max_attempts)
Phase 5: US2 (P2) + US5 (P3) - Spend Workflow + Logs
  ↓ (workflows complete, add polish)
Phase 6: US6, US7 (P3) - Polish, Debug, Status Display
  ↓
Phase 7: Documentation
```

**Critical Path**: Setup → US4 → US3 → US1 → US2

**Independent Stories** (can reorder if needed):
- US5 (Logs) can integrate with US1 or US2
- US6 (Debug) can integrate anytime after Phase 1
- US7 (Status Display) can integrate with US3

---

## Phase 1: Setup NiceGUI Infrastructure

**Goal**: Create minimal native desktop application skeleton
**Time Estimate**: 30 minutes
**Delivers**: Runnable GUI that launches in native window

### Tasks

- [X] T001 Add nicegui[native]>=2.10.0 dependency in pyproject.toml
- [X] T002 Run `uv sync` to install NiceGUI with native mode support
- [X] T003 [P] Create src/autoraid/gui/__init__.py (empty module file)
- [X] T004 [P] Create src/autoraid/gui/app.py with minimal NiceGUI native window showing "AutoRaid Web Interface" title
- [X] T005 Add `gui` command to src/autoraid/cli/cli.py that launches GUI via app.main()
- [X] T006 Manual test: Run `uv run autoraid gui` and verify native window launches (not browser), displays title, is resizable/closable

### Acceptance Criteria (Phase 1)

- ✅ `uv sync` installs NiceGUI successfully
- ✅ `uv run autoraid gui` launches native desktop window
- ✅ Window displays "AutoRaid Web Interface" title
- ✅ Window is resizable and closable
- ✅ Existing CLI commands still work: `uv run autoraid upgrade count --help`

### Commit Message Template

```
feat(gui): add NiceGUI native desktop interface skeleton

- Add nicegui[native] dependency to pyproject.toml
- Create gui/ module with minimal app in native mode
- Add 'autoraid gui' CLI command
- Native window displays "AutoRaid Web Interface"
```

---

## Phase 2: US4 (P2) - Manage Network Adapters

**User Story**: Manage Network Adapters (Priority P2)
**Goal**: Network adapter selection and management UI
**Time Estimate**: 2.5 hours
**Delivers**: Independently testable adapter management (blocks Count workflow)

### Independent Test Criteria (US4)

Can be fully tested by:
1. Launching GUI
2. Scrolling to Network Adapters section
3. Selecting adapters via checkboxes
4. Verifying status changes and persistence across restart

Delivers value: Simplifies network control without leaving app

### Tasks

- [X] T007 [P] [US4] Create src/autoraid/gui/components/__init__.py (empty module file)
- [X] T008 [P] [US4] Create src/autoraid/gui/utils.py with state management helpers
- [X] T009 [US4] Create src/autoraid/gui/components/network_panel.py with NetworkPanel component showing adapter table (ID, Name, Status columns)
- [X] T010 [US4] Add checkbox per adapter row for multi-select, persist selected IDs in app.storage.user['selected_adapters']
- [X] T011 [US4] Add "Refresh" button to reload adapter table with updated status
- [X] T012 [US4] Add internet status indicator (green=online, red=offline) with ui.timer() polling every 5 seconds
- [X] T013 [US4] Wire container in src/autoraid/gui/app.py, add NetworkPanel to main page
- [X] T014 [US4] Manual test: Select 2 adapters, restart app, verify checkboxes remain checked (FR-031 persistence)
- [X] T015 [P] [US4] Create test/unit/gui/test_network_panel.py with smoke test verifying component instantiation

### Acceptance Criteria (US4)

- ✅ Table displays all adapters from NetworkManager.list_all()
- ✅ Checkboxes allow multi-select (any number of adapters)
- ✅ "Refresh" button updates table
- ✅ Internet status indicator shows green/red, updates every 5 seconds
- ✅ Selected adapter IDs persist in app.storage.user['selected_adapters']
- ✅ Same functionality as `autoraid network list` CLI command

### Commit Message Template

```
feat(gui): implement Network adapter management UI

- Add NetworkPanel with adapter table and selection
- Internet access status indicator
- Store selected adapters in app.storage for Count workflow
- Wire to NetworkManager
```

---

## Phase 3: US3 (P1) - Select UI Regions for Detection

**User Story**: Select UI Regions (Priority P1)
**Goal**: Region viewing and selection via OpenCV popups
**Time Estimate**: 2 hours
**Delivers**: Independently testable region management (blocks all workflows)

### Independent Test Criteria (US3)

Can be fully tested by:
1. Clicking "Select Regions (Auto)" → verify automatic detection or manual fallback
2. Clicking "Select Regions (Manual)" → verify OpenCV ROI selection UI
3. Verifying status updates show cached region names

Delivers value: Enables all upgrade detection workflows

### Tasks

- [X] T016 [P] [US3] Create src/autoraid/gui/components/region_panel.py with RegionPanel component
- [X] T017 [US3] Add status display showing current window size (width x height) via screenshot_service.get_window_size()
- [X] T018 [US3] Add cached region status display showing found regions (upgrade_bar, upgrade_button, artifact_icon)
- [X] T019 [US3] Add "Show Regions" button that opens OpenCV window with annotated screenshot (asyncio.to_thread)
- [X] T020 [US3] Add "Select Regions (Auto)" button calling locate_region_service.get_regions(manual=False) with manual fallback
- [X] T021 [US3] Add "Select Regions (Manual)" button calling locate_region_service.get_regions(manual=True) for manual ROI selection
- [X] T022 [US3] Add ui.timer() to check window size every 5 seconds, show warning banner if size changed (invalidates regions)
- [X] T023 [US3] Wire RegionPanel to LocateRegionService, ScreenshotService, CacheService via DI in src/autoraid/gui/app.py
- [X] T024 [P] [US3] Create test/unit/gui/test_region_panel.py with smoke test for component instantiation and DI wiring
- [X] T025 [US3] Manual test: Click "Select Regions (Auto)", verify automatic detection or manual fallback, check status updates

### Acceptance Criteria (US3)

- ✅ Status shows current window size and cached regions
- ✅ "Show Regions" opens OpenCV window with regions overlaid
- ✅ "Select Regions (Auto)" attempts automatic detection, falls back to manual on failure
- ✅ "Select Regions (Manual)" opens OpenCV ROI selection UI
- ✅ Status updates after selection: "Regions cached for window size: 1920x1080"
- ✅ Warning shown if Raid window not found
- ✅ Warning shown if window size changes (every 5s check)

### Commit Message Template

```
feat(gui): implement Region management UI

- Add RegionPanel with show/select buttons
- OpenCV popups for region selection (external windows)
- Wire to LocateRegionService via DI
- Display cached region status and window size warnings
```

---

## Phase 4: US1 (P1) - Count Upgrade Fails with Airplane Mode

**User Story**: Count Upgrade Fails (Priority P1)
**Goal**: Count workflow UI with network adapter integration
**Time Estimate**: 2 hours
**Delivers**: Independently testable Count workflow (core value)

### Independent Test Criteria (US1)

Can be fully tested by:
1. Selecting network adapters (from US4)
2. Clicking "Start Count"
3. Verifying count increments in real-time while network disabled

Delivers value: Shows exact number of fails needed (primary feature)

### Tasks

- [ ] T026 [P] [US1] Create src/autoraid/gui/components/upgrade_panel.py with UpgradePanel component structure
- [ ] T027 [US1] Add Count section (left): Display selected network adapters from app.storage.user (read-only field)
- [ ] T028 [US1] Add "Start Count" button with async handler calling orchestrator.count_workflow() via asyncio.to_thread()
- [ ] T029 [US1] Add "Current Count" display with ui.refreshable() for real-time n_fails updates during workflow
- [ ] T030 [US1] Implement workflow cancellation: "Stop" button calling task.cancel() and re-enabling network in finally block
- [ ] T031 [US1] Add error handling: Show toast notifications for WindowNotFoundException, NetworkAdapterError, no regions (FR-045 to FR-047)
- [ ] T032 [US1] Store last count result in app.storage.user['last_count_result'] after workflow completion (for Spend auto-populate)
- [ ] T033 [US1] Wire UpgradePanel to UpgradeOrchestrator via DI in src/autoraid/gui/app.py (add to container.wire modules)
- [ ] T034 [P] [US1] Create test/unit/gui/test_upgrade_panel.py with smoke test for Count workflow component instantiation
- [ ] T035 [US1] Manual test: Select adapters (US4), click "Start Count", verify network disables, count increments, network re-enables on completion/cancel

### Acceptance Criteria (US1)

- ✅ Count section shows selected network adapters from Phase 2
- ✅ "Start Count" triggers orchestrator.count_workflow() with selected adapters
- ✅ "Current Count" field updates in real-time during workflow (<500ms latency, FR-009)
- ✅ Count result auto-populates "Max Attempts" in Spend section (stored in app.storage)
- ✅ "Stop" button cancels workflow, re-enables network adapters (FR-040)
- ✅ Buttons disabled while workflow running (FR-039)
- ✅ Toast notifications for errors (FR-045 to FR-048)

### Commit Message Template

```
feat(gui): implement Count workflow UI

- Add Count section in UpgradePanel
- Real-time count display with workflow cancellation
- Network adapter integration from NetworkPanel
- Error toast notifications
- Wire to UpgradeOrchestrator via DI
```

---

## Phase 5: US2 (P2) + US5 (P3) - Spend Workflow + Real-Time Logs

**User Stories**:
- US2: Spend Counted Attempts (Priority P2)
- US5: Monitor Workflows with Real-Time Logs (Priority P3)

**Goal**: Complete upgrade workflows with log streaming
**Time Estimate**: 2 hours
**Delivers**: Full Count + Spend workflow with visual feedback

### Independent Test Criteria (US2)

Can be fully tested by:
1. Manually setting max attempts
2. Clicking "Start Spend"
3. Verifying tool clicks upgrade button specified number of times

Delivers value: Automates repetitive clicking

### Independent Test Criteria (US5)

Can be fully tested by:
1. Starting any workflow
2. Verifying logs appear in real-time with color coding

Delivers value: Transparency and troubleshooting

### Tasks

- [ ] T036 [P] [US2] Add Spend section (right) in src/autoraid/gui/components/upgrade_panel.py: Max attempts input (ui.number, min=1)
- [ ] T037 [US2] Auto-populate "Max Attempts" field with app.storage.user['last_count_result'] on component mount
- [ ] T038 [US2] Add "Continue Upgrade" checkbox and "Start Spend" button with async handler calling orchestrator.spend_workflow()
- [ ] T039 [US2] Add "Current Spent" display with ui.refreshable() for real-time n_attempts updates
- [ ] T040 [US2] Add error handling: Toast for no internet access (FR-049), WindowNotFoundException
- [ ] T041 [P] [US5] Add shared log section (bottom) in upgrade_panel.py: ui.log(max_lines=1000) with auto-scroll
- [ ] T042 [US5] Set up loguru sink in src/autoraid/gui/utils.py to capture logs and push to ui.log() element
- [ ] T043 [US5] Configure log color coding: INFO=green, DEBUG=blue, WARNING=yellow, ERROR=red (FR-036)
- [ ] T044 [US5] Clear log area when new workflow starts (FR-038)
- [ ] T045 [US2] [US5] Manual test: Complete Count workflow, verify Max Attempts auto-filled, run Spend workflow, verify logs stream in real-time

### Acceptance Criteria (US2 + US5)

**US2**:
- ✅ "Max Attempts" auto-populated from last count result (FR-015)
- ✅ "Start Spend" triggers orchestrator.spend_workflow()
- ✅ "Current Spent" updates in real-time (<500ms latency, FR-017)
- ✅ Final result shows n_upgrades, n_attempts, n_remaining (FR-018)
- ✅ "Continue Upgrade" checkbox works for level 10+ gear (FR-019, FR-020)
- ✅ Toast for no internet access (FR-049)

**US5**:
- ✅ Logs stream to UI from both workflows (FR-035)
- ✅ Color-coded by level (FR-036)
- ✅ Auto-scroll to latest entry (FR-037)
- ✅ Log area clears when new workflow starts (FR-038)

### Commit Message Template

```
feat(gui): implement Spend workflow and real-time log streaming

- Add Spend section with Max Attempts auto-populate
- Continue Upgrade checkbox for level 10+ gear
- Shared log area with color-coded real-time streaming
- Wire loguru sink to ui.log() element
```

---

## Phase 6: US6, US7 (P3) - Polish, Debug Mode, Status Display

**User Stories**:
- US6: Enable Debug Mode for Troubleshooting (Priority P3)
- US7: View Cached Region Status (Priority P3)

**Goal**: Single-page layout, debug mode, status indicators, UX polish
**Time Estimate**: 3 hours
**Delivers**: Polished, production-ready GUI

### Independent Test Criteria (US6)

Can be fully tested by:
1. Enabling debug checkbox
2. Running Count workflow
3. Verifying debug artifacts in `cache-raid-autoupgrade/debug/`

Delivers value: Detailed troubleshooting capability

### Independent Test Criteria (US7)

Can be fully tested by:
1. Caching regions
2. Clicking "Show Regions"
3. Verifying annotated screenshot displays

Delivers value: Visual confirmation of cached regions

### Tasks

- [ ] T046 [P] [US6] Add header in src/autoraid/gui/app.py: Application title, status indicators (Raid window green/red, Network online/offline)
- [ ] T047 [US6] Add debug mode checkbox in header, persist state in app.storage.user['debug_enabled']
- [ ] T048 [US6] Pass debug_dir parameter to orchestrator workflows when debug enabled: Path('cache-raid-autoupgrade/debug')
- [ ] T049 Reorganize app.py for single-page scrollable layout: Upgrade Workflows (top) → Region Management (middle) → Network Adapters (bottom)
- [ ] T050 [P] Add visual section dividers using ui.separator() between functional areas
- [ ] T051 [P] Add tooltips (ui.tooltip) for all input fields: "Max Attempts", "Continue Upgrade", network adapter selection (FR-051, FR-052)
- [ ] T052 [P] Add keyboard shortcuts: Esc to cancel workflow, Enter to submit forms (FR-053, FR-054)
- [ ] T053 [P] Style improvements: Colors, spacing, scrollable container with ui.column().classes('w-full')
- [ ] T054 Manual test: Enable debug, run Count, verify artifacts saved; verify single-page layout scrolls smoothly; verify tooltips appear on hover
- [ ] T055 Run existing pytest suite to ensure no regressions: `uv run pytest`

### Acceptance Criteria (US6 + US7 + Polish)

**US6**:
- ✅ Debug checkbox in header toggles debug artifact saving (FR-041)
- ✅ Debug artifacts save to `cache-raid-autoupgrade/debug/` when enabled (FR-042)
- ✅ Debug state persists across restarts (FR-043)
- ✅ Log shows debug artifact save locations (FR-044)

**US7**:
- ✅ Region status display shows window size and cached region names (from Phase 3, FR-021, FR-022)
- ✅ "Show Regions" displays annotated screenshot (from Phase 3, FR-023)

**Polish**:
- ✅ Single-page scrollable layout (~1400px height, FR-001 to FR-004)
- ✅ Header status: Raid window (green/red), Network (online/offline), updated every 5s
- ✅ Visual dividers separate sections
- ✅ Scrolling works smoothly
- ✅ Error toasts for all exceptions (FR-045 to FR-050)
- ✅ Tooltips on hover (500ms delay, FR-051, FR-052)
- ✅ Keyboard shortcuts work (Esc, Enter, FR-053, FR-054)
- ✅ Responsive layout (1920x1080, 1280x720)

### Commit Message Template

```
feat(gui): add single-page layout, debug mode, and UI polish

- Single-page vertical layout with scrollable sections
- Header with status indicators (Raid window, network)
- Debug mode toggle for artifact saving
- Visual dividers, tooltips, keyboard shortcuts
- Responsive layout with smooth scrolling
```

---

## Phase 7: Documentation and Testing

**Goal**: Comprehensive documentation and manual testing checklist
**Time Estimate**: 1.5 hours
**Delivers**: User-facing docs and testing guide

### Tasks

- [ ] T056 [P] Update README.md with "GUI Usage" section explaining `uv run autoraid gui` command
- [ ] T057 [P] Update CLAUDE.md with GUI architecture notes (thin layer over orchestrator, DI wiring, component structure)
- [ ] T058 [P] Update CLAUDE.md project structure section to include gui/ module
- [ ] T059 Create docs/gui-testing-checklist.md with manual testing scenarios for all workflows (Count, Spend, Region selection, Network management)
- [ ] T060 Manual end-to-end test: Run through complete user journey (select adapters → select regions → count → spend → verify debug mode)

### Acceptance Criteria (Documentation)

- ✅ README.md explains how to launch GUI
- ✅ README.md references UI layout diagram (single-page-layout.svg)
- ✅ CLAUDE.md documents GUI architecture (thin layer, DI, components)
- ✅ CLAUDE.md project structure includes gui/ module
- ✅ Manual testing checklist covers all 7 user stories
- ✅ Debug mode usage documented
- ✅ All phases tested end-to-end

### Commit Message Template

```
docs(gui): add GUI documentation and testing checklist

- Update README.md with GUI usage instructions
- Update CLAUDE.md with GUI architecture notes
- Add manual testing checklist for all workflows
- Document debug mode and keyboard shortcuts
```

---

## Testing Strategy

### Smoke Tests (Unit Level)

**Location**: `test/unit/gui/`

**Purpose**: Verify components instantiate without errors

**Files**:
- `test_network_panel.py` (T015)
- `test_region_panel.py` (T024)
- `test_upgrade_panel.py` (T034)

**Example**:
```python
def test_create_upgrade_panel_smoke():
    """Verify panel creation without errors"""
    mock_orchestrator = Mock(spec=UpgradeOrchestrator)
    create_upgrade_panel(orchestrator=mock_orchestrator)
    # No exception = pass
```

**Run**: `uv run pytest test/unit/gui/`

---

### Manual Testing (Integration Level)

**Location**: `docs/gui-testing-checklist.md` (created in T059)

**Checkpoints After Each Phase**:
1. ✅ GUI launches without errors: `uv run autoraid gui`
2. ✅ CLI still functional: `uv run autoraid upgrade count --help`
3. ✅ Existing tests pass: `uv run pytest`
4. ✅ Manual acceptance criteria verified (per phase)
5. ✅ No regressions in existing workflows

---

## Parallel Execution Examples

### Phase 1 (Setup)
```bash
# T003 and T004 can run in parallel (different files)
# Create __init__.py and app.py simultaneously
```

### Phase 2 (US4 - Network)
```bash
# T007, T008 can run in parallel (different files)
# Create components/__init__.py, utils.py simultaneously

# T015 (smoke test) can run in parallel with T009-T013 (implementation)
# Test file is independent of component implementation
```

### Phase 3 (US3 - Regions)
```bash
# T016 (create region_panel.py) can run in parallel with T024 (smoke test)
# Different files, no dependencies
```

### Phase 4 (US1 - Count)
```bash
# T026 (create upgrade_panel.py) can run in parallel with T034 (smoke test)
# Different files, no dependencies
```

### Phase 5 (US2 + US5 - Spend + Logs)
```bash
# T036 (Spend section) and T041 (Log section) can run in parallel
# Both modify upgrade_panel.py but different sections
# Merge required at end
```

### Phase 6 (Polish)
```bash
# T046-T048 (header), T050 (dividers), T051 (tooltips), T052 (shortcuts), T053 (styles)
# All can run in parallel - different UI areas or orthogonal concerns
```

### Phase 7 (Documentation)
```bash
# T056, T057, T058 can all run in parallel
# Different documentation files (README, CLAUDE, testing checklist)
```

---

## Rollback Strategy

Each phase is a separate git commit. If issues arise:

1. Identify problematic phase
2. `git revert <phase-commit-hash>`
3. Fix issues in isolation
4. Re-apply phase with updated commit

**Example**:
```bash
# Rollback Phase 4 (US1 - Count)
git revert <t026-t035-commit-hash>

# Fix issues
# ... make changes ...

# Re-commit Phase 4
git add .
git commit -m "feat(gui): implement Count workflow UI [v2]"
```

---

## Validation Checklist

Before marking feature complete, verify:

- [ ] All 44 tasks completed
- [ ] All 7 user stories independently testable
- [ ] All acceptance criteria met (per phase)
- [ ] Manual testing checklist passed
- [ ] No regressions in existing CLI workflows
- [ ] Documentation updated (README, CLAUDE.md)
- [ ] Smoke tests pass: `uv run pytest test/unit/gui/`
- [ ] Existing tests pass: `uv run pytest`
- [ ] GUI launches in <5 seconds (SC-007)
- [ ] Count/Spent updates <500ms latency (SC-004)
- [ ] Network re-enables within 3s (SC-005)
- [ ] State persists across restarts (SC-010)

---

## Notes

- **No strict TDD**: Smoke tests only, not full test coverage (per feature spec)
- **Commit messages**: Do NOT include Claude signature (per user request)
- **Each phase produces runnable code**: Can deploy incrementally
- **Constitution compliance**: All phases follow simplicity, pragmatic testing, debug-friendly principles
