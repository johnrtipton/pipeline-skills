# Pipeline Skill ROADMAP

## Priority Matrix

Active, selectable work. Priorities are a heuristic starting point — adjust freely.

| Priority | Feature | Why | Milestone |
|----------|---------|-----|-----------|
| **P1** | runnable pipeline gates script | Extract pipeline-run Gates 1-4 + the retro gate into `scripts/pipeline-gates.sh`, removing the dangling canonical reference (#28) | v0.3.0 |
| **P1** | template structure validator | A `make` target that validates `templates/*.json` parse and have the required per-type stage shape (the pipeline-init verify step, as a committed check) | v0.3.0 |
| **P1** | CI workflow running the gates | GitHub Actions runs `make check` + the gates + template validation on every PR, so enforcement stops being manual | v0.3.0 |

_Chosen via strategy session [2026-06-04-v0-2-end](docs/strategy-sessions/2026-06-04-v0-2-end.md) (Path 1 — Runnable gates first). See [ADR-0001](docs/adr/0001-executable-quality-gates.md)._

## Milestones

### Milestone: v0.3.0 — Executable gates + CI

**runnable pipeline gates script**
Extract pipeline-run's MANDATORY Post-Commit Programmatic Gates (Gate 1 changelog-boundary, Gate 2 docs-only, Gate 3 3-clean-runs, Gate 4 retro artifact) plus the pipeline-ship pre-merge gate into `scripts/pipeline-gates.sh` — one shell function per gate, parameterized by the detected default branch and test command. Update the skills to reference the functions instead of inlining bash. Closes the dangling reference flagged by the #7 staleness check. Tracks issue (#28). Acceptance: `scripts/pipeline-gates.sh` exists with one function per gate; pipeline-run/pipeline-ship reference it.

**template structure validator**
Add a `make validate-templates` target (and `scripts/validate-templates.sh`) that checks every `templates/*.json` parses and has `pipeline_type` + `stages` keyed `"1".."N"` in order, each with `name`/`status`/`verdict`/`checklist` — the verify step `pipeline-init` describes, committed as a runnable check. Acceptance: the target passes on the current templates and fails on a malformed one.

**CI workflow running the gates**
Add `.github/workflows/ci.yml` that runs `make check`, the gates script, and template validation on every PR and push, so the quality machinery is enforced automatically rather than via a manual `make check`. Acceptance: CI is green on a conforming PR and red when a branch literal or malformed template is introduced.


## Completed

- v0.2.0 — Pipeline hardening: branch-agnostic `run_auto` + literal guard (#11, #18, PR #21); three-dot diff mandate in pipeline-ship (#17, PR #22); lint scope-discipline + per-task coverage expectation (#5, #9, PR #23); hard programmatic retro-stage gate (#8, PR #24); pre-drain symbol staleness check (#7, PR #25); PR `#TBD` placeholder substitution (#6, PR #26). ✅ Shipped
- v0.1.0 — Branch-agnostic pipeline family + vendored, hardened `pipeline-init` (PR #10). ✅ Shipped
- v0.1.0 — Documented `/pipeline-init` across README, CLAUDE.md, and install.sh (PRs #12, #13, #14). ✅ Shipped
- v0.1.0 — Stage-5 enumerated-unit inventory gate in pipeline-shared + all four templates (PR #15). ✅ Shipped
- Foundation — instruction-rot rationale, learning-channel design, retro-artifact gate (PRs #1, #2). ✅ Shipped

## Future

- **v0.4.0 — Drift guards** (deferred from the 2026-06-04 strategy session, Path 2 / Cluster C; easier once the v0.3.0 CI harness exists to hang it on): a SKILL.md bash-snippet self-test harness for branch-resolution-chain drift; a flexion-plugin sync check (published copy vs canonical `skills/`); and tightening `check-branch-literals.sh` against backtick prose (#29, Action Tracker #7). Promote to the Priority Matrix when v0.3.0 closes.

## Contributing

Active work lives under `## Milestones` with a matching Priority Matrix row (byte-identical feature name). Shipped work moves to `## Completed`. `/pipeline-next` reads this file; keep the matrix header columns `Priority | Feature | Why | Milestone` and put milestones under a non-reserved `## ` heading.
