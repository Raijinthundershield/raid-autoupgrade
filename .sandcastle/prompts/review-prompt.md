# TASK

Review the work on branch `{{BRANCH}}` for {{REVIEW_SCOPE}}.

You are reviewing the changes between the fixed point `{{FIXED_POINT}}` and
`HEAD`. The diff command is:

    git diff {{FIXED_POINT}}...HEAD

# HOW TO REVIEW

Follow this repo's **`review` skill** at `.claude/skills/review/SKILL.md`. Read
it now and run its two-axis process:

- **Standards** — does the diff conform to this repo's documented standards
  (`CLAUDE.md`, `CONTEXT.md`, `docs/adr/`, `docs/engineering-principles.md`,
  `docs/testing.md`, `docs/testing_practical.md`)? Skip anything `ruff` /
  `pre-commit` already enforce.
- **Spec** — does the diff faithfully implement what the in-scope issues asked
  for? Report missing/partial requirements, scope creep, and requirements that
  look implemented but wrong.

**Fixed point and spec are already decided — do not ask.** The fixed point is
`{{FIXED_POINT}}`. The spec is these issues:

<spec-issues>

{{SPEC_ISSUES}}

</spec-issues>

The implementer left a handoff for each issue describing what was built and why
(intent, interface, key decisions, anything left out of scope). Use it to inform
the **Spec** axis, but verify against the diff — treat the handoff as a claim,
not ground truth:

<implementer-handoff>

{{HANDOFFS}}

</implementer-handoff>

You may run the two axes as parallel sub-agents per the skill, or inline if
sub-agents are unavailable. **This is a review: do not change code.**

# OUTPUT — write two files, then signal

Write your findings to these absolute paths (create parent dirs if needed):

1. `{{BLOCKING_PATH}}` — the **blocking** findings a fixer must resolve before
   this ships: hard Standards violations, Spec gaps, and scope creep. Use a
   short markdown checklist. If there are none, write exactly `NONE`.

2. `{{NOTES_PATH}}` — a markdown report for the human reviewing the PR: a
   one-paragraph summary, then a `## Judgment calls` section listing the
   subjective/stylistic findings you deliberately did NOT treat as blocking
   (with file:line and a one-line rationale each). This becomes the PR body.

Distinguish hard violations (blocking) from judgment calls (notes) exactly as
the `review` skill describes.

When both files are written, output:

<promise>COMPLETE</promise>
