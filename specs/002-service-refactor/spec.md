# Feature Specification: Service-Based Architecture Refactoring

**Feature Branch**: `002-service-refactor`
**Created**: 2025-10-17
**Status**: Draft
**Input**: User description: "Refactor autoupgrade tool into service-based architecture with focused single-purpose services for improved testability and maintainability"

## Clarifications

### Session 2025-10-17

- Q: What is the error handling strategy for service-level failures? → A: Fail fast with clear error messages - Services raise exceptions immediately on error with descriptive messages; let caller (orchestrator or CLI) decide recovery
- Q: Which services should be singletons vs factories? → A: Singletons: CacheService, ScreenshotService, WindowInteractionService, LocateRegionService; Factories: UpgradeStateMachine, UpgradeOrchestrator
- Q: What is the rollback strategy if a refactoring phase introduces bugs or breaks tests? → A: No rollback - Fix forward by debugging and correcting the phase implementation until tests pass
- Q: What logging should services produce in normal (non-debug) mode? → A: Info-level workflow milestones - Services log high-level events (e.g., "Starting count workflow", "Captured screenshot", "Upgrade completed") in normal mode
- Q: What size should the state deque be? → A: Size 4 - Match the consecutive state requirement (4 standby or 4 connection_error triggers stop)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Core Upgrade Logic Testing (Priority: P1)

As a developer, I need to test the upgrade counting state machine with fixture images from the test suite without requiring a running Raid window, so that I can verify state transitions, failure counts, and stop conditions work correctly in isolation.

**Why this priority**: This is the most critical piece of logic in the tool - counting upgrade failures. Making it testable with fixture images enables regression testing and makes development faster.

**Independent Test**: Can be fully tested by creating an UpgradeStateMachine instance, feeding it a sequence of test images representing different progress bar states (fail/progress/standby/connection_error), and asserting that fail counts and stop reasons match expected values. Delivers a testable core business logic without GUI dependencies.

**Acceptance Scenarios**:

1. **Given** a sequence of progress bar images showing fail states, **When** fed to the state machine, **Then** the state machine correctly counts the number of failures
2. **Given** a sequence ending with 4 consecutive standby states, **When** processed by the state machine, **Then** it returns stop reason "upgraded"
3. **Given** a sequence ending with 4 consecutive connection_error states, **When** processed by the state machine, **Then** it returns stop reason "connection_error"
4. **Given** max attempts set to 10 and 10 fail states, **When** processed by the state machine, **Then** it returns stop reason "max_attempts_reached"

---

### User Story 2 - Service Isolation for Debugging (Priority: P2)

As a developer debugging an issue, I need clear service boundaries with logging at entry/exit points, so that I can trace the flow of data through the system and identify where problems occur without reading through monolithic functions.

**Why this priority**: Debugging is a frequent activity when issues arise. Clear service boundaries with logging make troubleshooting faster and reduce the cognitive load of understanding complex interactions.

**Independent Test**: Can be tested by running a count workflow in normal mode (see INFO-level milestones like "Starting count workflow", "Captured screenshot") and with debug mode enabled (see detailed entry/exit points like "ScreenshotService.capture_window() called", "ScreenshotService.capture_window() returned screenshot of size 1920x1080"). Delivers improved developer experience for debugging.

**Acceptance Scenarios**:

1. **Given** normal mode, **When** running a count workflow, **Then** logs show high-level workflow milestones at INFO level
2. **Given** debug mode enabled, **When** running a count workflow, **Then** logs show detailed entry/exit points for each service method call at DEBUG level
3. **Given** debug mode enabled, **When** an error occurs in a service, **Then** logs show which service and method failed with relevant context
4. **Given** the dependency injection container, **When** inspecting wiring, **Then** all service dependencies are explicitly documented and visible

---

### User Story 3 - Unit Testing with Mocks (Priority: P2)

As a developer writing tests, I need to inject mock services as dependencies, so that I can test individual services in isolation without external dependencies like windows, screenshots, or file I/O.

**Why this priority**: Enables fast unit tests that don't require the full application stack. This makes TDD practical and reduces test execution time.

**Independent Test**: Can be tested by creating a test that injects a mock ScreenshotService into UpgradeOrchestrator, runs a workflow, and verifies that the orchestrator calls the expected service methods. Delivers a testable architecture with fast feedback loops.

**Acceptance Scenarios**:

1. **Given** a mock ScreenshotService, **When** injected into UpgradeOrchestrator, **Then** the orchestrator can execute workflows without requiring a real window
2. **Given** a mock WindowInteractionService, **When** testing the click workflow, **Then** the test can verify click coordinates without executing actual GUI clicks
3. **Given** a mock NetworkManager, **When** testing count workflow, **Then** the test can verify network disable/enable calls without changing actual network state

---

### User Story 4 - Unchanged User Workflows (Priority: P1)

As a user of the autoupgrade tool, I need the existing CLI commands and workflows to continue working exactly as before, so that my existing scripts and muscle memory remain valid after the refactoring.

**Why this priority**: User-facing behavior must not change. Breaking existing workflows would force users to relearn the tool and potentially break automation scripts.

**Independent Test**: Can be tested by running existing CLI commands (`autoraid upgrade count -n 1`, `autoraid upgrade spend --fail-count 5`) and verifying they produce the same output, interact with the Raid window identically, and use the same cache keys. Delivers backward compatibility and zero user disruption.

**Acceptance Scenarios**:

1. **Given** an existing command `autoraid upgrade count -n 1`, **When** executed after refactoring, **Then** it produces the same output format and behavior as before
2. **Given** cached regions from the old code, **When** the refactored code runs, **Then** it loads and uses those cached regions successfully
3. **Given** debug mode enabled, **When** running workflows, **Then** screenshots and metadata are saved to the same locations with the same naming conventions

---

### User Story 5 - Phased Rollout Safety (Priority: P1)

As a developer performing the refactoring, I need each refactoring phase to leave the code in a working state with passing tests, so that I can stop at any checkpoint and have a functional tool without being forced to complete the entire refactoring.

**Why this priority**: This is a large refactoring for a one-person project. Having safe checkpoints prevents "broken code for weeks" situations and allows incremental progress. Phases are implemented with supervision, fixing issues forward rather than rolling back.

**Independent Test**: Can be tested by completing Phase 1 (extract state machine), running the full test suite, and executing manual smoke tests against a live Raid window. Delivers incremental progress with continuous functionality.

**Acceptance Scenarios**:

1. **Given** Phase 0 completed (DI container), **When** running the tool, **Then** all existing functionality works as before
2. **Given** Phase 1 completed (state machine extracted), **When** running tests, **Then** all tests pass and new unit tests for state machine exist
3. **Given** any phase completed, **When** running integration tests, **Then** count and spend workflows execute successfully
4. **Given** a phase introduces test failures, **When** debugging, **Then** issues are fixed forward in the same phase until all tests pass

---

### User Story 6 - Thin CLI Commands (Priority: P3)

As a developer reading CLI code, I need commands to be 10-20 lines of simple glue code (parse args → inject orchestrator → call workflow → display results), so that I can understand what each command does at a glance without wading through business logic.

**Why this priority**: Improves long-term maintainability and makes it easy to add new commands. Lower priority because it's a quality-of-life improvement that doesn't affect functionality.

**Independent Test**: Can be tested by reviewing the refactored CLI files and measuring lines of code per command. Each command should have <20 lines excluding imports and docstrings. Delivers improved code readability.

**Acceptance Scenarios**:

1. **Given** a refactored CLI command, **When** reading the function, **Then** it contains only argument parsing, orchestrator injection, workflow call, and result display
2. **Given** business logic in the orchestrator, **When** adding a new CLI command, **Then** the new command can reuse existing workflow methods with minimal code
3. **Given** CLI commands, **When** reviewing dependencies, **Then** CLI files depend only on Click, the orchestrator, and display utilities (no direct imports of screenshot/cache/state services)

---

### Edge Cases

- **Service initialization failure**: Services raise descriptive exceptions immediately (e.g., CacheService raises `CacheInitializationError` if cache directory creation fails). Orchestrator or CLI catches and displays error to user.
- **Cleanup on shutdown**: Services do not implement cleanup logic. Orchestrator ensures NetworkManager re-enables adapters in a finally block. If orchestrator crashes, adapters remain disabled (user must manually re-enable).
- **Hard-coded dependencies in services**: Not allowed by design. All services must accept dependencies via constructor parameters to enable mocking.
- **Unexpected state transitions**: State machine logs warning and returns state as "unknown". Continues processing unless it causes a stop condition failure.
- **Container misconfiguration**: Container raises `DependencyResolutionError` with details about missing or circular dependencies during initialization. Application fails to start.
- **Duplicate debug metadata**: Each service logs with its own name prefix (e.g., `[ScreenshotService]`, `[CacheService]`). Orchestrator coordinates debug file writes to avoid conflicts.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST extract upgrade state machine logic into a service that accepts progress bar images as input and returns fail count and stop reason
- **FR-002**: System MUST create a CacheService that generates window-size-based cache keys and provides save/load methods for regions and screenshots
- **FR-003**: System MUST create a ScreenshotService that captures window screenshots, checks window existence, and extracts regions of interest from full screenshots
- **FR-004**: System MUST create a LocateRegionService that attempts automatic region detection first, falls back to manual selection, and caches results via CacheService
- **FR-005**: System MUST create a WindowInteractionService that clicks region centers and activates the Raid window before interactions
- **FR-006**: System MUST create an UpgradeOrchestrator service that coordinates all other services to execute count and spend workflows
- **FR-007**: System MUST implement a dependency injection container that wires services with explicit constructor dependencies
- **FR-008**: Services MUST declare dependencies in constructors (e.g., `__init__(self, screenshot_service: ScreenshotService)`)
- **FR-009**: CLI commands MUST be refactored to inject the orchestrator, call workflow methods, and display results (max 20 lines per command excluding imports)
- **FR-010**: System MUST maintain existing cache key formats (`regions_{width}_{height}`) for backward compatibility
- **FR-011**: System MUST maintain existing debug mode behavior (save screenshots and metadata to `cache-raid-autoupgrade/debug/`)
- **FR-012**: System MUST preserve existing CLI command signatures and output formats (`autoraid upgrade count`, `autoraid upgrade spend`) and cache key formats (see FR-010)
- **FR-013**: State machine MUST track progress bar states (fail/progress/standby/connection_error/unknown) using color detection
- **FR-014**: State machine MUST count transitions to "fail" state and stop on max attempts, 4 consecutive "standby" states, or 4 consecutive "connection_error" states (deque size defined in FR-025)
- **FR-015**: Each service MUST be in a separate file under `src/autoraid/services/` directory
- **FR-016**: Services MUST log high-level workflow milestones (e.g., "Starting count workflow", "Captured screenshot") at INFO level in normal mode, and detailed entry/exit points at DEBUG level when debug mode is enabled
- **FR-017**: System MUST support testing with fixture images from `test/images/` without requiring a live Raid window
- **FR-018**: Refactoring MUST be performed in 9 sequential phases where each phase leaves code in a working state with passing tests
- **FR-019**: System MUST keep ProgressBarStateDetector as pure functions without changes (already well-designed)
- **FR-020**: Network management MUST remain as a separate module (not part of services) and be used by the orchestrator
- **FR-021**: Services MUST raise descriptive exceptions immediately on error (fail fast) rather than attempting silent recovery or fallback behavior
- **FR-022**: Orchestrator MUST ensure network adapters are re-enabled in a finally block, even if workflow fails
- **FR-023**: DependencyContainer MUST register CacheService, ScreenshotService, WindowInteractionService, and LocateRegionService as singletons (single shared instance)
- **FR-024**: DependencyContainer MUST register UpgradeStateMachine and UpgradeOrchestrator as factories (new instance per request)
- **FR-025**: UpgradeStateMachine MUST maintain a deque of size 4 to track recent progress bar states for detecting stop conditions

### Key Entities

- **UpgradeStateMachine**: Represents the state tracking logic for upgrade attempts. Maintains a deque of size 4 to track recent states, counts fail transitions, and determines stop conditions (4 consecutive standby or connection_error states). Does not perform I/O or interact with windows.
- **CacheService**: Represents caching operations. Generates cache keys based on window dimensions, saves/loads regions and screenshots, provides cache directory paths.
- **ScreenshotService**: Represents window screenshot operations. Captures full window screenshots, checks window existence, extracts regions of interest from screenshots based on region coordinates.
- **LocateRegionService**: Represents region detection workflow. Coordinates automatic template matching, manual user selection fallback, and caching via CacheService.
- **WindowInteractionService**: Represents GUI automation. Handles window activation and clicking at specified coordinates within the Raid window.
- **UpgradeOrchestrator**: Represents the full workflow coordination. Manages network state, coordinates service calls, implements count_workflow() and spend_workflow() methods, handles debug output.
- **DependencyContainer**: Represents service wiring configuration. Registers stateful services (CacheService, ScreenshotService, WindowInteractionService, LocateRegionService) as singletons and stateless workflow services (UpgradeStateMachine, UpgradeOrchestrator) as factories. Resolves dependencies and provides service instances to CLI commands.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: State machine unit tests can execute with fixture images in under 1 second for the full test suite (no window dependencies)
- **SC-002**: Each service file is under 200 lines of code (excluding imports and docstrings)
- **SC-003**: CLI commands are under 20 lines each (excluding imports and docstrings)
- **SC-004**: Debug logs show clear service entry/exit points for every service method call during a workflow execution
- **SC-005**: All existing integration tests pass after each of the 9 refactoring phases
- **SC-006**: Code coverage for state machine logic reaches 90% or higher with unit tests
- **SC-007**: Developer can create a fully mocked test of count workflow that runs without pyautogui, pygetwindow, or diskcache
- **SC-008**: Existing cached regions from pre-refactor code are successfully loaded and used by refactored code
- **SC-009**: User can run `autoraid upgrade count -n 1` and get identical behavior (clicks, timings, cache usage, output) compared to pre-refactor version
- **SC-010**: Dependency injection container initialization completes in under 100ms
- **SC-011**: Each service has explicit dependencies visible in constructor signature (no hidden global imports)
- **SC-012**: Refactoring process completes with zero breaking changes to user-facing CLI commands or cache formats

## Assumptions

- The existing ProgressBarStateDetector logic correctly identifies progress bar states from BGR color values and does not need refactoring
- The project will continue to use diskcache for caching (not switching cache backends during this refactoring)
- Dependency injection container will use the `dependency-injector` library (justified exception to minimize-dependencies principle: eliminates manual singleton boilerplate, provides type-safe resolution, simplifies testing with container overrides - see plan.md Phase 0 for full rationale)
- Each refactoring phase will be completed sequentially and committed before moving to the next phase
- Network management (`network.py`) will remain as-is and be orchestrated but not refactored into a service
- Existing test images in `test/images/` are sufficient for state machine unit testing
- The refactoring will not add new features - only restructure existing code
- Adding `dependency-injector` library is justified despite adding a dependency because it reduces overall complexity compared to manual singleton management (see plan.md Complexity Tracking table for detailed rationale)
- Windows-specific dependencies (WMI, pywinauto) remain unchanged
- Debug mode flag (`--debug`) continues to be a global CLI option passed through context
- Service constructors will use explicit type hints for all dependencies
- The tool will continue to require admin rights when Raid is launched via RSLHelper
- Service extraction will not change the core algorithms (state detection, color analysis, region matching)

## Constraints

- Must maintain backward compatibility with existing cache keys and cached data
- Must preserve all existing CLI command signatures and options
- Refactoring cannot break existing user scripts or workflows
- Each phase must result in working, deployable code with passing tests
- Services must be testable without external dependencies (windows, network, file system)
- Must use Python type hints for all service interfaces
- Must minimize third-party dependencies (exception: `dependency-injector` library justified for reducing manual DI boilerplate and improving testability - see Complexity Tracking table in plan.md)
- Must maintain debug mode functionality with identical output locations and formats
- Must work on Windows only (no need for cross-platform service abstractions)
- State machine must handle the same edge cases as current implementation (4 consecutive states for stop conditions)

## Open Questions

None at this time. The plan provides comprehensive detail on service responsibilities, phasing, and architectural decisions.
