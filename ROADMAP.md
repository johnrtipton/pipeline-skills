# Pipeline Skill ROADMAP

## Priority Matrix

Active, selectable work. Priorities are a heuristic starting point — adjust freely.

| Priority | Feature | Why | Milestone |
|----------|---------|-----|-----------|
| **P1** | validate the family on a foreign repo | The family has only ever been dogfooded; the one externally-sourced bug (#36) proved real external use finds what self-use misses. Run pipeline-init→next→run→retro end-to-end on a non-`main`/non-python repo and capture every gap as an issue | v0.5.0 |
| **P1** | adoption quickstart for external repos | After 4 milestones there is no guide for adopting the family in someone else's repo; write one and verify `pipeline-init` on a fresh clone | v0.5.0 |
| **P2** | release process and first tags | 0 git tags after 4 milestones — nothing is consumable/versioned; establish a tagging + release flow and cut the first tag | v0.5.0 |
| **P3** | untracked-files gap in worktree-restore reflex | `git restore` doesn't remove untracked files a subagent leaves (#40) | v0.5.0 |

_Chosen via strategy session [2026-06-04-v0-4-end](docs/strategy-sessions/2026-06-04-v0-4-end.md) (Path 2 — Outward pivot). See [ADR-0002](docs/adr/0002-outward-pivot.md)._

## Milestones

### Milestone: v0.5.0 — Outward pivot

**validate the family on a foreign repo**
Take a real repository that is NOT this one — ideally `master`-default and/or non-python — and run the full family end-to-end: `/pipeline-init`, then `/pipeline-next`, `/pipeline-run`, `/pipeline-retro`. Record every place the family assumes pipeline-skill's own conventions, branch, or language. File each gap as an issue. The deliverable is a validation report under `docs/` + the issues, not a green checkmark. Tracks the twice-deferred broaden-dogfooding candidate. Acceptance: a foreign-repo run report exists and any blocking gaps are filed.

**adoption quickstart for external repos**
Write `docs/adoption.md` (or a README section) that walks an external user from clone to first shipped PR: install the skills, run `/pipeline-init`, what the pipeline-config block means, the next→run→retro loop. Verify the steps against a fresh clone. Acceptance: a new user can follow it without reading the skill internals.

**release process and first tags**
Define how this repo versions and releases (it has 0 tags despite 4 shipped milestones). Document the flow (tag `vX.Y.Z` at milestone close, what the tag includes) and cut the first tag retroactively for the shipped milestones. Acceptance: `git tag` is non-empty and a release process is documented.

**untracked-files gap in worktree-restore reflex**
Extend the #36 worktree-restore reflex (pipeline-run + template prompts) to also clear untracked files a subagent leaves — a guarded `git clean -fd` or a post-restore re-check — so a build/scp after a subagent can't pick up stray files. Tracks issue (#40).

## Completed` for v0.4.0._

## Completed

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
