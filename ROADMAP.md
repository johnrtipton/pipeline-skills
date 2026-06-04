# Pipeline Skill ROADMAP

## Priority Matrix

Active, selectable work. Priorities are a heuristic starting point — adjust freely.

| Priority | Feature | Why | Milestone |
|----------|---------|-----|-----------|
| **P1** | run_auto branch-agnostic auto-mode naming | `pipeline.py` `run_auto` still hard-codes `else "main"` for auto-mode branch naming while every skill now resolves the default branch dynamically (#11) | v0.2.0 |
| **P1** | retro-stage programmatic enforcement gate | Harden `pipeline-run` retro-stage enforcement with a programmatic gate, mirroring the pipeline-ship pre-merge gate (#8) | v0.2.0 |
| **P2** | per-task test-coverage expectation at selection | `pipeline-next` should surface a per-task test-coverage expectation at selection time so coverage isn't an afterthought (#9) | v0.2.0 |
| **P2** | pre-drain symbol staleness check | `pipeline-next`/`pipeline-drain` should verify cited symbols exist in the codebase before queuing an issue (#7) | v0.2.0 |
| **P2** | leave pre-existing lint untouched in scoped PRs | Canonicalize the rule that scoped PRs do not fix unrelated pre-existing lint (#5) | v0.2.0 |
| **P3** | automate PR placeholder substitution in docs commits | Automate `PR #TBD` placeholder substitution in docs commits so merged PRs get their real number (#6) | v0.2.0 |

## Milestones

### Milestone: v0.2.0 — Pipeline hardening

**run_auto branch-agnostic auto-mode naming**
Make `pipeline.py` `run_auto` resolve the repo default branch the same way the skills do (pipeline-config `default_branch` → `origin/HEAD` → `git remote show origin` → fallback) instead of the literal `else "main"` at `pipeline.py:798`. Tracks issue (#11). Acceptance: no `"main"` literal remains in `run_auto`; auto-mode branch naming uses the detected branch.

**retro-stage programmatic enforcement gate**
Add a programmatic gate to `pipeline-run` that physically blocks completion until the retro stage has produced its artifact, mirroring the pipeline-ship pre-merge gate in `skills/pipeline-ship/SKILL.md`. Tracks issue (#8). Acceptance: a run cannot report complete without a retro artifact on the PR.

**per-task test-coverage expectation at selection**
Have `skills/pipeline-next/SKILL.md` surface an expected test-coverage note for the selected task at selection time, so the implementing agent knows the coverage bar before Stage 1. Tracks issue (#9).

**pre-drain symbol staleness check**
Before `pipeline-drain` queues an issue, verify every code symbol the issue cites still exists in the codebase (a pre-drain staleness check shared with `pipeline-next`). Tracks issue (#7). Acceptance: issues citing removed symbols are flagged, not silently queued.

**leave pre-existing lint untouched in scoped PRs**
Canonicalize, in `skills/pipeline-shared/SKILL.md`, that a scoped PR does not fix unrelated pre-existing lint warnings — keep the diff scoped. Tracks issue (#5).

**automate PR placeholder substitution in docs commits**
Add tooling so a docs commit written with a `PR #TBD` placeholder gets the real PR number substituted after creation. Tracks issue (#6).

## Completed

- v0.1.0 — Branch-agnostic pipeline family + vendored, hardened `pipeline-init` (PR #10). ✅ Shipped
- v0.1.0 — Documented `/pipeline-init` across README, CLAUDE.md, and install.sh (PRs #12, #13, #14). ✅ Shipped
- v0.1.0 — Stage-5 enumerated-unit inventory gate in pipeline-shared + all four templates (PR #15). ✅ Shipped
- Foundation — instruction-rot rationale, learning-channel design, retro-artifact gate (PRs #1, #2). ✅ Shipped

## Future

- Publish/track the flexion plugin copy in lockstep with the canonical skills.
- A self-test harness that lints every `skills/*/SKILL.md` bash snippet for the branch-resolution chain drift.

## Contributing

Active work lives under `## Milestones` with a matching Priority Matrix row (byte-identical feature name). Shipped work moves to `## Completed`. `/pipeline-next` reads this file; keep the matrix header columns `Priority | Feature | Why | Milestone` and put milestones under a non-reserved `## ` heading.
