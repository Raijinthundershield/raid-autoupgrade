# Testing Principles

## Testing Philosophy

- Tests are a tool for confidence, not a goal
- Write minimal tests that maximize impact and coverage of critical paths
- Focus testing resources on real-world failure modes, not theoretical edge cases
- Prefer testing behavior over implementation details
- Tests should catch real bugs, not validate framework contracts
- One well-designed test is better than multiple weak tests

## Test Prioritization

Tests should be prioritized in this order:

1. **Safety-Critical Scenarios** - Exception handling, resource cleanup, error boundaries
2. **Core Business Logic** - The unique value and algorithms your system provides
3. **Program Flow and Orchestration** - How components coordinate across workflows
4. **Critical User Workflows** - End-to-end paths that must never break
5. **Complex Conditionals** - Logic with multiple branches and states

Skip or minimize:
- Edge case validation (null, empty, invalid types) unless they represent real failure modes
- Happy path scenarios where everything works perfectly
- Debug/diagnostic features that are rarely used
- Redundant coverage already provided by other test layers

## Integration Testing Strategy

Integration tests serve a distinct purpose from unit tests: they validate that components work together correctly to achieve outcomes.

**Write integration tests to verify:**
- **Program flow and orchestration** - How components coordinate across multiple steps
- **State transitions across components** - Data and state flowing correctly through the system
- **Multi-component interactions** - Components calling each other in the right order with correct data
- **Workflow-level logic** - Business processes that span multiple components
- **End-to-end critical paths** - Complete workflows from entry to exit

**Integration tests should NOT:**
- Re-verify individual component behavior already tested in unit tests
- Test internal implementation details of individual components
- Duplicate assertion logic from unit tests
- Test every edge case combination (use unit tests for edge cases)

**Key distinction:**
- **Unit tests** verify *what each component does* (correctness of individual behavior)
- **Integration tests** verify *how components work together* (orchestration and flow)

**Examples:**

Good integration tests (test orchestration):
- ✅ "Workflow creates new session per iteration and decrements remaining attempts correctly across multiple upgrades"
- ✅ "Session configuration flows correctly from workflow to orchestrator with proper stop conditions"
- ✅ "Multi-step process maintains state consistency as data moves between components"

Bad integration tests (duplicate unit tests):
- ❌ "Workflow creates correct stop conditions" (unit test should verify stop condition creation)
- ❌ "Result mapping converts orchestrator result to workflow result" (unit test should verify mapping logic)
- ❌ "Workflow validates internet availability" (unit test should verify validation logic)

## What to Test

**Always Test:**
- Core business logic and algorithms
- Error handling and validation at system boundaries
- Exception-safe resource cleanup (files, connections, locks)
- Critical paths that would break user workflows
- Data transformations and processing
- Public APIs and interfaces
- Scenarios that could cause data loss or security issues

**Conditionally Test:**
- Complex conditionals and state machines
- Edge cases that represent real-world failures
- Multi-component orchestration not covered by unit tests

## What Not to Test

**Infrastructure and Glue Code:**
- Trivial getters/setters and pass-through functions
- Framework code and third-party libraries
- Configuration files and constants
- Code that only calls other tested functions
- Generated code

**Implementation Details:**
- Private methods and internal state
- Protocol compliance (e.g., context managers returning self)
- Default parameter values and timeout constants
- Internal tracking mechanisms

**Debug and Diagnostic Features:**
- Debug logging and frame capture
- Diagnostic tools and utilities
- Development-only features

**Redundant Coverage:**
- Individual component behavior already validated by unit tests
- Multiple tests verifying the same outcome in the same way
- Integration tests that only verify single-component logic (not orchestration)

**Low-Value Scenarios:**
- Happy paths where nothing goes wrong
- Edge cases unlikely to occur in practice (e.g., None when type hints enforce otherwise)

## Test Quality

- Each test verifies one behavior or scenario
- Test names describe what is being tested and expected outcome
- Tests are isolated and can run in any order
- Tests are fast and deterministic (no flaky tests)
- Use clear assertions that explain failures
- Avoid test interdependencies

## Test Organization

- Group related tests by feature or module
- Use clear naming conventions for test files and functions
- Separate unit tests from integration tests
- Keep test data and fixtures close to tests
- Extract common setup into reusable helpers
- Maintain test code with same quality as production code
