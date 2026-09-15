# `stale-base-review`

**Rule** (the line the rule sheet carries): Reviewing a branch behind its base reviews a
different program than the merge applies — three-dot diff, rebase first.
→ this page

**Status**: `skill` · **gate**: none · **candidate for mechanical gate**: yes
**Origin**: family (`pipeline-shared` Code Review premises, `pipeline-ship` Stage 1).

## Instances

| PR | what drifted / what was missed | cure | rule in force? |
|---|---|---|---|
| #2843 | a **worktree** branch cut before four sibling PRs landed. `git merge-tree --write-tree origin/main HEAD` showed conflicts in *generated* artifacts (`client.js`, `client.min.js`, `client-sizes.json`, a `CLAUDE.md` size claim) while the source diff stayed clean — a merge blocker that cost a full review round, and the review had been written against the older base | merged `origin/main` and **regenerated** the artifacts (never hand-merged them) | yes, missed |

## Detection

- `git merge-tree --write-tree origin/main HEAD` **before opening the PR** — it reports
  generated-artifact conflicts that a source-only diff hides.
- In a worktree fleet, merge `origin/main` **early**, while the branch is one or two files, so
  the merge is trivially conflict-free. Deferring it to merge time is what made this cost a
  review round.
- Generated artifacts are the recurring collision surface: they are rewritten by every sibling
  that touches the build, so they conflict even when no source line does. Resolve them by
  re-running the build, never by editing the file.

## Rejected shapes

- **"The branch is only one commit behind, it will be fine."** It was one commit behind — the
  conflicting commit was #2831, which touched the same source file *and* regenerated the same
  three artifacts.
