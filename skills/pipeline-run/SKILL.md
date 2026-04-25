---
name: pipeline-run
description: >
  Execute pipeline stages by reading the state file and spawning agents.
  Reads .pipeline-state/<branch>.json, finds the next pending stage,
  spawns an agent to execute it, updates the state file, and repeats.
  Run /pipeline-next first to create the state file.
---

# Pipeline Run — Execute Stages from State File

This skill is a tiny loop. The state file is the program. You are the executor.

**Usage**:
- `/pipeline-run` — resume most recent incomplete pipeline
- `/pipeline-run fix-event-sequencing-560` — run a specific pipeline by branch name
- `/pipeline-run --milestone v0.4.0` — pick next task from ROADMAP and run it
- `/pipeline-run --milestone v0.4.0 --priority P1` — pick next P1 task and run it
- `/pipeline-run --milestone v0.4.0 --all` — **process ALL remaining tasks** in the milestone sequentially
- `/pipeline-run --milestone v0.4.0 --priority P1 --all` — process all remaining P1 tasks
- `/pipeline-run --all-milestones` — **process ALL milestones** from ROADMAP.md in order
- `/pipeline-run --all-milestones --priority P0` — process all milestones, but only P0 tasks in each
- `/pipeline-run --all-milestones --group` — process all milestones, grouping related tasks into batch PRs
- `/pipeline-run --milestone v1.4 --all --group` — process all v1.4 tasks, grouped where it makes sense

## Before the Loop

If `--all-milestones` was specified, jump to the **All Milestones Loop** section below.

If no incomplete state file exists (no `.pipeline-state/*.json` with `completed_at` = null):
1. If `--milestone` or `--priority` or `--feature` was specified, run the **pipeline-next** skill to pick a task and create the state file.
2. If no flags specified, tell the user: "No incomplete pipeline found. Run `/pipeline-run --milestone v0.4.0` to pick a task from the roadmap."

**State file templates** — check for project-local templates first, then fall back to the pipeline skill's templates:

1. **Project-local** (preferred): `.pipeline-templates/feature-state.json` (or `bugfix-state.json`, `refactor-state.json`) in the project root. Projects customize these to add stages, subagent prompts, and project-specific checklists.
2. **Skill default** (fallback): `templates/` directory in the pipeline skill's directory (locate via `PIPELINE_SKILL_DIR` env var or the directory containing `pipeline.py`).

If a project-local template exists, **always use it** — it overrides the default.

## Autonomous Execution

When `--all`, `--all-milestones`, or `--group` is specified, the pipeline runs **fully autonomously**. Do NOT pause to ask the user if they want to continue between tasks or groups. The flag itself is the user's confirmation. Only stop on failure.

## Stage 1: Branch and Environment Setup

The Environment Check stage needs care when local `main` is ahead of `origin/main`:

1. **Check for unpushed commits**: `git log origin/main..main --oneline`. If there are any, push main first (`git push origin main`) before creating the feature branch. Otherwise the branch will be based on stale code.
2. **Create the branch**: `git checkout -B {branch_name} origin/main` (now that origin/main is current).
3. **Install dependencies**: Always re-run `uv pip install -r requirements.txt` (or the project's equivalent) after branching. The branch may have different dependency versions than what's currently installed in `.venv`.

## Parallel Stages

Stages named "Test Execution", "Self-Review", and "Security Check" are independent read-only stages. **Run them in parallel** by spawning 3 agents simultaneously. This cuts wall-clock time significantly. Wait for all 3 to complete before proceeding to the next stage.

To identify parallel stages: scan the state file for stages with these exact names (regardless of stage number). Do NOT hardcode stage numbers — projects may have different stage counts.

### When parallel stages fail

If multiple parallel stages fail (e.g., both Self-Review and Security Check find issues), **combine all findings into a single fix pass**:

1. Collect findings from ALL failed parallel stages
2. Spawn ONE fixer agent with the combined finding list
3. After fixes, mark all failed parallel stages as `passed` (with `_AFTER_FIXES` suffix on verdict)
4. Do NOT re-run each failed stage individually — that wastes time. The Code Review stage (Stage 11) will catch anything the fix missed.

## Conditional Stages

Stages with a `"_note"` field containing "SKIP if" should be evaluated:
- If the skip condition is met (e.g., no findings from review), mark the stage as `skipped` with a note
- The stage's checklist may include a "skip" action as the first item — check it before proceeding

### Stages that MUST NEVER be skipped

Regardless of conditions, time pressure, or the pipeline executor's own
reasoning, these stages are **load-bearing quality gates** and cannot be
skipped under any circumstances:

- **Stage 11 — Code Review** — catches defects implementation misses. Observed
  case: PR #91 had Stage 11 skipped to save time; when run manually after
  the fact it found a race condition (`select_for_update` missing), unhandled
  DocuSign exceptions, and zero test coverage for a new mutation handler.
- **Stage 13 — Re-Review** — verifies that findings from Stage 11 were
  actually addressed, not just claimed addressed. May be marked `skipped`
  ONLY when Stage 11 produced zero 🔴 and zero 🟡 findings (the `skip_if`
  condition in the template). Never skipped "to save time" when findings exist.
- **Stage 15 — Retrospective** — milestone learning lives here. Skipping it
  is how lessons get lost between milestones.

If the executor finds itself reasoning "I'll skip Stage 11/13/15 because the
change is small / I already reviewed it / we're in a hurry" — STOP. That
reasoning is the failure mode. Run the stage.

## Gate Check (Integrity Audit)

Before spawning any stage agent, verify that all prior stages completed properly.
This prevents skipping stages (accidentally or deliberately) and catches backfilled
state files where `status: passed` was set without actually running the stage.

**Run this check every iteration**, between Step 2 (find next stage) and Step 3 (spawn agent):

```
for each prior_stage (1 to current_stage - 1):
    if prior_stage.status not in ("passed", "skipped"):
        STOP — "Stage {N} ({name}) was not completed. Run it before proceeding."
    
    if prior_stage.status == "passed" and prior_stage.verdict is None:
        STOP — "Stage {N} has status=passed but no verdict. 
               This looks backfilled. Re-run the stage properly."
```

**Artifact verification** for critical stages (check AFTER the stage is marked passed):

| Stage name | Required artifact |
|-----------|-------------------|
| Commit & PR | `pr_number` and `pr_url` set in state file |
| Code Review | PR has a review comment (check `gh pr view $PR --json comments`) |
| Retrospective | PR has a retro comment (check `gh pr view $PR --json comments`) |
| Merge PR | PR state is `MERGED` (check `gh pr view $PR --json state`) |

If artifact verification fails: mark the stage back to `pending` and re-run it.

**Close-without-code path**: If investigation reveals the issue doesn't need a code
change (already fixed, by-design, config issue), the pipeline supports a short-circuit:

1. Set `pipeline_type` to `"investigation"` in the state file
2. Skip stages: Implementation, Test Execution, Self-Review, Security Check, Commit & PR, Merge PR
3. Required stages: Environment Check, Planning (investigation), Documentation (close issue with comment), Retrospective
4. The "Documentation" stage should close the GitHub issue with a detailed explanation

## Pre-Commit Checklist

Before running `git commit` in the Implementation or Commit & PR stage, always run
the project's linters and formatters **against the exact staged files**, not the
whole tree:

```bash
# 1. Stage the files you intend to commit FIRST.
git add <file1> <file2> ...

# 2. Run formatters + linters scoped to staged files only.
STAGED=$(git diff --cached --name-only --diff-filter=ACMR)

# Rust — only if any staged .rs files:
if echo "$STAGED" | grep -q '\.rs$'; then cargo fmt; fi

# Python — scope to staged .py files:
PY=$(echo "$STAGED" | grep '\.py$' || true)
if [ -n "$PY" ]; then ruff check $PY --fix && ruff format $PY; fi

# JS — scope to staged .js files (not the whole tree; pre-existing
# issues in unrelated files will fail the hook otherwise):
JS=$(echo "$STAGED" | grep '\.js$' || true)
if [ -n "$JS" ]; then npx eslint --fix $JS; fi

# 3. Re-stage any files the formatters touched, then commit.
git add <changed-files>
git commit -m "..."
```

**Why scope to staged files?** Observed in djust PR #814 (v0.5.0): running
`ruff check .` / `eslint` across the whole tree tripped the pre-commit hook on
**pre-existing errors in unrelated files**, which then looped with the hook's
stash-restore cycle — six commit attempts to land one PR. Scoping eliminates this.

This prevents the common pattern of 3-5 failed commit attempts due to formatting hooks.

## MANDATORY Post-Commit Verification (Action #122)

**After every `git commit`, run this verification:**

```bash
# Verify the commit actually registered. Pre-commit hooks that stash
# the working tree, run a formatter, and restore can silently SWALLOW
# the commit when the formatter touches files — `git commit` exits 0
# but no new commit is created. Without this check, the bug is invisible
# until you push and `git push` reports "nothing to push" — by which
# time you've already moved on.
LATEST=$(git log -1 --format='%H %s' 2>/dev/null)
if ! grep -qF "<expected commit subject>" <<< "$LATEST"; then
    echo "FAIL: commit did not register. Latest is: $LATEST"
    echo "Re-stage and retry — pre-commit hook likely bounced."
    git add <files-again>
    git commit -m "<message>"
    LATEST=$(git log -1 --format='%H %s')
fi
echo "OK: commit registered as $LATEST"
```

Or more concisely as a one-liner after each `git commit`:

```bash
git commit -m "..." && git log -1 --oneline
```

The `&& git log -1 --oneline` is the load-bearing detail — if the commit
silently failed, you see `<previous-commit-subject>` and know to re-stage.
If it registered correctly, you see `<new-commit-hash> <new-subject>`.

**Why this is mandatory**: observed **8 occurrences in a single 24-hour
session** (djust PRs #989, #996, #1007, #1008, #1014, #1015, #1021, #1024).
Pattern: ruff or another pre-commit hook stashes the working tree, reformats
a file, and on stash-pop creates a conflict that rolls back the commit. The
hook output ends with `[INFO] Restored changes from /Users/tip/.cache/pre-commit/patch...`
but no `[<branch> <hash>] <commit message>` line — that's the signal the
commit didn't register.

**Failure mode without this check**: agent moves on assuming the commit
landed, then `git push` reports "Everything up-to-date" and the agent has to
backtrack to figure out what happened — typically losing 5-10 minutes per
occurrence. Across 8 occurrences in a session, that's a meaningful chunk
of time lost to a check that takes 50 ms to run.

**When to skip the check**: never. The `&& git log -1 --oneline` form has
zero overhead on success and immediate signal on failure. Make it a reflex
chained onto every `git commit` invocation.

## Duplicate PR Prevention

Before creating a PR in the Commit & PR stage, check if one already exists:

```bash
gh pr list --head $BRANCH_NAME --state open --json number,url
```

If a PR already exists, use it (set `pr_number` and `pr_url` from the existing PR)
instead of creating a duplicate.

## State-File Gate (the #840 prevention)

**Before ANY of these actions**, the executor MUST verify a state file exists
for the current branch:

- `git checkout -B <feature-branch>` (branch creation)
- `git commit` on a feature branch (the first commit of the pipeline's work)
- `gh pr create` (PR opening)

Check:

```bash
STATE_FILE=$(ls .pipeline-state/*.json 2>/dev/null | xargs grep -l "\"branch_name\": \"$(git branch --show-current)\"" 2>/dev/null | head -1)
if [ -z "$STATE_FILE" ]; then
    echo "ERROR: no pipeline state file for branch $(git branch --show-current)."
    echo "Run /pipeline-next first to create one, or /pipeline-ship if starting"
    echo "from an existing working-tree."
    exit 1
fi
```

If no state file is found, **the executor must STOP** and run pipeline-next
first. Do not proceed with `gh pr create` — the retroactive Stage 11 that the
user will inevitably ask for after merge is more expensive than running
pipeline-next upfront.

**Why this gate exists**: PR #840 in djust (v0.5.1 form-polish batch) was
shipped without a state file. A retroactive Stage 11 review surfaced 2
must-fix defects (IME composition bug, push-event namespace inconsistency)
that would have reached production. Root cause was a missing mechanical
gate; awareness of the Stage 7-vs-11 delta was not sufficient — it had
already been documented in the v0.5.0 milestone retro and in PR #837's
retro, and #840 fell into the trap anyway.

## The Loop

Repeat these steps until all stages are done:

```
1. READ the state file from .pipeline-state/
2. FIND the next stage where status != "passed" and status != "skipped"
2b. RUN GATE CHECK on all prior stages (see above)
3. SPAWN an agent to execute that stage
4. COLLECT the agent's output and extract the verdict
5. UPDATE the state file (checklist items, verdict, status)
6. GO TO step 1
```

### Step 1: Read the state file

```bash
cat .pipeline-state/<branch-name>.json
```

If no branch name specified, find the most recent incomplete state file:
```bash
ls -t .pipeline-state/*.json
```
Read each, pick the first where `completed_at` is null.

If NO state file exists, tell the user to run `/pipeline-next` first.

### Step 2: Find next stage

Look through `stages` in order (by key as integer). Find the first where `status` is `pending` or `failed`.

If the stage has `"skip_if": "DOCS_ONLY"` and a previous stage's verdict was `DOCS_ONLY`, mark it `skipped` and continue to the next.

If all stages are `passed` or `skipped`, the pipeline is complete — set `completed_at` and print the summary.

### Step 3: Spawn an agent

Use the **Agent tool** with this pattern:

**If the stage has a `subagent_prompt` field**, use it directly (fill in `{pr_number}`, `{project_path}`, `{pr_target_branch}`, `{task_description}` from the state file's top-level fields).

**If no `subagent_prompt`**, build the prompt from the checklist:

```
Stage <N>: <stage name>
Project: <project_path>
Branch: <branch_name>
Task: <task_description>
PR target: <pr_target_branch>
PR: #<pr_number> (if set)

Complete each action:
- [ ] <checklist item 1>
- [ ] <checklist item 2> [MANDATORY]
...

Previous stage results:
- Stage 1 (Environment Check): ENV_OK
- Stage 2 (Conflict Check): MERGE_CLEAN
...
```

### Step 4: Collect and extract verdict

From the agent's output, look for verdict strings:
- ENV_OK, ENV_FAILED
- MERGE_CLEAN, MERGE_CONFLICTS_FOUND
- CODE_CHANGES, DOCS_ONLY
- TESTS_PASSED, TESTS_FAILED
- REVIEW_PASSED, REVIEW_FAILED
- REGRESSION_PASSED, REGRESSION_FAILED
- SECURITY_PASSED, SECURITY_FAILED
- DOCS_UPDATED
- PR_CREATED: <url>, PR_EXISTS: <url>, PR_SKIPPED: <reason>
- APPROVE, REQUEST_CHANGES, COMMENT
- PR_MERGED, MERGE_FAILED
- RETRO_COMPLETE

**FAILED always overrides PASSED** if both appear.

Extract PR number/URL from `PR_CREATED:` or `PR_EXISTS:` lines.

### Step 5: Update the state file

```python
# Mark checklist items done
for item in stage["checklist"]:
    item["done"] = True

# Check mandatory items were actually done
# (Look for evidence in agent output — e.g., "gh pr review" for mandatory GitHub posting)

# Set status and verdict
stage["status"] = "passed"  # or "failed"
stage["verdict"] = "<extracted verdict>"

# Update top-level fields
state["current_stage"] = next_stage_number
state["pr_number"] = extracted_pr_number  # if found
state["pr_url"] = extracted_pr_url  # if found

# Track review findings (if the state file has a review_findings field)
# After Code Review stage: extract 🔴/🟡 findings from agent output and store them
# After Address Findings stage: verify each finding was addressed
# After Re-Review stage: set review_findings.all_addressed = true/false
if "review_findings" in state and stage["name"] == "Code Review":
    # Parse findings from agent output and store for tracking
    pass  # Implementation reads from pr/feedback/ file
```

Write the updated JSON back to the state file.

### Step 6: Go to step 1

Read the state file again (from disk, not memory). Find the next pending stage. Continue the loop.

## On Failure

If a stage returns a FAILED verdict:
- Mark the stage as `failed` in the state file
- Print: `⚠️ Stage <N> (<name>) FAILED: <verdict>`
- **Stop the loop**. Tell the user what failed and how to fix it.
- The user can fix the issue and run `/pipeline-run` again — it will resume from the failed stage.

## On Completion

When all stages are passed/skipped:

### MANDATORY retro-artifact gate (before setting `completed_at`)

Run this check **every time** before `completed_at` is set or `PIPELINE_COMPLETE`
is reported:

```bash
# Must return 1+ — at least one comment from the pipeline user (not a bot)
COUNT=$(gh pr view $PR_NUMBER --json comments \
  -q '[.comments[] | select(.author.login != "github-actions" and (.author.login | startswith("dependabot") | not))] | length')
if [ "$COUNT" -lt 1 ]; then
    echo "FAIL: retro not posted on PR #$PR_NUMBER — do not set completed_at"
    # Re-run retro stage
    exit 1
fi
```

Why this gate exists: observed three drain iterations (djust PRs #946, #955, #956)
where the subagent completed merge + issue-closes + state-file update but dropped
the retro-comment post. Root cause was subagent returning control to parent after
invoking Monitor for CI poll. Without this gate, retro dropout is invisible —
the state file shows `completed_at` and the outer loop proceeds to the next task.

**Fix pattern** when the gate fails:
1. Write the retro file (`pr/feedback/retro-<N>.md`) if it doesn't exist yet
2. Post via `gh pr comment $PR_NUMBER --body "$(cat pr/feedback/retro-<N>.md)"`
3. Verify the gate passes, THEN set `completed_at`

### After the retro gate passes

- Set `completed_at` to current timestamp
- Print summary:
```
═══════════════════════════════════════════
  Pipeline Complete: <type>
  Task: <description>
  Branch: <branch>
  PR: #<number> — <url>
  Stages: <passed> passed, <skipped> skipped
═══════════════════════════════════════════
```

## Post-Completion Housekeeping

After each pipeline completes (before moving to the next task in `--all` mode):

### 1. Create GitHub issues for deferred findings

If the Code Review stage found 🟡 should-fix items that were NOT addressed before merge (i.e., they appear in `review_findings.should_fix` but `all_addressed` is false, or the re-review noted items were deferred), create a GitHub issue for each:

```bash
gh issue create --title "tech-debt: <finding summary>" \
  --body "From PR #<number> code review. <finding detail>" \
  --label "tech-debt"
```

This prevents deferred findings from silently accumulating in retro files.

### 2. Check for milestone retro trigger

After the pipeline completes, check whether this was the last task in the milestone:

```bash
# Count remaining incomplete tasks for this milestone in ROADMAP.md
grep "| v<milestone>" ROADMAP.md | grep -v "✅" | grep -v "~~" | grep -v "^|.*—" | wc -l
```

If zero tasks remain (or the user specified this is a milestone boundary):
- Remind the user: "Milestone vX.Y.Z appears complete. Run `/pipeline-retro --milestone vX.Y.Z` to write the milestone retrospective and update the Action Tracker."

### 3. Push main if needed

If main has unpushed commits (from the merge), push them:
```bash
git log origin/main..main --oneline | head -1
# If non-empty:
git push origin main
```

## After Completion — Continue to Next Task (--all mode)

If `--all` was specified with `--milestone` (and optionally `--priority`):

1. After the current pipeline completes, **run pipeline-next again** with the same milestone/priority filters
2. If pipeline-next finds another task → create state file, start the stage loop again
3. If no more tasks match → print the milestone summary and stop

This is the **outer loop**:
```
while true:
    1. Run pipeline-next with filters → picks task, creates state file
    2. If no task found → break (all done)
    3. ASSERT: ls .pipeline-state/*.json includes a file for the branch
       pipeline-next just picked. If not → STOP with error
       "Outer loop bug: pipeline-next did not create a state file."
    4. Run the stage loop (inner loop) → completes all stages
    5. Print task summary
    6. Go to 1
```

### Outer-loop integrity (the #840 failure mode)

The outer loop above is the program. The common failure is for the operator
(human or LLM) to complete iteration 1 correctly (full pipeline-next →
state file → stages → merge → retro) and then treat iteration 2 as a
"continuation" rather than a fresh iteration — skipping pipeline-next
and starting implementation directly on a new branch without a state
file.

**Observed cost** (djust PR #840, v0.5.1 form-polish batch): the operator
finished iteration 1 correctly, then created a new feature branch
directly and ran implementation/commit/PR without a state file. Stage 11
(Code Review) was never spawned as a subagent. When the user asked
"did we use pipeline-run for #840?", a retroactive Stage 11 review
surfaced 2 real must-fix defects that would have shipped: IME composition
not guarded in a keydown handler (CJK correctness bug), and a push-event
namespace inconsistency (wire-protocol back-compat trap).

**Hard rule**: iteration 2+ MUST re-run pipeline-next before any code is
written. If a state file does not exist for the branch, pipeline-run
must refuse to execute stages against that branch.

Print a milestone summary when all tasks are done:
```
═══════════════════════════════════════════
  Milestone Complete: v0.4.0
  Tasks processed: 4
  Succeeded: 3 (PRs: #571, #572, #573)
  Failed: 1 (transition/priority — TESTS_FAILED)
═══════════════════════════════════════════
```

## All Milestones Loop (--all-milestones mode)

When `--all-milestones` is specified, wrap the existing `--all` outer loop inside a milestone loop.

### Step 1: Discover milestones from ROADMAP.md

Find the project's ROADMAP.md (check `ROADMAP.md`, `docs/ROADMAP.md`, `docs/roadmap.md`).

Parse all `### Milestone: vX.Y.Z — Title` headings in document order. These are the milestones to process. Skip any milestone where ALL features in the Priority Matrix are marked completed (~~strikethrough~~ ✅).

### Step 2: The milestone loop

```
milestones = [parsed from ROADMAP.md in order]

for milestone in milestones:
    1. Print: "Starting milestone: <milestone>"
    2. Run the --all outer loop with --milestone <milestone>
       - Pass through --priority if specified
       - Pass through --group if specified (pipeline-next groups related tasks into batch PRs)
       - This picks tasks/groups via pipeline-next, runs all stages, repeats until no tasks remain
    3. If a task FAILS and stops the pipeline:
       - Print the failure summary
       - STOP the milestone loop (do not advance to the next milestone)
       - The user can fix the issue and re-run --all-milestones to resume
    4. Print milestone summary (tasks processed, succeeded, failed)
    5. Continue to next milestone
```

**With `--group`**: pipeline-next analyzes remaining tasks per milestone and proposes groups of related small features that ship as a single PR. Large/complex tasks stay solo. This significantly reduces the number of PRs and avoids tiny one-liner branches.

### Step 3: On completion

When all milestones are processed, print a full summary:

```
═══════════════════════════════════════════
  All Milestones Complete
  Milestones: <count> processed
  Tasks: <total> succeeded, <total> failed
  PRs: #<list>

  Per milestone:
  - v1.4: 35 tasks, 35 succeeded
  - v1.5: 42 tasks, 42 succeeded
  - v2.0: 30 tasks, 30 succeeded
═══════════════════════════════════════════
```

### Resume behavior

On resume (`/pipeline-run --all-milestones` after a failure or interruption):

1. Discover milestones from ROADMAP.md (same as initial run)
2. For each milestone, check if all its tasks are done (state files with `completed_at` set, or merged PRs)
3. Skip fully-completed milestones
4. Resume from the first milestone with remaining work
5. Within that milestone, the `--all` logic handles resuming from the incomplete task

This means `--all-milestones` is always safe to re-run — it picks up where it left off.

---

## Review Quality Rules

Code Review and Retrospective stages must meet minimum depth requirements.

**Code Review** must include:
- At least 2 specific line-number citations from the diff
- At least 1 question or concern (even if minor)
- Statement of what edge cases were considered

If the review comment is under 100 words, mark it `REVIEW_INSUFFICIENT` and
re-run with: "Your review was too brief. Cite specific lines, raise at least
one concern, and explain what edge cases you checked."

**Retrospective** must include:
- At least one "what could be improved" item that is specific (not generic)
- Reference to how this task's findings relate to previous tasks in the milestone

**After 3+ tasks in `--all` mode**, print: "3 tasks completed. Consider
having the user review the PRs before continuing." The user can say "continue"
to proceed.

---

## Why This Works

This skill is deliberately tiny — just the loop logic. All stage details (checklists, subagent prompts, mandatory flags) live in the state file on disk, not in this skill's text. The state file is re-read from disk at each iteration, so context compression can never lose the remaining stages.
