# ADR-0003: The loop is human-gated at strategy decisions; full autonomy is opt-in

**Status**: Proposed
**Date**: 2026-06-04
**Source**: Strategy session [2026-06-04-self-driving-loop](../strategy-sessions/2026-06-04-self-driving-loop.md)

## Context

The pipeline family has skills for every phase — plan (`/pipeline-strategy`),
pick (`/pipeline-next`), execute (`/pipeline-run`), close (`/pipeline-retro`) —
but no skill that *chains* them. Across six milestones (v0.1.0–v0.6.0) a human
was the outer loop, invoking `strategy → run → retro → strategy` ~20 times by
hand. The natural next step is `/pipeline-cycle`, an orchestrator that runs the
cadence to a clean terminal state.

The open question is *how autonomous*. Two phases of the loop differ sharply in
how much human judgment they need:

- **Execution** (`next → implement → review → merge → retro` for a *planned*
  milestone) is already safely autonomous — `--all` ran dozens of tasks this
  session with subagent review + programmatic gates and no human turn.
- **Strategy decisions** (the `/pipeline-strategy` Stage-7 choice among ≥2
  distinct paths) are where this session's value concentrated. The v0.4.0→v0.5.0
  **outward pivot** — which directly produced bug #45's discovery — came from a
  human choosing a path the loop would otherwise have continued past. A loop that
  auto-confirms the strategy recommendation would have rubber-stamped "continue
  inward" and never pivoted. Confident, not wise.

## Decision

`/pipeline-cycle` is **semi-autonomous by default**:

1. It runs **execution autonomously** — `pipeline-next → pipeline-run --all →
   pipeline-retro` for each captured milestone, no human turn.
2. It **STOPS and hands control to the human at every `/pipeline-strategy`
   Stage-7 path decision**, and on any stage failure.
3. It **terminates** when the terminal-state detector reports clean (0 open
   issues, 0 active ROADMAP tasks, no `Proposed` ADR, CI green) or strategy finds
   no pass-tagged candidates.

Full hands-off autonomy is available **only behind an explicit `--auto` flag**,
which auto-confirms the strategy recommendation (light mode throughout). `--auto`
is a deliberate opt-in for low-stakes or well-bounded backlogs — never the
default.

## Consequences

- **Gains**: the repetitive, safe part of the loop (execution) is automated; the
  per-step invocation burden drops; the one checkpoint where human judgment
  demonstrably changed the outcome is preserved by default.
- **`--auto` trade-off**: hands-off operation at the cost of the path-choice
  judgment. Appropriate when the backlog is unambiguous; risky when a directional
  fork is live (it will confidently take the recommended path). The flag exists so
  the choice to give up the gate is explicit and logged, not silent.
- **Risk**: an orchestrator that pauses at the wrong granularity is annoying
  (over-pause) or unsafe (under-pause). The stop points are defined narrowly:
  strategy Stage-7 decisions and stage failures only.
- Compatible with ADR-0001 (gates stay in force inside every run) and ADR-0002
  (the cycle serves outward adoption — it makes the family drivable by others).
