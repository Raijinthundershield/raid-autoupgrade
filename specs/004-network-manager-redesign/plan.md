# Implementation Plan: NetworkManager Service Redesign

**Branch**: `004-network-manager-redesign` | **Date**: 2025-10-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-network-manager-redesign/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Redesign the NetworkManager service to encapsulate network state waiting logic within a unified `toggle_adapters()` method, eliminating duplicated waiting loops across all workflows. The redesign separates display/interaction logic from core service functionality, moving Rich table formatting and interactive prompts to the CLI layer. This refactoring provides automatic state verification with configurable timeouts (5s disable, 10s enable by default) and supports both blocking and non-blocking operation modes for different use cases (workflows vs cleanup code).

**Technical Approach**: Refactor existing NetworkManager class to add `wait_for_network_state()` and enhanced `toggle_adapters()` methods, remove display methods (`display_adapters()`, `select_adapters()`, etc.), and update dependency injection wiring in CLI and GUI layers.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: dependency-injector (DI), wmi (Windows network adapter control), rich (CLI display - CLI layer only)
**Storage**: diskcache (existing, not modified by this feature)
**Testing**: pytest (with smoke tests for service methods, not strict TDD)
**Target Platform**: Windows only (WMI-based adapter management)
**Project Type**: Single project with service-based architecture and DI
**Performance Goals**: Network state verification within 100ms (non-blocking mode), state change completion within configured timeouts (5s/10s defaults)
**Constraints**:
- Maintain 100% backward compatibility for existing CLI commands and GUI panels
- No breaking changes to public API surface
- Zero display/formatting dependencies in service layer (no Rich in NetworkManager)
- Network state must be stable for 2 consecutive checks before confirming (prevents transient flickers)
**Scale/Scope**:
- Single NetworkManager service class (~200-300 LOC)
- 3+ existing workflows to refactor (UpgradeOrchestrator workflows)
- 6 new smoke tests (unit tests for new methods)
- 2 CLI commands to update (display logic migration)
- 1 GUI component to update (dependency injection)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Simplicity Over Complexity ✅ PASS

**Assessment**: The redesign **reduces** complexity by consolidating waiting logic into a single location, replacing 10-15 lines of duplicated timeout handling with a single `wait=True` parameter. No new abstractions are introduced - just better encapsulation of existing behavior.

**Evidence**:
- Eliminates 3+ instances of manual waiting loops across workflows
- Method signature is straightforward: `toggle_adapters(ids, enable, wait=False, timeout=None)`
- No inheritance changes, no metaprogramming, no magic
- Existing `toggle_adapter()` (singular) remains unchanged for single-adapter use cases

### Principle II: Readability First ✅ PASS

**Assessment**: Constants with clear names and units (`DEFAULT_DISABLE_TIMEOUT = 5.0`, `CHECK_INTERVAL = 0.5`), method names describe exact behavior (`wait_for_network_state`, `toggle_adapters`), and the technical plan includes clear docstrings.

**Evidence**:
- Magic numbers replaced with named constants: `CHECK_INTERVAL = 0.5  # seconds`
- Method names are self-documenting: `wait_for_network_state(expected_online, timeout)`
- Error messages include context: `"Timeout waiting for network to be {online|offline} after {timeout}s"`
- Separation of concerns is explicit: service layer vs CLI layer vs GUI layer

### Principle III: Pragmatic Testing ✅ PASS

**Assessment**: Smoke tests target core logic (state waiting, timeout handling, parameter defaults) without requiring 100% coverage. GUI injection and CLI display changes rely on manual testing. Matches user requirement: "We do not follow strict TDD, but require smoke tests."

**Evidence**:
- 6 targeted smoke tests for new methods (`test_toggle_adapters_without_wait`, `test_wait_for_network_state_timeout`, etc.)
- Tests use mocking for external dependencies (`toggle_adapter`, network checks)
- No tests for trivial display logic in CLI layer (principle allows skipping)
- Tests verify timeout defaults and waiting behavior (high-value coverage)

### Principle IV: Debug-Friendly Architecture ✅ PASS

**Assessment**: Maintains existing debug infrastructure (`--debug` flag, cache system, loguru logging). New wait logic includes progress logging every 2s and clear error messages with timeout context.

**Evidence**:
- `wait_for_network_state()` logs progress every 2 seconds during waiting
- Error messages include which operation failed and timeout used: `"Timeout waiting for network to be offline after 5.0s"`
- Existing debug artifacts (screenshots, metadata) remain available
- Rich terminal output preserved in CLI layer (not removed, just relocated)

### Principle V: Incremental Improvement Over Perfection ✅ PASS

**Assessment**: Implements minimum feature to solve identified pain point (duplicated waiting logic). Does not add speculative features like retry strategies, exponential backoff, or advanced network diagnostics. Backward compatible - existing code continues to work.

**Evidence**:
- Solves current problem: eliminates manual waiting loops in workflows
- No over-engineering: simple polling with linear timeout, no complex retry logic
- Backward compatible: existing `toggle_adapter()` calls unchanged
- New `wait` parameter defaults to `False` (opt-in behavior)
- Migration path documented but not enforced (workflows can adopt incrementally)

**Gate Result**: ✅ **PASS** - All 5 constitution principles satisfied, no violations to justify

## Project Structure

### Documentation (this feature)

```
specs/004-network-manager-redesign/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (design decisions and patterns)
├── data-model.md        # Phase 1 output (entities and state model)
├── quickstart.md        # Phase 1 output (developer guide for using new API)
├── contracts/           # Phase 1 output (NetworkManager service contract)
│   └── network-manager-service.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# Single project structure (existing AutoRaid architecture)
src/autoraid/
├── platform/
│   └── network.py             # [MODIFIED] NetworkManager service implementation
├── services/
│   └── upgrade_orchestrator.py  # [MODIFIED] Use new wait=True pattern
├── cli/
│   └── network_cli.py         # [MODIFIED] Display logic moved here from service
├── gui/
│   └── components/
│       └── network_panel.py   # [MODIFIED] Add @inject decorator
└── container.py               # [MODIFIED] Register network_manager singleton

test/
├── unit/
│   └── platform/
│       └── test_network_manager.py  # [NEW] Smoke tests for new methods
└── integration/
    └── test_upgrade_orchestrator.py  # [MODIFIED] Test new wait=True pattern

docs/
└── CLAUDE.md                  # [MODIFIED] Document NetworkManager as service layer
```

**Structure Decision**: Single project structure with service-based architecture. NetworkManager lives in `platform/` layer (platform-specific Windows WMI code), with DI registration in `container.py`. Display logic moves to `cli/` layer, GUI components updated for injection in `gui/components/`. Testing follows existing structure: `test/unit/platform/` for service tests, `test/integration/` for orchestrator tests.

## Complexity Tracking

*No violations identified - all constitution principles pass.*
