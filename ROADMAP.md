# Pipeline Skill ROADMAP

## Priority Matrix

Active, selectable work. Priorities are a heuristic starting point — adjust freely.

| Priority | Feature | Why | Milestone |
|----------|---------|-----|-----------|

_No active tasks — v0.3.0 shipped (PRs #32–#34). Next milestone: v0.4.0 "Drift guards" (see `## Future`); run `/pipeline-strategy` to promote it._

## Milestones

_No active milestone. See `## Completed` for v0.3.0 and `## Future` for the v0.4.0 backlog._

## Completed

- v0.3.0 — Executable gates + CI: runnable `scripts/pipeline-gates.sh` (#28, PR #32); template structure validator + `make validate-templates` (PR #33); GitHub Actions CI enforcing the gates (PR #34). Established ADR-0001. ✅ Shipped

- v0.2.0 — Pipeline hardening: branch-agnostic `run_auto` + literal guard (#11, #18, PR #21); three-dot diff mandate in pipeline-ship (#17, PR #22); lint scope-discipline + per-task coverage expectation (#5, #9, PR #23); hard programmatic retro-stage gate (#8, PR #24); pre-drain symbol staleness check (#7, PR #25); PR `#TBD` placeholder substitution (#6, PR #26). ✅ Shipped
- v0.1.0 — Branch-agnostic pipeline family + vendored, hardened `pipeline-init` (PR #10). ✅ Shipped
- v0.1.0 — Documented `/pipeline-init` across README, CLAUDE.md, and install.sh (PRs #12, #13, #14). ✅ Shipped
- v0.1.0 — Stage-5 enumerated-unit inventory gate in pipeline-shared + all four templates (PR #15). ✅ Shipped
- Foundation — instruction-rot rationale, learning-channel design, retro-artifact gate (PRs #1, #2). ✅ Shipped

## Future

- **v0.4.0 — Drift guards** (deferred from the 2026-06-04 strategy session, Path 2 / Cluster C; easier once the v0.3.0 CI harness exists to hang it on): a SKILL.md bash-snippet self-test harness for branch-resolution-chain drift; a flexion-plugin sync check (published copy vs canonical `skills/`); and tightening `check-branch-literals.sh` against backtick prose (#29, Action Tracker #7). Promote to the Priority Matrix when v0.3.0 closes.

## Contributing

Active work lives under `## Milestones` with a matching Priority Matrix row (byte-identical feature name). Shipped work moves to `## Completed`. `/pipeline-next` reads this file; keep the matrix header columns `Priority | Feature | Why | Milestone` and put milestones under a non-reserved `## ` heading.
