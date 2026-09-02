# PURPOSE — pipeline-shared

Why each mandatory gate, reflex or stage rule in `SKILL.md` exists: the
pattern it serves (a row in [`docs/patterns/README.md`](../../docs/patterns/README.md))
and where it came from. A row whose pattern is `—` is a gate with no
living pattern behind it — a candidate for the Stage 3.7 gate once a
page exists. (ADR-0004.)

| gate / rule | pattern | origin | in SKILL.md |
|---|---|---|---|
| Code Review environment premises (CHANGELOG absent, stale base, gitignored paths) | `stale-base-review` | — | “Environment premises” |
| Patterns in play + `[class: …]` tagging | `ineffective-rule` | ADR-0004 | “Patterns in play” |
| Security Check scope discipline: leave pre-existing lint untouched | `scope-creep-lint` | #5 | “Scope discipline” |
| Code Review `Step FINAL`: restore the executor's tree | `worktree-dirty-tree` | — | “Code Review” |
| Retrospective persisted to `.pipeline-log.md` + PR comment | `retro-dropout` | — | “Persist Retrospective Output” |
| Retrospective step 6b: findings by pattern class | `ineffective-rule` | ADR-0004 | “Findings by pattern class” |
