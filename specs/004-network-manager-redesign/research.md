# Research: NetworkManager Service Redesign

**Feature**: NetworkManager Service Redesign
**Date**: 2025-10-22
**Phase**: 0 (Outline & Research)

## Purpose

This document consolidates research findings and design decisions for refactoring the NetworkManager service to encapsulate network state waiting logic. Since the user provided a detailed technical plan (`plans/nw-technical.md`), this research phase focuses on validating those decisions and documenting any additional patterns or best practices.

## Research Areas

### 1. Network State Verification Patterns

**Question**: What is the best practice for verifying network state changes with stability guarantees?

**Decision**: Require 2 consecutive successful connectivity checks (with expected state) before confirming state change

**Rationale**:
- Prevents false positives from transient network flickers (brief disconnect/reconnect)
- Based on clarification from `/speckit.clarify`: "Require sustained offline status for 2 consecutive checks by default before succeeding"
- Simple implementation: add counter that resets on state mismatch
- Low overhead: 2 checks at 0.5s intervals = minimal additional latency (0.5s max)
- Industry pattern: Kubernetes readiness probes use similar "consecutive success" threshold

**Alternatives Considered**:
- **Single check** (immediate completion): Rejected due to transient flicker risk
- **3+ consecutive checks**: Rejected as over-engineering for this use case (adds unnecessary latency)
- **Time-based stability** (sustained for N seconds): Rejected as more complex than check-count approach

**Implementation Impact**:
- `wait_for_network_state()` maintains a consecutive success counter
- Counter resets to 0 when state doesn't match expected
- Counter increments when state matches expected
- Complete when counter reaches 2

---

### 2. Multiple Adapter Handling

**Question**: Should `toggle_adapters()` accept multiple adapter IDs, and how should it handle them?

**Decision**: Accept list of adapter IDs, toggle all sequentially, succeed if at least one succeeds

**Rationale**:
- Based on clarification from `/speckit.clarify`: "Support multiple adapter IDs in a single operation (toggle all specified adapters together)"
- Matches real-world usage: workflows often need to disable multiple adapters (e.g., WiFi + Ethernet)
- Technical plan explicitly shows `adapter_ids: list[str]` parameter
- Graceful degradation: log warnings for invalid IDs, continue with valid ones (per clarification)

**Alternatives Considered**:
- **Single adapter only**: Rejected, doesn't match usage patterns in workflows
- **Parallel toggling**: Rejected, sequential is simpler and WMI operations are fast (<100ms each)
- **All-or-nothing semantics**: Rejected, graceful degradation is more robust

**Implementation Impact**:
- Parameter: `adapter_ids: list[str]` (accepts multiple)
- Loop over IDs calling `toggle_adapter(id, enable)` for each
- Track success count, return `True` if count > 0
- Log warning for each invalid ID (per clarification Q2)

---

### 3. Error Handling Strategy

**Question**: How should the service handle various error conditions identified in clarifications?

**Decision Summary**:

| Condition | Behavior | Rationale |
|-----------|----------|-----------|
| **Multiple network paths** (internet remains after disabling adapters) | Report warning/error | Per clarification Q1: developers need to know network isn't fully offline |
| **Invalid adapter IDs** | Log warning, continue with valid IDs | Per clarification Q2: graceful degradation |
| **Oscillating network state** | Require 2 consecutive checks | Per clarification Q3: prevent false positives from flickers |
| **No adapters available** | Succeed silently (no-op) | Per clarification Q5: nothing to toggle, not an error |
| **Timeout waiting for state change** | Raise NetworkAdapterError | Existing pattern, clear error message |

**Rationale**:
- All decisions based on explicit clarifications from `/speckit.clarify` session
- Consistent error handling: warnings for degraded operation, errors for failures
- Graceful degradation preferred over fail-fast (aligns with Constitution Principle I: Simplicity)

**Implementation Impact**:
- After toggling adapters, if `wait=True`:
  - Check network state
  - If still online after disabling: log warning "Internet still accessible via other network paths"
  - If offline as expected: proceed normally
- Invalid adapter IDs: filter before toggling, log warning for each invalid ID
- No adapters: early return with success (no-op)

---

### 4. Dependency Injection Best Practices

**Question**: What's the best pattern for wiring NetworkManager into CLI and GUI layers?

**Decision**: Singleton provider in container, `@inject` decorator on functions, `Provide[]` for parameters

**Rationale**:
- Existing AutoRaid pattern: `dependency-injector` library with `DeclarativeContainer`
- Technical plan shows exact wiring: `providers.Singleton(NetworkManager)` in container
- Singleton appropriate: NetworkManager has no per-request state, interacts with OS-level resources
- CLI example from technical plan matches existing wiring patterns in `upgrade_cli.py`

**Pattern**:
```python
# container.py
class Container(containers.DeclarativeContainer):
    network_manager = providers.Singleton(NetworkManager)

# CLI usage
@inject
def list(
    network_manager: NetworkManager = Provide[Container.network_manager],
):
    adapters = network_manager.get_adapters()
    # Display with Rich table (CLI layer)

# GUI usage
@inject
def create_network_panel(
    network_manager: NetworkManager = Provide[Container.network_manager],
) -> None:
    # Use injected manager
```

**Alternatives Considered**:
- **Factory provider**: Rejected, NetworkManager has no per-instance state
- **Direct instantiation in GUI**: Rejected, breaks DI pattern and testing
- **Global singleton**: Rejected, DI container provides better testability

**Implementation Impact**:
- Add one line to `container.py`: `network_manager = providers.Singleton(NetworkManager)`
- Update CLI commands: add `@inject` decorator, use `Provide[]` parameter
- Update GUI component: replace `NetworkManager()` with injected parameter

---

### 5. Testing Strategy (Smoke Tests)

**Question**: What smoke tests are needed to verify new functionality without strict TDD?

**Decision**: 6 targeted smoke tests for new methods, mock external dependencies

**Rationale**:
- User requirement: "We do not follow strict TDD, but require smoke tests"
- Constitution Principle III: Pragmatic Testing - focus where it provides most value
- Technical plan lists 6 specific test cases covering core logic paths
- Tests verify timeout defaults, waiting behavior, and parameter handling

**Test List** (from technical plan):
1. `test_toggle_adapters_without_wait`: Returns immediately when `wait=False`
2. `test_toggle_adapters_with_wait_success`: Calls `wait_for_network_state` when `wait=True`
3. `test_toggle_adapters_uses_default_timeout_disable`: 5s timeout for disable
4. `test_toggle_adapters_uses_default_timeout_enable`: 10s timeout for enable
5. `test_wait_for_network_state_immediate_success`: Returns when state matches
6. `test_wait_for_network_state_timeout`: Raises NetworkAdapterError on timeout

**Mocking Pattern** (from technical plan):
```python
with patch.object(manager, 'toggle_adapter', return_value=True):
    with patch.object(manager, 'wait_for_network_state'):
        manager.toggle_adapters(["0"], enable=False, wait=True)
        manager.wait_for_network_state.assert_called_once_with(
            expected_online=False,
            timeout=5.0,
        )
```

**Alternatives Considered**:
- **Integration tests with real adapters**: Rejected, flaky and requires admin rights
- **100% code coverage**: Rejected, over-engineering for refactor (Constitution Principle V)
- **No tests**: Rejected, violates pragmatic testing requirement

**Implementation Impact**:
- Create `test/unit/platform/test_network_manager.py`
- Use `unittest.mock.patch.object` for mocking
- Test core paths: wait=True/False, timeout defaults, state verification, error handling
- Skip testing trivial display logic in CLI layer (principle allows)

---

## Technology Stack Validation

**Existing Dependencies** (no changes):
- `wmi`: Windows Management Instrumentation for adapter control
- `dependency-injector`: DI container framework
- `rich`: Terminal UI (CLI layer only, not in service)
- `loguru`: Structured logging
- `pytest`: Testing framework

**No New Dependencies Required**: This is a refactoring using existing libraries.

---

## Design Patterns Applied

### 1. Service Layer Pattern
- **NetworkManager** is a pure service: business logic, no display/interaction
- Display logic (Rich tables) lives in CLI layer
- Interaction logic (prompts) lives in CLI layer
- GUI consumes service via injection

### 2. Encapsulation Pattern
- Waiting logic encapsulated in `wait_for_network_state()` method
- Callers use simple `wait=True` parameter instead of manual loops
- Implementation details (polling interval, logging frequency) hidden

### 3. Graceful Degradation Pattern
- Invalid adapter IDs: log warning, continue with valid IDs
- No adapters available: succeed silently (no-op)
- Multiple network paths: warn but don't block (developer awareness)

### 4. Dependency Injection Pattern
- Constructor injection via `dependency-injector`
- Singleton lifecycle for stateless service
- Testable via mock injection

---

## Open Questions

**None** - All design decisions resolved via:
1. User-provided technical plan (`plans/nw-technical.md`)
2. Clarifications from `/speckit.clarify` session (5 edge cases resolved)
3. Existing AutoRaid architecture patterns (DI, service layer, testing)

---

## Summary

This redesign is straightforward: refactor existing NetworkManager to encapsulate waiting logic, remove display methods, and update DI wiring. All design decisions are validated against:

- **User requirements**: Smoke tests, maintainability priority
- **Constitution principles**: Simplicity, readability, pragmatic testing, debug-friendly, incremental
- **Existing patterns**: Service layer, DI, Windows-only constraints
- **Clarifications**: All 5 edge cases resolved with specific behaviors

**Next Phase**: Proceed to Phase 1 (Design & Contracts) to generate data model, service contract, and quickstart guide.
