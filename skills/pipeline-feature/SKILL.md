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

**CRITICAL: You MUST execute ALL 15 stages. Do NOT stop after Commit & PR (Stage 10). Stages 11-15 (Code Review, Test Verification, Review Verdict, Merge PR, Retrospective) are mandatory — they are where quality is verified and the PR is merged. A pipeline that stops at Stage 10 is incomplete.**

---

## Before You Start

1. Follow the **Configuration Gathering** procedure from pipeline-shared to identify project config
2. Generate a branch name from the task description: `feat/<short-slug>` (e.g., `feat/add-user-auth`)
3. Note the project's pr_target_branch (default: `main`)
4. **Check for resume state**: Follow the **Pipeline State File** procedure from pipeline-shared. If `.pipeline-state/<branch-name>.json` exists, resume from the last incomplete stage — skip all passed stages and print a resume summary
5. **Write state after every stage**: Update `.pipeline-state/<branch-name>.json` after each stage completes (pass or fail). This enables resuming if the session is interrupted.

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

2. **Auto-reject triggers** (any of these → `REVIEW_FAILED`):
   - `print()` statements instead of project logging system
   - f-string formatting in logger calls (use `%s` style instead)
   - `console.log` in production JS without debug guard (e.g., `if (globalThis.djustDebug)`)
   - Silent exception handling (`except: pass`, `except Exception: pass`)
   - No tests for new functionality
   - Tests reference modules/APIs that don't exist in the diff
   - `mark_safe()` with unescaped interpolated values
   - `|safe` template filter on user-controlled variables
   - `@csrf_exempt` without documented justification
   - Placeholder/stub implementations (`return True`, hardcoded fake data)
   - Comments indicating incomplete code ("simulate", "would be implemented", "for now")
   - Untracked files that tests depend on are missing from the diff
   - `noqa` on security issues
   - New JS feature files without corresponding test files
   - Missing CHANGELOG.md update for `feat:` or `fix:` changes

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

**After this stage completes, you MUST continue to Stage 11. The pipeline is NOT done.**

---

## Stages 11-15: Review, Verify, Merge, Retrospective

**These stages run as subagents to ensure they execute with fresh context.** This prevents context compression from losing the review instructions — the same reason the orchestrator uses fresh sessions for these stages.

### Stage 11-13: Code Review + Test Verification + Review Verdict

Use the **Agent tool** to spawn a subagent with this prompt:

> You are reviewing PR #`<pr_number>` on GitHub. The project directory is `<project_path>`. The PR targets `<pr_target_branch>`.
>
> **Step 1 — Code Review**:
> 1. Run `git diff <pr_target_branch>...HEAD` to see all changes. Read changed files for full context.
> 2. Check for a project PR checklist at `docs/PULL_REQUEST_CHECKLIST.md` or `PULL_REQUEST_CHECKLIST.md` — if found, use it as the review framework.
> 3. Review for: correctness, security (mark_safe, |safe, csrf_exempt, XSS, injection), testing gaps, code quality (print vs logging, f-string in loggers, silent exceptions, console.log without debug guards), documentation (CHANGELOG updated for feat/fix), performance (N+1 queries), architecture.
> 4. Flag auto-reject triggers: print() instead of logging, f-string in loggers, unguarded console.log, except:pass, no tests for new code, tests referencing phantom modules, mark_safe with unescaped interpolation, placeholder/stub code.
> 5. **Post the review to GitHub** as a PR review comment:
>    `gh pr review <pr_number> --comment --body '<formatted review with checklist, findings, and verdict>'`
>    Include a checklist summary of what was checked and pass/fail status.
> 6. If the project has a `pr/feedback/` directory, also save the review to `pr/feedback/pr-<number>-<short-slug>.md`.
>
> **Step 2 — Test Verification**: Run the project test suite. Report pass/fail. If tests fail, output TESTS_FAILED.
>
> **Step 3 — Review Verdict**: Synthesize findings.
> - If any auto-reject triggers found OR tests failed → post `gh pr review <pr_number> --request-changes --body '<issues>'` and output REQUEST_CHANGES.
> - Otherwise → output APPROVE.
> Output exactly one of: APPROVE, REQUEST_CHANGES, or COMMENT.

Collect the subagent's output.

- If `APPROVE` → proceed to Stage 14
- If `REQUEST_CHANGES` → fix the issues listed, re-commit, re-push, then re-run this subagent. If second attempt also returns `REQUEST_CHANGES` → **STOP PIPELINE**.
- If `TESTS_FAILED` → fix and retry once. If still failing → **STOP PIPELINE**.

### Stage 14: Merge PR

Use the **Agent tool** to spawn a subagent with this prompt:

> Approve and merge PR #`<pr_number>` in `<project_path>`.
> 1. Run: `gh pr review <pr_number> --approve --body 'Automated review passed: tests pass, no auto-reject triggers, checklist clean.'`
> 2. Run: `gh pr merge <pr_number> --squash --delete-branch`
> 3. If merge succeeds, output: PR_MERGED
> 4. If merge fails, output: MERGE_FAILED followed by error details.

Collect the subagent's output.

- If `PR_MERGED` → proceed to Stage 15
- If `MERGE_FAILED` → retry once. If still failing → **STOP PIPELINE**.

### Stage 15: Retrospective

Use the **Agent tool** to spawn a subagent with this prompt:

> Review the pipeline execution for the task: `<task description>`. The project is at `<project_path>`.
> Run `git log --oneline <pr_target_branch>..HEAD` to see what was done.
> 1. Rate execution quality (1-5)
> 2. What went well?
> 3. What could improve?
> 4. Output improvement ideas as IDEA: lines (one per line)
> 5. If useful scripts/tools were created, output as TOOL: name | language | description

Collect and report the retrospective output. **The pipeline is now complete.**

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
