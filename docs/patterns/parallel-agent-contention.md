# `parallel-agent-contention`

**Rule** (the line the rule sheet carries): One implementer agent per checkout; worktrees for
parallelism.
→ this page

**Status**: `skill` · **gate**: none (it *is* a rule) · **candidate for mechanical gate**: no
**Origin**: GitHub #1172 / Action Tracker #180 (v0.9.1).

## Instances

| PR | what drifted / what was missed | cure | rule in force? |
|---|---|---|---|
| #2843, #2844, #2846 | three worktree pipelines ran concurrently and exhausted the account-wide **5-hour usage quota**. All three implementer agents died at the *same step* — immediately before spawning their own Code Review reviewer — and their PRs reached CI-green **unreviewed**; fresh-context review is the family's main quality mechanism | the executor finished all three by hand, reviewing inline and **stating that limitation in each posted review** | yes, missed — the rule covers *checkout* contention, and says nothing about the quota |

## Detection

- The one-checkout rule removes branch-flip corruption; it does not buy headroom. Three
  concurrent pipelines roughly triple the burn against **one shared cap**. Cap at one or two.
- If an agent dies mid-task, the PR is in an unknown review state. Finish it by hand and make
  the posted review admit that it is inline rather than fresh-context — an artifact that
  implies the family's normal independence is worse than one that names its weakness.

## Rejected shapes

- **"More worktrees = more throughput."** Measured false against a shared quota: the fleet dies
  together at the same step, and the recovery cost (three hand-finished PRs) exceeds the
  parallelism gained.
- **Re-spawning the dead reviewer.** It consumes the same exhausted quota; the failure repeats.
