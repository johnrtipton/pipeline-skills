---
name: pipeline-next
description: >
  Pick the next task from ROADMAP.md and set up a pipeline state file.
  Reads the roadmap, filters by milestone/priority, checks what's already
  done, and creates .pipeline-state/<branch>.json from the template.
  Run /pipeline-run after this to execute the stages.
---

# Pipeline Next — Pick a Task and Initialize

Pick the next task from the project's ROADMAP.md and create a pipeline state file.

**Usage**:
- `/pipeline-next` — next highest-priority task from first milestone
- `/pipeline-next --milestone v0.4.0` — next task from v0.4.0
- `/pipeline-next --milestone v0.4.0 --priority P1` — next P1 task
- `/pipeline-next --feature "dj-value"` — specific feature by keyword
- `/pipeline-next --list` — list available tasks without starting

## Steps

### 1. Find and read ROADMAP.md

Look for: `ROADMAP.md`, `docs/ROADMAP.md`, `docs/roadmap.md`

### 2. Parse the Priority Matrix

The table at the top maps features to priorities (P0-P3). Parse it. Items with ~~strikethrough~~ or ✅ are completed — skip them.

### 3. Parse milestones and features

Scan for `### Milestone: vX.Y.Z — Title` sections. Within each, find `**Feature Name**` entries. Skip sections: Completed, Future, Contributing, Investigate, Differentiators, Parity Tracker.

For each feature extract: name, milestone, section, priority (from matrix), issue number (#NNN if present), type (bugfix if section has "Bug Fix" or description mentions fixing/broken, else feature), and the full spec text.

### 4. Filter and select

Apply the user's filters (milestone, priority, feature keyword). Sort by priority (P0 first), then bug fixes before features.

### 5. Check what's already done

For each matching task, check:
- `.pipeline-state/<branch>.json` exists with `completed_at` set → done
- `gh pr list --state merged --head <branch>` finds a merged PR → done
- `.pipeline-state/<branch>.json` exists without `completed_at` → **resume this one**

Print status of all matching tasks. Pick the first one that's not done.

### 6. Create the state file

This is the critical step. Read the template file DIRECTLY — do not search for it:

```bash
# For features:
cat ~/online_projects/ai/pipeline-skill/templates/feature-state.json
# For bugfixes:
cat ~/online_projects/ai/pipeline-skill/templates/bugfix-state.json
# For refactors:
cat ~/online_projects/ai/pipeline-skill/templates/refactor-state.json
```

Copy it, fill in:
- `task_description`: the full ROADMAP spec
- `branch_name`: `fix/<slug>` or `feat/<slug>`
- `pr_target_branch`: `dev/<milestone>` if milestone specified, else project default
- `project_path`: current working directory
- `started_at`: current ISO 8601 timestamp

Write to `.pipeline-state/<branch-name>.json`. Ensure `.pipeline-state/` is in `.gitignore`.

### 7. Output

Print:
```
═══════════════════════════════════════════
  Task selected: <name>
  Type: <feature|bugfix> | Priority: <P0-P3>
  Branch: <branch-name>
  State: .pipeline-state/<file>.json
  Stages: <N> (from template)

  Run /pipeline-run to start executing stages.
═══════════════════════════════════════════
```
