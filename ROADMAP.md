# Pipeline Skill ROADMAP

## Priority Matrix

Active, selectable work. Priorities are a heuristic starting point — adjust freely.

| Priority | Feature | Why | Milestone |
|----------|---------|-----|-----------|
| **P1** | pipeline-cycle orchestrator skill | The missing outer loop: a human drove strategy→run→retro→strategy ~20x by hand across 6 milestones. Add `/pipeline-cycle` that chains them — semi-autonomous by default, stopping at strategy decisions + on failure (per ADR-0003) | v0.7.0 |
| **P1** | pipeline-cycle --auto full-autonomy flag | An explicit opt-in flag that auto-confirms strategy (light mode) and drives to the terminal state with no human gate — deliberate, never the default | v0.7.0 |
| **P2** | terminal-state detector | The cycle's stop condition: clean = 0 open issues + 0 active ROADMAP tasks + no `Proposed` ADR + CI green | v0.7.0 |

_Chosen via strategy session [2026-06-04-self-driving-loop](docs/strategy-sessions/2026-06-04-self-driving-loop.md). Directional — see [ADR-0003](docs/adr/0003-loop-autonomy-boundary.md)._

## Milestones

### Milestone: v0.7.0 — Self-driving the loop

**pipeline-cycle orchestrator skill**
Add `skills/pipeline-cycle/SKILL.md`: a state-file-driven outer loop that runs `/pipeline-strategy` → (if a milestone is captured) `/pipeline-run --milestone <v> --all` → `/pipeline-retro` → back to strategy. **Default is semi-autonomous**: it runs execution autonomously but STOPS and hands control to the human at every `/pipeline-strategy` Stage-7 path decision, and on any stage failure. Loop terminates when the terminal-state detector reports clean OR strategy's brainstorm yields no pass-tagged candidates. Per ADR-0003. Acceptance: the skill exists and is installed; **adding it updates the README skill table, the CLAUDE.md Key-components list, and install.sh** (the Stage-5 enumerated-unit inventory gate); a dry-run shows the loop structure without executing.

**pipeline-cycle --auto full-autonomy flag**
Add a `--auto` flag to `/pipeline-cycle` that runs `/pipeline-strategy` in auto-confirm (light) mode throughout, removing the human gate so the loop drives to the terminal state hands-off. This is a deliberate opt-in, NOT the default. Acceptance: without `--auto` the loop pauses at strategy decisions; with `--auto` it auto-confirms the recommended path and continues; ADR-0003 documents the trade-off.

**terminal-state detector**
Add a check (script or `make` target) that reports the repo's "clean" terminal state: 0 open issues, 0 active ROADMAP tasks (parser), no ADR left at `Proposed`, CI green. `/pipeline-cycle` uses it as the stop condition. Acceptance: it reports clean on the current repo state and not-clean when any condition fails.

## Completed` for v0.6.0._

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
