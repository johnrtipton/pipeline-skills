# PURPOSE — pipeline-ship

Why each mandatory gate, reflex or stage rule in `SKILL.md` exists: the
pattern it serves (a row in [`docs/patterns/README.md`](../../docs/patterns/README.md))
and where it came from. A row whose pattern is `—` is a gate with no
living pattern behind it — a candidate for the Stage 3.7 gate once a
page exists. (ADR-0004.)

| gate / rule | pattern | origin | in SKILL.md |
|---|---|---|---|
| Stage 1 three-dot diff; predict conflicts with `merge-tree --write-tree` (Step 2.6, Stage 6), never the three-argument form | `stale-base-review` | the three-argument form reported 0 on a branch whose merge conflicted | “three-dot”, “--write-tree” |
| Pre-merge gate: Code Review artifact + state | `retro-dropout` | — | “Pre-merge gate” |
| End-of-run retrospective gate | `retro-dropout` | — | “Retrospective (Stage 10)” |
