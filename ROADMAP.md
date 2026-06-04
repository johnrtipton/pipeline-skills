# Pipeline Skill ROADMAP

## Priority Matrix

Active, selectable work. Priorities are a heuristic starting point — adjust freely.

| Priority | Feature | Why | Milestone |
|----------|---------|-----|-----------|

_No active tasks — v0.6.0 shipped (PRs #53–#55). No open issues. Larger drift-guard ideas remain in `## Future`; run `/pipeline-strategy` to plan v0.7.0._

## Milestones

_No active milestone. See `## Completed` for v0.6.0._

## Completed` for v0.5.0._

## Completed` for v0.4.0._

## Completed

- v0.6.0 — Follow through on the pivot: fixed detect_default_branch for master/no-origin repos (#45, PR #53); end-to-end foreign-repo validation incl. PR stages on a real master/Node repo (PR #55); flipped ADR-0001/0002 to Accepted (PR #54). ✅ Shipped

- v0.5.0 — Outward pivot (ADR-0002): foreign-repo validation surfaced branch-detection bug #45 (PR #46); adoption quickstart `docs/adoption.md` (PR #47); release process + first tags v0.1.0–v0.4.0 (PR #48); worktree-restore reflex clears untracked files (#40, PR #49). ✅ Shipped

- v0.4.0 — Drift guards: review subagents restore HEAD on exit + executor worktree-restore reflex (#36, PR #39); branch-literal guard ignores backtick prose (#29, PR #41). ✅ Shipped

- v0.3.0 — Executable gates + CI: runnable `scripts/pipeline-gates.sh` (#28, PR #32); template structure validator + `make validate-templates` (PR #33); GitHub Actions CI enforcing the gates (PR #34). Established ADR-0001. ✅ Shipped

- v0.2.0 — Pipeline hardening: branch-agnostic `run_auto` + literal guard (#11, #18, PR #21); three-dot diff mandate in pipeline-ship (#17, PR #22); lint scope-discipline + per-task coverage expectation (#5, #9, PR #23); hard programmatic retro-stage gate (#8, PR #24); pre-drain symbol staleness check (#7, PR #25); PR `#TBD` placeholder substitution (#6, PR #26). ✅ Shipped
- v0.1.0 — Branch-agnostic pipeline family + vendored, hardened `pipeline-init` (PR #10). ✅ Shipped
- v0.1.0 — Documented `/pipeline-init` across README, CLAUDE.md, and install.sh (PRs #12, #13, #14). ✅ Shipped
- v0.1.0 — Stage-5 enumerated-unit inventory gate in pipeline-shared + all four templates (PR #15). ✅ Shipped
- Foundation — instruction-rot rationale, learning-channel design, retro-artifact gate (PRs #1, #2). ✅ Shipped

## Future

- **Larger drift guards** (Cluster C remainder, not yet broken into issues — promote via a future `/pipeline-strategy`): a SKILL.md bash-snippet self-test harness for branch-resolution-chain drift, and a flexion-plugin sync check (published copy vs canonical `skills/`). (The two concrete drift issues, #36 and #29, were promoted into the v0.4.0 milestone above.)

## Contributing

Active work lives under `## Milestones` with a matching Priority Matrix row (byte-identical feature name). Shipped work moves to `## Completed`. `/pipeline-next` reads this file; keep the matrix header columns `Priority | Feature | Why | Milestone` and put milestones under a non-reserved `## ` heading.
