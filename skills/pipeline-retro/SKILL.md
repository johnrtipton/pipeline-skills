---
name: pipeline-retro
description: >
  Run milestone retrospectives, maintain the action tracker, and reconcile
  deferred findings across RETRO.md, PR retros, and GitHub issues.
  Use after completing a milestone or when the user asks to review retros.
---

# Pipeline Retro — Milestone Retrospectives and Action Tracking

Synthesize per-PR retrospectives into milestone-level learnings, maintain a
consolidated action tracker, and ensure deferred findings become GitHub issues.

**Usage**:
- `/pipeline-retro` — run retro for the most recently completed milestone (auto-detect)
- `/pipeline-retro --milestone v0.4.0` — run retro for a specific milestone
- `/pipeline-retro --actions` — show the action tracker (open items)
- `/pipeline-retro --actions --all` — show all actions (open + closed)
- `/pipeline-retro --reconcile` — scan all sources, deduplicate, create missing GitHub issues

## Files

| File | Purpose |
|------|---------|
| `RETRO.md` | Milestone retrospective log + action tracker (source of truth) |
| `pr/feedback/retro-{N}.md` | Per-PR retrospectives (input to milestone retros) |
| GitHub Issues (`tech-debt` label) | Deferred findings that need resolution |

## The Action Tracker

`RETRO.md` has an **Action Tracker** table at the top — the single source of truth for
all retrospective actions. Every "What to Improve" recommendation and every deferred
code review finding must appear here.

```markdown
## Action Tracker

Items from retrospectives that need resolution. Every item must have a GitHub
issue or be explicitly closed with a reason.

| # | Action | Source | GitHub | Status | Notes |
|---|--------|--------|--------|--------|-------|
| 1 | SLA iterator batching | PR #50 | #51 | Open | |
| 2 | Template sandboxing | PR #50 | #52 | Open | |
| 3 | Audit existing mutation handlers | Retro v0.4.0 | — | Open | One-time task |
| 4 | HMAC-based SSN lookup | Retro v0.3.0 | — | Closed | No current need |
```

**Rules**:
- Every row must have a Source (PR number or milestone retro)
- Every open row should have a GitHub issue number (create one if missing)
- Close items with a reason, don't delete them
- Deduplicate: if the same item appears in multiple retros, keep one row with all sources

## Running a Milestone Retro

### Step 1: Identify the milestone and its PRs

If `--milestone` is specified, use that. Otherwise, detect the most recent milestone
by reading RETRO.md and finding the latest entry, then look for the next milestone
that has completed work but no retro entry.

Find the PRs for the milestone:
```bash
# Check pipeline state files for completed pipelines
ls .pipeline-state/*.json | while read f; do
  python3 -c "import json; s=json.load(open('$f')); print(s.get('pr_number',''), s.get('branch_name',''), s.get('completed_at',''))" 2>/dev/null
done

# Or check merged PRs on GitHub
gh pr list --state merged --limit 50 --json number,title,mergedAt
```

### Step 2: Read the per-PR retros

For each PR in the milestone, read `pr/feedback/retro-{N}.md`. Extract:
- What Worked Well (patterns to repeat)
- What Didn't Work (problems encountered)
- What to Improve (action items)
- Knowledge Base Updates Needed
- Review Stats
- Recurring Issue Tracker (if present)

### Step 3: Write the milestone entry

Append to `RETRO.md` using this template:

```markdown
## vX.Y.Z — Title (PRs #NN–#MM)

**Date**: YYYY-MM-DD
**Scope**: Brief description of what shipped
**Tests at close**: NNN

### What We Learned

**1. Finding title.**
Description of what happened, which PR(s) it affected, and why it matters.

**Action taken**: What was done about it (checklist update, CLAUDE.md change,
code fix, etc.). If nothing was done, say "Open — tracked in Action Tracker #N."

(Repeat for each significant finding — aim for 3-6 per milestone.
Synthesize across PRs; don't just list each PR's findings separately.)

### Insights

- Bullet points: patterns that worked, surprises, process observations
- What should we keep doing?
- What was different about this milestone vs previous ones?

### Review Stats

| Metric | PR #A | PR #B | ... | Total |
|--------|-------|-------|-----|-------|
| Tests added | N | N | | N |
| 🔴 Findings | N | N | | N |
| 🟡 Findings | N | N | | N |
| Findings fixed | N | N | | N |
| CI failures | N | N | | N |

### Process Improvements Applied

**CLAUDE.md**: List additions/changes made during this milestone
**Pipeline template**: List additions/changes
**Checklist**: List additions/changes
**Skills**: List any skill updates (pipeline-run, pipeline-next, etc.)

### Open Items

- [ ] Item 1 — tracked in Action Tracker #N (GitHub #NN)
- [ ] Item 2 — tracked in Action Tracker #N (GitHub #NN)
```

### Step 4: Update the Action Tracker

For each milestone retro entry:

1. **Extract new actions**: Every "What to Improve" item, every deferred finding,
   every "Knowledge Base Updates Needed" item → add a row to the Action Tracker

2. **Create GitHub issues**: For each new action that doesn't have a GitHub issue:
   ```bash
   gh issue create --title "tech-debt: <action summary>" \
     --body "Source: <milestone retro or PR number>\n\n<details>" \
     --label "tech-debt"
   ```

3. **Close resolved items**: Check existing open rows — if the action was completed
   during this milestone, mark it closed with the PR/commit that resolved it

4. **Deduplicate**: If an item from a previous milestone's Open Items is now in the
   Action Tracker, remove the checkbox from the old entry and reference the tracker row

### Step 5: Update previous milestone entries

Check off any Open Items from earlier milestones that are now resolved.
Add a note like `— resolved in vX.Y.Z (PR #NN)`.

### Step 6: Commit

```bash
git add RETRO.md
git commit -m "docs: milestone retro vX.Y.Z + action tracker update"
git push origin main
```

## Reconcile Mode (`--reconcile`)

Scan all tracking locations and reconcile:

1. **Read RETRO.md Action Tracker** — get all tracked items
2. **Read RETRO.md Open Items** (per-milestone) — find any not in the tracker
3. **Read PR retros** — find "What to Improve" and "Deferred" items not in the tracker
4. **Read GitHub issues** (`tech-debt` label) — find any not in the tracker
5. **Reconcile**:
   - Items in Open Items but not in Action Tracker → add to tracker
   - Items in PR retros but not in Action Tracker → add to tracker
   - Items in GitHub issues but not in Action Tracker → add to tracker
   - Items in Action Tracker without GitHub issues → create issues
   - Duplicate items → merge into single tracker row with multiple sources
6. **Report** what was found and what was fixed

## Actions Mode (`--actions`)

Print the Action Tracker table from RETRO.md, filtered by status:
- `--actions` → open items only
- `--actions --all` → all items (open + closed)

For each open item, check if the GitHub issue is still open:
```bash
gh issue view <number> --json state -q '.state'
```

Flag any inconsistencies (tracker says Open but issue is Closed, or vice versa).

## Integration with pipeline-run

The `pipeline-run` skill's "Post-Completion Housekeeping" section checks whether a
milestone retro is due and reminds the user. This skill does the actual work.

The handoff:
1. `pipeline-run` completes → checks if milestone is done → prints reminder
2. User runs `/pipeline-retro` → this skill synthesizes the retro
3. This skill updates the Action Tracker and creates GitHub issues
4. Next `pipeline-run` starts clean

## Why This Matters

Without this skill:
- "What to Improve" items accumulate in retro files and are never actioned
- Deferred findings exist only in PR comments — invisible to planning
- The same recommendation appears in multiple retros ("create GitHub issues for deferred findings" — recommended in PRs #25, #28, AND #50 before it was finally done)
- No one knows which actions are open vs resolved

With this skill:
- Single Action Tracker table in RETRO.md — the dashboard
- Every action has a GitHub issue — visible in project board
- Reconcile mode catches drift between the 3 tracking locations
- Milestone retros are consistent (same template, same process)
