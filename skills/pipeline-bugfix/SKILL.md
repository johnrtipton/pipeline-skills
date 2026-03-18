---
name: pipeline-bugfix
description: >
  Execute a Bug Fix pipeline: environment check, diagnosis, fix, test, regression
  check, documentation, commit & PR, code review, test verification, review verdict,
  merge, and retrospective. Invoke with /pipeline-bugfix followed by the bug report.
---

# Bug Fix Pipeline

Run a complete bug fix cycle with diagnosis, targeted fix, regression checking, and quality gates.

**Usage**: `/pipeline-bugfix <bug report / description>`

---

## Before You Start

1. Follow the **Configuration Gathering** procedure from pipeline-shared to identify project config
2. Generate a branch name from the bug report: `fix/<short-slug>` (e.g., `fix/login-timeout`)
3. Note the project's pr_target_branch (default: `main`)

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

## Stage 3: Diagnosis

Investigate the codebase, identify the root cause, and propose a fix.

### Instructions

1. Read the bug report carefully
2. Search the codebase for relevant code paths
3. Identify the root cause (not just the symptom)
4. Propose a targeted fix
5. **Scope check**: Compare what you found against the bug report. If you found violations/issues in MORE files or locations than described, output on its own line:
   ```
   SCOPE_EXPANDED: found X violations across Y files (spec described N)
   ```
   This is informational — continue with the full diagnosis.

### Gate
This stage always passes (informational). The diagnosis output will be referenced by Fix and Regression Check.

---

## Stage 4: Fix

Apply the fix based on the diagnosis from Stage 3.

### Instructions

1. Implement the fix — keep changes minimal and focused
2. Only fix what the diagnosis identified as the root cause
3. Do not refactor surrounding code or fix unrelated issues
4. **Edge cases**: Verify the Edge Case Checklist from pipeline-shared
5. **Clean git state**: Follow the Clean Git State procedure from pipeline-shared

If the branch already has commits from a previous attempt, build on that work — do NOT redo what's already done.

### Gate
Stage passes if fix completes without errors. Proceed to testing.

---

## Stage 5: Test Execution

Follow the **Test Execution** procedure from pipeline-shared.

Gate: `TESTS_PASSED` required.

**On TESTS_FAILED**: Go back and fix the failing code, then re-run tests (attempt 2 of 2). If tests still fail → **STOP PIPELINE**.

---

## Stage 6: Regression Check

Verify the fix doesn't introduce regressions and actually addresses the root cause.

### Instructions

1. **Root cause verification**: Cross-reference the Diagnosis stage output (Stage 3) against the fix. Verify the root cause identified was actually addressed, not just a symptom. Flag if the fix diverged from the diagnosis.

2. **Regression check**: Verify no related functionality is broken

3. **Edge case review**: Confirm edge cases are handled

### Gate
- **Pass**: `REGRESSION_PASSED` — no regressions found
- **Fail**: `REGRESSION_FAILED` — followed by details

**On REGRESSION_FAILED (attempt 1)**: Fix the issues, then re-check.

**On REGRESSION_FAILED (attempt 2)**: **Rewind to Stage 3 (Diagnosis)**. The original diagnosis may have been incomplete. Re-investigate with the regression context. Then re-fix from Stage 4 onward. Maximum 1 rewind. If second pass also fails → **STOP PIPELINE**.

---

## Stage 7: Documentation

Follow the **Documentation** procedure from pipeline-shared.

Gate: `DOCS_UPDATED` (always passes).

---

## Stage 8: Commit & PR

Follow the **Commit & PR** procedure from pipeline-shared.

Use conventional commit format: `fix: <description>`

Gate: `PR_CREATED`, `PR_EXISTS`, or `PR_SKIPPED`.

---

## Stage 9: Code Review

Follow the **Code Review** procedure from pipeline-shared.

Gate: `REVIEW_COMPLETE` (always passes, informational).

---

## Stage 10: Test Verification

Follow the **Test Verification** procedure from pipeline-shared.

Gate: `TESTS_PASSED` required.

**On TESTS_FAILED**: Retry once. If retry fails → **STOP PIPELINE**.

---

## Stage 11: Review Verdict

Follow the **Review Verdict** procedure from pipeline-shared.

Output `APPROVE`, `REQUEST_CHANGES`, or `COMMENT`.

---

## Stage 12: Merge PR

Follow the **Merge PR** procedure from pipeline-shared.

Gate: `PR_MERGED` required.

**On MERGE_FAILED**: Retry once. If retry fails → **STOP PIPELINE**.

---

## Stage 13: Retrospective

Follow the **Retrospective** procedure from pipeline-shared. Use the Agent tool to run this as a subagent.

---

## Stop Conditions

- `ENV_FAILED` after retry
- `MERGE_CONFLICTS_FOUND`
- `TESTS_FAILED` after retry (Stage 5 or 10)
- `REGRESSION_FAILED` after retry + rewind
- `MERGE_FAILED` after retry

---

## Rewind Rules

| Stage | Can Rewind To | Max Rewinds | Trigger |
|---|---|---|---|
| Stage 6 (Regression Check) | Stage 3 (Diagnosis) | 1 | REGRESSION_FAILED after retry |
