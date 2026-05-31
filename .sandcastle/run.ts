/**
 * Sandcastle orchestration for Raid Autoupgrade.
 *
 * Resolves a passed-in set of GitHub issues ONE FEATURE AT A TIME:
 *
 *   planner (Opus)  -> groups+orders the issues into features {branch, base, reviewMode, issues}
 *   per feature:
 *     per issue:    implement (Sonnet, TDD) -> safety-net gate -> bounded gate-fix retries
 *     review:       (Opus, two-axis "review" skill) once per feature, or per issue
 *     review-fix:   (Sonnet, fresh agent) resolves blocking findings only
 *     PR:           gh pr create (you merging the PR is the human gate; merge closes the issues)
 *
 * Isolation: noSandbox() — agents run on the host (WSL/Linux for now; Windows
 * also supported) inside a per-feature git worktree. On Linux the gate runs the
 * cross-platform test subset (`-m "not windows"`); the Win32/WMI tests run on a
 * Windows host pre-merge. See .sandcastle/README.md.
 */
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { execSync, execFileSync } from "node:child_process";
import * as sandcastle from "@ai-hero/sandcastle";
import { noSandbox } from "@ai-hero/sandcastle/sandboxes/no-sandbox";
import type { StandardSchemaV1 } from "@standard-schema/spec";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url)); // .../.sandcastle
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..");
const PROMPTS = path.join(SCRIPT_DIR, "prompts");

const MODELS = {
  planner: "claude-opus-4-8",
  implement: "claude-opus-4-8",
  // implement: "claude-sonnet-4-6",
  review: "claude-opus-4-8",
  // reviewFix: "claude-sonnet-4-6",
  reviewFix: "claude-opus-4-8",
} as const;

// Reasoning effort per role (claude --effort): "low" | "medium" | "high" | "xhigh" | "max".
const EFFORT = {
  planner: "high",
  implement: "medium",
  review: "high",
  reviewFix: "medium",
} as const;

const GATE_RETRY_ATTEMPTS = 2; // resume-the-implementer fix passes before giving up
const DEFAULT_MAX_FEATURES = 20;

// The loop runs on WSL/Linux: the Win32/WMI tests are tagged `windows` and
// auto-skip there, so we deselect them to keep the gate clean. On a Windows
// host the full suite runs. The `windows` subset is validated on Windows
// pre-merge (CI / before opening the PR). See CONTRIBUTING.md.
const PYTEST_CMD =
  process.platform === "win32" ? "uv run pytest" : 'uv run pytest -m "not windows"';

// --------------------------------------------------------------------------
// Small shell + gh helpers (run on the host)
// --------------------------------------------------------------------------

const BIG = 64 * 1024 * 1024;

const sh = (cmd: string, cwd: string = REPO_ROOT): string =>
  execSync(cmd, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], maxBuffer: BIG });

const ghJson = <T>(args: string[]): T =>
  JSON.parse(execFileSync("gh", args, { cwd: REPO_ROOT, encoding: "utf8", maxBuffer: BIG }) as string) as T;

const ghRun = (args: string[], cwd: string = REPO_ROOT): string =>
  execFileSync("gh", args, { cwd, encoding: "utf8", maxBuffer: BIG }) as string;

const tail = (s: string, n: number): string => (s.length <= n ? s : `…(truncated)…\n${s.slice(s.length - n)}`);

const sanitizeBranch = (b: string): string => b.replace(/[/\\:*?"<>|]/g, "-");

// --------------------------------------------------------------------------
// Plan schema (hand-rolled StandardSchema — no zod dependency)
// --------------------------------------------------------------------------

type ReviewMode = "per-issue" | "per-feature";
interface Feature {
  readonly branch: string;
  readonly base: string;
  readonly reviewMode: ReviewMode;
  readonly issues: number[];
}
interface Plan {
  readonly features: Feature[];
}

const standardSchema = <T>(validate: (v: unknown) => T): StandardSchemaV1<unknown, T> => ({
  "~standard": {
    version: 1,
    vendor: "autoraid-sandcastle",
    validate: (value: unknown) => {
      try {
        return { value: validate(value) };
      } catch (error) {
        return { issues: [{ message: error instanceof Error ? error.message : "Validation failed" }] };
      }
    },
  },
});

const asObj = (v: unknown, label: string): Record<string, unknown> => {
  if (typeof v !== "object" || v === null || Array.isArray(v)) throw new Error(`${label} must be an object`);
  return v as Record<string, unknown>;
};
const asStr = (v: unknown, label: string): string => {
  if (typeof v !== "string" || v.trim() === "") throw new Error(`${label} must be a non-empty string`);
  return v;
};
const asArr = (v: unknown, label: string): unknown[] => {
  if (!Array.isArray(v)) throw new Error(`${label} must be an array`);
  return v;
};

const parsePlan = (raw: unknown): Plan => {
  const obj = asObj(raw, "plan");
  const features = asArr(obj.features, "plan.features").map((f, i) => {
    const fo = asObj(f, `features[${i}]`);
    const reviewMode = asStr(fo.reviewMode, `features[${i}].reviewMode`);
    if (reviewMode !== "per-issue" && reviewMode !== "per-feature")
      throw new Error(`features[${i}].reviewMode must be "per-issue" or "per-feature"`);
    const issues = asArr(fo.issues, `features[${i}].issues`).map((n, j) => {
      if (typeof n !== "number" || !Number.isInteger(n)) throw new Error(`features[${i}].issues[${j}] must be an integer`);
      return n;
    });
    if (issues.length === 0) throw new Error(`features[${i}].issues must be non-empty`);
    return {
      branch: asStr(fo.branch, `features[${i}].branch`),
      base: asStr(fo.base, `features[${i}].base`),
      reviewMode,
      issues,
    } satisfies Feature;
  });
  return { features };
};

// --------------------------------------------------------------------------
// Issue fetching
// --------------------------------------------------------------------------

interface IssueData {
  number: number;
  title: string;
  body: string;
  labels: { name: string }[];
  comments: { body: string }[];
}

const issueCache = new Map<number, IssueData>();

const fetchIssue = (n: number): IssueData => {
  const cached = issueCache.get(n);
  if (cached) return cached;
  const data = ghJson<IssueData>(["issue", "view", String(n), "--json", "number,title,body,labels,comments"]);
  issueCache.set(n, data);
  return data;
};

const formatIssue = (d: IssueData): string => {
  const labels = d.labels.map((l) => l.name).join(", ") || "(none)";
  const comments = d.comments.length
    ? d.comments.map((c, i) => `--- comment ${i + 1} ---\n${c.body}`).join("\n")
    : "(no comments)";
  return `### Issue #${d.number}: ${d.title}\n\nLabels: ${labels}\n\n${d.body}\n\nComments:\n${comments}`;
};

// --------------------------------------------------------------------------
// The verification gate (safety net; the agents own green themselves)
// --------------------------------------------------------------------------

const touchedFrontend = (wt: string, base: string): boolean => {
  try {
    return sh(`git diff --name-only ${base}...HEAD -- frontend/`, wt).trim().length > 0;
  } catch {
    return false;
  }
};

interface GateResult {
  ok: boolean;
  output: string;
}

const runGate = (wt: string, base: string): GateResult => {
  const steps: { cmd: string; cwd: string }[] = [
    { cmd: PYTEST_CMD, cwd: wt },
    { cmd: "uv run pre-commit run --all-files", cwd: wt },
  ];
  if (touchedFrontend(wt, base)) {
    const fe = path.join(wt, "frontend");
    steps.push(
      { cmd: "npm install", cwd: fe },
      { cmd: "npm run build", cwd: fe },
      { cmd: "npm test -- --run", cwd: fe },
    );
  }
  let log = "";
  for (const step of steps) {
    log += `\n$ ${step.cmd}\n`;
    try {
      log += execSync(step.cmd, { cwd: step.cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], maxBuffer: BIG });
    } catch (e) {
      const err = e as { stdout?: string; stderr?: string; status?: number };
      log += `${err.stdout ?? ""}${err.stderr ?? ""}\n[exit ${err.status ?? "?"}]`;
      return { ok: false, output: log };
    }
  }
  return { ok: true, output: log };
};

// --------------------------------------------------------------------------
// Agents
// --------------------------------------------------------------------------

type Effort = "low" | "medium" | "high" | "xhigh" | "max";

const agent = (model: string, effort?: Effort) => {
  const token = process.env.CLAUDE_CODE_OAUTH_TOKEN;
  return sandcastle.claudeCode(model, {
    ...(token ? { env: { CLAUDE_CODE_OAUTH_TOKEN: token } } : {}),
    ...(effort ? { effort } : {}),
  });
};

class FeatureError extends Error {
  constructor(
    message: string,
    readonly output: string,
    readonly issues: number[],
  ) {
    super(message);
    this.name = "FeatureError";
  }
}

// --------------------------------------------------------------------------
// Planner
// --------------------------------------------------------------------------

const plan = async (issueDetails: string): Promise<Plan> => {
  const output = sandcastle.Output.object({ tag: "plan", schema: standardSchema(parsePlan) });
  const common = {
    name: "planner",
    agent: agent(MODELS.planner, EFFORT.planner),
    sandbox: noSandbox(),
    cwd: REPO_ROOT,
    logging: { type: "stdout" } as const,
    output,
  };
  try {
    const r = await sandcastle.run({
      ...common,
      promptFile: path.join(PROMPTS, "plan-prompt.md"),
      promptArgs: { ISSUE_DETAILS: issueDetails },
    });
    return r.output;
  } catch (e) {
    if (e instanceof sandcastle.StructuredOutputError && e.sessionId) {
      const r = await sandcastle.run({
        ...common,
        resumeSession: e.sessionId,
        prompt:
          "Your previous response did not contain a valid <plan> JSON block. " +
          "Re-emit ONLY a corrected <plan>...</plan> block matching the schema. Do not change files.",
      });
      return r.output;
    }
    throw e;
  }
};

// --------------------------------------------------------------------------
// Per-feature pipeline
// --------------------------------------------------------------------------

const reviewScope = (issues: number[]): string =>
  issues.length === 1 ? `issue #${issues[0]}` : `the feature (issues ${issues.map((n) => `#${n}`).join(", ")})`;

const specIssuesText = (issues: number[]): string =>
  issues.map((n) => formatIssue(fetchIssue(n))).join("\n\n---\n\n");

const handoffPathFor = (featureDir: string, issueNum: number): string =>
  path.join(featureDir, `handoff-issue-${issueNum}.md`);

const handoffsText = (featureDir: string, issues: number[]): string => {
  const parts = issues
    .map((n) => {
      const p = handoffPathFor(featureDir, n);
      return fs.existsSync(p) ? `### Handoff for issue #${n}\n\n${fs.readFileSync(p, "utf8").trim()}` : null;
    })
    .filter(Boolean) as string[];
  return parts.length ? parts.join("\n\n---\n\n") : "(no handoff was written)";
};

const gateWithRetry = async (
  sandbox: sandcastle.Sandbox,
  wt: string,
  base: string,
  issueNum: number,
  handoffPath: string,
): Promise<void> => {
  let gate = runGate(wt, base);
  let attempt = 0;
  while (!gate.ok && attempt < GATE_RETRY_ATTEMPTS) {
    attempt++;
    console.log(`  gate red for #${issueNum} — fix attempt ${attempt}/${GATE_RETRY_ATTEMPTS}`);
    await sandbox.run({
      name: `gate-fix-#${issueNum} (attempt ${attempt})`,
      agent: agent(MODELS.implement, EFFORT.implement),
      logging: { type: "stdout" },
      maxIterations: 20,
      prompt:
        `The verification gate failed after your implementation of issue #${issueNum} on branch ${sandbox.branch}. ` +
        `You have the full implementation in this worktree — find the cause and make the gate green. ` +
        `The gate is: \`${PYTEST_CMD}\`; \`uv run pre-commit run --all-files\`; and, if you touched frontend/, ` +
        `\`npm install && npm run build && npm test -- --run\` in frontend/. ` +
        `Do NOT delete or weaken any test to pass. Commit your fix (conventional commit, no RALPH prefix).\n\n` +
        `Gate output:\n\n${tail(gate.output, 12000)}\n\n` +
        `If your fix changed the design or anything the handoff at \`${handoffPath}\` describes, append a short ` +
        `"Gate fix" note to that file (do not commit it). ` +
        `When the gate is green, output <promise>COMPLETE</promise>.`,
    });
    gate = runGate(wt, base);
  }
  if (!gate.ok) {
    throw new FeatureError(
      `Gate still failing after ${GATE_RETRY_ATTEMPTS} fix attempt(s) for issue #${issueNum}.`,
      gate.output,
      [issueNum],
    );
  }
};

const reviewAndFix = async (
  sandbox: sandcastle.Sandbox,
  wt: string,
  feature: Feature,
  featureDir: string,
  issues: number[],
  fixedPoint: string,
): Promise<string> => {
  const tag = issues.length === 1 ? `issue-${issues[0]}` : "feature";
  const blockingPath = path.join(featureDir, `review-${tag}-blocking.md`);
  const notesPath = path.join(featureDir, `review-${tag}-notes.md`);
  const spec = specIssuesText(issues);
  const handoffs = handoffsText(featureDir, issues);

  await sandbox.run({
    name: `review-${tag}`,
    agent: agent(MODELS.review, EFFORT.review),
    logging: { type: "stdout" },
    maxIterations: 15,
    promptFile: path.join(PROMPTS, "review-prompt.md"),
    promptArgs: {
      BRANCH: feature.branch,
      FIXED_POINT: fixedPoint,
      REVIEW_SCOPE: reviewScope(issues),
      SPEC_ISSUES: spec,
      HANDOFFS: handoffs,
      BLOCKING_PATH: blockingPath,
      NOTES_PATH: notesPath,
    },
  });

  const blocking = fs.existsSync(blockingPath) ? fs.readFileSync(blockingPath, "utf8").trim() : "NONE";
  if (blocking && blocking.toUpperCase() !== "NONE") {
    console.log(`  review found blocking findings for ${tag} — running fix pass`);
    await sandbox.run({
      name: `review-fix-${tag}`,
      agent: agent(MODELS.reviewFix, EFFORT.reviewFix),
      logging: { type: "stdout" },
      maxIterations: 20,
      promptFile: path.join(PROMPTS, "review-fix-prompt.md"),
      promptArgs: {
        BRANCH: feature.branch,
        FIXED_POINT: fixedPoint,
        SPEC_ISSUES: spec,
        HANDOFFS: handoffs,
        BLOCKING_PATH: blockingPath,
        BLOCKING_FINDINGS: blocking,
      },
    });
    const gate = runGate(wt, feature.base);
    if (!gate.ok) {
      throw new FeatureError(`Gate failing after review-fix for ${tag}.`, gate.output, issues);
    }
  }

  return fs.existsSync(notesPath) ? fs.readFileSync(notesPath, "utf8").trim() : "";
};

const openPullRequest = (wt: string, feature: Feature, featureDir: string, notes: string[]): void => {
  // Push the branch (force-with-lease keeps re-runs idempotent without clobbering others' work).
  sh(`git push -u origin ${feature.branch} --force-with-lease`, wt);

  const lines = feature.issues.map((n) => `- #${n} ${fetchIssue(n).title}`).join("\n");
  const closes = feature.issues.map((n) => `Closes #${n}`).join("\n");
  const notesBody = notes.filter(Boolean).join("\n\n") || "_No judgment-call findings._";
  const title =
    feature.issues.length === 1
      ? fetchIssue(feature.issues[0]).title
      : `${fetchIssue(feature.issues[0]).title} (+${feature.issues.length - 1} more)`;

  const gateNote =
    process.platform === "win32"
      ? "Gate ran the full `uv run pytest` suite."
      : "⚠️ Gate ran the **cross-platform subset** (`uv run pytest -m \"not windows\"`) on Linux/WSL. " +
        "The Win32/WMI (`windows`-marked) tests were not run — validate them with a full `uv run pytest` on Windows before merging.";
  const body =
    `## Summary\n\nAutomated feature branch resolving:\n\n${lines}\n\n${closes}\n\n` +
    `## Review notes\n\n${notesBody}\n\n## Verification\n\n${gateNote}\n\n---\n` +
    `🤖 Generated by the sandcastle one-feature loop (\`.sandcastle/run.ts\`).\n`;
  const bodyPath = path.join(featureDir, "pr-body.md");
  fs.writeFileSync(bodyPath, body);

  // Stacked features target their predecessor branch; main-based features target main.
  const prBase = feature.base;
  try {
    const out = ghRun(
      ["pr", "create", "--base", prBase, "--head", feature.branch, "--title", title, "--body-file", bodyPath],
      wt,
    );
    console.log(`  PR: ${out.trim()}`);
  } catch (e) {
    const err = e as { stdout?: string; stderr?: string };
    console.log(`  PR create skipped/failed (a PR may already exist): ${(err.stderr ?? err.stdout ?? "").trim()}`);
  }
};

const processFeature = async (feature: Feature, featureDir: string): Promise<string[]> => {
  fs.mkdirSync(featureDir, { recursive: true });
  const allNotes: string[] = [];

  const sandbox = await sandcastle.createSandbox({
    branch: feature.branch,
    baseBranch: feature.base,
    sandbox: noSandbox(),
    cwd: REPO_ROOT,
    // `.claude/` is gitignored, so a worktree forked from a branch does NOT
    // contain the skills/instructions the prompts rely on (tdd, review,
    // handoff). Copy them in at creation so the agents — whose cwd is the
    // worktree — can find them. See README "load-bearing behaviors".
    copyToWorktree: [".claude"],
    hooks: { host: { onWorktreeReady: [{ command: "uv sync", timeoutMs: 600_000 }] } },
  });

  try {
    const wt = sandbox.worktreePath;
    console.log(`  worktree: ${wt}`);

    for (const issueNum of feature.issues) {
      const baseSha = sh("git rev-parse HEAD", wt).trim();
      const issue = fetchIssue(issueNum);
      console.log(`  implementing #${issueNum}: ${issue.title}`);

      await sandbox.run({
        name: `implement-#${issueNum}`,
        agent: agent(MODELS.implement, EFFORT.implement),
        logging: { type: "stdout" },
        maxIterations: 30,
        promptFile: path.join(PROMPTS, "implement-prompt.md"),
        promptArgs: {
          ISSUE_NUMBER: String(issueNum),
          ISSUE_TITLE: issue.title,
          BRANCH: feature.branch,
          ISSUE_CONTEXT: formatIssue(issue),
          HANDOFF_PATH: handoffPathFor(featureDir, issueNum),
        },
      });

      await gateWithRetry(sandbox, wt, feature.base, issueNum, handoffPathFor(featureDir, issueNum));

      if (feature.reviewMode === "per-issue") {
        allNotes.push(await reviewAndFix(sandbox, wt, feature, featureDir, [issueNum], baseSha));
      }
    }

    if (feature.reviewMode === "per-feature") {
      allNotes.push(await reviewAndFix(sandbox, wt, feature, featureDir, feature.issues, feature.base));
    }

    openPullRequest(wt, feature, featureDir, allNotes);
    return allNotes;
  } finally {
    await sandbox.close();
  }
};

// --------------------------------------------------------------------------
// CLI + main loop
// --------------------------------------------------------------------------

interface Args {
  issues: number[];
  reviewModeOverride?: ReviewMode;
  maxFeatures: number;
}

const parseArgs = (argv: string[]): Args => {
  const issues: number[] = [];
  let reviewModeOverride: ReviewMode | undefined;
  let maxFeatures = DEFAULT_MAX_FEATURES;
  for (const a of argv) {
    if (a.startsWith("--review-mode=")) {
      const v = a.slice("--review-mode=".length);
      if (v !== "per-issue" && v !== "per-feature") throw new Error(`--review-mode must be per-issue|per-feature`);
      reviewModeOverride = v;
    } else if (a.startsWith("--max-features=")) {
      maxFeatures = Number(a.slice("--max-features=".length));
      if (!Number.isInteger(maxFeatures) || maxFeatures < 1) throw new Error(`--max-features must be a positive integer`);
    } else {
      const n = Number(a);
      if (!Number.isInteger(n) || n < 1) throw new Error(`Unrecognized argument: ${a}`);
      issues.push(n);
    }
  }
  if (issues.length === 0) throw new Error("Pass at least one issue number, e.g. `npm start -- 40 41 42`.");
  return { issues, reviewModeOverride, maxFeatures };
};

const main = async (): Promise<void> => {
  const args = parseArgs(process.argv.slice(2));

  const runId = new Date().toISOString().replace(/[:.]/g, "-");
  const runDir = path.join(SCRIPT_DIR, "runs", runId);
  fs.mkdirSync(runDir, { recursive: true });
  console.log(`Run ${runId}\nIssues: ${args.issues.join(", ")}\nArtifacts: ${runDir}\n`);

  // Prefetch issues and plan.
  const issueDetails = args.issues.map((n) => formatIssue(fetchIssue(n))).join("\n\n---\n\n");
  console.log("Planning…");
  const planned = await plan(issueDetails);

  // Apply CLI override + cap.
  let features = planned.features.map((f) =>
    args.reviewModeOverride ? { ...f, reviewMode: args.reviewModeOverride } : f,
  );
  if (features.length > args.maxFeatures) {
    console.log(`Plan has ${features.length} features; capping at --max-features=${args.maxFeatures}.`);
    features = features.slice(0, args.maxFeatures);
  }

  fs.writeFileSync(path.join(runDir, "plan.json"), JSON.stringify({ features }, null, 2));

  if (features.length === 0) {
    console.log("Planner produced no actionable features. Nothing to do.");
    return;
  }

  console.log(`\nPlan: ${features.length} feature(s)`);
  for (const f of features) {
    console.log(`  ${f.branch} (base ${f.base}, ${f.reviewMode}): ${f.issues.map((n) => `#${n}`).join(" ")}`);
  }
  console.log("");

  const plannedBranches = new Set(features.map((f) => f.branch));
  const outcome = new Map<string, "success" | "failed" | "skipped">();

  for (const f of features) {
    const featureDir = path.join(runDir, sanitizeBranch(f.branch));
    // If this feature stacks on an in-run feature that did NOT succeed, skip it as blocked.
    if (f.base !== "main" && plannedBranches.has(f.base) && outcome.get(f.base) !== "success") {
      outcome.set(f.branch, "skipped");
      console.log(`⏭  ${f.branch}: skipped (base ${f.base} did not succeed)`);
      for (const n of f.issues) {
        try {
          ghRun(["issue", "comment", String(n), "--body", `🤖 Skipped by sandcastle: blocked on unfinished base branch \`${f.base}\`.`]);
        } catch { /* best effort */ }
      }
      continue;
    }

    console.log(`\n=== Feature ${f.branch} ===`);
    try {
      await processFeature(f, featureDir);
      outcome.set(f.branch, "success");
      console.log(`✅ ${f.branch}: PR opened.`);
    } catch (e) {
      outcome.set(f.branch, "failed");
      const fe = e instanceof FeatureError ? e : new FeatureError(String(e), e instanceof Error ? (e.stack ?? e.message) : String(e), f.issues);
      console.error(`❌ ${f.branch}: ${fe.message}`);
      fs.writeFileSync(path.join(featureDir, "failure.txt"), `${fe.message}\n\n${fe.output}`);
      const comment =
        `🤖 Sandcastle could not complete this automatically.\n\n` +
        `**Branch left for inspection:** \`${f.branch}\`\n\n` +
        `**Reason:** ${fe.message}\n\n` +
        `<details><summary>gate / error output</summary>\n\n\`\`\`\n${tail(fe.output, 8000)}\n\`\`\`\n</details>`;
      for (const n of fe.issues) {
        try {
          ghRun(["issue", "comment", String(n), "--body", comment]);
        } catch { /* best effort */ }
      }
    }
  }

  // Summary
  const rows = features.map((f) => `  ${outcome.get(f.branch) ?? "?"}\t${f.branch}\t${f.issues.map((n) => `#${n}`).join(" ")}`);
  const summary = `Run ${runId}\n\n${rows.join("\n")}\n`;
  fs.writeFileSync(path.join(runDir, "summary.md"), summary);
  console.log(`\n=== Summary ===\n${summary}`);
};

main().catch((e) => {
  console.error(`\nFATAL: ${e instanceof Error ? e.stack ?? e.message : String(e)}`);
  process.exit(1);
});
