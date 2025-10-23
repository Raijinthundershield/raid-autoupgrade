# Research: State Monitor Redesign

**Feature**: State Monitor Redesign
**Date**: 2025-10-23
**Status**: Complete

## Overview

This refactoring uses existing AutoRaid patterns and requires no new technology research. All architectural decisions are based on established project conventions.

## Research Questions

### Q1: Pattern for separating CV from business logic?

**Decision**: Dependency Injection with layered architecture

**Rationale**:
- AutoRaid already uses `dependency-injector` library throughout
- Existing pattern: services inject dependencies via constructor
- Core layer should have no I/O, services orchestrate, platform handles OS-specific code
- Constitution Principle II mandates separation of concerns

**Alternatives Considered**:
- Callback pattern: Rejected (more complex, harder to test)
- Direct coupling: Rejected (violates separation of concerns)
- Strategy pattern: Rejected (unnecessary abstraction for single implementation)

**References**:
- [CLAUDE.md: Architecture](../../CLAUDE.md#architecture)
- [container.py](../../src/autoraid/container.py) - Existing DI configuration

---

### Q2: How to make components independently testable?

**Decision**: Mock detector in monitor tests, use fixture images in detector tests

**Rationale**:
- Python's `unittest.mock.Mock` is standard library, no new dependencies
- AutoRaid already has fixture images in `test/fixtures/images/`
- Constitution Principle IV: Pragmatic testing with ≥90% coverage for core logic
- Mocking enables testing business logic without CV operations

**Alternatives Considered**:
- Dependency injection of mock: Rejected (over-engineering for internal refactoring)
- Test doubles (hand-written fakes): Rejected (more maintenance overhead)
- Integration tests only: Rejected (doesn't meet independent testability requirement)

**References**:
- [test/unit/core/test_state_machine.py](../../test/unit/core/test_state_machine.py) - Existing test patterns
- [test/fixtures/images/](../../test/fixtures/images/) - Existing fixture library

---

### Q3: Lifecycle management for new components?

**Decision**: Detector as Singleton, Monitor as Factory (existing DI pattern)

**Rationale**:
- Detector is stateless → Singleton (consistent with ScreenshotService, CacheService)
- Monitor is stateful per-workflow → Factory (consistent with UpgradeOrchestrator pattern)
- Matches existing container configuration conventions
- Constitution Principle I: Use existing patterns, avoid new abstractions

**Alternatives Considered**:
- Both as Factory: Rejected (detector has no per-request state)
- Both as Singleton: Rejected (monitor needs fresh state per workflow)
- Manual instantiation: Rejected (bypasses DI, breaks testability)

**References**:
- [container.py](../../src/autoraid/container.py) - Lines 35-69 show existing Singleton/Factory usage

---

### Q4: API design for monitor (properties vs methods)?

**Decision**: Use `@property` decorators for read-only state access

**Rationale**:
- Python convention: Properties for computed/read-only values
- Constitution Principle III: Readability First - properties self-document intent
- Prevents accidental mutation (`monitor.fail_count = 5` would be a bug)
- Matches existing service patterns in AutoRaid

**Alternatives Considered**:
- Public mutable attributes: Rejected (violates encapsulation, error-prone)
- Getter methods (`get_fail_count()`): Rejected (un-Pythonic, verbose)
- Dataclass with frozen=True: Rejected (monitor needs internal mutability)

**References**:
- [services/cache_service.py](../../src/autoraid/services/cache_service.py) - Uses properties for derived values
- PEP 8 and Python idioms for property usage

---

### Q5: Logging strategy for state transitions?

**Decision**: Use loguru at DEBUG level with structured context

**Rationale**:
- AutoRaid already uses loguru globally (configured in CLI entry point)
- DEBUG level matches existing convention for detailed operational info
- Structured logging enables filtering by component in production
- Constitution Principle V: Debug-Friendly Architecture

**Alternatives Considered**:
- INFO level: Rejected (too verbose for normal operation)
- No logging: Rejected (violates FR-018, FR-019 requirements)
- Custom logger: Rejected (breaks consistency with existing codebase)

**References**:
- [CLAUDE.md: Dependencies](../../CLAUDE.md#dependencies) - Loguru is documented
- [cli/cli.py](../../src/autoraid/cli/cli.py) - Logger initialization with --debug flag

---

## Technology Decisions

### No New Dependencies Required

All implementation needs are met by existing dependencies:

| Requirement | Technology | Status |
|-------------|-----------|--------|
| State enums | Python stdlib `enum.Enum` | ✅ Existing |
| Detector class | Plain Python class | ✅ No new deps |
| Monitor class | Plain Python class | ✅ No new deps |
| DI container | `dependency-injector` | ✅ Already in pyproject.toml |
| Mocking | `unittest.mock` | ✅ Python stdlib |
| Test fixtures | Existing images | ✅ test/fixtures/images/ |
| Logging | `loguru` | ✅ Already in pyproject.toml |
| Image arrays | `numpy` | ✅ Already in pyproject.toml |
| CV operations | `opencv-python` | ✅ Already in pyproject.toml |

**Justification**: Constitution Principle VI mandates minimal dependencies. Internal refactoring should not require new libraries.

---

## Best Practices Applied

### 1. SOLID Principles (from technical draft)
- **Single Responsibility**: Detector=CV, Monitor=Logic
- **Open/Closed**: Can swap detector implementation without changing monitor
- **Liskov Substitution**: Any detector with same interface works
- **Interface Segregation**: Minimal interfaces (1 method detector, 3 properties monitor)
- **Dependency Inversion**: Monitor depends on detector abstraction

### 2. Python Idioms
- Properties for read-only access
- Type hints on all public methods
- Docstrings with Args/Returns/Raises sections
- Enums for state representation
- `@property` instead of getter methods

### 3. Testing Strategies
- Unit tests for each component independently
- Integration tests for workflow parity
- Mock external dependencies (detector in monitor tests)
- Use real fixtures for CV testing
- ≥90% coverage target

---

## Implementation Notes

### Enum Naming Convention
- Enum class names: PascalCase (`ProgressBarState`, `StopReason`)
- Enum values: SCREAMING_SNAKE_CASE (`MAX_ATTEMPTS_REACHED`, `CONNECTION_ERROR`)
- Enum string values: lowercase with underscores (`"max_attempts_reached"`)

**Rationale**: Matches PEP 8 and existing AutoRaid conventions (see `NetworkState` in platform/network.py)

### Deque Usage
- `collections.deque(maxlen=4)` for state history
- Automatic eviction of old states (FIFO queue)
- O(1) append and length check

**Rationale**: Existing state machine already uses deque, proven pattern for this use case

### Error Handling
- `ValueError` for invalid inputs (null/empty images, max_attempts≤0)
- No custom exceptions needed (Principle I: Simplicity)
- Clear error messages with context

**Rationale**: ValueError is Python convention for bad argument values

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| API changes break orchestrator | Low | High | Integration tests verify parity |
| Logging too verbose | Low | Low | DEBUG level only, opt-in via --debug flag |
| Test coverage gaps | Low | Medium | pytest-cov with 90% threshold gates |
| Behavior divergence | Low | High | Behavior parity tests compare old vs new |

---

## References

1. **AutoRaid Documentation**
   - [CLAUDE.md](../../CLAUDE.md) - Architecture and conventions
   - [Constitution](../../.specify/memory/constitution.md) - Design principles

2. **Existing Code Patterns**
   - [container.py](../../src/autoraid/container.py) - DI configuration
   - [core/state_machine.py](../../src/autoraid/core/state_machine.py) - Current implementation
   - [services/upgrade_orchestrator.py](../../src/autoraid/services/upgrade_orchestrator.py) - Orchestration pattern

3. **Test Patterns**
   - [test/unit/core/test_state_machine.py](../../test/unit/core/test_state_machine.py) - Existing tests
   - [test/integration/test_upgrade_orchestrator.py](../../test/integration/test_upgrade_orchestrator.py) - Integration tests

4. **Python Documentation**
   - [PEP 8](https://peps.python.org/pep-0008/) - Style guide
   - [unittest.mock](https://docs.python.org/3/library/unittest.mock.html) - Mocking library
   - [enum](https://docs.python.org/3/library/enum.html) - Enum usage

---

## Conclusion

No new research required. All architectural decisions leverage existing AutoRaid patterns:
- Dependency injection (existing)
- Layered architecture (existing)
- Pragmatic testing with mocks and fixtures (existing)
- Loguru for DEBUG logging (existing)
- Python stdlib and existing dependencies (no additions)

Ready to proceed with Phase 1 implementation.
