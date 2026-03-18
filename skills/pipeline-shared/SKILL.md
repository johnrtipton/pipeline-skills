---
name: pipeline-shared
description: >
  Shared pipeline stage procedures used by pipeline-feature, pipeline-bugfix,
  and pipeline-refactor skills. Not invoked directly — referenced by pipeline-specific
  skills as reusable building blocks for environment setup, testing, security scanning,
  documentation, commit/PR, code review, merge, and retrospective stages.
---

# Shared Pipeline Procedures

These procedures are referenced by name from the pipeline-feature, pipeline-bugfix, and pipeline-refactor skills. Each procedure is a self-contained stage with its own quality gate.

---

## Quality Gate Protocol

Every stage MUST output its verdict string on its own line. Follow these rules:

1. **Explicit FAILED overrides PASSED**: If output contains both `TESTS_PASSED` and `TESTS_FAILED`, the result is **FAILED**. The failure marker always wins.
2. **Retry protocol**: On first failure, re-examine the issue and try again (attempt 2 of 2). If second attempt also fails, follow the stage's failure action (stop or rewind).
3. **Rewind protocol**: When a stage rewinds, carry the failure details as context. Re-plan/re-diagnose addressing every flagged issue. Maximum 1 rewind per pipeline run.
4. **Never skip the verdict**: Every stage MUST end with its verdict string. Do not proceed without it.

---

## Configuration Gathering

At the start of any pipeline, gather project context:

1. Read CLAUDE.md in the project root (if it exists) for project conventions
2. Detect or read from CLAUDE.md:
   - `test_command` — how to run tests (e.g., `make test`, `pytest`, `npm test`)
   - `venv_path` — virtual environment location (`.venv/`, `venv/`, etc.)
   - `default_branch` — main branch name (`main`, `master`, `development`)
   - `pr_target_branch` — branch PRs should target (usually same as default_branch)
   - `build_command` — how to build the project
   - `lint_command` — how to lint
3. If CLAUDE.md doesn't specify these, auto-detect:
   - Check for `Makefile` targets (`make test`, `make lint`)
   - Check for `pyproject.toml`, `package.json`, `Cargo.toml`
   - Check for `.python-version`
   - Check git remote for repo URL

---

## Environment Check

Validate the project environment and create a fresh branch from upstream.

### Steps

1. **Git freshness**: Create a fresh branch from the upstream target.
   - Run `git fetch origin`
   - Determine the target branch: check for `pr_target_branch` first, then `default_branch`, then try `main`, `master`, `development`
   - Create a new task branch: `git checkout -B <task-branch> origin/<target_branch>`
   - This sets HEAD to the remote target — no stale history, no carry-over from previous branches
   - Do NOT use `git reset --hard` or `git checkout -- .` — these don't move HEAD

2. **Python version**: Run `python --version` or `python3 --version`. Verify compatibility with `.python-version` or `pyproject.toml` if present.

3. **Virtualenv**: Check for venv (`.venv/`, `venv/`, `env/`, or project-configured path). If none found, create one: `python -m venv .venv`.

4. **Dependencies**: Activate venv, run install command (`pip install -e .`, `uv sync`, `pip install -r requirements.txt`, or project-configured command).

5. **Smoke test**: Run a minimal import check (e.g., `python -c 'import django'` for Django projects).

If any step fails, attempt to fix it before proceeding.

### Gate
- **Pass**: `ENV_OK` — environment is ready
- **Fail**: `ENV_FAILED` — followed by details of what could not be fixed
- **On failure**: Retry once. If retry fails, **stop the pipeline**.

---

## Conflict Check

Check the working tree for unresolved merge conflict markers.

### Steps

1. Run `git diff --check` — exits non-zero if conflict markers exist
2. Run `grep -rn '^<<<<<<< \|^=======\|^>>>>>>> ' . --include='*.py' --include='*.js' --include='*.ts' --include='*.html' --include='*.css' --include='*.json' --include='*.yaml' --include='*.yml' --include='*.md' 2>/dev/null | head -20`

### Gate
- **Pass**: `MERGE_CLEAN` — no conflict markers found
- **Fail**: `MERGE_CONFLICTS_FOUND` — followed by list of affected files
- **On failure**: **Stop the pipeline immediately.** Do NOT attempt to resolve conflicts — report them so they can be resolved manually.

---

## Change Detection

Determine whether changes are code or documentation-only to enable conditional stage skipping.

### Steps

Run: `git diff --name-only origin/<target_branch>...HEAD 2>/dev/null || git diff --name-only HEAD~1 2>/dev/null`

- If ALL changed files match `*.md` → documentation only
- If any non-markdown files were changed → code changes
- If no changed files or branch cannot be determined → treat as code changes

### Gate
- Output exactly one of: `DOCS_ONLY` or `CODE_CHANGES`
- This verdict is used by downstream stages to conditionally skip (Test Execution, Self-Review, Security Check skip on DOCS_ONLY)

---

## Test Execution

Run the project test suite and report results. **Read-only — do NOT create or modify any source files.**

### Steps

1. Identify the test command from Configuration Gathering
2. Run the full test suite
3. Report: total tests run, pass/fail counts, any failing test details, coverage summary if available

### Constraints
- Do NOT create or modify any source files
- If tests fail due to missing modules or import errors, report them as failures — do NOT fix them

### Gate
- **Pass**: `TESTS_PASSED` — all tests pass
- **Fail**: `TESTS_FAILED` — any tests fail
- **On failure**: Retry once (go back and fix the failing code, then re-run tests). If retry fails, **stop the pipeline**.

---

## Security Check

Scan files changed by this task for security vulnerabilities. Pre-existing issues in unchanged files are reported as improvements, not failures.

### Steps

1. **Get changed files**: `git diff --name-only origin/<target_branch>...HEAD 2>/dev/null || git diff --name-only HEAD~1 2>/dev/null`
   — This is your **scope**. Only issues in these files can cause failure.

2. **Scan changed files** for these patterns:
   - `mark_safe` — Django XSS risk
   - `@csrf_exempt` — CSRF protection disabled
   - `|safe` — Django template XSS risk
   - Raw SQL queries (string interpolation in SQL)
   - Hardcoded secrets, API keys, passwords
   - `shell=True` — command injection risk

3. **Broad codebase scan** (for context): grep the full codebase for the same patterns. Hits in files NOT in your scope are pre-existing — report as `IMPROVEMENT:` lines, do NOT let them influence your verdict.

### Gate
- **Pass**: `SECURITY_PASSED` — no issues in changed files
- **Fail**: `SECURITY_FAILED` — followed by issues found **in changed files only**
- **On failure**: Retry once (fix the security issues, then re-scan). If retry fails, **stop the pipeline**.

For pre-existing issues in unchanged files, output each as:
```
IMPROVEMENT: Security: <brief description of issue and file>
```

**Important**: Use the Agent tool to run this as a subagent for independent evaluation with clean context.

---

## Documentation

Update documentation for the changes made.

### Steps

1. Update relevant docstrings, README sections, and inline comments as needed
2. Do not create unnecessary documentation files
3. Focus on what changed and why

### Gate
- **Pass**: `DOCS_UPDATED` — followed by a list of files modified and what changed
- If no documentation changes were needed: `DOCS_UPDATED` followed by "No changes needed."
- This gate always passes.

---

## Commit & PR

Create a branch, commit changes, push, and create a pull request.

### Steps

1. **Remote check**: Run `git remote -v`
   - If remote URL contains github.com, proceed normally
   - If no remote or local/file-based remote, output `PR_SKIPPED: no GitHub remote configured` and stop

2. **Checkout/create branch**: `git checkout <branch-name> 2>/dev/null || git checkout -b <branch-name>`

3. **Pull if exists**: `git pull --rebase origin <branch-name> 2>/dev/null || true`

4. **Stage tracked changes**: `git add -u`

5. **Check for conflict markers**: `git diff --check` — must be clean. If conflicts found, resolve them first.

6. **Stage new files explicitly** (do NOT stage .env, credentials, or secrets)

7. **Commit** with conventional commit format:
   - Features: `feat: <description>`
   - Bug fixes: `fix: <description>`
   - Refactors: `refactor: <description>`
   - Docs: `docs: <description>`

8. **Push**: `git push -u origin <branch-name>`

9. **Create PR**: `gh pr create --base <pr_target_branch> --title "<type>: <description>" --body '<summary>'`
   - If PR already exists: `echo 'PR already exists'`
   - If task is linked to a GitHub issue, include `Closes #<issue-number>` in the PR body

### Gate
- **Pass**: `PR_CREATED: <full PR URL>` or `PR_EXISTS: <full PR URL>` or `PR_SKIPPED: <reason>`
- **Fail**: Stop the pipeline if push or PR creation fails unexpectedly

---

## Code Review

Review the code changes in the current branch against the base branch.

### Steps

1. Run `git diff <pr_target_branch>...HEAD` to see all changes
2. Read changed files for full context where needed

Review for:
- **Correctness**: Logic errors, edge cases, off-by-one errors
- **Security**: Injection vulnerabilities, auth issues, secrets exposure
- **Style**: Consistency with project conventions, readability
- **Testing gaps**: New code paths without test coverage
- **Performance**: Obvious inefficiencies, N+1 queries
- **Architecture**: Design concerns, coupling, separation of concerns

For each finding, include: file and line number, severity (critical/warning/suggestion), description, suggested fix.

### Gate
- Output `REVIEW_COMPLETE` — this stage always passes (informational)

---

## Test Verification

Re-run the test suite after PR creation to catch integration issues.

### Steps
Same as Test Execution — run the full test suite, report results.

### Gate
- **Pass**: `TESTS_PASSED`
- **Fail**: `TESTS_FAILED`
- **On failure**: Retry once. If retry fails, stop the pipeline.

---

## Review Verdict

Synthesize all findings from Code Review and Test Verification into a final verdict.

### Output Structure

```
## Summary
One-paragraph summary of the PR quality.

## Verdict
APPROVE / REQUEST_CHANGES / COMMENT

## Critical Issues
(list any blocking issues, empty if APPROVE)

## Suggestions
(non-blocking improvements)

## Test Results
(summary of test pass/fail status)
```

Output exactly one of: `APPROVE`, `REQUEST_CHANGES`, or `COMMENT` on its own line as the final verdict.

---

## Merge PR

Approve and merge the pull request.

### Steps

1. Approve: `gh pr review <pr-number> --approve --body 'Auto-approved: tests pass, review complete.'`
2. Merge: `gh pr merge <pr-number> --squash --delete-branch`

### Gate
- **Pass**: `PR_MERGED`
- **Fail**: `MERGE_FAILED` — followed by error details
- **On failure**: Retry once. If retry fails, stop the pipeline.

---

## Retrospective

Review the pipeline execution and provide feedback for continuous improvement.

### Steps

1. Rate the execution quality (1-5)
2. What went well?
3. What could improve? (prompt quality, stage ordering, quality gates)
4. Suggest follow-up tasks if needed
5. Output improvement ideas as `IDEA:` lines — one per line:
   ```
   IDEA: Add retry backoff to reduce flaky test failures
   IDEA: Split large prompts into focused sub-prompts
   ```
6. If you created useful scripts or tools, output as:
   ```
   TOOL: name | language | one-line description
   ```

Be concise. Focus on actionable improvements.

**Important**: Use the Agent tool to run this as a subagent for independent evaluation with clean context.

---

## Edge Case Checklist

Before marking implementation complete, verify handling of:
- Null/None/empty values in all inputs
- Circular references (if working with recursive data structures)
- Boundary conditions (empty collections, single items)
- Concurrent access (if modifying shared state)

Note any edge cases found and how you handled them.

---

## Clean Git State

Before finishing implementation, you MUST:
1. Resolve any merge conflict markers (`git diff --check` — must return clean)
2. Stage all changes: `git add -u`
3. Stage any new files explicitly: `git add <new_file>`
4. Verify: `git status` must show no untracked/unstaged changes relevant to the task

The Commit & PR stage expects a clean, fully-staged working tree.
