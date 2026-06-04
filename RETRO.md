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
| 6 | Consolidate pipeline-run inline gates into `scripts/pipeline-gates.sh` (dangling canonical reference) | Retro v0.2.0 / PR #24 | #28 | Closed | Resolved in PR #32 (v0.3.0) — executable gate functions |
| 7 | `check-branch-literals.sh` diff/rev-parse regex can false-positive on backtick-wrapped prose | Retro v0.2.0 / PR #21 | #29 | Closed | Resolved in PR #41 (v0.4.0) — strips inline-code spans before matching |
| 8 | Review subagents leave the executor's working tree on `main` → builds/scp from a stale tree | Retro v0.3.0 / djustlive v0.4.0 | #36 | Closed | Resolved in PR #39 (v0.4.0) — template restore-HEAD step + pipeline-run worktree-restore reflex |
| 9 | Worktree-restore reflex doesn't remove untracked files left by a subagent | Retro v0.4.0 / PR #39 | #40 | Closed | Resolved in PR #49 (v0.5.0) — `git clean -fd` + re-verify |
| 10 | `detect_default_branch` returns `main` for a `master`-default repo with no `origin/HEAD` | Retro v0.5.0 / PR #46 | #45 | Closed | Resolved in PR #53 (v0.6.0) — origin-probe + current-branch fallback; validated end-to-end in PR #55 |

<!-- Milestone retro entry template:
## <milestone> — <Title> (PRs #NN–#MM)
**Date**: YYYY-MM-DD · **Quality**: N/5
### What We Learned
**1. Finding.** … **Action taken**: diff | skill_update | tracker_row | closed
### Insights
### Review Stats
### Open Items
-->

## v0.6.0 — Follow through on the pivot (PRs #53, #54, #55)

**Date**: 2026-06-04
**Scope**: Continued ADR-0002. Fixed the entry-point branch bug v0.5.0 found (#45), proved the full family end-to-end on a real foreign repo including the PR stages, and flipped both ADRs to Accepted.
**Tests at close**: n/a — CI green on every PR; end-to-end validated on a live foreign repo.

### What We Learned

**1. The outward pivot's loop closed in one milestone-pair.**
v0.5.0's validation *found* #45 (`detect_default_branch` wrong on `master`/no-origin); v0.6.0 *fixed* it (PR #53, parity with the pipeline-init SKILL chain) and *proved* the fix end-to-end on a real throwaway `master`/Node GitHub repo — including the PR-create-against-`master` → review → squash-merge stages the v0.5.0 local-only run could not exercise (PR #55). Zero new family gaps surfaced. Found → fixed → validated, with the validation done on a genuinely foreign remote, not a simulation.

**Action taken**: closed — #45 resolved in PR #53; end-to-end validation in PR #55.

**2. ADR status drift resolved.**
ADR-0001 (executable gates) and ADR-0002 (outward pivot) were both implemented and in force but still marked `Proposed` — the exact drift the pipeline-shared Documentation stage's ADR-reconciliation step exists to catch. Flipped both to `Accepted` with their implementing versions/PRs cited.

**Action taken**: closed — ADR statuses flipped in PR #54.

### Insights

- **The harness Bash shell runs with `noclobber` ON** (a Claude Code default, not in the user's dotfiles and not user-configurable). `cat > existing_file` silently no-ops, which bit the validation setup twice. The durable fix is operator-side — use the Write/Edit tools, not `>` to existing files. (The pipeline skills' own bash snippets use `>`/heredoc redirects; a future cleanup could make them `>|`-safe, but most write new files or use git, so it's low-signal — noted, not filed.)
- **A "throwaway repo" validation needs the `delete_repo` gh scope to clean up.** The default `gh` token lacks it (403 on delete); `gh auth refresh -h github.com -s delete_repo` or the web UI is required. Worth mentioning in any future validation runbook.
- **Two milestones converted a found bug into a proven fix** — the clearest demonstration this session that the retro→strategy→run→retro loop drives real correction, not just documentation.

### Review Stats

| Metric | #53 | #54 | #55 | Total |
|--------|-----|-----|-----|-------|
| Subagent code reviews | 1 | 0 (docs) | 0 (docs) | 1 |
| Review verdict | APPROVE | self/APPROVE | self/APPROVE | — |
| Regression cases verified | 5 | — | — | 5 |
| 🔴 Findings | 0 | 0 | 0 | 0 |
| New family gaps found | 0 | 0 | 0 | 0 |
| Real foreign-repo PRs exercised | — | — | 1 (merged) | 1 |
| CI runs (green) | 1 | 1 | 1 | 3 |

### Process Improvements Applied

**Harness**: `detect_default_branch` gained an origin-probe + current-branch fallback (PR #53).
**Docs**: `docs/validation/2026-06-04-foreign-repo-e2e.md` end-to-end report (PR #55).
**ADR**: ADR-0001 + ADR-0002 → Accepted (PR #54).

### Open Items

- None. Action Tracker has no open rows; 0 open issues at milestone close.

**→ Forward**: strategy session [2026-06-04-self-driving-loop](docs/strategy-sessions/2026-06-04-self-driving-loop.md) → **v0.7.0 "Self-driving the loop"**: add `/pipeline-cycle` (semi-autonomous default + `--auto` opt-in) + a terminal-state detector. Directional → [ADR-0003](docs/adr/0003-loop-autonomy-boundary.md) (the loop is human-gated at strategy decisions; full autonomy is opt-in).

## v0.5.0 — Outward pivot (PRs #46, #47, #48, #49)

**Date**: 2026-06-04
**Scope**: First outward milestone (ADR-0002). Validated the family on a foreign repo, wrote an adoption guide, established a release process + cut the first tags, and closed the #40 untracked-files gap.
**Tests at close**: n/a — CI green on every PR.

### What We Learned

**1. The outward pivot found a foundational bug on the first probe.**
Running the family's detection against a deliberately-foreign scratch repo (`master`-default, Node, checkbox ROADMAP) immediately surfaced that `detect_default_branch` returns `main` for a `master` repo with no `origin/HEAD` (#45) — a branch-agnosticism hole at the harness entry point that four inward milestones never hit, because dogfooding only ever ran on this `main`-default repo with an origin. ADR-0002's bet (external use finds what self-use can't) paid on the first try.

**Action taken**: Open — tracked in Action Tracker #10 (GitHub #45).

**2. The repo was not actually consumable; now it is.**
After four milestones the repo had 0 git tags and referenced a flexion plugin not present — nobody but the author had a supported path in. v0.5.0 added `docs/adoption.md` (clone → first PR) and a release process, and cut the first four tags (`v0.1.0`–`v0.4.0`) at their retro commits.

**Action taken**: closed — adoption quickstart (PR #47) + release process & tags (PR #48).

**3. The capture loop closed across two milestones.**
PR #39's Code Review flagged that the #36 restore reflex only handled tracked files → filed #40 → tracked as Action #9 → shipped in PR #49 (`git clean -fd` + re-verify). A finding noticed mid-implementation two milestones ago became a tracked, then resolved, action — the exact "capture what's out of scope, process it later" loop the harness is built on.

**Action taken**: closed — Action Tracker #9 resolved in PR #49.

### Insights

- **Gate 4 earned its keep in production, not a drill.** On PR #46 the retro comment silently failed to post (a heredoc-in-compound-command quirk); the retro-artifact gate flagged the dropout and I re-posted. This is precisely the failure mode (#8) the gate was built for, caught for real.
- **Validation's deliverable is a report + issues, not a green checkmark.** The foreign-repo task "succeeded" by *finding a bug* — the right success criterion for a validation task, and the reason it was framed that way in the ROADMAP acceptance.
- **The outward turn was itself a product of the inward discipline.** Four tightly-run inward milestones (clean retros, tracked actions, ADRs) made the "how is this useful?" inflection legible and the pivot cheap — exactly the master_control arc the strategy skill documents.

### Review Stats

| Metric | #46 | #47 | #48 | #49 | Total |
|--------|-----|-----|-----|-----|-------|
| Subagent code reviews | 0 (docs) | 0 (docs) | 0 (docs) | 1 | 1 |
| Review verdict | self/APPROVE | self/APPROVE | self/APPROVE | APPROVE | — |
| Bugs found (filed) | 1 (#45) | 0 | 0 | 0 | 1 |
| Gate-4 dropout caught | 1 | 0 | 0 | 0 | 1 |
| Tags cut | — | — | 4 | — | 4 |
| CI runs (green) | 1 | 1 | 1 | 1 | 4 |

### Process Improvements Applied

**Docs**: `docs/adoption.md` (PR #47), `docs/releasing.md` (PR #48), `docs/validation/2026-06-04-foreign-repo.md` (PR #46).
**Release**: first tags `v0.1.0`–`v0.4.0` + documented release flow (PR #48).
**Skills/templates**: worktree-restore reflex + Code Review prompts now `git clean -fd` untracked files (PR #49).
**ADR**: ADR-0002 (outward pivot) established (strategy capture, PR #44).

### Open Items

- [x] `detect_default_branch` foreign-repo bug — Action Tracker #10 (GitHub #45) — resolved in v0.6.0 (PR #53; validated end-to-end PR #55)

**→ Forward**: strategy session [2026-06-04-v0-5-end](docs/strategy-sessions/2026-06-04-v0-5-end.md) → **v0.6.0 "Follow through"** (Path 1): fix #45, fuller end-to-end foreign-repo validation, flip ADR-0001/0002 to Accepted. Continues ADR-0002; no new ADR.

## v0.4.0 — Drift guards (PRs #39, #41)

**Date**: 2026-06-04
**Scope**: Promoted (PR #38) and shipped the two concrete drift issues: review subagents now restore HEAD on exit + an executor worktree-restore reflex (#36), and the branch-literal guard no longer false-positives on backtick prose (#29).
**Tests at close**: n/a — CI (`make check` + script syntax + parse) green on every PR.

### What We Learned

**1. The subagent-pollution fix was validated by the mechanism it fixes.**
#36 (a cross-project bug from djustlive that broke a base-image build across 5 PRs) was fixed by making Code Review subagents restore HEAD. The proof it works: PRs #39 and #41 each spawned a Code Review subagent under the new prompt, and both started and ended on the feature branch with a clean tree — the executor verified `worktree==HEAD` after each. Dogfooding the dogfooder: a "subagents misbehave" fix is most convincingly validated by spawning subagents under it and confirming they behave.

**Action taken**: closed — Action Tracker #8 resolved in PR #39 (template restore step + pipeline-run reflex).

**2. The branch-literal guard was tightened without opening a false-negative.**
#29's fix strips inline-code spans before matching, so prose like `` `git diff origin/main` `` is ignored while real fenced-block commands are still caught. The Code Review confirmed (on bash 3.2/BSD) there is no reachable false-negative — the dangerous direction for a guard.

**Action taken**: closed — Action Tracker #7 resolved in PR #41.

**3. The #36 fix left a narrower gap; the capture channel caught it.**
PR #39's review noted that `git restore --staged --worktree .` only touches tracked files — a subagent leaving NEW untracked files would still pass them into a build. Low severity (the observed djustlive failure was a reverted tracked file), but real.

**Action taken**: Open — tracked in Action Tracker #9 (GitHub #40).

### Insights

- **Dogfooding-the-dogfooder is uniquely available here**: the repo's own pipeline uses Code Review subagents, so a fix to subagent behavior is exercised the moment the next PR's review runs. The validation is free and direct.
- **A full re-serialize obscures a small change**: `json.dump(indent=2)` on the templates in PR #39 bloated the diff to 1303/298 for what was a one-line-per-prompt addition. Prefer string-level edits to template prompts to keep diffs reviewable.
- **Two clean milestones running (v0.3.0, v0.4.0) with 0 retro-gate violations** — the Gate 4 + per-PR-retro habit is now reliable, not luck.
- **Cross-project bug-flow-back works end to end**: #36 originated in djustlive, was filed against this repo mid-v0.3.0, promoted in PR #38, and shipped in v0.4.0 — one milestone from report to fix.

### Review Stats

| Metric | #39 | #41 | Total |
|--------|-----|-----|-------|
| Subagent code reviews | 1 | 1 | 2 |
| Review verdict | APPROVE | APPROVE | — |
| 🔴 Findings | 0 | 0 | 0 |
| Deferred to issue | 1 (#40) | 0 | 1 |
| Subagent left clean tree (the #36 check) | yes | yes | 2/2 |
| CI runs (green) | 1 | 1 | 2 |
| Tests added | 0 (no suite) | 0 | 0 |

### Process Improvements Applied

**Templates**: Code Review `subagent_prompt` restores HEAD on exit, all four templates (PR #39).
**Skills**: pipeline-run worktree-restore reflex before build/scp/ship (PR #39).
**Scripts**: `check-branch-literals.sh` strips inline-code spans before matching (PR #41).

### Open Items

- [x] Worktree-restore reflex should also clear untracked files — Action Tracker #9 (GitHub #40) — resolved in v0.5.0 (PR #49)

**→ Forward**: strategy session [2026-06-04-v0-4-end](docs/strategy-sessions/2026-06-04-v0-4-end.md) → **v0.5.0 "Outward pivot"** (Path 2). After 4 inward milestones, [ADR-0002](docs/adr/0002-outward-pivot.md) shifts to proving + packaging the family (foreign-repo validation, adoption quickstart, first release/tags). #40 rides along; inward drift ideas deferred.

## v0.3.0 — Executable gates + CI (PRs #32, #33, #34)

**Date**: 2026-06-04
**Scope**: Strategy-chosen Path 1. Turned the pipeline's prose quality gates into executable artifacts: `scripts/pipeline-gates.sh` (#28), a template structure validator (`make validate-templates`), and a GitHub Actions CI workflow enforcing both on every PR. Established ADR-0001.
**Tests at close**: n/a — no unit suite; CI (`make check` + script syntax + pipeline.py parse) is now the enforcement surface, green on every PR.

### What We Learned

**1. The gates validated their own construction (dogfooding closed the loop).**
From PR #32 onward every commit was checked by the gate functions it shipped: Gate 1 (changelog-boundary) on each implementation commit, Gate 2 (docs-only) on each docs commit, `gate_premerge` before each merge, Gate 4 (retro-artifact) after each retro. ADR-0001's goal — enforcement that doesn't depend on the model remembering — is met, and PR #34's CI ran green on its own diff.

**Action taken**: closed — #28 resolved (PR #32); CI enforcing it (PR #34).

**2. Review depth caught a fail-open bug a checker must never have.**
PR #33's Code Review returned REQUEST_CHANGES (the project's first): a template that was valid JSON but not an object crashed the validator with an uncaught exception that escaped the per-file loop, silently skipping every template after it. A validator that stops checking is worse than none. Fixed (`isinstance` guard + `continue`) and re-verified before merge.

**Action taken**: closed — fixed in PR #33 (commit 3483ca9), re-verified against the exact failing case.

**3. Review subagents can silently dirty the executor's working tree.**
This milestone leaned on Code Review subagents (#32, #33). A sibling project (djustlive v0.4.0) reported that read-only review subagents `git checkout` the branch to read the diff and leave the executor's tree on `main`, so a subsequent build/scp ships stale files — it broke a base-image build there, recurring across 5 PRs. No breakage here only because the executor re-synced (`git checkout main`) after every merge; the risk is systemic and unguarded for build/scp steps.

**Action taken**: Open — tracked in Action Tracker #8 (GitHub #36).

### Insights

- **Self-referential validation is uniquely available to a tooling repo and uniquely high-signal**: the gates checked the gates, the validator validated itself, CI tested itself. Each caught real issues during its own construction.
- **Building a checker teaches you your own data.** The template validator immediately surfaced a structural assumption I'd have missed — `retro-state.json` legitimately uses fractional sub-stage keys (3.5/4.5) — forcing the correct "numeric, strictly-ascending" rule instead of "contiguous integers."
- **Cross-project retro signal is valuable.** #36 arrived mid-milestone from djustlive, a different consumer of these skills. Bugs found in one consumer should flow back to the canonical repo — the pipeline-* family has more than one user now.

### Review Stats

| Metric | #32 | #33 | #34 | Total |
|--------|-----|-----|-----|-------|
| Subagent code reviews | 1 | 1 | 0 (inline + live CI) | 2 |
| Review verdict | COMMENT | REQUEST_CHANGES | APPROVE | — |
| Bugs caught & fixed pre-merge | 0 | 1 | 0 | 1 |
| Calibration fixes during build | 2 | 1 | 0 | 3 |
| CI runs (green) | — | — | 1 | 1 |
| Tests added | 0 (no suite) | 0 | 0 | 0 |

### Process Improvements Applied

**Scripts**: `scripts/pipeline-gates.sh` (PR #32), `scripts/validate-templates.sh` (PR #33).
**CI**: `.github/workflows/ci.yml` — `make check` + script syntax + pipeline.py parse on every PR/push (PR #34).
**Skills**: pipeline-run "Where to place the gates" now references the executable script (PR #32).
**Makefile**: `make check` now runs the branch-literal guard + template validator (PRs #32, #33).
**ADR**: ADR-0001 (executable gates) established (strategy session capture).

### Open Items

- [x] Review-subagent working-tree pollution — Action Tracker #8 (GitHub #36) — resolved in v0.4.0 (PR #39)
- [x] `check-branch-literals.sh` regex tighten — Action Tracker #7 (GitHub #29) — resolved in v0.4.0 (PR #41)

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

- [x] Consolidate pipeline-run gates into `scripts/pipeline-gates.sh` — Action Tracker #6 (GitHub #28) — resolved in v0.3.0 (PR #32)
- [ ] Tighten `check-branch-literals.sh` regex against backtick prose — Action Tracker #7 (GitHub #29)

**→ Forward**: planned in strategy session [2026-06-04-v0-2-end](docs/strategy-sessions/2026-06-04-v0-2-end.md) → **v0.3.0 "Executable gates + CI"** (Path 1; #28 is the P1 anchor). Established [ADR-0001](docs/adr/0001-executable-quality-gates.md). #29 deferred to v0.4.0 drift cluster.

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
