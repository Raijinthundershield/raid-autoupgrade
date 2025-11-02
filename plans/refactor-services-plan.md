# Services Refactoring - Implementation Plan

## Overview

**Purpose**: Restructure AutoRaid's architecture to clearly separate infrastructure from application logic, aligning folder structure with DI container simplification

**Scope**:
- Refactor folder structure to distinguish infrastructure (services) from application logic (orchestration)
- Remove workflows, orchestrator, and monitor from DI container
- Keep only infrastructure singletons in DI container
- Update all imports and references across codebase

**Out of Scope**:
- Protocol abstraction for WindowInteractionService/ScreenshotService (Phase 3 - future work)
- Changing business logic or algorithms
- GUI/CLI functionality changes

**Success Criteria**:
- Container reduced from 13 providers to 8 providers (zero factories)
- All application logic constructed directly (workflows, orchestrator, monitor)
- Folder structure clearly separates infrastructure (`/services`, `/detection`) from application (`/orchestration`, `/workflows`)
- All tests passing with updated architecture
- No functionality regressions

---

## Architecture & Design

### Current State Problems

**DI Container Issues:**
- 13 providers (8 singletons, 5 factories)
- Factory pattern for one-shot objects (YAGNI violation)
- Triple indirection: Workflow → Orchestrator (factory) → Monitor (factory) → Detector (singleton)
- Application logic mixed with infrastructure in container

**Folder Structure Issues:**
- `/core` contains both pure algorithms (detector) and application helpers (monitor, stop conditions)
- `/services` contains orchestrator which is application coordination, not infrastructure
- Semantic confusion: "What belongs in core vs services?"

### Target State Architecture

**DI Container (8 Infrastructure Singletons):**
```python
Container:
├── Configuration
│   ├── cache_dir
│   └── debug
├── app_data (Singleton)
├── disk_cache (Singleton)
├── cache_service (Singleton)
├── screenshot_service (Singleton)
├── window_interaction_service (Singleton)
├── locate_region_service (Singleton)
├── network_manager (Singleton)
└── progress_bar_detector (Singleton)
```

**Application Logic (Direct Construction):**
- ProgressBarMonitor - Created by orchestrator per session
- UpgradeOrchestrator - Created by workflows
- CountWorkflow, SpendWorkflow, DebugMonitorWorkflow - Created by CLI/GUI

### Project Structure

```
src/autoraid/
├── cli/                                    [MODIFY] - Update imports, construct workflows directly
│   ├── cli.py                              [MODIFY] - Update container wiring
│   ├── upgrade_cli.py                      [MODIFY] - Inject services, construct workflows
│   ├── network_cli.py                      (unchanged)
│   └── debug_cli.py                        [MODIFY] - Update imports
│
├── gui/                                    [MODIFY] - Update imports, construct workflows directly
│   ├── app.py                              [MODIFY] - Update container initialization
│   └── components/
│       ├── upgrade_panel.py                [MODIFY] - Inject services, construct workflows
│       ├── region_panel.py                 [MODIFY] - Update imports
│       └── network_panel.py                (unchanged)
│
├── workflows/                              [MODIFY] - Remove from DI, update constructor
│   ├── __init__.py                         [MODIFY]
│   ├── count_workflow.py                   [MODIFY] - Accept services directly, construct orchestrator
│   ├── spend_workflow.py                   [MODIFY] - Accept services directly, construct orchestrator
│   └── debug_monitor_workflow.py           [MODIFY] - Accept services directly, construct orchestrator
│
├── orchestration/                          [CREATE] - New folder for application coordination
│   ├── __init__.py                         [CREATE]
│   ├── upgrade_orchestrator.py             [MOVE from services/] [MODIFY] - Accept detector, create monitor internally
│   ├── progress_bar_monitor.py             [MOVE from core/] (unchanged)
│   ├── stop_conditions.py                  [MOVE from core/] (unchanged)
│   └── debug_frame_logger.py               [MOVE from core/] (unchanged)
│
├── services/                               [MODIFY] - Infrastructure singletons only
│   ├── __init__.py                         [MODIFY]
│   ├── app_data.py                         (unchanged)
│   ├── cache_service.py                    (unchanged)
│   ├── screenshot_service.py               (unchanged)
│   ├── window_interaction_service.py       (unchanged)
│   ├── locate_region_service.py            [MODIFY] - Update imports
│   └── network.py                          (unchanged)
│
├── detection/                              [CREATE] - New folder for CV algorithms
│   ├── __init__.py                         [CREATE]
│   ├── progress_bar_detector.py            [MOVE from core/] (unchanged)
│   └── locate_region.py                    [MOVE from core/] (unchanged)
│
├── utils/                                  [MODIFY] - Update imports
│   ├── common.py                           (unchanged)
│   ├── interaction.py                      [MODIFY] - Update imports
│   ├── visualization.py                    (unchanged)
│   └── network_context.py                  (unchanged)
│
├── debug/                                  [MODIFY] - Update imports
│   ├── app.py                              [MODIFY]
│   ├── components/                         [MODIFY]
│   ├── models.py                           (unchanged)
│   ├── progressbar_review_gui.py           [MODIFY]
│   └── utils.py                            [MODIFY]
│
├── container.py                            [MODIFY] - Remove 5 factory providers, keep 8 singletons
├── exceptions.py                           (unchanged)
└── logging_config.py                       (unchanged)
```

### Design Decisions

**Decision 1: Two-tier folder structure (Infrastructure vs Application)**
- **Why**: Aligns with constitutional principle "Separation of Concerns"
- **Trade-off**: More folders but crystal clear boundaries
- **Alternative considered**: Keep current structure (rejected - semantically confusing)

**Decision 2: Create `/orchestration` for application coordination**
- **Why**: Clearly distinguishes application logic from infrastructure services
- **Rationale**: Orchestrator, monitor, stop conditions are context-aware helpers, not reusable services
- **Alternative considered**: Keep in `/core` (rejected - "core" mixes algorithms with coordination)

**Decision 3: Create `/detection` for CV algorithms**
- **Why**: Groups stateless computer vision algorithms separately from stateful monitors
- **Rationale**: Detector and locate_region are pure algorithms with no application context
- **Alternative considered**: Keep detector in `/core` (rejected - would leave `/core` semantically mixed)

**Decision 4: Remove all factories from DI container**
- **Why**: Factories violate YAGNI (used for one-shot objects), Simplicity (triple indirection), and Explicit Over Implicit (hidden dependencies)
- **Rationale**: Workflows, orchestrator, and monitor have 1:1 lifecycles with their creators
- **Impact**: CLI/GUI signatures become more verbose (5-7 injected params) but dependencies are explicit

**Decision 5: UpgradeOrchestrator creates ProgressBarMonitor internally**
- **Why**: Monitor is a per-session helper, not a shared component
- **Rationale**: Orchestrator receives detector (singleton), creates fresh monitor per session
- **Benefit**: Simpler lifecycle, clearer ownership

**Decision 6: Workflows construct UpgradeOrchestrator directly**
- **Why**: Orchestrator lifetime = workflow lifetime (1:1 coupling)
- **Rationale**: No reusability benefit from factory pattern
- **Benefit**: Explicit dependency graph at call site

### Data Flow

**Before (Current):**
```
CLI/GUI
  ↓ inject
Workflow Factory (from container)
  ↓ call with runtime params
Workflow Instance
  ↓ inject
Orchestrator Factory (from container)
  ↓ call
Orchestrator Instance
  ↓ inject
Monitor Factory (from container)
  ↓ call
Monitor Instance
  ↓ inject
Detector Singleton (from container)
```

**After (Target):**
```
CLI/GUI
  ↓ inject services
Services (cache, screenshot, window, network, detector)
  ↓ direct construction
Workflow Instance
  ↓ direct construction
Orchestrator Instance (receives detector)
  ↓ creates internally
Monitor Instance (per session)
  ↓ uses
Detector Singleton
```

---

## Technical Approach

### Dependencies

**No new dependencies** - This is purely a refactoring effort.

**Existing dependencies affected:**
- `dependency-injector` - Container configuration simplified
- All test files - Import paths updated

### Integration Points

**DI Container (`container.py`):**
- Remove 5 factory providers (workflows, orchestrator, monitor)
- Keep 8 singleton providers (infrastructure only)
- Remove wiring for workflow modules
- Keep wiring for CLI/GUI components (now inject services directly)

**CLI Commands (`cli/upgrade_cli.py`):**
- Change from injecting workflow factories to injecting services
- Construct workflows directly with explicit parameters
- More verbose signatures (5-7 params) but explicit dependencies

**GUI Components (`gui/components/upgrade_panel.py`):**
- Same pattern as CLI - inject services, construct workflows
- Update async workflow execution to use direct construction

**Workflows (`workflows/*.py`):**
- Remove from DI container
- Accept services as constructor parameters
- Construct orchestrator directly (no longer injected)
- Pass runtime parameters directly (network_adapter_ids, max_attempts, etc.)

**UpgradeOrchestrator (`orchestration/upgrade_orchestrator.py`):**
- Accept `ProgressBarStateDetector` instead of `ProgressBarMonitor`
- Create `ProgressBarMonitor` internally in `run_upgrade_session()`
- Fresh monitor instance per session

**All Import Statements:**
- Update from `autoraid.core.X` to `autoraid.detection.X` or `autoraid.orchestration.X`
- Update from `autoraid.services.upgrade_orchestrator` to `autoraid.orchestration.upgrade_orchestrator`

### Error Handling

**Import Errors:**
- Strategy: Update all imports atomically in single commit per phase
- Fallback: Use IDE refactoring tools (rename/move) to catch all references

**Test Failures:**
- Strategy: Update tests immediately after each file move
- Validation: Run `pytest` after each phase to ensure no regressions

**DI Wiring Errors:**
- Strategy: Update container and all injection points together
- Validation: Test CLI commands and GUI panels after DI changes

### Testing Strategy

**Unit Tests:**
- Update import paths in all test files
- Update test fixtures to construct objects directly (no factory mocking)
- Verify behavior unchanged despite structural changes

**Integration Tests:**
- Update to construct workflows with mocked services
- Verify end-to-end flows still work (count, spend, debug monitor)

**Manual Testing:**
- Run CLI commands: `uv run autoraid count`, `uv run autoraid spend`
- Launch GUI: `uv run autoraid gui`
- Verify network adapter management, region selection, upgrade workflows

---

## Implementation Strategy

### Phase Breakdown

**Phase 0: Branch Setup**
- Create feature branch `refactor-services`
- Verify current tests pass as baseline

**Phase 1: Folder Structure Refactoring**
- Create `/orchestration` and `/detection` directories
- Move files from `/core` and `/services` to new locations
- Update all import statements across codebase
- Verify tests pass with new structure
- **Checkpoint**: New folder structure in place, imports updated, tests passing

**Phase 2: Remove Workflows from DI**
- Remove workflow factory providers from container
- Update CLI/GUI to inject services and construct workflows directly
- Update workflow constructors to accept services
- Update tests to construct workflows directly
- **Checkpoint**: Workflows constructed directly, 10 providers remaining (3 factories)

**Phase 3: Remove Orchestrator & Monitor from DI**
- Remove orchestrator and monitor factory providers from container
- Update orchestrator to accept detector and create monitor internally
- Update workflows to construct orchestrator directly
- Update CLI/GUI to inject detector (no longer orchestrator)
- Update tests to construct orchestrator/monitor with mocked services
- **Checkpoint**: Zero factories in container, 8 singletons only

**Phase 4: Documentation & Cleanup**
- Update CLAUDE.md with new architecture and folder structure
- Update import statements in test files
- Clean up any unused imports
- Run full test suite and verify coverage
- **Checkpoint**: Documentation updated, all tests passing, ready for merge

### Testing Approach

**After Each Phase:**
```bash
# Run all tests
uv run pytest

# Run specific test suites
uv run pytest test/unit/
uv run pytest test/integration/

# Verify CLI still works
uv run autoraid --help
uv run autoraid gui  # Quick GUI launch test (don't run workflows)

# Check for import errors
uv run python -c "from autoraid.cli.cli import autoraid; print('OK')"
```

**Coverage Validation:**
- No decrease in test coverage
- All critical paths tested (count, spend, debug monitor workflows)

### Deployment Notes

**Git Strategy:**
- Atomic commits per phase
- Descriptive commit messages referencing phase
- Squash merge to main after all phases complete

**Rollback Plan:**
- If issues discovered, revert entire branch
- Each phase is independently functional (can pause between phases)

**Communication:**
- Update CLAUDE.md before merging
- Notify any collaborators of structural changes

---

## Risks & Considerations

### Challenges

**Risk 1: Import Statement Sprawl**
- **Impact**: 40+ files need import updates
- **Mitigation**: Use IDE refactoring tools, grep verification
- **Fallback**: Manual import fixing with systematic file-by-file review

**Risk 2: Missed DI Injection Points**
- **Impact**: Runtime errors when services not injected
- **Mitigation**: Update all CLI commands and GUI components together
- **Validation**: Manual testing of all CLI commands and GUI panels

**Risk 3: Test Breakage**
- **Impact**: Integration tests may break with new construction patterns
- **Mitigation**: Update tests immediately after code changes in same commit
- **Validation**: Run `pytest` after every commit

**Risk 4: Verbose Function Signatures**
- **Impact**: CLI/GUI functions now inject 5-7 services instead of 1 workflow factory
- **Mitigation**: This is intentional (Explicit Over Implicit principle)
- **Acceptance Criteria**: Verbosity acceptable for clarity

### Performance

**No performance impact expected:**
- Same number of object instantiations (just different construction locations)
- Singleton services still cached in container
- Workflow/orchestrator/monitor construction overhead negligible (milliseconds)

### Security

**No security implications:**
- Pure refactoring, no logic changes
- No new external dependencies
- No changes to network adapter control or window interaction

### Technical Debt

**Debt Introduced:**
- None - this refactoring REDUCES technical debt

**Debt Removed:**
- Constitutional violations: YAGNI (factory overhead), Simplicity (triple indirection), Explicit Over Implicit (hidden dependencies)
- Semantic confusion: clear folder structure aligns with architecture
- Over-engineered DI: 62% reduction in factory complexity

**Future Improvements:**
- Phase 3 (not in this plan): Protocol abstraction for WindowInteractionService/ScreenshotService
- Potential: Extract common service injection pattern into helper function (evaluate after Phase 3)

---

## Validation Checklist

Before considering this refactoring complete:

- [ ] All tests passing (`pytest` shows 100% pass rate)
- [ ] No import errors when running CLI/GUI
- [ ] Manual testing of CLI commands successful (count, spend, debug monitor)
- [ ] Manual testing of GUI panels successful (upgrade, region, network)
- [ ] Container has exactly 8 singleton providers, 0 factory providers
- [ ] Folder structure matches target state (orchestration/, detection/ created)
- [ ] CLAUDE.md updated with new architecture
- [ ] No decrease in test coverage
- [ ] All constitutional violations addressed (YAGNI, Simplicity, Explicit)
- [ ] Git history clean with atomic commits per phase

---

## References

- **Constitutional Principles**: `.constitution/software-engineering.md`, `.constitution/python-standards.md`, `.constitution/testing.md`
- **Detailed Analysis**: `plans/di-holistic-evaluation.md`, `plans/di-service-evaluation.md`
- **Monitor/Orchestrator Removal**: `plans/monitor-orchestrator-injection-analysis.md`
- **Workflow Removal** (if exists): `plans/remove-workflow-injection-plan.md`, `plans/remove-workflow-injection-tasklist.md`
