---
name: pipeline-feature
description: >
  Execute a full Feature Implementation pipeline: environment check, planning,
  TDD implementation, test, self-review, security scan, documentation, commit & PR,
  code review, test verification, review verdict, merge, and retrospective.
  Invoke with /pipeline-feature followed by the task description.
---

# Feature Implementation Pipeline

Run a complete feature development cycle with quality gates, retry, and rewind capabilities.

**Usage**: `/pipeline-feature <task description>`

---

## Before You Start

1. Follow the **Configuration Gathering** procedure from pipeline-shared to identify project config
2. Generate a branch name from the task description: `feat/<short-slug>` (e.g., `feat/add-user-auth`)
3. Note the project's pr_target_branch (default: `main`)

---

## Stage 1: Environment Check

Follow the **Environment Check** procedure from pipeline-shared.

Use the branch name generated above. Gate: `ENV_OK` required.

**On ENV_FAILED**: Retry once. If retry fails → **STOP PIPELINE**.

---

## Stage 2: Change Detection

Follow the **Change Detection** procedure from pipeline-shared.

Record the result (`CODE_CHANGES` or `DOCS_ONLY`) — it controls whether stages 6, 7, and 8 run.

---

## Stage 3: Conflict Check

Follow the **Conflict Check** procedure from pipeline-shared.

Gate: `MERGE_CLEAN` required.

**On MERGE_CONFLICTS_FOUND** → **STOP PIPELINE** immediately.

---

## Stage 4: Planning

Analyze the task and create a detailed implementation plan.

### Instructions

Read the codebase to understand the current state. Output a structured plan:

1. **Files to create or modify** — list every file with a brief description of changes
2. **Key design decisions** — architecture choices, library selection, API design
3. **Test strategy** — what to test, test types (unit, integration), edge cases
4. **Potential risks** — breaking changes, performance concerns, security considerations

This stage is read-only — do not modify any files yet.

### Gate
This stage always passes (informational). The plan output will be referenced by Implementation and Self-Review.

---

## Stage 5: Implementation (TDD)

Implement the feature using test-driven development. Write tests first, then implement to make them pass.

### Instructions

1. **Write tests first**: Based on the plan from Stage 4, write comprehensive tests
2. **Implement**: Write the code to make all tests pass
3. **Edge cases**: Before finishing, verify the Edge Case Checklist from pipeline-shared:
   - Null/None/empty values in all inputs
   - Circular references (if recursive data structures)
   - Boundary conditions (empty collections, single items)
   - Concurrent access (if modifying shared state)
4. **Clean git state**: Follow the Clean Git State procedure from pipeline-shared:
   - Resolve any conflict markers
   - Stage all changes (`git add -u` + explicit `git add` for new files)
   - Verify `git status` shows clean state

If the branch already has commits from a previous attempt, build on that work — do NOT redo what's already done.

### Gate
Stage passes if implementation completes without errors. Proceed to testing.

---

## Stage 6: Test Execution

**Skip this stage if Stage 2 output was DOCS_ONLY.**

Follow the **Test Execution** procedure from pipeline-shared.

Gate: `TESTS_PASSED` required.

**On TESTS_FAILED**: Go back and fix the failing code, then re-run tests (attempt 2 of 2). If tests still fail → **STOP PIPELINE**.

---

## Stage 7: Self-Review

**Skip this stage if Stage 2 output was DOCS_ONLY.**

Review the changes made in Stages 4-5.

### Instructions

Check for:

1. **Plan compliance**: Cross-reference the Planning stage output (Stage 4) against the implementation. List every deliverable from the plan and mark each as DONE or MISSING. If any scope was silently dropped, output `REVIEW_FAILED` with the missing items.

2. **Auto-reject triggers**: Skipped tests, `noqa` on security issues

3. **Test coverage gaps**: New code paths without tests

4. **Type hint completeness**: Missing type annotations on public APIs

5. **Breaking changes**: Unintended API or behavior changes

6. **Code quality** — specifically check for:
   - Broad `except Exception` or bare `except:` where a specific exception should be caught
   - Missing exception chaining (`raise X from e` — not just `raise X`)
   - Unused function parameters or fixture arguments
   - Misleading or incorrect test fixtures/settings
   - Lazy imports inside loops or properties that should be module-level
   - Warning/error messages that reference implementation details or outdated instructions

### Gate
- **Pass**: `REVIEW_PASSED`
- **Fail**: `REVIEW_FAILED` — followed by list of issues

**On REVIEW_FAILED (attempt 1)**: Fix the issues identified, then re-check. Output `REVIEW_PASSED` or `REVIEW_FAILED`.

**On REVIEW_FAILED (attempt 2)**: **Rewind to Stage 4 (Planning)**. Re-read the review failures. Create a new plan that addresses every issue flagged. Then re-implement from Stage 5 onward. This rewind can happen at most once. If the second pass also fails Self-Review → **STOP PIPELINE**.

---

## Stage 8: Security Check

**Skip this stage if Stage 2 output was DOCS_ONLY.**

Follow the **Security Check** procedure from pipeline-shared. Use the Agent tool to run this as a subagent for independent evaluation.

Gate: `SECURITY_PASSED` required.

**On SECURITY_FAILED**: Fix the issues, then re-scan (attempt 2 of 2). If still failing → **STOP PIPELINE**.

---

## Stage 9: Documentation

Follow the **Documentation** procedure from pipeline-shared.

Gate: `DOCS_UPDATED` (always passes).

---

## Stage 10: Commit & PR

Follow the **Commit & PR** procedure from pipeline-shared.

Use conventional commit format: `feat: <description>`

Gate: `PR_CREATED`, `PR_EXISTS`, or `PR_SKIPPED`.

---

## Stage 11: Code Review

Follow the **Code Review** procedure from pipeline-shared.

Gate: `REVIEW_COMPLETE` (always passes, informational).

---

## Stage 12: Test Verification

Follow the **Test Verification** procedure from pipeline-shared.

Gate: `TESTS_PASSED` required.

**On TESTS_FAILED**: Retry once. If retry fails → **STOP PIPELINE**.

---

## Stage 13: Review Verdict

Follow the **Review Verdict** procedure from pipeline-shared.

Synthesize Code Review and Test Verification findings. Output `APPROVE`, `REQUEST_CHANGES`, or `COMMENT`.

If `REQUEST_CHANGES`: list the issues that need to be addressed. These become follow-up tasks.

---

## Stage 14: Merge PR

Follow the **Merge PR** procedure from pipeline-shared.

Gate: `PR_MERGED` required.

**On MERGE_FAILED**: Retry once. If retry fails → **STOP PIPELINE**.

---

## Stage 15: Retrospective

Follow the **Retrospective** procedure from pipeline-shared. Use the Agent tool to run this as a subagent for independent evaluation.

Rate the execution, identify improvements, output `IDEA:` and `TOOL:` lines.

---

## Stop Conditions

The pipeline stops immediately when any of these occur:
- `ENV_FAILED` after retry
- `MERGE_CONFLICTS_FOUND`
- `TESTS_FAILED` after retry (Stage 6 or 12)
- `REVIEW_FAILED` after retry + rewind
- `SECURITY_FAILED` after retry
- `MERGE_FAILED` after retry

When stopping, output a clear summary: which stage failed, what the failure was, and what needs to be fixed before re-running.

---

## Rewind Rules

| Stage | Can Rewind To | Max Rewinds | Trigger |
|---|---|---|---|
| Stage 7 (Self-Review) | Stage 4 (Planning) | 1 | REVIEW_FAILED after retry |

When rewinding:
1. Carry the full failure context (what was wrong, what was tried)
2. The new plan MUST address every issue flagged in the review
3. Re-implement from Stage 5 through Stage 7
4. If the second pass also fails → stop the pipeline
