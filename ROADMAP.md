# Pipeline Skill ROADMAP

## Priority Matrix

Active, selectable work. Priorities are a heuristic starting point — adjust freely.

| Priority | Feature | Why | Milestone |
|----------|---------|-----|-----------|

_No active tasks — v0.8.0 shipped via `/pipeline-cycle --auto`. Larger drift-guard ideas remain in `## Future`._

## Milestones

_No active milestone. See `## Completed` for v0.8.0._

## Completed

- v0.8.0 — Cycle hardening (first `/pipeline-cycle --auto` run): terminal-state ignores `backlog`/`wontfix`/`someday`-labelled issues so a deferred-but-open issue can't livelock the loop (#61); flipped ADR-0003 to Accepted. ✅ Shipped

- v0.7.0 — Self-driving the loop: `/pipeline-cycle` orchestrator + `--auto` full-autonomy flag + `terminal-state` detector, all shipped in one grouped PR #59. Established ADR-0003 (the loop is human-gated at strategy decisions; full autonomy is opt-in). ✅ Shipped

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

- **Upstream candidates from downstream use** (surfaced 2026-08-18 by auditing the djust consumer repo at ~440 harness runs — 647 state files, 390 PR retros, 330 tracker rows; not yet broken into issues — promote via a future `/pipeline-strategy`). Ranked by value:

  1. **Retro-bypass audit** (#68) — port the consumer's `scripts/audit-pipeline-bypass.py` + a daily `retro-gate-audit.yml` that scans merged PRs for a missing Stage-14 retro marker. This is the single highest-value item: it is the only existing *measurement* of the family's central promise (did the executor actually run the stage?), and `CANON.md` already cites exactly this as the CI-venue worked example while the harness ships no such thing. Closes the "evals" gap named in every retro since v0.3.0.
  2. **Release stage / pipeline type** (#69) — the family stops at Merge; merged ≠ shipped. Downstream carries `RELEASING.md`, a release skill, RC trains (rc1→rc14), release branches, a pre-release security-audit workflow, and a publish path — none of it modelled. Candidate: a `release-state.json` template + `/pipeline-release`, or at minimum document the expected artifacts.
  3. **Release-line PR targeting in `/pipeline-init`** (#70) — `pr_target_branch` is honoured but init only detects the *default* branch. Downstream hand-edits all three templates to target the active dev line (`1.1`) and documents an escape hatch to the stabilization line for P0s. Candidate: detect or prompt for an active release line at init.
  4. **`OUT-OF-REPO` tracker status** (#71) — downstream invented a status for findings blocked on another repo, excluded from its own open-tracker total (41 rows, most pointing here). Needs `/pipeline-retro` support plus a `terminal-state.sh` counting rule — same class of livelock fix as the deferred-label work in v0.8.0 (#61).
  5. **`.pipeline-log.md` as a specified artifact** (#72) — both this repo and the consumer keep a one-line-per-PR ledger (issue → PR → verdict → quality score), and no skill writes it. Candidate: Stage 14 appends the line.
  6. **Drain-bucket cadence as documented canon** (#73) — downstream ROADMAP is 4,886 lines of successive drain buckets ("post-12 drain", "post-13 drain"), with only 4 strategy sessions in ~440 runs. The docs imply milestone-first planning; steady state is bucket-first. Document the real cadence.
  7. **Concurrency guidance** (#74) — ~20 agent git worktrees in flight at peak, and the two-commit CHANGELOG gate exists *because* two implementer agents collided on one checkout. `pipeline-shared` should document the worktree pattern and its hazards.
  8. **Forbidden-identifier scan as a profile feature** (#75) — generalize the consumer's Stage-7 name-leak grep (gitignored identifier list, scanned across commit subject/body, PR title/body, and full diff; any match = `REVIEW_FAILED`). Useful for any repo extracted from private client work.
  9. **Extra pipeline types invented downstream** (#76) — `investigation`, `milestone-retro`, `review-existing-pr`, plus per-run `<run>-plan.md` / `<run>-changes.txt` sidecars.
  10. **Canon-compaction guidance in CANON.md** (#77) — downstream `CLAUDE.md` reached 1,543 lines across 25 "process canonicalizations from *X* retro arc" sections. The ladder's weakest venue accumulates the most; CANON.md should say how to graduate or compact a section rather than only how to choose a venue.
  11. **Executor eval fixtures** (#78) — a fixtures directory of state files at various stages, replayed to assert the executor refuses to advance past unticked mandatory items. Complements the SKILL.md self-test above.

  Already captured in the working tree from the same source (pending commit): the `gh issue create` URL-parse trap (`pipeline-drain`, `pipeline-retro`), the ROADMAP duplicate-heading drift guard (`pipeline-drain`), and the pre-commit unstaged-work-preservation reflex (`pipeline-run`, from djust Action #292).

## Contributing

Active work lives under `## Milestones` with a matching Priority Matrix row (byte-identical feature name). Shipped work moves to `## Completed`. `/pipeline-next` reads this file; keep the matrix header columns `Priority | Feature | Why | Milestone` and put milestones under a non-reserved `## ` heading.
