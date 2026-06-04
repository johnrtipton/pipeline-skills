# Pipeline Skill — Retrospectives

## Action Tracker

Items from retrospectives that need resolution. Every item must have a GitHub
issue or be explicitly closed with a reason.

| # | Action | Source | GitHub | Status | Notes |
|---|--------|--------|--------|--------|-------|
| 1 | pipeline-ship: mandate three-dot diff in Inventory/Self-Review/Stage-7 (behind-base phantom-deletion trap) | Retro v0.1.0 / PR #10 | #17 | Closed | Resolved in PR #22 (v0.2.0) |
| 2 | Guard against reintroduced hard-coded `origin/main` / `master` / `else "main"` branch literals | Retro v0.1.0 / PR #10 | #18 | Closed | Resolved in PR #21 (v0.2.0) — `make check` / check-branch-literals.sh |
| 3 | run_auto branch-agnostic auto-mode naming (`pipeline.py:798`) | PR #10 | #11 | Closed | Resolved in PR #21 (v0.2.0) — `detect_default_branch()` |
| 4 | Stage-5 enumerated-unit inventory gate (README/CLAUDE.md/install.sh rot) | PRs #12–#15 | — | Closed | Resolved in PR #15 — `pipeline-shared` step 4.5 + feature/bugfix/refactor/ship templates |
| 5 | Self-initialize the pipeline-skill repo (no ROADMAP/RETRO/config existed) | Retro v0.1.0 | — | Closed | Resolved in PR #16 — ROADMAP, RETRO, CHANGELOG, pipeline-config block |
| 6 | Consolidate pipeline-run inline gates into `scripts/pipeline-gates.sh` (dangling canonical reference) | Retro v0.2.0 / PR #24 | #28 | Open | |
| 7 | `check-branch-literals.sh` diff/rev-parse regex can false-positive on backtick-wrapped prose | Retro v0.2.0 / PR #21 | #29 | Open | Latent — no current trigger |

<!-- Milestone retro entry template:
## <milestone> — <Title> (PRs #NN–#MM)
**Date**: YYYY-MM-DD · **Quality**: N/5
### What We Learned
**1. Finding.** … **Action taken**: diff | skill_update | tracker_row | closed
### Insights
### Review Stats
### Open Items
-->

## v0.2.0 — Pipeline hardening (PRs #21–#26)

**Date**: 2026-06-04
**Scope**: Drained 8 issues — completed the branch-agnostic effort (harness + regression guard), added the three-dot diff mandate, a hard retro-stage gate, lint scope-discipline, per-task coverage expectation, a pre-drain staleness check, and PR `#TBD` substitution tooling.
**Tests at close**: n/a — no test suite (CLAUDE.md). Verification = `make check` + script self-tests + 2 subagent reviews.

### What We Learned

**1. The branch-agnostic effort is now complete and self-guarding.**
All three open v0.1.0 actions shipped this milestone: `run_auto` resolved via `detect_default_branch()` (#11→PR #21), the reintroduction guard via `make check` (#18→PR #21), and the three-dot mandate in pipeline-ship (#17→PR #22). The harness no longer lags the skills, and `make check` ran green on every subsequent PR — the guard is already doing its job.

**Action taken**: closed — Action Tracker #1, #2, #3 closed (PRs #21, #22).

**2. The gate canon references a script that doesn't exist.**
pipeline-run's Gates 1–4 (including the retro gate added in #8/PR #24) are documented as inline bash, but the skill says they "should live in `scripts/pipeline-gates.sh`" — which isn't in the repo. The very staleness check shipped this milestone (#7) is designed to catch exactly this kind of dangling reference. Consolidating the gates into that script would make them runnable and testable rather than copy-pasted prose.

**Action taken**: Open — tracked in Action Tracker #6 (GitHub #28).

**3. The new literal guard carries a latent false-positive.**
`check-branch-literals.sh`'s diff/rev-parse alternative only excludes backticks inside the match span, so a future inline-code prose example like `git diff origin/main` would trip it. No such line exists today — latent only — but it should be tightened before it bites.

**Action taken**: Open — tracked in Action Tracker #7 (GitHub #29).

### Insights

- **Zero retro-gate violations this milestone** (vs **4** in v0.1.0). The per-PR retro comments plus the hard Gate 4 added in PR #24 meant Stage 2 found a valid artifact on every PR — the tooling built earlier in the session enforced discipline on the work that came after it. Closed loop.
- **Verification discipline kept paying off.** Self-review and subagent review caught three real issues *before* merge: the bash-3.2 `mapfile` incompatibility in #25's first draft, the dash-leading-token grep bug in #25 (found by the subagent), and the unsafe `#TBD` auto-detect footgun in #26.
- **Grouped PRs traded review granularity for drain throughput.** #21 and #23 each bundled two issues — fine for small, tightly-coupled changes, but a grouped PR hiding a real bug would be harder to bisect. Prefer grouping only closely-related issues.
- **`make check` green-gating every PR is cheap insurance** — keep it, and grow it (see #28: fold the pipeline-run gates into the same runnable surface).

### Review Stats

| Metric | #21 | #22 | #23 | #24 | #25 | #26 | Total |
|--------|-----|-----|-----|-----|-----|-----|-------|
| Issues closed | 2 | 1 | 2 | 1 | 1 | 1 | 8 |
| Subagent reviews | 1 | 0 | 0 | 0 | 1 | 0 | 2 |
| 🔴 Findings | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Bugs caught & fixed in-PR | 0 | 0 | 0 | 0 | 1 | 1 | 2 |
| Deferred to issue | 0 | 0 | 0 | 1 | 1 | 0 | 2 (#28,#29) |
| Re-review rounds | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Tests added | 0 (no suite) | 0 | 0 | 0 | 0 | 0 | 0 |

### Process Improvements Applied

**pipeline.py**: `detect_default_branch()` resolution helper (PR #21).
**Skills**: pipeline-ship three-dot mandate + trap warning (PR #22); pipeline-shared lint scope-discipline + PR `#TBD` step 11 (PRs #23, #26); pipeline-next `coverage_expectation` step 7.5 + staleness pointer (PRs #23, #25); pipeline-run hard retro Gate 4 (PR #24); pipeline-drain staleness Step 3 (PR #25).
**Pipeline template**: three-dot mandate in ship Stage 1 & 3 checklists (PR #22).
**Tooling**: `Makefile` + `check-branch-literals.sh` (PR #21), `check-issue-symbols.sh` (PR #25), `substitute-pr-number.sh` (PR #26).

### Open Items

- [ ] Consolidate pipeline-run gates into `scripts/pipeline-gates.sh` — Action Tracker #6 (GitHub #28)
- [ ] Tighten `check-branch-literals.sh` regex against backtick prose — Action Tracker #7 (GitHub #29)

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

- [x] Mandate three-dot diff in pipeline-ship — Action Tracker #1 (GitHub #17) — resolved in v0.2.0 (PR #22)
- [x] Branch-literal reintroduction guard — Action Tracker #2 (GitHub #18) — resolved in v0.2.0 (PR #21)
- [x] `run_auto` branch-agnostic naming — Action Tracker #3 (GitHub #11) — resolved in v0.2.0 (PR #21)
