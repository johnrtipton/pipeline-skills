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

**CRITICAL: You MUST execute ALL stages in the pipeline, from first to last. Do NOT stop after Commit & PR. The Code Review, Test Verification, Review Verdict, Merge PR, and Retrospective stages are mandatory — they are not optional follow-ups. After creating a PR, immediately continue to Code Review.**

---

## Step 0: Initialize State File (FIRST THING)

**This is the very first action in any pipeline — before Environment Check, before anything else.**

1. `mkdir -p .pipeline-state`
2. Copy the appropriate template from the pipeline-skill repo's `templates/` directory:
   - Feature: `templates/feature-state.json`
   - Bugfix: `templates/bugfix-state.json`
   - Refactor: `templates/refactor-state.json`
3. Fill in: `task_description`, `branch_name`, `pr_target_branch`, `project_path`, `started_at` (ISO 8601)
4. Write to `.pipeline-state/<branch-name>.json`
5. Ensure `.pipeline-state/` is in `.gitignore`

**If a state file already exists** for this branch, this is a resume — read it, find the first stage that isn't `passed`, and skip to that stage.

This must happen first so that if the pipeline is interrupted at ANY point — even during stage 1 — the state file exists and resume is possible.

---

## Pipeline State File (Resume Support)

Pipelines write progress to `.pipeline-state/<branch-name>.json` in the project root. This enables resuming after interruptions (context limit, crash, user stop).

### State File Format

```json
{
  "pipeline_type": "feature",
  "task_description": "Add health check endpoint",
  "branch_name": "feat/add-health-check",
  "pr_target_branch": "main",
  "project_path": "/path/to/project",
  "started_at": "2026-03-18T14:30:00Z",
  "current_stage": 6,
  "stages": {
    "1": {"name": "Environment Check", "status": "passed", "verdict": "ENV_OK"},
    "2": {"name": "Change Detection", "status": "passed", "verdict": "CODE_CHANGES"},
    "3": {"name": "Conflict Check", "status": "passed", "verdict": "MERGE_CLEAN"},
    "4": {"name": "Planning", "status": "passed"},
    "5": {"name": "Implementation", "status": "passed"},
    "6": {"name": "Test Execution", "status": "running"}
  },
  "pr_number": null,
  "pr_url": null,
  "rewind_count": 0
}
```

### Initializing State

At pipeline start, copy the appropriate template from the pipeline-skill repo's `templates/` directory:
- `templates/feature-state.json` for feature pipelines
- `templates/bugfix-state.json` for bugfix pipelines
- `templates/refactor-state.json` for refactor pipelines

Fill in: `task_description`, `branch_name`, `pr_target_branch`, `project_path`, `started_at`.

Each stage has a `checklist` array of objects:
```json
{"action": "post review to GitHub: gh pr review --comment", "done": false, "mandatory": true}
```

- `action` — what to do
- `done` — set to `true` when completed
- `mandatory` — if `true`, this action must not be skipped (GitHub posting, verdicts, log persistence)

Stages with `"run_as": "subagent"` run as Agent tool subagents with fresh context.
Stages with `"skip_if": "DOCS_ONLY"` are skipped when Change Detection returned DOCS_ONLY.

```bash
mkdir -p .pipeline-state
# Copy template and fill in task details
```

### Writing State

After each stage completes (pass or fail), update the state file:

1. Set each checklist item's `done` to `true` as you complete it
2. Set the stage's `status` to `passed` or `failed`
3. Record the `verdict` string
4. Increment `current_stage` to the next stage
5. Save any extracted data (PR number, PR URL)

**Before marking a stage as passed, verify all `mandatory` checklist items have `done: true`.** If a mandatory item was skipped, go back and do it before proceeding.

### Reading State (Resume)

At pipeline start, before Stage 1:
1. Check for `.pipeline-state/<branch-name>.json`
2. If found, read it and determine the last completed stage
3. Skip all completed stages — jump directly to the first incomplete stage
4. Print a resume summary:
   ```
   Resuming pipeline from Stage 6 (Test Execution)
   Stages 1-5 completed previously. Branch: feat/add-health-check
   ```
5. If the branch already exists with commits, `git checkout <branch>` instead of creating fresh

### Resume Rules

- **Passed stages**: Skip entirely — their work is already done
- **Failed stages**: Re-run from the failed stage (not from the beginning)
- **Running stages**: Treat as not started — re-run them
- **Rewind state**: If `rewind_count > 0`, resume at the rewind target stage
- **PR already created**: Skip Commit & PR, jump to Code Review

### Cleanup

When the pipeline completes (all stages passed) or is abandoned:
```bash
rm .pipeline-state/<branch-name>.json
```

Add `.pipeline-state/` to `.gitignore` — state files should not be committed.

---

## Stage Loop — The State File Drives the Pipeline

**The state file is the program counter.** Do not try to remember all stages from the skill text — the skill text WILL be compressed out of context during long runs. Instead, follow this loop:

### The Loop (repeat until all stages are done):

```
1. READ the state file: .pipeline-state/<branch-name>.json
2. FIND the next stage where status != "passed"
3. READ that stage's checklist items — these are your instructions
4. EXECUTE each checklist item, marking done: true as you go
5. For items marked mandatory: true — you MUST complete these
6. WRITE the verdict and update the state file
7. GO TO step 1
```

### Before each stage:

1. **Read the state file**. If it doesn't exist, create it from the template NOW.
2. Find the current stage (first non-`passed` stage).
3. Read its `checklist` array — these are the specific actions for this stage.
4. If the stage has `"run_as": "subagent"`, spawn it as a subagent via the Agent tool.
5. If the stage has `"skip_if": "DOCS_ONLY"` and Change Detection returned DOCS_ONLY, mark it passed and go to next.

### After each stage:

1. Mark each checklist item's `done` field.
2. **Verify all `mandatory` items are `done: true`** — if any mandatory item is not done, go back and do it before proceeding.
3. Set the stage's `status` to `passed` or `failed`, record the `verdict`.
4. Write the updated state file to disk.
5. Continue the loop.

### Gate rules:

- **Explicit FAILED overrides PASSED**: If output contains both `TESTS_PASSED` and `TESTS_FAILED`, the result is **FAILED**.
- **Retry**: On first failure, retry once. If second attempt fails, follow the stage's failure action (stop or rewind).
- **Rewind**: Carry failure details as context. Re-plan/re-diagnose. Maximum 1 rewind per pipeline run.

### Why this works:

The state file is re-read from disk at each stage boundary. Even if the skill text is fully compressed out of context, the state file on disk still has every stage and every checklist item. The agent just needs to follow the loop: read → find next → execute checklist → write → repeat.

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

6. **Gitignore audit**: Check if `.gitignore` contains rules that would block adding new source files (e.g., a rule like `components/` that matches `src/*/components/`). If found, note it so the Implementation stage can use `git add -f` for blocked paths. Common gotcha: overly broad directory rules that match nested source directories.

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
   - `mark_safe` — must use `escape()` or `format_html()` for interpolated values
   - `mark_safe` inside `<script>` blocks — HTML escaping (`conditional_escape`) is **insufficient** in JS context. User-controlled values interpolated inside `<script>` tags need allowlist validation (regex like `^[a-zA-Z0-9_-]+$`) or `json.dumps()`, not HTML entity escaping
   - `@csrf_exempt` — CSRF protection disabled without justification
   - `|safe` — template filter on user-controlled variables bypasses auto-escaping
   - Raw SQL queries (string interpolation in SQL)
   - Hardcoded secrets, API keys, passwords
   - `shell=True` — command injection risk
   - String concatenation in JS contexts — must use `json.dumps()` for JS string escaping
   - Unescaped user input in template tags
   - `eval()` or `exec()` with user-controlled input — even with restricted builtins

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

Ensure all user-facing and developer documentation is complete, accurate, and well-structured for the changes made.

### Steps

#### 1. Discover the project's docs structure

Look for a documentation directory — common locations:
- `docs/` with a `README.md` index (the djust pattern — organized by topic with guides/, components/, etc.)
- `docs/` with mkdocs/sphinx config
- Top-level `README.md` only

Read the docs index (e.g., `docs/README.md`) to understand how documentation is organized. This tells you where new docs should go and what existing docs need updating.

#### 2. Code-level documentation

- **Docstrings**: Add or update docstrings for all new/modified public classes, methods, and functions
- **Type annotations**: Ensure public APIs have type hints (they serve as documentation)
- **Inline comments**: Add comments only where logic isn't self-evident

#### 3. User-facing documentation

For new features or significant changes, determine what documentation users need:

**Guide or reference page** — Does this feature need its own doc?
- New user-facing feature (attribute, decorator, mixin, command) → YES, create a guide
- Place it in the appropriate docs subdirectory (e.g., `docs/guides/` for how-to guides)
- Follow the existing docs style and structure (check 2-3 nearby docs for conventions)
- Include: what it does, when to use it, API/usage, example code, common patterns

**Existing docs update** — Does this change affect an existing doc?
- Search docs for references to the feature area you changed
- Update any outdated examples, API references, or descriptions
- If a guide covers the area you modified, update it to reflect the new behavior

**Docs index** — If you created a new doc page, add it to the docs index/README under the appropriate section with a one-line description.

#### 4. Component gallery / discovery

If the project has a component gallery or auto-discovery system:
- Add gallery examples for any new template tags or components
- Update discovery tests if they hardcode expected component lists
- Verify the gallery renders new components correctly (if a `--dry-run` flag exists, use it)

#### 5. CHANGELOG

For `feat:` and `fix:` changes:
- Update `CHANGELOG.md` (if the project has one)
- Add an entry under the current/unreleased version section
- Follow the existing format (typically: `- **Feature name** — description (#issue)`)

#### 6. CLAUDE.md / project config

If the change introduces:
- New conventions, patterns, or architectural decisions
- New commands, make targets, or scripts
- New project structure (directories, key files)

Suggest updating `CLAUDE.md` to reflect these (note in your output, don't modify CLAUDE.md directly unless the pipeline is for that project).

#### 7. Quality checks

- No orphaned docs — if you renamed/removed a feature, remove or redirect its docs
- No broken internal links — verify `[link text](path)` references are valid
- Examples compile/run — code examples should be accurate and tested
- Consistent terminology — use the same names the code uses

### Gate
- **Pass**: `DOCS_UPDATED` — followed by a categorized list:
  ```
  DOCS_UPDATED
  Code docs:
  - path/to/file.py: added docstring for FeatureClass
  User docs:
  - docs/guides/new-feature.md: created guide for dj-value-* attribute
  - docs/README.md: added link under Real-Time Features section
  CHANGELOG:
  - CHANGELOG.md: added entry for feat: dj-value-* static event params
  ```
- If no documentation changes were needed: `DOCS_UPDATED` followed by "No changes needed — documentation is current."
- This gate always passes, but incomplete documentation should be flagged for the Code Review stage to catch.

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

10. **Verify PR body**: Re-read the PR description against `git diff <pr_target_branch>...HEAD --stat`. The PR body must not mention features, template tags, error codes, or APIs that don't exist in the diff. Must not cite incorrect test counts or file counts, or use terminology that contradicts the code. If discrepancies are found, fix with `gh pr edit <pr_number> --body '<corrected body>'`.

### Gate
- **Pass**: `PR_CREATED: <full PR URL>` or `PR_EXISTS: <full PR URL>` or `PR_SKIPPED: <reason>`
- **Fail**: Stop the pipeline if push or PR creation fails unexpectedly

---

## Code Review

Review the code changes in the current branch against the base branch.

**IMPORTANT: This stage is mandatory. Do not skip it or stop the pipeline before reaching it.**

### Steps

1. Run `git diff <pr_target_branch>...HEAD` to see all changes
2. Read changed files for full context where needed
3. **Check for a project PR checklist**: Look for `docs/PULL_REQUEST_CHECKLIST.md`, `PULL_REQUEST_CHECKLIST.md`, or `.github/PULL_REQUEST_TEMPLATE.md` in the project root. If found, use it as the primary review framework.

### Review Categories

**Correctness**:
- Logic errors, edge cases, off-by-one errors
- Test-implementation alignment: tests actually import and exercise code in the diff
- Import names match shipped code (no phantom modules or renamed APIs)
- No placeholder/stub implementations (`return True`, hardcoded fake data, simulated APIs)
- No comments indicating incomplete code ("simulate", "would be implemented", "for now")

**Testing**:
- New features have tests; bug fixes have regression tests
- New JS feature files have corresponding test files
- Tests are deterministic (no flaky tests)
- All untracked files that tests depend on are included in the diff
- Edge cases covered (error conditions, boundary cases)

**Security**:
- No `mark_safe()` with unescaped interpolated values — must use `escape()` or `format_html()`
- No `|safe` template filter on user-controlled variables
- No `@csrf_exempt` without documented justification
- `json.dumps()` for values embedded in JavaScript strings (not HTML `escape()`)
- No XSS, SQL injection, CSRF bypass, or secrets exposure
- Template tags escape user input

**Code Quality**:
- No `print()` statements — use the project's logging system
- No f-string formatting in logger calls — use `%s` style
- No `console.log` in production JS without debug guards
- No silent exception handling (`except: pass`)
- Exception chaining (`raise X from e`)
- Appropriate log levels (error/warning/info/debug)
- `exc_info=True` for exception logging

**Documentation**:
- CHANGELOG.md updated for `feat:` and `fix:` PRs
- Public APIs documented with docstrings
- No internal tracking documents committed to repo
- Breaking changes documented with migration path

**Performance**:
- No N+1 queries or unnecessary database hits
- No memory leaks or excessive allocations
- Caching for expensive operations where appropriate
- VDOM/rendering impact considered (if applicable)

**Architecture**:
- Follows project patterns and conventions
- Single responsibility — focused functions and classes
- No code duplication — shared logic properly abstracted
- `reinitAfterDOMUpdate()` after DOM replacement (if applicable)

### Auto-Reject Triggers

Flag as critical if any of these are found:
- `print()` instead of logging
- f-string in logger calls
- Unguarded `console.log` in production JS
- Silent exception handling (`except: pass`)
- No tests for new functionality
- Tests reference modules/APIs that don't exist in the diff
- `mark_safe()` with unescaped interpolation
- `|safe` on user-controlled variables
- Placeholder/stub code shipped as production
- Missing CHANGELOG.md update for feat/fix PRs

For each finding, include: file and line number, severity (critical/warning/suggestion), description, suggested fix.

### Post Review to GitHub PR

If a PR number is available, post the review as a GitHub PR review:

**For inline comments on specific files/lines**, use:
```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  --method POST \
  -f body='## Automated Code Review\n\n<summary>' \
  -f event='COMMENT' \
  -f 'comments[][path]=<file>' \
  -f 'comments[][line]=<line>' \
  -f 'comments[][body]=<finding>'
```

**For a general review comment** (simpler, always works):
```bash
gh pr review <pr_number> --comment --body "$(cat <<'REVIEW'
## Automated Code Review

### Summary
<one paragraph summary>

### Findings
<categorized findings with file:line references>

### Checklist
- [x] Tests pass
- [x] No auto-reject triggers
- [ ] CHANGELOG updated (if applicable)
...

### Verdict
APPROVE / REQUEST_CHANGES / COMMENT
REVIEW
)"
```

**Choose the approach based on findings:**
- If you have specific line-level findings → use the inline comments API for the most useful ones, plus a summary review
- If findings are general → use the simple review comment
- Always include a checklist summary showing what was checked

### Save Review Locally

Also save the review to `pr/feedback/pr-<number>-<short-description>.md` if the project has a `pr/feedback/` directory (per the djust PR checklist convention).

### Gate
- Output `REVIEW_COMPLETE` — this stage always passes (informational)
- Critical findings will be evaluated in the Review Verdict stage

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

**IMPORTANT: This stage is mandatory. Do not skip it.**

### Decision Logic

- If any **auto-reject triggers** were found in Code Review → `REQUEST_CHANGES`
- If tests failed in Test Verification → `REQUEST_CHANGES`
- If only non-blocking suggestions → `APPROVE` or `COMMENT`
- If `REQUEST_CHANGES`: go back and fix the critical issues before proceeding to Merge

### Output Structure

```
## Summary
One-paragraph summary of the PR quality.

## Checklist Compliance
(list auto-reject items checked and their pass/fail status)

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

### Post Verdict to GitHub PR

Submit the verdict as a GitHub PR comment:
- If `APPROVE`: `gh pr comment <pr_number> --body '## ✅ Review Verdict: APPROVED\n\n<verdict summary>'`
- If `REQUEST_CHANGES`: `gh pr review <pr_number> --request-changes --body '<verdict with critical issues>'`
- If `COMMENT`: `gh pr comment <pr_number> --body '## Review Verdict: COMMENT\n\n<verdict with suggestions>'`

Note: Do NOT use `gh pr review --approve` — GitHub blocks self-approval on PRs you authored. Use `gh pr comment` for approvals instead.

If `REQUEST_CHANGES`: fix the issues, then re-evaluate. Only proceed to Merge PR when verdict is `APPROVE`.

---

## Merge PR

Approve and merge the pull request.

### Steps

0. **Verify CI**: Run `gh pr checks <pr_number>`. All checks must pass before merging.
   - If CI is failing due to changes in this PR, do NOT merge — go back and fix the issue.
   - If CI is failing due to pre-existing issues (not introduced by this PR), document it in a PR comment (`gh pr comment <pr_number> --body 'CI note: <description of pre-existing failure>'`) and proceed.

1. Merge: `gh pr merge <pr-number> --squash --delete-branch`
   - Note: Do NOT run `gh pr review --approve` — GitHub blocks self-approval on PRs you authored. The review comment from the Code Review stage serves as the review record.

### Gate
- **Pass**: `PR_MERGED`
- **Fail**: `MERGE_FAILED` — followed by error details
- **On failure**: Retry once. If retry fails, stop the pipeline.

---

## Retrospective

Review the pipeline execution and provide feedback for continuous improvement.

### Steps

1. Get PR details: `gh pr view <pr_number> --json commits,title,body,mergedAt` (the branch may have been deleted by squash merge — do NOT rely on `git log <target>..HEAD`)
2. Rate the execution quality (1-5)
3. What went well?
4. What could improve? (prompt quality, stage ordering, quality gates)
5. Lessons learned — insights about the codebase, architecture, or process
6. Suggest follow-up tasks if needed
7. Output improvement ideas as `IDEA:` lines — one per line:
   ```
   IDEA: Add retry backoff to reduce flaky test failures
   IDEA: Split large prompts into focused sub-prompts
   ```
8. If you created useful scripts or tools, output as:
   ```
   TOOL: name | language | one-line description
   ```

Be concise. Focus on actionable improvements.

**Important**: Use the Agent tool to run this as a subagent for independent evaluation with clean context.

### Persist Retrospective Output

Retrospective insights are valuable across pipeline runs. Save them to three places:

#### 1. Pipeline Log (per-task record)

Append to `.pipeline-log.md` in the project root:

```markdown
## <branch-name> — <date>
**Task**: <task description>
**PR**: #<number> — <status>
**Quality**: <rating>/5
**Duration**: <stages completed> stages

### What Went Well
- <bullet points>

### Lessons Learned
- <bullet points>

### Pipeline Improvements
- <IDEA: lines>

### Follow-up Tasks
- <if any>

---
```

This creates a running history of all pipeline executions on the project. Add `.pipeline-log.md` to `.gitignore`.

#### 2. GitHub PR Comment

Post a retrospective summary as a comment on the PR (even if already merged):
```bash
gh pr comment <pr_number> --body "$(cat <<'RETRO'
## Pipeline Retrospective

**Quality**: <rating>/5

**What went well**: <summary>

**Lessons learned**: <summary>

**Suggested improvements**: <IDEA lines>
RETRO
)"
```

This keeps the retrospective attached to the PR for future reference.

#### 3. Project Memory (if orchestrator is available)

If the project uses djust-orchestrator memory, write key lessons:
```bash
python manage.py memory_write --level project --project <project> --append '<lesson>'
```

If not, check if the project has a `docs/LESSONS_LEARNED.md` or similar file and append there. If neither exists, the pipeline log and PR comment are sufficient — do not create new documentation files.

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
