---
name: pipeline-refactor
description: >
  Execute a Refactor pipeline: environment check, analysis, refactor execution,
  test, review, documentation, commit & PR, code review, test verification,
  review verdict, merge, and retrospective. Invoke with /pipeline-refactor
  followed by the refactor description.
---

# Refactor Pipeline

Run a complete refactoring cycle with analysis, behavior-preserving execution, review, and quality gates.

**Usage**: `/pipeline-refactor <refactor description>`

**CRITICAL: You MUST execute ALL 13 stages. Do NOT stop after Commit & PR (Stage 8). Stages 9-13 (Code Review, Test Verification, Review Verdict, Merge PR, Retrospective) are mandatory.**

---

## Before You Start

1. Follow the **Configuration Gathering** procedure from pipeline-shared to identify project config
2. Generate a branch name from the task: `refactor/<short-slug>` (e.g., `refactor/split-views-module`)
3. Note the project's pr_target_branch (default: `main`)
4. **Check for resume state**: Follow the **Pipeline State File** procedure from pipeline-shared. If `.pipeline-state/<branch-name>.json` exists, resume from the last incomplete stage — skip all passed stages and print a resume summary
5. **Write state after every stage**: Update `.pipeline-state/<branch-name>.json` after each stage completes (pass or fail). This enables resuming if the session is interrupted.

---

## Stage 1: Environment Check

Follow the **Environment Check** procedure from pipeline-shared.

Gate: `ENV_OK` required.

**On ENV_FAILED**: Retry once. If retry fails → **STOP PIPELINE**.

---

## Stage 2: Conflict Check

Follow the **Conflict Check** procedure from pipeline-shared.

Gate: `MERGE_CLEAN` required.

**On MERGE_CONFLICTS_FOUND** → **STOP PIPELINE**.

---

## Stage 3: Analysis

Analyze the code to be refactored.

### Instructions

1. Read the refactor description and identify the target code
2. Understand the current structure and patterns
3. Identify code smells and issues motivating the refactor
4. Propose a refactoring approach
5. List all files that will be affected
6. Assess risk: what could break, what tests cover the code

### Output

- Current structure and patterns
- Code smells and issues found
- Proposed refactoring approach (step by step)
- Files that will be affected
- Risk assessment

### Gate
This stage always passes (informational). The analysis output will be referenced by Refactor Execution and Review.

---

## Stage 4: Refactor Execution

Execute the refactoring based on the analysis from Stage 3.

### Instructions

1. Apply the refactoring as planned in the analysis
2. **Preserve all existing behavior** — this is a refactor, not a feature change
3. Do not add new functionality or change APIs
4. Ensure all existing tests continue to pass
5. **Clean git state**: Follow the Clean Git State procedure from pipeline-shared

If the branch already has commits from a previous attempt, build on that work — do NOT redo what's already done.

### Gate
Stage passes if refactoring completes without errors. Proceed to testing.

---

## Stage 5: Test Execution

Follow the **Test Execution** procedure from pipeline-shared.

Gate: `TESTS_PASSED` required.

**On TESTS_FAILED**: Go back and fix the issue (behavior must be preserved), then re-run tests (attempt 2 of 2). If tests still fail → **STOP PIPELINE**.

---

## Stage 6: Review

Review the refactoring changes for quality and behavior preservation.

### Instructions

1. **Analysis compliance**: Cross-reference the Analysis stage output (Stage 3) against the refactoring. Flag any planned changes that were not implemented.

2. **Behavior preservation**: Verify that all existing behavior is preserved. No functional changes.

3. **Code quality**: Verify the code is cleaner and more maintainable than before.

4. **Dead code**: No dead code left behind.

5. **Naming consistency**: Variable, function, and class names are consistent.

### Gate
- **Pass**: `REVIEW_PASSED`
- **Fail**: `REVIEW_FAILED` — followed by list of issues

**On REVIEW_FAILED (attempt 1)**: Fix the issues, then re-check.

**On REVIEW_FAILED (attempt 2)**: **Rewind to Stage 3 (Analysis)**. The original analysis may have missed something. Re-analyze with the review context. Then re-execute from Stage 4 onward. Maximum 1 rewind. If second pass also fails → **STOP PIPELINE**.

---

## Stage 7: Documentation

Follow the **Documentation** procedure from pipeline-shared.

Gate: `DOCS_UPDATED` (always passes).

---

## Stage 8: Commit & PR

Follow the **Commit & PR** procedure from pipeline-shared.

Use conventional commit format: `refactor: <description>`

Gate: `PR_CREATED`, `PR_EXISTS`, or `PR_SKIPPED`.

**After this stage completes, you MUST continue to Stage 9. The pipeline is NOT done.**

---

## Stages 9-13: Review, Verify, Merge, Retrospective

**These stages run as subagents to ensure they execute with fresh context.**

### Stage 9-11: Code Review + Test Verification + Review Verdict

Use the **Agent tool** to spawn a subagent with this prompt:

> You are reviewing a pull request for a refactor. The project directory is `<project_path>`. The PR targets `<pr_target_branch>`.
>
> **Step 1 — Code Review**: Run `git diff <pr_target_branch>...HEAD` to see all changes. Read changed files for full context. Check for a project PR checklist at `docs/PULL_REQUEST_CHECKLIST.md` or `PULL_REQUEST_CHECKLIST.md` — if found, use it as the review framework. Review for: behavior preservation (refactor must not change functionality), correctness, security, testing gaps, code quality, documentation. Flag auto-reject triggers.
>
> **Step 2 — Test Verification**: Run the project test suite. Report pass/fail.
>
> **Step 3 — Review Verdict**: Synthesize findings. Output exactly one of: APPROVE, REQUEST_CHANGES, or COMMENT.

- If `APPROVE` → proceed to Stage 12
- If `REQUEST_CHANGES` → fix issues, re-commit, re-push, re-run subagent. Second failure → **STOP PIPELINE**.

### Stage 12: Merge PR

Use the **Agent tool** to spawn a subagent:

> Approve and merge PR #`<pr_number>` in `<project_path>`.
> 1. `gh pr review <pr_number> --approve --body 'Auto-approved: tests pass, review complete.'`
> 2. `gh pr merge <pr_number> --squash --delete-branch`
> 3. Output PR_MERGED or MERGE_FAILED.

- If `PR_MERGED` → proceed to Stage 13
- If `MERGE_FAILED` → retry once. Still failing → **STOP PIPELINE**.

### Stage 13: Retrospective

Use the **Agent tool** to spawn a subagent:

> Review the pipeline execution for the refactor: `<task description>`. Project: `<project_path>`.
> Run `git log --oneline <pr_target_branch>..HEAD`.
> Rate quality (1-5), what went well, what could improve. Output IDEA: and TOOL: lines.

**The pipeline is now complete.**

---

## Stop Conditions

- `ENV_FAILED` after retry
- `MERGE_CONFLICTS_FOUND`
- `TESTS_FAILED` after retry (Stage 5 or 10)
- `REVIEW_FAILED` after retry + rewind
- `MERGE_FAILED` after retry

---

## Rewind Rules

| Stage | Can Rewind To | Max Rewinds | Trigger |
|---|---|---|---|
| Stage 6 (Review) | Stage 3 (Analysis) | 1 | REVIEW_FAILED after retry |
