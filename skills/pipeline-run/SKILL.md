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

**Usage**: `/pipeline-run` — finds the most recent incomplete state file and starts executing
**Usage**: `/pipeline-run fix-event-sequencing-560` — run a specific pipeline by branch name

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

## Why This Works

This skill is deliberately tiny — just the loop logic. All stage details (checklists, subagent prompts, mandatory flags) live in the state file on disk, not in this skill's text. The state file is re-read from disk at each iteration, so context compression can never lose the remaining stages.
