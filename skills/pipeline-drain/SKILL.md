---
name: pipeline-drain
description: >
  Drain open GitHub issues into the current milestone and process them all.
  Checks for open issues, adds them to the ROADMAP milestone, then runs
  pipeline-run --milestone --all to process everything.
user_invocable: true
argument: >
  Optional: --milestone vX.Y.Z (defaults to latest incomplete milestone in ROADMAP.md).
  Optional: --label LABEL (filter issues by GitHub label, e.g. "tech-debt").
  Optional: --dry-run (show what would be added without modifying anything).
  Optional: --priority P0|P1|P2|P3 (assign priority to new issues, default P2).
---

# Pipeline Drain — Triage Open Issues into Milestone and Process

Automates the full cycle: discover open issues → add to ROADMAP → run pipeline.

**Usage**:
- `/pipeline-drain` — drain all open issues into latest milestone, process all
- `/pipeline-drain --milestone v0.4.3` — drain into specific milestone
- `/pipeline-drain --label tech-debt` — only drain issues with this label
- `/pipeline-drain --dry-run` — show plan without executing
- `/pipeline-drain --priority P1` — assign P1 to all new issues (default P2)

## Steps

### 1. Determine the target milestone

If `--milestone` specified, use it. Otherwise, find the latest milestone in
ROADMAP.md that has incomplete tasks (not all ~~strikethrough~~ ✅):

```bash
# Parse milestones from ROADMAP.md
grep "### Milestone:" ROADMAP.md
```

Pick the last one that has at least one non-completed task, or the last one
if all tasks are done (we're adding new ones).

**Milestone-name format**: two shapes are valid (per project convention):

- `vX.Y.Z` — actual release (3-digit SemVer), e.g., `v0.9.1`.
- `vX.Y.Z-N` — drain-bucket / planning iteration, e.g., `v0.9.2-1`. Drain
  buckets accumulate into the next release.

The grep `### Milestone:` matches either shape — no parser change needed.
When adding new buckets, prefer the pre-release form
(`v<next-release>-<N>`) over reusing the release name as both a release
and a planning bucket.

### 2. Fetch open GitHub issues

```bash
gh issue list --state open --json number,title,labels,body --limit 100
```

If `--label` specified, add `--label LABEL` to the filter.

Exclude issues that are already in the ROADMAP's Priority Matrix for this
milestone (check by issue number: `grep "#NNN" ROADMAP.md`).

### 3. Categorize each issue

For each open issue not already in the ROADMAP:

1. **Read the issue body** to understand what it is
2. **Determine type**: bugfix (title starts with "fix", "bug", or body describes broken behavior), tech-debt (label "tech-debt"), feature, or investigation
3. **Determine priority**: Use `--priority` flag if specified, otherwise:
   - Issues with "tech-debt" label → P2
   - Issues with "bug" label or "fix" in title → P1
   - Issues with "security" in title/body → P0
   - Everything else → P2
4. **Check if it's already fixed**: Look for merged PRs that reference the issue
   ```bash
   gh pr list --state merged --search "closes #NNN OR fixes #NNN" --limit 5
   ```
   If a merged PR exists, close the issue and skip it.

### 4. Show the plan

Print a table of what will be added:

```
═══════════════════════════════════════════
  Pipeline Drain: v0.4.3
  
  New issues to add:
  #715  P2  tech-debt  HTML-escape CSRF token value
  #716  P2  tech-debt  Log warning for bare except
  #717  P2  tech-debt  Unify GET/POST context processor pattern
  #718  P2  tech-debt  Python integration test for DATE_FORMAT
  
  Already in milestone: 8
  Already fixed (will close): 0
  Skipped (different milestone): 0
═══════════════════════════════════════════
```

If `--dry-run`, stop here.

### 5. Update ROADMAP.md

For each new issue, add a row to the Priority Matrix table:

```markdown
| **P2** | <issue title> (#NNN) | <one-line description from issue body> | vX.Y.Z |
```

Also add an entry to the milestone's detail section:

```markdown
**#NNN — <issue title>** — <first paragraph of issue body, truncated to 200 chars>
```

### 6. Update milestone detail section

Add new entries to the milestone section in ROADMAP.md, following the existing
format (bold issue number + title, em-dash, description).

### 7. Commit the ROADMAP update

```bash
git add ROADMAP.md
git commit -m "$(cat <<'EOF'
docs(roadmap): add N open issues to vX.Y.Z milestone

Audit-bypass-reason: docs-only ROADMAP update via pipeline-drain skill (no retro needed)
EOF
)"
git push origin main
```

### 8. Run the pipeline

Invoke the pipeline-run skill with the milestone:

```
/pipeline-run --milestone vX.Y.Z --all
```

This will:
1. Pick the next unprocessed task via pipeline-next
2. Run all stages (with gate checks)
3. Repeat until all tasks are done
4. Print the milestone summary

### 9. Handle "close without code" issues

During pipeline-run, if an issue is investigated and found to not need code:
- The gate check's close-without-code path handles this
- The issue is closed with a comment
- The ROADMAP entry is marked as closed (not ✅, but ~~strikethrough~~ with reason)

### 10. Post-drain summary

After all issues are processed, print:

```
═══════════════════════════════════════════
  Drain Complete: vX.Y.Z
  
  Issues processed: N
  PRs merged: N (#list)
  Closed without code: N (#list)
  Failed: N (#list)
  
  Remaining open issues: N
═══════════════════════════════════════════
```

If remaining open issues > 0, suggest running `/pipeline-drain` again or
creating a new milestone.

## Audit-driven drain: pre-staged work-graph recipe

When a milestone starts from an audit document that catalogs weaknesses and
files issues, the drain takes a different shape than the default
"discover → triage → process" flow. The audit is the entry point, not the
drain script. This recipe documents that shape.

**When this shape applies**: the issues come from an audit doc
(`docs/audits/` or `docs/<subsystem>/AUDIT-YYYY-MM-DD.md`). Sweet spot is
3-7 issues touching the same subsystem. Below 3, audit overhead dominates;
above 7, the drain PR becomes too big to review. Each issue should be < 1 day
of effort. Larger issues split out.

**Reference example**: v0.9.2-3 (VDOM audit #1257 → drain PR #1258).

### Step A — File issues before the audit-doc PR

```
gh issue create --label tech-debt --title "tech-debt: <summary>" --body "..."
```

File all N issues BEFORE opening the audit-doc PR. The audit doc can then
link real issue numbers (no TBD backfill). The milestone entry in ROADMAP.md
uses live numbers from day one.

### Step B — Open the milestone in the audit-doc PR

Single docs-only PR that adds:
- `docs/<subsystem>/AUDIT-YYYY-MM-DD.md` (the audit document)
- ROADMAP.md milestone entry (linked to the pre-filed issues)
- CHANGELOG.md note (audit added, not a user-facing change)

### Step C — Drain via grouped PR

```
/pipeline-drain --milestone vX.Y.Z-N --group --all
```

The drain script picks up the pre-staged issues from ROADMAP.md and groups
them into a single implementation PR. This is faster than N separate small PRs
because:
- Issues are pre-staged and contextualized in the audit doc.
- Stage 4 VERIFY LITERAL API CONTRACTS catches audit drift on first-use.
- Stage 7 / Stage 8 reviews can spot-check audit claims rather than
  re-deriving from scratch.

### Step D — Single retro covers both PRs

Run `/pipeline-retro --milestone vX.Y.Z-N`. The audit PR + drain PR are one
coherent unit; the retro synthesizes across both.

## Integration

This skill is the top-level orchestrator:
1. **pipeline-drain** discovers and triages issues
2. **pipeline-next** (called by pipeline-run) picks tasks and creates state files
3. **pipeline-run** executes each task through all stages
4. **pipeline-retro** (called manually after) writes the milestone retrospective

The user's workflow becomes:
```
/pipeline-drain --milestone v0.4.3
# ... wait for everything to complete ...
/pipeline-retro --milestone v0.4.3
# then cut a release with your repo's own release tooling:
#   git tag v0.4.3 && git push --tags
#   (or /your-release-skill 0.4.3 if you have one)
```
