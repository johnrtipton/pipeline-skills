# Pipeline Skill — Retrospectives

## Action Tracker

Items from retrospectives that need resolution. Every item must have a GitHub
issue or be explicitly closed with a reason.

| # | Action | Source | GitHub | Status | Notes |
|---|--------|--------|--------|--------|-------|
| 1 | pipeline-ship: mandate three-dot diff in Inventory/Self-Review/Stage-7 (behind-base phantom-deletion trap) | Retro v0.1.0 / PR #10 | #17 | Open | |
| 2 | Guard against reintroduced hard-coded `origin/main` / `master` / `else "main"` branch literals | Retro v0.1.0 / PR #10 | #18 | Open | |
| 3 | run_auto branch-agnostic auto-mode naming (`pipeline.py:798`) | PR #10 | #11 | Open | Also ROADMAP v0.2.0 |
| 4 | Stage-5 enumerated-unit inventory gate (README/CLAUDE.md/install.sh rot) | PRs #12–#15 | — | Closed | Resolved in PR #15 — `pipeline-shared` step 4.5 + feature/bugfix/refactor/ship templates |
| 5 | Self-initialize the pipeline-skill repo (no ROADMAP/RETRO/config existed) | Retro v0.1.0 | — | Closed | Resolved in PR #16 — ROADMAP, RETRO, CHANGELOG, pipeline-config block |

<!-- Milestone retro entry template:
## <milestone> — <Title> (PRs #NN–#MM)
**Date**: YYYY-MM-DD · **Quality**: N/5
### What We Learned
**1. Finding.** … **Action taken**: diff | skill_update | tracker_row | closed
### Insights
### Review Stats
### Open Items
-->

## v0.1.0 — Branch-agnostic family + self-bootstrap (PRs #10, #12, #13, #14, #15, #16)

**Date**: 2026-06-04
**Scope**: Made the entire `pipeline-*` family branch-agnostic, vendored & hardened `pipeline-init`, documented it across every inventory surface, added a Stage-5 documentation gate, and finally bootstrapped this repo with its own pipeline scaffolding.
**Tests at close**: n/a — standalone stdlib script, no test suite (CLAUDE.md).

### What We Learned

**1. Two-dot diffs lie when a branch is behind its base.**
During PR #10's ship, Stage 1 inventory ran `git diff origin/main..HEAD` (two-dot) on a branch 3 commits behind `origin/main` (merge-base `d0f7494`). It rendered base-added content — the pipeline-ship Pre-Merge Gate and pipeline-drain Step 8.5, added on `main` after the branch forked — as ~90 phantom deletions, looking as if the PR reverted safety gates. The three-dot diff (`origin/main...HEAD`, 984/13) and `git merge-tree` (0 conflicts) proved the gates were untouched; both were confirmed present on `main` post-merge. A wrong "this PR reverts gates" conclusion was one assumption away.

**Action taken**: Open — tracked in Action Tracker #1 (GitHub #17).

**2. Adding a skill silently rots every inventory surface.**
`pipeline-init` landed in PR #10 but the README skill table, CLAUDE.md Key-components list, and install.sh completion echo all hardcode the skill list and went stale. The gap surfaced one file at a time (PRs #12, #13, #14) because nothing tied the surfaces together, and pipeline-ship's `DOCS_ONLY` classification let Stage 5 self-satisfy without checking index docs.

**Action taken**: skill_update — added Stage-5 step "4.5 Enumerated-unit inventories" to `skills/pipeline-shared/SKILL.md` (with a grep recipe + "DOCS_ONLY does not exempt this") and a matching Documentation checklist item to the feature/bugfix/refactor/ship templates (PR #15).

**3. The harness script lagged the skills it ships.**
All six skills became branch-agnostic in PR #10, but `pipeline.py` `run_auto` still hard-codes `else "main"` for auto-mode branch naming (`pipeline.py:798`) — so the family is only partially branch-independent, and nothing guards against a future literal sneaking back in.

**Action taken**: Open — tracked in Action Tracker #3 (GitHub #11) for the fix, and #2 (GitHub #18) for the reintroduction guard.

**4. The tool repo wasn't dogfooding itself.**
`/pipeline-retro` could not start: the repo had no `RETRO.md`, `ROADMAP.md`, version scheme, or `CLAUDE.md` pipeline-config block — the very scaffolding the family assumes. Cobbler's children with no shoes.

**Action taken**: diff — ran `/pipeline-init` on the repo (PR #16): conforming ROADMAP (parser-verified, 6 tasks, 0 phantoms), RETRO Action Tracker, CHANGELOG, pipeline-config block, support dirs. Adapted to skip `.pipeline-templates/` since this repo *is* the canonical template source.

### Insights

- **The capture-everything-block-nothing channel worked in real time.** One substantive PR (#10) spawned a clean cascade of scoped follow-ups (#11 issue, #12–#14 doc fixes, #15 systemic gate, #16 self-init) instead of one sprawling PR or a pile of lost findings.
- **Evidence beat assumption.** The three-dot/`merge-tree` verification caught a convincing false positive before it drove a wrong action — the discipline paid for itself once already.
- **Dogfooding found what docs missed.** Running the tool on its own repo immediately exposed an onboarding gap (no scaffolding) that the README never flagged.

### Review Stats

| Metric | PR #10 | PR #12–14 | PR #15 | PR #16 | Total |
|--------|--------|-----------|--------|--------|-------|
| Tests added | 0 (no suite) | 0 | 0 | 0 | 0 |
| 🔴 Findings | 0 | 0 | 0 | 0 | 0 |
| 🟡 / process findings | 2 | 0 | 0 | 0 | 2 |
| Findings fixed in-branch | 2 | — | — | — | 2 |
| Deferred to issue | 1 (#11) | 0 | — | — | 1 |
| False positives caught | 1 | 0 | 0 | 0 | 1 |
| Re-review rounds | 0 | 0 | 0 | 0 | 0 |

### Process Improvements Applied

**CLAUDE.md**: added `pipeline-init` to Key components (PR #13); added the `<!-- pipeline-config -->` block (PR #16).
**Pipeline template**: enumerated-unit inventory checklist item added to feature/bugfix/refactor/ship Documentation stages (PR #15).
**Skills**: `pipeline-shared` Stage-5 step 4.5 (PR #15); branch-agnostic resolution chain across all six skills (PR #10).
**Repo**: self-initialized — ROADMAP/RETRO/CHANGELOG/config scaffolding (PR #16).

### Open Items

- [ ] Mandate three-dot diff in pipeline-ship — Action Tracker #1 (GitHub #17)
- [ ] Branch-literal reintroduction guard — Action Tracker #2 (GitHub #18)
- [ ] `run_auto` branch-agnostic naming — Action Tracker #3 (GitHub #11)
