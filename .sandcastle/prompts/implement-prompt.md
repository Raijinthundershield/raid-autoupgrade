# TASK

Implement issue #{{ISSUE_NUMBER}}: {{ISSUE_TITLE}}

You are working on branch `{{BRANCH}}` in a dedicated git worktree. The branch
already contains any predecessor work this feature builds on. **Only implement
this single issue.** Do not start other issues.

# THE ISSUE

<issue>

{{ISSUE_CONTEXT}}

</issue>

If the issue references a parent PRD, read it with `gh issue view <number>` for
context — but still only implement THIS issue.

# HOW TO IMPLEMENT — TDD, run unattended

Follow this repo's **`tdd` skill** at `.claude/skills/tdd/SKILL.md` and its
reference docs. Read it now.

**AFK override (important):** the `tdd` skill is written for an interactive
session and tells you to confirm the interface and the behavior list *with the
user* and to get approval before coding. There is no user here. Wherever it
says to confirm with or ask the user, instead **derive the public interface and
the prioritized behavior list from this issue's Acceptance Criteria** (and the
parent PRD if any), decide, and proceed. Do not stop to ask questions.

Also read and honor, for this repo's standards and vocabulary:

- `docs/engineering-principles.md` — structural/design decisions.
- `docs/testing.md` and `docs/testing_practical.md` — what a good test is, and
  where to put test doubles.
- `CONTEXT.md` and `docs/adr/` — domain glossary and architectural decisions.
  Use the project's vocabulary in test names and interfaces; respect ADRs in the
  area you touch.

Work in **vertical tracer-bullet slices**: one test -> minimal code to pass ->
repeat. Never write all tests first. Never weaken or delete a test to make
things pass.

# FEEDBACK LOOP (the gate)

Tests are your inner loop — run them continuously. Before you are done, the
**full gate must be green**:

1. `uv run pytest`
2. `uv run pre-commit run --all-files` (this auto-fixes formatting/lint; re-stage
   and amend/commit the fixups)
3. **Only if your change touched `frontend/`**, also run, from `frontend/`:
   `npm install` (the worktree has no `node_modules`), then `npm run build`
   (this is the TypeScript typecheck) and `npm test`.

Do not emit the completion signal until every applicable step above passes.

# COMMITS

Commit your work with **conventional-commit** messages matching this repo
(`feat(...)`, `fix(...)`, `test(...)`, `refactor(...)`, `docs(...)`). For
multi-line messages write the message to a temp file and use `git commit -F`.

- Reference the issue in the body: `Refs #{{ISSUE_NUMBER}}`.
- Add the trailer: `Co-Authored-By: Claude <noreply@anthropic.com>`.
- Do **not** use a `RALPH:` or any subject prefix.
- Do **not** close the issue and do **not** open a PR — the orchestrator does
  that once the whole feature is reviewed.

# HANDOFF (do this once the gate is green, before signalling)

Write a handoff document so the fresh agents that review and fix this work can
pick it up without re-deriving everything. Follow this repo's **`handoff` skill**
at `.claude/skills/handoff/SKILL.md`. The skill takes the **next-session intent**
as its argument — use exactly this intent:

> "Two fresh agents will pick up next: a reviewer that checks these changes for
> issue #{{ISSUE_NUMBER}} against the repo's standards and the issue spec, and a
> fix agent that resolves any blocking findings without weakening tests. Give
> them what they need to do that well."

Apply two overrides to the skill's defaults:

- **Write it to this exact path** (an orchestration artifact, NOT the workspace —
  do not commit it): `{{HANDOFF_PATH}}`
- Tailor the content to the intent above.

Keep it tight. Reference the issue, commits, and diff by identifier/path —
don't duplicate them. Cover: what behavior you implemented and the public
interface you chose; the key design/test decisions and any you were unsure
about; anything intentionally left out of scope; and a "Suggested skills"
section (e.g. `review`). Redact any secrets.

# WHEN DONE

Once the issue is implemented, the full gate is green, and the handoff is
written, output the literal line:

<promise>COMPLETE</promise>

If you genuinely cannot complete the issue, leave a `gh issue comment` on
#{{ISSUE_NUMBER}} explaining what you did and what blocked you, then still output
<promise>COMPLETE</promise> so the orchestrator's gate can detect the state.
