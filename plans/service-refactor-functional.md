# Service-Based Architecture Refactoring - Functional Overview

## Why Refactor?

### Current Problems

The autoupgrade tool currently suffers from four key issues that make it difficult to maintain and test:

1. **Mixed Responsibilities**: The core upgrade counting function does too many things at once - it manages state transitions, captures screenshots, handles caching, and writes debug files. This makes it hard to understand and modify.

2. **Testing Difficulty**: To test the core upgrade logic, you need a running Raid window. You can't test the state machine logic with simple test images.

3. **Business Logic in CLI**: The CLI commands contain orchestration logic that should be separated. This makes it hard to reuse the upgrade workflows outside of the CLI.

4. **Repeated Code**: Cache key generation and screenshot-to-region-of-interest patterns are duplicated across multiple places.

## What We're Building

We're separating concerns into focused, single-purpose services that each do one thing well. This follows the project's constitution principles of simplicity and readability.

### Service Overview

#### 1. UpgradeStateMachine
**What it does**: Tracks upgrade state transitions and counts failures.

**Why it exists**: The core counting logic should work with just image data - no window management, no file I/O. This makes it testable with fixture images saved in the test directory.

**Responsibility**: Takes progress bar images as input, determines state (fail/progress/standby/connection_error), tracks transitions, and returns fail count + stop reason.

#### 2. CacheService
**What it does**: Manages all caching operations for regions and screenshots.

**Why it exists**: Caching logic is currently scattered across multiple functions. Centralizing it means one place to look for cache-related behavior.

**Responsibility**: Generate window-size-based cache keys, save/load regions and screenshots, provide clear cache API.

#### 3. ScreenshotService
**What it does**: Captures screenshots of the Raid window and extracts regions of interest.

**Why it exists**: All screenshot operations should go through one place. This isolates pyautogui/pygetwindow dependencies.

**Responsibility**: Take window screenshots, check if window exists, extract ROI from screenshots.

#### 4. LocateRegionService
**What it does**: Finds upgrade UI regions automatically or prompts user to select them manually.

**Why it exists**: Region detection combines automatic template matching with manual fallback. This service handles the full workflow including caching.

**Responsibility**: Try automatic detection first, fall back to manual selection if needed, cache results, integrate with CacheService and ScreenshotService.

#### 5. WindowInteractionService
**What it does**: Clicks on regions and manages window activation.

**Why it exists**: All GUI interaction (clicking, activating windows) should be isolated in one service.

**Responsibility**: Click region centers, activate windows, handle pyautogui interaction.

#### 6. UpgradeOrchestrator
**What it does**: Coordinates all services to execute the count and spend workflows.

**Why it exists**: Business logic belongs in a service layer, not in CLI commands. The orchestrator knows the full workflow: disable network → get regions → click button → count failures → re-enable network.

**Responsibility**: Implement `count_workflow()` and `spend_workflow()` methods, coordinate services, handle network management, manage debug output.

#### 7. ProgressBarStateDetector (Keep As Is)
**What it does**: Determines progress bar state from color values.

**Why it exists**: Already well-designed as pure functions. No changes needed.

**Responsibility**: Analyze BGR color values and return state (fail/progress/standby/connection_error/unknown).

## How Services Work Together

### Count Workflow Example

1. **User runs**: `autoraid upgrade count -n 1`
2. **CLI** receives command, injects UpgradeOrchestrator
3. **Orchestrator** starts count workflow:
   - Uses WindowInteractionService to check if Raid window exists
   - Uses NetworkManager to disable adapters
   - Uses ScreenshotService to capture window
   - Uses LocateRegionService to get upgrade button and progress bar regions
   - Uses WindowInteractionService to click upgrade button
   - Creates UpgradeStateMachine instance
   - Loop: ScreenshotService captures → extracts ROI → StateMachine processes state
   - StateMachine returns fail count and stop reason
   - NetworkManager re-enables adapters
4. **CLI** displays result to user

### Key Architectural Decisions

**Dependency Injection**: Services declare their dependencies in constructors. A central container wires everything together. This makes testing easy - just inject mocks.

**Singleton vs Factory**:
- Services with state (caching, window management) are Singletons - one instance shared
- Services for per-operation logic (state machine, orchestrator) are Factories - new instance each time

**Thin CLI**: CLI commands become 10-20 lines max. They parse arguments, inject the orchestrator, call a workflow method, and display results.

## Benefits for a One-Person Project

### Testability
- State machine can be tested with saved images (no GUI needed)
- Services can be tested with mocks (fast, no external dependencies)
- Integration tests can use test containers with mocked services

### Debuggability
- Each service logs entry/exit points
- Clear data flow through services
- Container shows all wiring relationships

### Maintainability
- Each service < 150 lines
- Clear single responsibilities
- Easy to find where behavior lives
- Obvious where to add new features

### Simplicity
- Flat structure (no deep inheritance)
- Services, not frameworks
- Explicit dependencies (no magic)
- Easy to understand data flow

## Phased Rollout Strategy

Each phase leaves the code in a working state. You can stop at any phase and have a functional tool.

**Phase 0**: Set up dependency injection container (foundation)
**Phase 1**: Extract state machine (core logic becomes testable)
**Phase 2**: Extract cache service (centralized caching)
**Phase 3**: Extract screenshot service (consolidated window I/O)
**Phase 4**: Extract locate region service (unified region management)
**Phase 5**: Extract window interaction service (isolated GUI operations)
**Phase 6**: Create orchestrator (business logic layer)
**Phase 7**: Simplify CLI (thin presentation layer)
**Phase 8**: Cleanup (remove dead code)

After each phase, the tool still runs. Tests guard against regressions. You can ship at any checkpoint.

## What Stays the Same

- Command-line interface (same commands, same options)
- User workflows (count → spend pattern unchanged)
- Cache behavior (same keys, same storage)
- Progress bar detection logic (already good)
- Network management (stays as separate module)
- Debug mode (still saves screenshots and metadata)

## What Changes

- Code organization (services directory instead of monolithic files)
- Dependency management (explicit via DI instead of implicit)
- Testing approach (unit tests with mocks instead of only integration tests)
- CLI implementation (thin wrappers instead of business logic)

## Alignment with Constitution

**Principle I - Simplicity Over Complexity**: Each service has one clear job. No clever abstractions or deep hierarchies.

**Principle II - Readability First**: Service names tell you exactly what they do. Clear data flow.

**Principle III - Pragmatic Testing**: Test what matters (state machine, cache logic). Skip what's hard (GUI automation).

**Principle IV - Debug-Friendly Architecture**: Services log clearly. Container shows wiring. Debug mode still saves artifacts.

**Principle V - Incremental Improvement**: Nine phases, each one shippable. Build iteratively based on real needs.
