# Sandcastle one-feature loop

Automated implementation loop for Raid Autoupgrade. You hand it a set of GitHub
issues; it groups them into features, implements each issue with TDD, reviews
the work, and opens **one pull request per feature** for you to merge.

It is built on [sandcastle](https://github.com/mattpocock/sandcastle) and is
deliberately **single-track**: one feature at a time, sequential, with a review
step on every feature. (Contrast with sandcastle's stock example, which fans out
N issues in parallel and merges straight to `main`.)

## How it works

```
planner (Opus)
  └─ groups + orders the passed issues into features:
       { branch, base, reviewMode, issues[] }

per feature (sequential):
  per issue (in dependency order, on the feature's worktree):
    implement (Sonnet, TDD)  ── owns "green" itself
      └─ safety-net gate (pytest + pre-commit [+ frontend build/test])
      │    └─ if red: up to 2 implementer fix passes, else FAIL the feature
      └─ handoff (the repo's `handoff` skill) ── intent/interface/decisions for
           the next agents; written to runs/ artifacts, NOT committed
  review (Opus, the repo's `review` skill, two-axis Standards + Spec)
    └─ once per feature, or per issue (planner decides; --review-mode overrides)
    └─ reads the implementer handoff as context (verifies against the diff)
  review-fix (Sonnet, FRESH agent) ── resolves BLOCKING findings only
    └─ reads the handoff for original intent; never weakens tests;
       judgment-call findings are left for the PR
  PR (gh pr create) ── you merging the PR is the human gate; merge closes issues
```

The **handoff** is the bridge from the implementer (who has full context) to the
deliberately-fresh review and fix agents: the implementer invokes the `handoff`
skill with the intent "a reviewer + fix agent will pick this up next" and writes
it to `runs/<runId>/<branch>/handoff-issue-<N>.md` (gitignored, never committed).

### Key decisions baked in

- **Isolation:** `noSandbox()` — agents run directly on the **host**, currently
  **WSL/Linux**. There the gate runs the cross-platform test subset
  (`uv run pytest -m "not windows"`); the Win32/WMI tests are validated on a
  Windows host pre-merge (CONTRIBUTING.md). Each feature gets its own git
  **worktree** under `.sandcastle/worktrees/` for branch isolation. `noSandbox`
  also works on a Windows host (runs the full suite); a Linux container
  (`docker()`) is viable for the cross-platform subset but we run `noSandbox`
  for now.
- **Models:** Sonnet 4.6 implements; Opus 4.8 plans and reviews.
- **Gate is a safety net, not the feedback loop.** The implementer runs the gate
  itself through its TDD loop; the script re-runs it independently to catch a
  missed step. A red gate resumes the **implementer** (full code context, in the
  same worktree). Review findings go to a **fresh** agent (fresh eyes beat the
  implementer's anchoring).
- **Stacking:** dependent or code-overlapping features are `base`d on their
  predecessor's branch (the planner decides). Their PRs stack and must be merged
  predecessor-first; independent features are `base`d on `main`.
- **Commits:** conventional commits (`feat(...)`, `fix(...)`, …), no `RALPH:`
  prefix, `Co-Authored-By` trailer, issues closed via the PR's `Closes #N`.

## Prerequisites

Run it from your **WSL/Linux** environment (where the cross-platform test subset
runs). There you need:

- Node 20.11+ (uses `import.meta`), `npm`.
- `uv` on PATH (the gate runs `uv run pytest -m "not windows"` / `uv run pre-commit`).
- `gh` authenticated (`gh auth status`) with push rights to the repo.
- `claude` CLI authenticated with your subscription. If it is, no token is
  needed. Otherwise run `claude setup-token` and put the token in
  `.sandcastle/.env` as `CLAUDE_CODE_OAUTH_TOKEN` (see `.env.example`).

If you instead run it on a **Windows host** (PowerShell), also install **Git for
Windows**: `noSandbox` shells out via `sh -c` and uses coreutils like `cp`, which
PowerShell lacks on PATH — `run.ts` auto-prepends Git's `usr\bin`/`bin` (missing →
`spawn sh/cp ENOENT`). On WSL/Linux those tools are native and the shim is a no-op.

## Usage

From the repo root:

```bash
cd .sandcastle
npm install          # first time only
npm start -- 40 41 42
```

Flags (after the issue numbers):

- `--review-mode=per-issue|per-feature` — override the planner's per-feature choice.
- `--max-features=N` — safety cap on how many features one run will attempt.

Examples:

```bash
npm start -- 40 41 42                      # let the planner group + order
npm start -- 35                            # a single independent issue
npm start -- 40 41 42 --review-mode=per-issue
```

## Output

- **Live:** progress streams to the console. Note the console only surfaces the
  agent's prose plus four allowlisted tools (Bash/WebSearch/WebFetch/Agent) —
  Read/Edit/Write/Grep/thinking are dropped before display. To see in full
  detail what an agent is doing, tail its raw Claude session transcript in a
  second pane: `./watch-agent.sh` (see `watch-agent.sh -h`).
- **Successful feature:** the **PR** is the report — body carries the summary,
  `Closes #…`, and a "Review notes" section with the reviewer's judgment calls.
- **Failed feature:** a comment is left on the issue(s) with the gate/error
  output and the branch name, which is left in place for inspection. Features
  stacked on a failed feature are skipped as blocked.
- **Durable record (gitignored):** `.sandcastle/runs/<runId>/` holds `plan.json`,
  each review's `*-blocking.md` / `*-notes.md`, `pr-body.md`, `failure.txt`, and
  `summary.md`.

## Files

| File | Role |
| --- | --- |
| `run.ts` | Orchestrator: planner call + per-feature loop + gate + PR + summary. |
| `watch-agent.sh` | Tail an agent's raw Claude session transcript (full tool calls + thinking) in a second pane. |
| `prompts/plan-prompt.md` | Planner: group/order issues into features (structured `<plan>` output). |
| `prompts/implement-prompt.md` | Implementer: TDD via the repo's `tdd` skill (AFK override) + the gate. |
| `prompts/review-prompt.md` | Reviewer: the repo's two-axis `review` skill; writes blocking + notes files. |
| `prompts/review-fix-prompt.md` | Fresh agent: resolve blocking findings only; never weaken tests. |

## Notes / limits

- Input is an **explicit issue list** for now (PRD→children auto-discovery is not
  wired up).
- The gate-fix re-invokes the implementer **in the same worktree** (full code +
  commit context) rather than literally resuming the chat session — sandcastle's
  `Sandbox.run()` doesn't expose session resume, and the worktree carries the
  substance anyway.
- Each feature worktree runs its own `uv sync`; first run per feature pays that
  cost. Frontend deps (`npm install`) are installed lazily, only when a feature
  touches `frontend/`.

## Changing the setup later — load-bearing behaviors

These are non-obvious and will break things subtly if changed without care.
Verified against **sandcastle 0.7.0**; re-check against the installed version
before relying on the API points.

1. **`noSandbox()` is the current choice; the gate runs the cross-platform test
   subset.** Agents run on the host — currently **WSL/Linux**, where
   `PYTEST_CMD` is `uv run pytest -m "not windows"` (the Win32/WMI tests are
   `windows`-marked and validated on a Windows host pre-merge). The full app
   (WMI/Win32/GUI) only *runs* on Windows, but the in-scope issues are
   cross-platform Python, so Linux is fine. `noSandbox` on a Windows host runs
   the full suite (`PYTEST_CMD` switches on `process.platform`). A Linux
   container (`docker()`) is viable for this subset, but we run `noSandbox` for
   now — so the loop sees real `uv`/`gh`/`claude` and a real worktree. Branch
   isolation comes from the **worktree**, not a container. The loop CANNOT
   validate `windows`-marked tests; the PR body flags this.
2. **Gate-fix is a fresh agent in the same worktree, NOT a resumed session.**
   `Sandbox.run()` (the createSandbox handle) exposes neither session-resume nor
   structured `output` — only top-level `run()` does. To get literal
   implementer-session resume you must abandon `createSandbox` and drive the
   feature with top-level `run()` + a `head`/`branch` strategy, losing the clean
   persistent-worktree model. The worktree carries the code context, which is the
   substance.
3. **Planner uses top-level `run()` + `Output.object`; this requires
   `maxIterations: 1`** (the default) and the resolved prompt **must contain the
   opening tag literal** (`<plan>`). Rename the tag → update both the schema and
   the prompt. Move planning into a `sandbox.run()` → you lose structured
   output + validation/retry.
4. **Stacking relies on two facts:** features are ordered after the feature named
   in their `base`, and **`sandbox.close()` removes the worktree but keeps the
   branch**. Stacked features `base` on the predecessor branch and their PR
   targets that branch (`prBase = feature.base`); they must merge
   predecessor-first. Forcing all PRs to target `main` makes stacked diffs wrong.
5. **The handoff is written to an absolute artifact path OUTSIDE the worktree** so
   it is never committed. Writing it inside the worktree would pollute the branch.
   This depends on `noSandbox` giving host-wide filesystem access.
6. **Auth follows the provider.** `noSandbox` uses the host's `claude` login (or
   `CLAUDE_CODE_OAUTH_TOKEN` from `.env`). If you ever switch to a container
   provider you MUST inject the token into the agent env — host login is invisible
   inside a container.
7. **The gate is a safety net, not the feedback loop**, and the **two fix roles
   are intentionally different**: gate-fix = the implementer (mechanical miss,
   full context, anchoring harmless); review-fix = a FRESH agent (qualitative,
   fresh eyes beat anchoring). Don't "simplify" by merging them.
8. **`pre-commit` auto-fixes and then exits non-zero.** A clean implementer leaves
   nothing to fix, so the gate passes; a non-zero `pre-commit` in the gate means
   the agent left unstaged fixups — that's a real red gate, not a false alarm.
9. **vitest must run once:** the frontend gate uses `npm test -- --run` to avoid
   watch mode hanging an unattended run.
10. **Input is an explicit issue list.** PRD→children auto-discovery is not wired
    up; the planner only groups/orders the numbers you pass.
11. **Tooling is contained under `.sandcastle/`** with its own `package.json`;
    `run.ts` passes `cwd: REPO_ROOT` so sandcastle anchors
    `.sandcastle/{worktrees,logs,.env}` at the repo root. Moving `package.json`
    to the repo root or changing `cwd` shifts all of that path anchoring.
12. **`.claude/` is gitignored, so worktrees don't get the skills from git.** The
    agents' cwd is the worktree, not your main checkout, and a worktree only
    materializes *tracked* files — so `createSandbox` uses
    `copyToWorktree: [".claude"]` to copy the skills/instructions
    (`tdd`/`review`/`handoff`, project settings) into each worktree. If you ever
    start tracking `.claude` in git, this copy becomes redundant; if you add a new
    skill the prompts depend on, it rides along automatically via this copy. Note
    it copies the host's **current** `.claude` (not the branch's), which is what
    you want for ungitted tooling.

If any of these change, update this list. A full ADR isn't warranted (this is
build tooling, not product architecture), but these are the decisions a future
edit is most likely to trip over.
