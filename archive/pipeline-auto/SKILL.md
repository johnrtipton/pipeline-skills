---
name: pipeline-auto
description: >
  Automatically pull tasks from a ROADMAP.md file and process them through
  pipeline skills into a development branch. Parses milestone features,
  selects work by priority/milestone, and runs pipeline-feature or pipeline-bugfix
  for each task. Invoke with /pipeline-auto followed by optional filters.
---

# Automated Roadmap Pipeline

Pull tasks from a project's ROADMAP.md and process them through pipeline skills, pushing all work to a development branch.

**Usage**:
- `/pipeline-auto` — process the next P0 task from the current milestone
- `/pipeline-auto --milestone v0.4.0` — process next task from a specific milestone
- `/pipeline-auto --milestone v0.4.0 --all` — process all tasks from a milestone sequentially
- `/pipeline-auto --feature "dj-value-*"` — process a specific feature by name/keyword
- `/pipeline-auto --priority P0` — process next P0 task across all milestones
- `/pipeline-auto --list` — list available tasks without processing
- `/pipeline-auto --list --milestone v0.4.0` — list tasks for a specific milestone

---

## Configuration

The skill needs to know:

1. **ROADMAP path** — defaults to `ROADMAP.md` in the project root. Override with `--roadmap <path>`
2. **Project directory** — the project to work on (where the code lives), defaults to cwd
3. **Development branch** — branch to accumulate work on, defaults to `development` or `dev/<milestone>` (e.g., `dev/v0.4.0`)

If the project has a CLAUDE.md, read it for project conventions before starting.

---

## Step 1: Parse ROADMAP.md

Read the ROADMAP file and extract tasks. The parser should handle this structure:

### Expected ROADMAP Structure

```markdown
## Next Up / In Progress / Planned

### Milestone: v0.X.0 — Title

#### Section Name

**Feature Name** — Description...

#### Another Section

**Another Feature** (#issue) — Description...
```

### Parsing Rules

1. **Milestones**: Lines matching `### Milestone: <version> — <title>` define milestone boundaries
2. **Sections**: Lines matching `#### <name>` define groupings within milestones (e.g., "Critical Bug Fixes", "Quick Wins")
3. **Features**: Lines starting with `**<name>**` within a milestone section are individual tasks
4. **Feature body**: Everything from the bold name to the next bold name (or section/milestone boundary) is the feature's spec
5. **Skip sections**: "Completed", "Future (Post-1.0)", "Contributing", "Investigate & Decide", "Differentiators", "Parity Tracker" — these aren't actionable tasks
6. **Priority**: Check the Priority Matrix table at the top. Match features by name to get their priority (P0-P3). Features not in the matrix default to P2.
7. **Status markers**: Features with checkmarks or "Already implemented" / "Completed" should be skipped
8. **Issue links**: Extract `(#NNN)` GitHub issue numbers if present

### Output: Task List

Build a structured task list:
```
[
  {
    "milestone": "v0.4.0",
    "section": "Critical Bug Fixes",
    "name": "VDOM structural patching",
    "priority": "P0",
    "issue": 559,
    "spec": "<full description from ROADMAP>",
    "type": "bugfix" | "feature"
  },
  ...
]
```

### Type Detection
- If section name contains "Bug Fix" or feature description mentions "fix", "broken", "fails", "regression" → type is `bugfix`
- Otherwise → type is `feature`

---

## Step 2: Select Tasks

Apply filters from the user's arguments:

| Filter | Behavior |
|---|---|
| `--list` | Print the task list and stop (don't process) |
| `--milestone <version>` | Only tasks from this milestone |
| `--priority <P0-P3>` | Only tasks at this priority level |
| `--feature "<keyword>"` | Fuzzy match feature name or description |
| `--all` | Process all matching tasks sequentially (default: just the first one) |
| `--resume` | Resume the most recent incomplete pipeline (reads `.pipeline-state/`) |
| No filters | Pick the highest-priority unprocessed task from the first "Next Up" milestone |

### Task Selection Order (when multiple tasks match)
1. P0 before P1 before P2 before P3
2. Within same priority: "Critical Bug Fixes" section first, then other sections in document order
3. **Resume detection**: Check `.pipeline-state/` for state files matching task branch names. If a state file exists with incomplete stages, that task should be **resumed first** (not skipped). A task is only skipped if its pipeline state shows all stages completed, OR if it has a merged PR.
4. Skip tasks that have a merged PR (check `gh pr list --state merged --head <branch>`)
5. Tasks with an open PR but incomplete review stages should be resumed at the review stage

---

## Step 3: Prepare Development Branch

Before processing tasks, set up the branch structure:

1. **Fetch latest**: `git fetch origin`
2. **Base branch**: Determine from project config (default_branch or pr_target_branch, typically `main`)
3. **Dev branch**: Create or checkout `dev/<milestone>` (e.g., `dev/v0.4.0`)
   - If it exists: `git checkout dev/<milestone> && git pull --rebase origin dev/<milestone>`
   - If new: `git checkout -b dev/<milestone> origin/<base_branch>`
4. **Task branch**: For each task, create a branch off the dev branch: `feat/<task-slug>` or `fix/<task-slug>`

This means:
- Each task gets its own branch off `dev/<milestone>`
- PRs target `dev/<milestone>` (not `main`)
- When the milestone is complete, `dev/<milestone>` gets merged to `main`

---

## Step 4: Process Each Task

For each selected task:

### 4a. Announce
Print a clear header:
```
═══════════════════════════════════════════
  Processing: <task name>
  Milestone: <version> | Priority: <priority>
  Type: <feature|bugfix> | Issue: #<number>
═══════════════════════════════════════════
```

### 4b. Build Task Spec

Compose a complete task spec from the ROADMAP entry:

```
## Task: <feature name>

<full ROADMAP description>

## Context
- Milestone: <version> — <milestone title>
- Priority: <priority>
- GitHub Issue: #<number> (if present)
- Section: <section name within milestone>

## Project
- Directory: <project path>
- Branch: <task branch> → PR targets dev/<milestone>
```

### 4c. Initialize State File (BEFORE running pipeline)

**This must happen BEFORE starting any pipeline stages.** Create the state file immediately after announcing the task:

```bash
mkdir -p .pipeline-state
```

1. If `.pipeline-state/<branch-name>.json` already exists → this is a **resume**. Read it, find the first non-`passed` stage, and skip to that stage.
2. If no state file exists → copy the appropriate template:
   - Bugfix: use the bugfix-state.json template structure
   - Feature: use the feature-state.json template structure
3. Fill in: `task_description`, `branch_name`, `pr_target_branch` (= `dev/<milestone>`), `project_path`, `started_at`
4. **Write it to `.pipeline-state/<branch-name>.json` NOW** — before running any stages

### 4d. Run Pipeline

Based on the task type:
- **bugfix**: Follow the full pipeline-bugfix procedure (all 13 stages)
- **feature**: Follow the full pipeline-feature procedure (all 15 stages)

**After EVERY stage**: Update the state file — set stage status, verdict, checklist items. This is defined in the Quality Gate Protocol in pipeline-shared.

**Critical overrides for automated mode:**
- PR target branch is `dev/<milestone>` (NOT `main`)
- Branch name follows the task slug
- If a GitHub issue number exists, link it in the PR
- Commit message must reference the milestone: `feat(v0.4.0): <description>`

**Resume shortcut**: If `--resume` is passed, skip ROADMAP parsing. Instead:
1. Find the most recent `.pipeline-state/*.json` file
2. Read it for pipeline type, branch name, task description, and current stage
3. Checkout the branch and run the appropriate pipeline skill — it will auto-resume from the state file

### 4e. Record Progress

After each task completes (success or failure):

1. **Update ROADMAP.md** — Mark the completed feature in the roadmap:
   - Find the feature's bold name line (e.g., `**VDOM structural patching**`)
   - Prepend a status marker: `**VDOM structural patching** (#559) — ✅ PR #563 (2026-03-18)`
   - If failed: `**Event sequencing** (#560) — ❌ Pipeline failed at Test Execution (2026-03-18)`
   - Commit the ROADMAP update: `git add ROADMAP.md && git commit -m "docs: mark <feature> as completed in ROADMAP (PR #<number>)"`
   - Push to the dev branch so the status is visible
   - **Only modify the status marker** — do not change the feature description or move it between sections

2. **Update tracking file** at `.pipeline-status.md` in the project root:
   ```markdown
   # Pipeline Status

   ## v0.4.0
   - [x] VDOM structural patching (#559) — PR #45 — 2026-03-18
   - [x] Focus preservation — PR #46 — 2026-03-18
   - [ ] Event sequencing (#560) — FAILED: tests_failed at Stage 6 — 2026-03-18
   - [ ] dj-value-* static event params — pending
   ```

3. **If task failed**: Print a summary of what failed and why. Do NOT attempt to fix it — move to the next task (if `--all`) or stop.

4. **If task succeeded**: Print the PR URL and continue to next task (if `--all`).

---

## Step 5: Summary

After all tasks are processed (or the single task completes), print a summary:

```
═══════════════════════════════════════════
  Pipeline Run Complete
═══════════════════════════════════════════

  Milestone: v0.4.0
  Tasks processed: 5
  Succeeded: 3 (PRs: #45, #46, #48)
  Failed: 1 (Event sequencing — tests_failed)
  Skipped: 1 (already had branch)

  Dev branch: dev/v0.4.0
  Ready for milestone merge: No (1 failure)
═══════════════════════════════════════════
```

---

## Milestone Merge

When all tasks in a milestone succeed, offer to create a milestone merge PR:

1. Checkout `dev/<milestone>`
2. Ensure it's up to date with all task branches merged
3. Create PR: `gh pr create --base main --title "Milestone: <version> — <title>" --body '<summary of all features>'`

---

## Safety Rules

1. **Never force-push** — all branches use normal push
2. **Never modify main directly** — all work goes through dev branches
3. **Stop on conflict** — if a task branch can't merge cleanly into dev, skip it and report
4. **Respect existing work** — if a branch already has commits, skip that task
5. **One at a time** — process tasks sequentially, not in parallel (context continuity matters)
6. **Confirm before --all** — if `--all` would process more than 3 tasks, ask for confirmation first

---

## Example Workflows

### Process the next P0 bug fix
```
/pipeline-auto --milestone v0.4.0 --priority P0
```
Picks "VDOM structural patching" (P0, Critical Bug Fixes section), runs pipeline-bugfix, pushes to `fix/vdom-structural-patching`, PRs to `dev/v0.4.0`.

### List what's available in v0.4.0
```
/pipeline-auto --list --milestone v0.4.0
```
Prints all features in v0.4.0 with their priority, type, and status.

### Process all quick wins
```
/pipeline-auto --milestone v0.4.0 --feature "Quick Wins" --all
```
Processes every feature under the "Quick Wins" section sequentially.

### Process a specific feature
```
/pipeline-auto --feature "dj-value-*"
```
Finds the "dj-value-* — Static event parameters" feature and runs pipeline-feature on it.
