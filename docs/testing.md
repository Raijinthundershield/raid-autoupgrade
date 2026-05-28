# Testing

## Philosophy

Test the **contract at each layer seam**, not the implementation inside a layer.

A seam is the boundary between two components — the interface one component exposes to its caller. A contract test asks: "Given these inputs at this boundary, does the component honour its promise?" It does not ask how the component achieves that promise internally.

## What is a contract?

A contract is the observable agreement at a seam:

- **Inputs**: the arguments a component accepts
- **Outputs**: the return value or raised exception
- **Side effects visible to the caller**: state changes on collaborators the caller provided

Anything else — internal state, private methods, intermediate steps, the order in which private helpers are called — is not part of the contract and must not be asserted on.

## How to write a contract test

1. **Identify the seam.** What is the boundary being tested? Name the caller and the callee.
2. **Isolate with mocks at the seam.** Replace every collaborator the callee accepts as a dependency with a test double. Do not patch internals.
3. **Assert on the contract.** Assert on return values, raised exceptions, and calls made to injected collaborators — nothing else.
4. **One scenario per test.** Each test exercises one behavior of the contract: happy path, one error branch, or one edge case.

## Anti-patterns

**Testing internal state**
Asserting on private attributes, intermediate variables, or the internal sequence of steps inside a component. If the implementation is refactored without changing behavior, these tests break unnecessarily.

**Testing implementation details**
Coupling tests to the names of internal methods or the exact call order of private helpers. Tests must survive any refactor that keeps the contract intact.

**Trivial coverage padding**
Tests that assert something which cannot plausibly be wrong — a constructor stored a value, a constant equals itself — written only to hit a coverage number. These add noise without catching regressions.

## Test layers

| Layer | What to test | What to mock |
|-------|-------------|-------------|
| Detection | State classification from image inputs | Nothing — pure function, use fixture images |
| Orchestration | Stop condition logic, monitor state transitions | Detector, services |
| Workflow | Validation rules, stop condition assembly | Orchestrator |
| Service | Service behavior given its platform dependencies | Platform calls (WMI, Win32, diskcache) |
| Integration | Workflow → Orchestrator contract end-to-end | Platform services only |

## Coverage

Coverage is a signal, not a target. A test suite that fully exercises every contract at every seam will naturally achieve high coverage. Do not add tests to raise a number; add tests to cover a contract that is not yet tested.
