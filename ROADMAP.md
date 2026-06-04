# Pipeline Skill ROADMAP

## Priority Matrix

Active, selectable work. Priorities are a heuristic starting point — adjust freely.

| Priority | Feature | Why | Milestone |
|----------|---------|-----|-----------|
| **P1** | review-subagent worktree restore | Code Review subagents leave the executor's working tree on `main`, so a following build/scp ships stale files — broke a base-image build in djustlive across 5 PRs (#36) | v0.4.0 |
| **P2** | tighten check-branch-literals regex | The `check-branch-literals.sh` diff/rev-parse pattern can false-positive on backtick-wrapped prose like `git diff origin/main` (#29) | v0.4.0 |

## Milestones

### Milestone: v0.4.0 — Drift guards

**review-subagent worktree restore**
A Code Review (or any read-only) subagent that runs `git checkout`/`git diff origin/main...HEAD` to read a PR diff must restore the executor's working tree on exit — `git checkout <original-branch>` (or `git restore --source=HEAD --staged --worktree`) — leaving the tree exactly as found. Add this to the Code Review stage `subagent_prompt` in the feature/bugfix/refactor/ship templates, and add an executor reflex to `skills/pipeline-run/SKILL.md`: re-verify `git status --porcelain` is clean and `git rev-parse HEAD` matches the state file's expected commit before any build/scp/ship that follows a subagent. Tracks issue (#36). Acceptance: the template prompts include the restore step; pipeline-run documents the pre-build worktree==HEAD reflex.

**tighten check-branch-literals regex**
Tighten the `git (diff|rev-parse)...origin/(main|master)` alternative in `scripts/check-branch-literals.sh` so a backtick-wrapped inline-code prose example does not false-positive — anchor on actual command context / fenced bash, not inline code. Tracks issue (#29). Acceptance: a doc line containing inline `git diff origin/main` does not trip the guard; real command-line literals still do.

## Completed

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
