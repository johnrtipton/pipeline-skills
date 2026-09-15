# `retro-dropout`

**Rule** (the line the rule sheet carries): A task is not complete until a retro artifact
exists on the PR — **and a bucket is not complete until a `RETRO.md` entry exists**.
→ this page

**Status**: `skill` · **gate**: `gate_retro_artifact` (PR) + `gate_retro_coverage` (milestone) ·
**candidate for mechanical gate**: no (both halves now have one)
**Origin**: #8 / #68; the milestone half from djust v1.2.0-6.

## Instances

| PR | what drifted / what was missed | cure | rule in force? |
|---|---|---|---|
| #2837, #2838 | merged with **no review artifact at all** — the only comment on either was a CI bot. `gate_premerge` already refuses a PR with no Code Review artifact, but it was never *invoked*: the merge went through `gh pr merge --admin` directly | both reviews posted after the fact, and a rule added that a Code Review stage ends with a comment on the PR | yes, missed — the gate existed and was not run |
| 14 buckets | fourteen drain buckets were complete (every issue CLOSED) with **no `RETRO.md` entry and no canonicalization**. The per-PR gate cannot see this: a bucket is a milestone, not a PR. Not a one-off — djust #2140 was a *previous* backfill for the same reason | backfilled; `gate_retro_coverage` added (upstream #84); per-bucket headings required | yes, missed — the rule was PR-scoped |

## Detection

- `gate_retro_artifact <pr>` — the PR half, already shipped.
- `gate_retro_coverage [ROADMAP.md RETRO.md]` — the milestone half: a bucket whose matrix rows
  all carry a completion marker must have a `## <bucket>` heading in `RETRO.md`.
  **Known limitation, measured:** it saw 6 of the 14 drifted buckets, because 8 were completed
  *without striking their rows* and so record no completion signal at all. A scan with issue
  access can do better — "every issue in the bucket is closed" is authoritative and
  `closedByPullRequestsReferences` gives exact attribution in one call.
- Both halves are only as good as being invoked. A gate the executor may skip is a reminder;
  see the enforcement note in upstream #3.

## Rejected shapes

- **"`pipeline-run` housekeeping prints a reminder."** It does — and it did not hold across
  fourteen buckets and at least one prior backfill. A reminder is the shape that fails here.
- **A single consolidated backfill entry covering every drifted bucket.** It documents them but
  satisfies no per-bucket check and is not findable by grepping a bucket's name. One heading
  per bucket, however thin.
