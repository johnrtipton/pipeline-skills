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

**State file templates are at** (read directly, do not search):
- `~/online_projects/ai/pipeline-skill/templates/feature-state.json`
- `~/online_projects/ai/pipeline-skill/templates/bugfix-state.json`
- `~/online_projects/ai/pipeline-skill/templates/refactor-state.json`

## Autonomous Execution

When `--all`, `--all-milestones`, or `--group` is specified, the pipeline runs **fully autonomously**. Do NOT pause to ask the user if they want to continue between tasks or groups. The flag itself is the user's confirmation. Only stop on failure.

## Parallel Stages

Stages 6 (Test Execution), 7 (Self-Review), and 8 (Security Check) are independent read-only stages. **Run them in parallel** by spawning 3 agents simultaneously. This cuts wall-clock time significantly. Wait for all 3 to complete before proceeding to Stage 9.

## The Loop

Repeat these steps until all stages are done:

```
1. READ the state file from .pipeline-state/
2. FIND the next stage where status != "passed" and status != "skipped"
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
    3. Run the stage loop (inner loop) → completes all stages
    4. Print task summary
    5. Go to 1
```

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

## Why This Works

This skill is deliberately tiny — just the loop logic. All stage details (checklists, subagent prompts, mandatory flags) live in the state file on disk, not in this skill's text. The state file is re-read from disk at each iteration, so context compression can never lose the remaining stages.
