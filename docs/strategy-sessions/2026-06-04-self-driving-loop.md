# Strategy Session — 2026-06-04 (self-driving-loop)

**Trigger**: on-demand (user question) · **Mode**: deep
**Outcome**: v0.7.0 — add `/pipeline-cycle` (semi-autonomous default + `--auto` opt-in). Directional → ADR-0003.

## The question

"Now that we've run the loop many times by hand, can the family self-drive it?
Are we missing a `/pipeline-brainstorm` or `/pipeline-nextsteps`? How does the
family drive to a clean fully-implemented solution?"

## Findings

- **Not missing brainstorm/nextsteps**: brainstorm = `/pipeline-strategy` Stage 2;
  nextsteps = strategy (which milestone) + next (which task). Standalones would
  duplicate existing stages.
- **The real gap is an outer orchestrator.** A human drove
  strategy→run→retro→strategy ~20× across six milestones. `pipeline-run
  --all-milestones` executes pre-planned milestones but never plans/retros
  between them.
- **A "clean fully-implemented solution" is a detectable terminal state** (0
  issues, 0 ROADMAP tasks, ADRs accepted, CI green) — reached after v0.6.0.
- **The loop has one irreducible human checkpoint**: the strategy Stage-7 path
  decision. This session's v0.5.0 outward pivot (which found bug #45) came from a
  human choosing a path auto-confirm would have skipped.

## Paths considered (Stage 5)

| Path | Scope | Risk | Notes |
|------|-------|------|-------|
| **A — Semi-autonomous /pipeline-cycle** ✅ default | autonomous execution; stop at strategy decisions | low | formalizes the manual cadence; keeps the human at the fork that mattered |
| **B — Fully autonomous --auto** ✅ as opt-in flag | no human gate; auto-confirm strategy | medium | maximally hands-off; would have skipped the v0.5.0 pivot |
| C — Runbook only | document the cadence, no skill | low | doesn't reduce the invocation burden |

## Decision (Stage 7)

**Recommended Path A.** **User chose: Path A as the default *plus* Path B's full
autonomy behind an explicit `--auto` flag** — i.e., semi-autonomous by default
(human-gated at strategy decisions), with `--auto` as a deliberate opt-in for
hands-off operation. This matches the recommendation's caveat that full autonomy
should be an ADR-captured opt-in, not the silent default.

**Directional change**: yes → [ADR-0003](../adr/0003-loop-autonomy-boundary.md)
(the loop's autonomy boundary).

## Captured into v0.7.0

3 Priority-Matrix rows: `/pipeline-cycle` orchestrator (semi-auto default),
`--auto` full-autonomy flag, terminal-state detector. Rejected: standalone
`/pipeline-brainstorm` and `/pipeline-nextsteps` (subsumed). Next:
`/pipeline-next --milestone v0.7.0`.
