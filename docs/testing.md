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
| Job registry | Single-active-job lifecycle: start-if-idle, busy → 409, cancel sets the event, event queue ordering | Orchestrator |
| API routes | Request → status code, response body, and which workflow/service was invoked | Collaborators, via `app.dependency_overrides` |
| WebSocket | Typed job events (`progress`/`log`/`done`/`error`) arrive in order over the stream | The job producing events |
| Integration | Workflow → Orchestrator contract end-to-end | Platform services only |

Mock at the route seam with FastAPI's `app.dependency_overrides` — substitute the provider, never patch internals. This is the API-layer equivalent of injecting a test double at the constructor.

## Frontend testing

The frontend (React/TypeScript) is tested with **Vitest** and **React Testing Library** (RTL). The contract philosophy above carries across the language boundary unchanged — only the tools and the location of the seam differ.

**The seam is the network boundary.** On the client, a component's collaborators are the HTTP API and the job WebSocket. A contract test mocks `fetch`/the API client (or the `WebSocket`) and asks: given this server response or event sequence, does the component render the right thing and call the right endpoint? Mock at that boundary — never reach into component internals, hook state, or the TanStack Query cache.

**RTL's "test what the user sees" is the client-side restatement of "test the contract, not the implementation."** Query by accessible role and visible text; assert on rendered output and on calls made to the mocked API; assert nothing about how the component achieves it.

**What gets tested:**

- **`useJobStream` reducer** — given a sequence of WS events, the derived view state is correct. Pure reducer; mock nothing.
- **Region-picker coordinate math** — display-pixel → image-pixel mapping is correct across render scales. Pure function.
- **Panels (light RTL pass)** — render the panel, assert it calls the right API on interaction, and that it renders loading and error states.

**Frontend anti-patterns** (the client-side equivalents of the anti-patterns above):

- Querying by CSS class or `data-testid` when an accessible role or visible text would work — couples the test to markup, not behavior.
- Asserting on component state, hook internals, or the query cache rather than on what the user sees.
- Snapshotting whole component trees — brittle, and breaks on any cosmetic change.

**No end-to-end (Playwright) tests** for now: the platform (real Raid window, WMI) cannot run headless, so e2e coverage is inherently limited and low-ROI.

## Coverage

Coverage is a signal, not a target. A test suite that fully exercises every contract at every seam will naturally achieve high coverage. Do not add tests to raise a number; add tests to cover a contract that is not yet tested.
