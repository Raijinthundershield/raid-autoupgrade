<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.1.0
- Modified principles:
  * II. Readability First → II. DRY & Separation of Concerns (expanded scope)
  * III. Pragmatic Testing (clarified smoke test approach vs TDD)
- Added sections: Explicit DRY enforcement guidance
- Removed sections: None
- Templates requiring updates:
  ✅ plan-template.md (verified, no updates needed)
  ✅ spec-template.md (verified, no updates needed)
  ✅ tasks-template.md (verified, no updates needed)
  ✅ checklist-template.md (verified, no updates needed)
  ✅ agent-file-template.md (verified, no updates needed)
- Follow-up TODOs: None
-->

# AutoRaid Constitution

## Core Principles

### I. Simplicity Over Complexity

**Code MUST prioritize simplicity over cleverness.** This is a one-person project where
maintainability trumps optimization. Choose straightforward solutions that are easy to
understand and modify. Avoid premature optimization, complex abstractions, and
"clever" solutions that sacrifice readability. The pragmatic programmer chooses
the simplest thing that works.

**Rationale:** As a solo developer, you are your own maintainer. Code you write today
will be debugged by future-you who won't remember the clever tricks. Simple code is
fast to debug, easy to extend, and requires no mental gymnastics. Complexity is a
liability, not an asset.

**Rules:**
- Prefer explicit over implicit
- Avoid deep inheritance hierarchies (max 2 levels)
- No metaprogramming or magic unless absolutely necessary
- Question every abstraction: does it truly reduce complexity or just hide it?
- When in doubt, write the obvious solution first
- YAGNI (You Aren't Gonna Need It) is law
- Premature optimization is the root of evil

### II. DRY & Separation of Concerns

**Code and knowledge MUST follow the DRY principle.** Don't Repeat Yourself applies
to both code and documentation. Every piece of knowledge should have a single,
authoritative source. When the same logic or information appears in multiple places,
it becomes a maintenance burden and a source of bugs.

**Code MUST be organized by separation of concerns.** Related functionality lives
together; unrelated concerns are isolated. Use layers and clear boundaries: CLI
is thin presentation, services contain business logic, core has pure domain logic,
platform has OS-specific code. Dependencies flow inward, never outward.

**Rationale:** Duplication means maintaining the same fix in multiple places. Knowledge
scattered across files creates documentation debt. Separation of concerns makes code
testable by letting you swap implementations (dependency injection, mocking) without
touching business logic. When concerns are mixed, changing one thing breaks unrelated code.

**Rules:**
- Single source of truth for all domain logic and critical knowledge
- Extract shared code into reusable functions/classes
- Extract shared documentation into CLAUDE.md or README.md (not scattered in docstrings)
- Layer architecture: CLI → Services → Core → Platform
- Services orchestrate; core implements pure logic; platform handles OS specifics
- No business logic in CLI; no I/O in core state machines
- Dependencies inject via constructors (dependency-injector pattern)
- Related code lives in the same module; unrelated code is isolated

### III. Readability First

**Code MUST be self-documenting through clear names and structure.** Variable names,
function names, and module organization should tell the story. Comments explain "why",
not "what". Code that needs extensive comments to be understood should be refactored.

**Rationale:** Good names and structure reduce cognitive load and make the codebase
navigable without context switching to documentation. For computer vision and
automation tasks, clarity is critical for debugging.

**Rules:**
- Functions do one thing with a name that describes exactly what
- Variable names are descriptive: `upgrade_bar_region` not `r1`
- Magic numbers become named constants with units: `POLL_INTERVAL_SECONDS = 0.25`
- Module structure reflects domain concepts
- Comments explain decisions, trade-offs, and non-obvious "why"
- Avoid abbreviations unless universally understood (e.g., `img` for image is OK)
- Type hints are mandatory for public APIs

### IV. Pragmatic Testing (Smoke Tests, Not TDD)

**Tests MUST exist for core logic and critical algorithms. Testing SHOULD be
pragmatic, not dogmatic.** Focus testing effort where it provides the most value:
state detection, color analysis, region detection, and upgrade counting logic.
Use **smoke tests** to verify basic functionality, not exhaustive TDD.

**Tests are regression protection, not design tools.** Write tests after core
implementation to catch regressions. For simple utilities and GUI wiring, manual
testing is acceptable. For complex algorithms (state machines, computer vision),
automated tests are mandatory.

**Rationale:** Computer vision algorithms are notoriously fragile and require
regression testing. However, this is a personal project - not every line needs
100% coverage. Test what breaks, test what's complex, skip what's trivial.
The pragmatic programmer tests strategically, not dogmatically.

**Rules:**
- MUST test: progress bar state detection, color analysis, state machine logic (≥90% coverage)
- SHOULD test: region detection, orchestrator workflows, error handling
- CAN skip: simple getters/setters, CLI argument parsing, straightforward utilities, GUI wiring
- Tests use real image fixtures from `test/fixtures/images/` to catch visual regressions
- Test names describe the scenario: `test_detects_fail_state_from_red_bar()`
- Integration tests use mocks to isolate services (dependency injection enables this)
- Pre-commit hooks run tests automatically to catch obvious breaks
- Tests are written AFTER implementation (smoke tests, not TDD)
- Coverage targets: core logic ≥90%, services ≥60%, overall ≥70%

### V. Debug-Friendly Architecture

**The system MUST be easy to debug when things go wrong.** Automation and computer
vision are inherently unpredictable. The architecture MUST support rapid diagnosis
through debug modes, cached artifacts, and clear error messages.

**Rationale:** When the tool misdetects a progress bar state at 2 AM during a
critical upgrade, you need to diagnose quickly. Debug artifacts (screenshots,
metadata, logs) are your flashlight. The pragmatic programmer builds for
debuggability from day one.

**Rules:**
- Global `--debug` flag saves screenshots and metadata to `cache-raid-autoupgrade/debug/`
- Cache system persists regions and screenshots for inspection
- Error messages include context: which state, which region, what was expected
- Rich terminal output shows progress, states, and decisions in real-time
- Loguru logging with structured context for trace-level debugging
- Region visualization commands (`autoraid upgrade region show`) for visual verification
- Custom exceptions inherit from base classes with clear names

### VI. Incremental Improvement Over Perfection

**Ship working features incrementally. Perfection is the enemy of done.** Features
should be functional and useful, not perfect. Improvements happen iteratively based
on real usage, not imagined requirements. YAGNI (You Aren't Gonna Need It) is law.

**Rationale:** This is a personal tool built for actual use, not a product. Build
what's needed now, improve based on pain points. Over-engineering features "just
in case" wastes time and adds maintenance burden.

**Rules:**
- Implement the minimum feature that solves the problem
- Add complexity only when pain is felt, not anticipated
- TODO comments track known limitations without blocking delivery
- Roadmap tracks "nice to have" separately from "need to have"
- Refactor when changing code, not "just because"
- Test with real usage before adding more features

## Development Standards

### Code Quality

**Ruff linting and formatting MUST pass before commits.** Pre-commit hooks enforce
this automatically. Code style is not negotiable - let the tools handle it.

- `uv run ruff check .` must pass (or use `--fix` to auto-correct)
- `uv run ruff format .` must be run before committing
- Pre-commit hooks run automatically: `uv run pre-commit install`
- No warnings in linting output

### Dependency Management

**Dependencies MUST be managed via `uv` and pinned in `pyproject.toml`.** Keep the
dependency tree minimal. Every dependency is a maintenance liability.

- Use `uv sync` to install and sync dependencies
- Update dependencies deliberately, not automatically
- Document why each major dependency exists in `CLAUDE.md`
- Prefer stdlib over external libraries when reasonable

### Windows-Only Constraints

**This tool is Windows-only by design.** Do not waste effort on cross-platform
compatibility. Use Windows-specific APIs freely (WMI, pygetwindow, etc.).

- Document Windows-specific requirements clearly
- Admin rights requirement is acceptable (RSLHelper compatibility)
- Platform checks can be assertions, not graceful fallbacks

## Governance

This constitution defines the non-negotiable principles for AutoRaid development.
These principles exist to maintain code quality, simplicity, and debuggability as
the project grows.

### Amendment Process

- Constitution changes require explicit documentation of what changed and why
- Version bumps follow semantic versioning:
  - **MAJOR**: Principle removal or fundamental redefinition
  - **MINOR**: New principle added or significant expansion
  - **PATCH**: Clarification, typo fixes, non-semantic changes
- Amendments update the Sync Impact Report at the top of this file

### Compliance

- All feature specifications SHOULD reference relevant principles
- Code reviews (by future-you) MUST verify principle adherence
- Complexity or principle violations MUST be justified in comments or docs
- When principles conflict, Simplicity (Principle I) is the tiebreaker

### Runtime Guidance

For agent-specific development guidance and best practices, refer to `CLAUDE.md`
in the repository root. The constitution defines principles; `CLAUDE.md` provides
practical implementation guidance.

**Version**: 1.1.0 | **Ratified**: 2025-10-17 | **Last Amended**: 2025-10-23
