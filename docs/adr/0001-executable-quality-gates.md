# ADR-0001: Quality gates must be executable, not prose

**Status**: Proposed
**Date**: 2026-06-04
**Source**: Strategy session [2026-06-04-v0-2-end](../strategy-sessions/2026-06-04-v0-2-end.md) (Path 1)

## Context

The pipeline-skill family's founding principle is "the state file is the
program; the model is the executor" — durability comes from forcing the model
to interact with a structured artifact rather than remembering instructions.
Yet the family's own quality gates contradict this: pipeline-run's MANDATORY
Post-Commit Programmatic Gates (1-4) and the pipeline-ship pre-merge gate are
written as **inline bash in SKILL.md prose**. The skills even say these "should
live in a project-local `scripts/pipeline-gates.sh`" — but that script does not
exist, a dangling canonical reference the v0.2.0 staleness check (#7) is
designed to catch.

Prose gates have the exact failure mode the project was built to defeat: an LLM
executor under context pressure can skip the read, and a fresh-session resume
can miss the gate entirely. A gate that only runs when the model remembers to
copy-paste it is a soft gate wearing a hard gate's label. The repo also has no
CI, so even `make check` (the one runnable check) runs only when invoked by hand.

## Decision

Quality gates in this project are **executable artifacts**, not documented bash:

1. Each gate is a shell function in a committed `scripts/pipeline-gates.sh`,
   parameterized by the detected default branch and test command.
2. The SKILL.md text references the function by name; it may show the body for
   human readability, but the **function** is the source of truth.
3. Gates are wired into CI (GitHub Actions) so they run on every PR/push
   independent of any model's attention.
4. A gate that cannot be made executable (genuinely requires human judgment) is
   labelled as advisory, not mandatory.

## Consequences

- **Gains**: enforcement becomes context-independent and auditable; the
  dangling `scripts/pipeline-gates.sh` reference resolves; every PR is checked
  automatically; new gates have a clear committed home.
- **Costs**: gate logic must be kept portable (bash 3.2 / BSD, per the existing
  scripts) and maintained as code, not prose; CI adds a small per-PR latency.
- **Risk**: over-proceduralizing — gates that genuinely need human judgment must
  stay advisory rather than being forced into a brittle script. The decision
  explicitly carves that out (point 4).
- **Supersedes nothing** — this is the repo's first ADR; it formalizes a
  principle that was implicit but unenforced. v0.3.0 implements it.
