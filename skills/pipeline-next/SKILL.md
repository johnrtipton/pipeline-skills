---
name: pipeline-next
description: >
  Pick the next task (or group of related tasks) from ROADMAP.md and set up
  a pipeline state file. Reads the roadmap, filters by milestone/priority,
  groups related small features into batches, checks what's already done,
  and creates .pipeline-state/<branch>.json from the template.
  Run /pipeline-run after this to execute the stages.
---

# Pipeline Next — Pick a Task and Initialize

Pick the next task from the project's ROADMAP.md and create a pipeline state file.

**Usage**:
- `/pipeline-next` — next highest-priority task from first milestone
- `/pipeline-next --milestone v0.4.0` — next task from v0.4.0
- `/pipeline-next --milestone v0.4.0 --priority P1` — next P1 task
- `/pipeline-next --feature "auth"` — specific feature by keyword
- `/pipeline-next --list` — list available tasks without starting
- `/pipeline-next --milestone v0.4.0 --group` — auto-group remaining tasks and pick next group
- `/pipeline-next --milestone v0.4.0 --list --group` — show proposed groups without starting

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

Print status of all matching tasks.

### 6. Group related tasks (--group mode)

If `--group` is specified, analyze the remaining (not-done) tasks and group them by relatedness. Tasks should be grouped when they:

- **Touch the same files** — tasks that modify the same source files
- **Share a pattern** — tasks that follow the same implementation pattern
- **Are small and related** — multiple small tasks in the same functional area
- **Belong to the same ROADMAP section** — tasks listed under the same section heading

**Grouping criteria** — analyze the actual ROADMAP tasks and group by:
- **Shared files**: tasks that modify the same source files
- **Shared patterns**: tasks that follow the same implementation pattern
- **Small and related**: multiple small tasks in the same functional area
- **Same section**: tasks listed under the same ROADMAP section heading

**Grouping rules:**
- Each group should have a clear theme name (e.g., "Form inputs", "Auth improvements")
- Max ~5-6 tasks per group (keeps implementation manageable)
- Large/complex tasks stay solo
- Bug fixes are never grouped with features

Print the proposed groups with `--list --group`. Without `--list`, pick the highest-priority group.

### 7. Create the state file

Read the template file — **check project-local templates first**:

```bash
# 1. Check for project-local template (preferred — has project-specific stages/prompts):
#    .pipeline-templates/feature-state.json
#    .pipeline-templates/bugfix-state.json
#    .pipeline-templates/refactor-state.json
#
# 2. Fall back to the pipeline-skill's templates/ directory:
#    Locate via: the directory containing pipeline.py, or PIPELINE_SKILL_DIR env var.
#    templates/feature-state.json
#    templates/bugfix-state.json
#    templates/refactor-state.json
#
# Project-local templates override skill defaults when they exist.
# Projects customize them to add stages (e.g., Re-Review), subagent prompts,
# and project-specific checklists.
```

**For a single task:** Copy template, fill in task_description, branch_name, etc.

**For a group (--group mode):** Copy the feature template, then:
- `task_description`: Include ALL tasks in the group with their specs:
  ```
  ## Batch: <group theme>

  Implement these related features as a single PR:

  ### 1. <task name>
  <spec from ROADMAP>

  ### 2. <task name>
  <spec from ROADMAP>
  ...
  ```
- `branch_name`: `feat/<group-slug>` (e.g., `feat/event-attributes`, `feat/ui-feedback-attrs`)
- The Planning stage will plan all tasks together
- The Implementation stage will implement all tasks in sequence
- One PR covers the entire group
- Add a `"batch_tasks"` field to the state file listing the individual task names:
  ```json
  "batch_tasks": ["search input", "password input", "autocomplete", "slider"]
  ```

Write to `.pipeline-state/<branch-name>.json`. Ensure `.pipeline-state/` is in `.gitignore`.

### 8. Output

**Single task:**
```
═══════════════════════════════════════════
  Task selected: <name>
  Type: <feature|bugfix> | Priority: <P0-P3>
  Branch: <branch-name>
  State: .pipeline-state/<file>.json
  Stages: <N> (from template)
═══════════════════════════════════════════
```

**Batch group:**
```
═══════════════════════════════════════════
  Group selected: <group theme>
  Tasks: <count> features
  Branch: feat/<group-slug>
  State: .pipeline-state/<file>.json
  Stages: <N> (from template)

  Included tasks:
  1. <task name>
  2. <task name>
  ...
═══════════════════════════════════════════
```
