# Pipeline Skill ROADMAP

## Priority Matrix

Active, selectable work. Priorities are a heuristic starting point — adjust freely.

| Priority | Feature | Why | Milestone |
|----------|---------|-----|-----------|
| **P1** | fix detect_default_branch foreign-repo bug | `pipeline.py detect_default_branch` returns `main` for a `master`-default repo with no `origin/HEAD`; add the local-branch probe + current-branch fallback the pipeline-init SKILL chain already documents (#45) | v0.6.0 |
| **P1** | fuller end-to-end foreign-repo validation | v0.5.0 validation skipped the PR-dependent stages (no remote); run a real throwaway GitHub repo through `init → next → run → retro` including Commit/Review/Merge | v0.6.0 |
| **P2** | flip ADR statuses to Accepted | ADR-0001 (executable gates) and ADR-0002 (outward pivot) are implemented and in force but still marked Proposed — the ADR-status drift the pipeline-shared Documentation stage flags | v0.6.0 |

_Chosen via strategy session [2026-06-04-v0-5-end](docs/strategy-sessions/2026-06-04-v0-5-end.md) (Path 1 — Follow through). Continues ADR-0002; no new ADR._

## Milestones

### Milestone: v0.6.0 — Follow through on the pivot

**fix detect_default_branch foreign-repo bug**
Bring `pipeline.py detect_default_branch` to parity with the pipeline-init SKILL's documented chain: after the CLAUDE.md / `origin/HEAD` / `git remote show` probes, add a local-branch probe (`git rev-parse --verify` for main/master/development) and a current-branch fallback before the literal `main`. Tracks issue (#45). Acceptance: on a `master`-default repo with no `origin`, it returns `master`, not `main`.

**fuller end-to-end foreign-repo validation**
Create a throwaway GitHub repo (ideally `master`-default / non-python), run the full family — `/pipeline-init`, `/pipeline-next`, `/pipeline-run`, `/pipeline-retro` — including the PR-dependent stages (Commit & PR, Code Review, Merge) that the v0.5.0 local-only validation could not exercise. Append to the `docs/validation/` report; file any new gaps as issues. Acceptance: a report covering the PR stages exists.

**flip ADR statuses to Accepted**
Update ADR-0001 and ADR-0002 from `Proposed` to `Accepted — implemented in <versions>` (0001 in v0.3.0; 0002 in v0.5.0). Acceptance: no in-force ADR is left marked Proposed.

## Completed` for v0.5.0._

## Completed` for v0.4.0._

## Completed

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
