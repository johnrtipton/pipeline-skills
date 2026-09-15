# PURPOSE — pipeline-retro

Why each mandatory gate, reflex or stage rule in `SKILL.md` exists: the
pattern it serves (a row in [`docs/patterns/README.md`](../../docs/patterns/README.md))
and where it came from. A row whose pattern is `—` is a gate with no
living pattern behind it — a candidate for the Stage 3.7 gate once a
page exists. (ADR-0004.)

| gate / rule | pattern | origin | in SKILL.md |
|---|---|---|---|
| Action Tracker: every finding has a row or a close | `prose-only-action` | — | “The Action Tracker” |
| Rule rows carry pattern / fired / re-violated | `ineffective-rule` | ADR-0004 | “Rule rows” |
| Stage 3.5 verification gate: classify `Action taken:` | `prose-only-action` | — | “Stage 3.5” |
| Stage 3.7 rule-sheet gate: KEEP / HARDEN / DEMOTE | `ineffective-rule` | ADR-0004 | “Stage 3.7” |
| Stage 4 step 2: `gh issue create` prints a URL, parse it | — | — | “gh issue create” |
| Stage 4.5 re-verify after backfill | `prose-only-action` | — | “Stage 4.5” |
| `OUT-OF-REPO` status counted separately | — | — | “OUT-OF-REPO” |
