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

**The state file is the program. The model is the executor.** Like
`/pipeline-run`, this skill is driven by a state file at
`.pipeline-state/retro-<milestone>.json`. The model must tick off mandatory
checklist items in that file (read fresh from disk, not remembered) before
advancing a stage. This pattern defends against the failure mode where the
model writes the milestone retro as prose and then *feels done* without filing
the actions the prose calls for.

**Usage**:
- `/pipeline-retro` — run retro for the most recently completed milestone (auto-detect)
- `/pipeline-retro --milestone v0.4.0` — run retro for a specific milestone
- `/pipeline-retro --resume` — resume an interrupted retro from its state file
- `/pipeline-retro --actions` — show the action tracker (open items)
- `/pipeline-retro --actions --all` — show all actions (open + closed)
- `/pipeline-retro --reconcile` — scan all sources, deduplicate, create missing GitHub issues

## Files

| File | Purpose |
|------|---------|
| `RETRO.md` | Milestone retrospective log + action tracker (source of truth) |
| `pr/feedback/retro-{N}.md` | Per-PR retrospectives (one input source) |
| GitHub PR comments | Per-PR retrospectives (the other input source — `gh pr view <N> --json comments`) |
| `.pipeline-state/retro-<milestone>.json` | This pipeline's state file — checklist + classifications + tracker rows + issue numbers |
| GitHub Issues (`tech-debt` label) | Filed for each new Action Tracker row |

## The Action Tracker

`RETRO.md` has an **Action Tracker** table at the top — the single source of
truth for all retrospective actions. Every "What to Improve" recommendation
and every deferred code-review finding must appear here.

**Status values**: `Open` (actionable in this repo), `Closed` (resolved with reason),
`OUT-OF-REPO` (blocked on work in a different repository; Notes must point at
upstream repo + issue).

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
| 5 | Something cross-repo | Retro v0.5.0 | — | OUT-OF-REPO | Awaiting pipeline-skill#NN |
```

**Rules**:
- Every row must have a Source (PR number or milestone retro)
- Every Open row should have a GitHub issue number (create one if missing)
- Close items with a reason, don't delete them
- OUT-OF-REPO rows must document the upstream repo + issue in the Notes column
- Deduplicate: if the same item appears in multiple retros, keep one row with all sources

## How the state file drives the retro

Pseudocode of the loop (mirrors `/pipeline-run`):

```
1. READ .pipeline-state/retro-<milestone>.json
2. FIND next stage where status != "passed" and status != "skipped"
3. EXECUTE every checklist item in that stage (mandatory items must be ticked)
4. WRITE state file (checklist .done = true, status = "passed", verdict = output)
5. GO TO step 1
```

Mandatory items cannot be marked `done: true` without evidence. If you can't
produce the artifact a mandatory item asks for, the stage fails and the
pipeline halts — fix the issue and resume.

## Stage walkthrough

### Stage 1 — Identify milestone PRs

If `--milestone` is given, use it. Otherwise read `RETRO.md` to find the
latest entry, then look for the next milestone with completed work but no
retro entry.

**Milestone-name format**: accepts both `vX.Y.Z` (actual release) and
`vX.Y.Z-N` (drain bucket / planning iteration toward release `vX.Y.Z`).
The state-file naming `retro-<milestone>.json` works for either shape;
just substitute the `.` for `-` if you prefer (e.g.,
`retro-v0.9.2-1.json` is fine).

```bash
# completed pipeline state files
ls .pipeline-state/*.json | while read f; do
  python3 -c "import json; s=json.load(open('$f')); print(s.get('pr_number',''), s.get('branch_name',''), s.get('completed_at',''))" 2>/dev/null
done

# OR merged PRs on GitHub
gh pr list --state merged --limit 50 --json number,title,mergedAt
```

Record `pr_numbers` in the state file. Output `MILESTONE_IDENTIFIED`.

### Stage 2 — Read per-PR retros

**This is the step where the milestone retro silently goes wrong.** Per-PR
retros may live in either of two places, and the model commonly checks only
the file path and proceeds when nothing's there:

1. `pr/feedback/retro-{N}.md` (the canonical local file)
2. GitHub PR comments (when `pipeline-run` posted the retro via
   `gh pr comment` instead of writing the file — verify with
   `gh pr view <N> --json comments`)

For each PR in `pr_numbers`, try the file first; fall back to the GitHub
comment. Extract:
- What Worked Well (patterns to repeat)
- What Didn't Work (problems encountered)
- What to Improve (action items)
- Knowledge Base Updates Needed
- Review Stats
- Recurring Issue Tracker (if present)

**If neither a file nor a comment retro exists for a PR**, that's a
`pipeline-run` retro-artifact-gate violation. Record it as a
`RETRO_GATE_VIOLATION` in the state file and require the backfill in stage 4.
The retro you write here will be the backfill.

Record `per_pr_findings` in the state file (keyed by PR number). Output
`PR_RETROS_READ`.

### Stage 3 — Write the milestone entry

Append to `RETRO.md` using this template:

```markdown
## vX.Y.Z — Title (PRs #NN–#MM)

**Date**: YYYY-MM-DD
**Scope**: Brief description of what shipped
**Tests at close**: NNN

### What We Learned

**1. Finding title.**
Description of what happened, which PR(s) it affected, and why it matters.

**Action taken**: <see Stage 3.5 — must be one of: diff | skill_update | tracker_row | closed>

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

Record the `findings` list in the state file (one entry per finding with
title and `action_taken_text`). Output `MILESTONE_ENTRY_DRAFTED`.

### Stage 3.5 — VERIFICATION GATE: classify Action taken: lines

This stage is the load-bearing addition. **Writing prose in `RETRO.md` is
Stage 3 (synthesis). Filing actions is Stage 4. If your `Action taken:`
line is the prose itself, the action is missing — you cannot pass this gate
by re-reading your own RETRO.md text and calling it an action.**

For each finding, classify the `Action taken:` line as exactly one of:

| Class | Shape | Example |
|---|---|---|
| `diff` | A specific file:line + change description; commit must already exist or be queued for stage 6 | `Added _setFormPending helper at python/djust/static/djust/src/09-event-binding.js:127.` |
| `skill_update` | A specific path to a SKILL.md or CLAUDE.md plus the section heading edited | `Updated ~/.claude/skills/pipeline-run/SKILL.md — section "MANDATORY Post-Commit Verification".` |
| `tracker_row` | `Open — tracked in Action Tracker #N (GitHub #NNN)` with both numbers present | `Open — tracked in Action Tracker #138 (GitHub #1029).` |
| `closed` | `Closed — <reason>` where reason references a PR/commit/test | `Closed — covered by tests/js/dj-form-pending.test.js (#1023).` |
| `prose_only` | **Anything else** — see Red Flags below | `Captured here as a milestone finding rather than scattering them per-PR.` |

Record `action_classifications` in the state file (finding_index →
classification).

**GATE**: If any finding classifies as `prose_only`, the gate FAILS. Do not
advance to stage 4. Fix one of three ways:

1. **Convert to tracker_row** — file the action in stage 4, then return here
   and re-classify with the issue number.
2. **Apply now** — commit a diff to a file other than RETRO.md (CLAUDE.md
   addition, PR-checklist update, code change), then re-classify as `diff`
   or `skill_update`.
3. **Delete the finding** from RETRO.md if it isn't worth either. Milestone
   findings exist to drive change. Observations that don't drive change
   belong in **Insights**, not in **What We Learned**.

Output `GATE_PASSED` or `GATE_FAILED <indices>`.

### Stage 4 — Update the Action Tracker

For each milestone retro entry:

1. **Extract new actions** — sources to scan:
   - Every per-PR "What to Improve" item not already tracked
   - Every per-PR "Knowledge Base Updates Needed" item
   - Every milestone finding classified `tracker_row` in stage 3.5
   - **Every generalizable framework pattern surfaced in per-PR retros**
     that isn't already canonicalized in CLAUDE.md, the PR checklist, or
     framework docs (these are the patterns the per-PR retro author
     extracted but the milestone retro will lose if you don't track them)

2. **Create GitHub issues** — for every new Action Tracker row:
   ```bash
   gh issue create \
     --title "tech-debt: <action summary>" \
     --body "Source: <milestone retro or PR number>\n\n<details>" \
     --label "tech-debt"
   ```
   Record the issue number in `new_github_issues`.

3. **Backfill prose Action taken: lines** — for each `tracker_row` finding,
   replace the prose in `RETRO.md` with `Open — tracked in Action Tracker
   #N (GitHub #NNN)` using the real numbers.

4. **Close resolved rows** — if a tracker row was resolved in this
   milestone, mark it `Closed` with the PR/commit reference. Record in
   `closed_rows`.

5. **Deduplicate** — items appearing in multiple sources merge into one row
   with a combined Source field.

6. **Backfill missing PR retros** — for each `RETRO_GATE_VIOLATION` from
   stage 2, post the backfill via `gh pr comment <N> --body-file <retro>`.

Output `ACTION_TRACKER_UPDATED <counts>`.

### Stage 4.5 — Re-verify Action taken: lines

After stage 4 backfills the tracker rows and issue numbers, re-run stage
3.5's classification. **No finding should classify as `prose_only` any
more.** If any do, stage 4 missed something — return to stage 4.

Output `REVERIFY_PASSED` or `REVERIFY_FAILED`.

### Stage 5 — Update previous milestone entries

Scan previous milestones' Open Items for items resolved in this milestone.
Annotate with `— resolved in vX.Y.Z (PR #NN)`.

Output `PREVIOUS_MILESTONES_UPDATED <count>`.

### Stage 6 — Commit

```bash
# Resolve the repo's default branch (pipeline-config → origin/HEAD → remote → fallback). Never assume main/master.
BASE=$(sed -n 's/^- *default_branch: *//p' CLAUDE.md 2>/dev/null | awk 'NR==1{print $1}')
[ -z "$BASE" ] && BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
[ -z "$BASE" ] && BASE=$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p')
[ -z "$BASE" ] && BASE=main
git add RETRO.md
# plus any CLAUDE.md / PR-checklist / skill files updated as `diff` or `skill_update` actions
git commit -m "docs(retro): milestone vX.Y.Z + action tracker update"
git log -1 --oneline   # Action #122 — verify commit landed with expected message
git push origin "$BASE"
```

Output `RETRO_COMPLETE`.

## Red Flags — STOP and complete Stage 4 before committing

If your milestone entry has any of these phrases on an `Action taken:` line,
the action is missing. The classification is `prose_only` and the gate fails:

- "Captured here as a milestone finding"
- "Pattern observation worth promoting"
- "Pattern documented in this retro"
- "Pattern documented in [CHANGELOG / docstring]" without a specific file:line
- "No code change. <anything that follows>" (the entire line is prose-only)
- "Generalizable pattern surfaced"
- "Worth canonicalizing in [docs / CLAUDE.md]" (without actually doing it this commit)
- "Documented for future reference"
- "Noted for future milestones"

**All of these mean: the synthesis is in `RETRO.md`, but the action is not.
File the Action Tracker row + GitHub issue (Stage 4) before committing, or
delete the finding from `RETRO.md`.**

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "I documented it in the milestone retro itself, that's the action" | Stage 3 (write entry) and Stage 4 (track action) are separate steps. Writing prose is the synthesis, not the action. |
| "Synthesis IS the milestone-level finding" | Synthesis is Stage 3. The action is Stage 4. Both must happen. |
| "It's a pattern, not a What-to-Improve item, so Stage 4 doesn't apply" | Stage 4 applies to every finding whose Action taken: line classifies as `prose_only` in Stage 3.5, regardless of label. |
| "Adding 6 issues for 6 patterns is over-tracking" | If the pattern is worth a milestone finding, it's worth a tracker row. Otherwise demote it to Insights or delete it. |
| "These are observations, not actions" | Then move them to the **Insights** section (which has no Action taken: line) or delete them. The **What We Learned** findings drive change. |
| "I'll create the issues later" | Later doesn't happen. Stage 4 is mandatory before Stage 6 commit. |
| "The per-PR retros are on GitHub, not in pr/feedback/, so Step 2 doesn't apply" | Both locations are valid input sources. Stage 2 mandates checking both. |
| "I already wrote a thoughtful synthesis — that has more value than 6 issue rows" | Synthesis and tracking are different things. Both have value. Skip neither. |

## Resume

If a retro is interrupted (context limit, crash, Ctrl+C), the state file
persists on disk. Run `/pipeline-retro --resume` to pick up from the last
incomplete stage.

## Reconcile Mode (`--reconcile`)

Scan all tracking locations and reconcile:

1. **Read RETRO.md Action Tracker** — get all tracked items
2. **Read RETRO.md Open Items** (per-milestone) — find any not in the tracker
3. **Read PR retros** (both `pr/feedback/retro-{N}.md` and GitHub PR comments)
   — find "What to Improve" and "Deferred" items not in the tracker
4. **Read GitHub issues** (`tech-debt` label) — find any not in the tracker
5. **Reconcile**:
   - Items in Open Items but not in Action Tracker → add to tracker
   - Items in PR retros but not in Action Tracker → add to tracker
   - Items in GitHub issues but not in Action Tracker → add to tracker
   - Items in Action Tracker without GitHub issues → create issues
   - Duplicate items → merge into single tracker row with multiple sources
   - PRs with no retro at all → flag as gate violations, surface for backfill
   - OUT-OF-REPO rows → verify the Notes column points at the upstream repo
     + issue number; if the cross-repo work is done, advance to Closed;
     if the Notes field is missing the upstream reference, flag it
6. **Re-run Stage 3.5 classification** against every existing milestone
   entry. Any `prose_only` lines from earlier milestones get backfilled with
   tracker rows + issue numbers.
7. **Report** what was found and what was fixed.

## Actions Mode (`--actions`)

Print the Action Tracker table from RETRO.md, filtered by status:
- `--actions` → open items only (Open + OUT-OF-REPO, counted separately)
- `--actions --all` → all items (Open + OUT-OF-REPO + Closed)

For each Open item, check if the GitHub issue is still open:
```bash
gh issue view <number> --json state -q '.state'
```

Flag any inconsistencies (tracker says Open but issue is Closed, or vice versa).

OUT-OF-REPO items are displayed in their own group under the open-items
output, labeled "Cross-repo (blocked on external work)". Their GitHub
issues (if any) are not checked for open/closed status since the blocking
work is in a different repository. The count line reports
"N open, M out-of-repo, T total" to avoid polluting the actionable-open
count with cross-repo-blocked items.

## Integration with pipeline-run

The `pipeline-run` skill's "Post-Completion Housekeeping" section checks
whether a milestone retro is due and reminds the user. This skill does the
actual work.

The handoff:
1. `pipeline-run` completes → checks if milestone is done → prints reminder
2. User runs `/pipeline-retro` → this skill creates the state file and
   walks the stages
3. This skill updates the Action Tracker and creates GitHub issues
4. Next `pipeline-run` starts clean

## Why this matters

Without the state file + classification gate:
- The model writes synthesized prose in `RETRO.md` and feels done
- "What to Improve" items accumulate in retro files and are never actioned
- Generalizable framework patterns surfaced in per-PR retros get lost
  in milestone-level prose with `Action taken: documented here` non-actions
- The same recommendation appears in multiple retros before it's finally
  filed (recommended in PRs #25, #28, AND #50 before "create GitHub issues
  for deferred findings" was actually done)
- No one knows which actions are open vs resolved

With this skill:
- State file is the program counter — mandatory items can't be skipped
- Stage 3.5 classification gate forces every finding to point at a
  concrete artifact (diff, skill update, tracker row, or closed)
- Stage 4 mandates GitHub issue creation, with numbers recorded in state
- Reconcile mode catches drift between the 4 tracking locations (RETRO.md,
  PR retro files, GitHub PR comments, GitHub tech-debt issues)
- Milestone retros are consistent and audit-trail-complete
