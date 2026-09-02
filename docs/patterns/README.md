# Pattern index (the family's own wiki)

One row per failure class the pipeline family guards against. Each row's
rule is the line a rule sheet carries; the page (when one exists) holds the
instance table, detection and rejected shapes. Template:
[TEMPLATE.md](TEMPLATE.md). Lifecycle: [CANON.md](../../CANON.md#compacting-canon-the-pattern-wiki-and-the-rule-sheet-adr-0004).

This index is also what `skills/*/PURPOSE.md` point at, so a gate with no
row here is a gate with no living pattern behind it.

| class | rule | status · gate | origin |
|---|---|---|---|
| `retro-dropout` | A task is not complete until a retro artifact exists on the PR. | skill · `pipeline-run` Gate 4, `pipeline-ship` pre-merge/end gate | #8 |
| `swallowed-commit` | Verify every commit landed (`git log -1`), and that `--amend` changed the HEAD hash. | skill · `pipeline-run` post-commit verification | Action #122 |
| `wrong-branch-commit` | Confirm HEAD matches the state file's branch before staging; code-writing subagents check out the branch first. | skill · `pipeline-run` branch-verify reflex + checkout preamble | — |
| `changelog-cross-contamination` | Implementation commit excludes CHANGELOG; docs commit contains only docs + CHANGELOG. | skill · `pipeline-run` Gates 1–2 | GitHub #1173 |
| `test-pollution` | A pollution/leak/flake fix passes the full suite three consecutive times. | skill · `pipeline-run` Gate 3 | GitHub #1174 |
| `parallel-agent-contention` | One implementer agent per checkout; worktrees for parallelism. | skill · `pipeline-run` rule | GitHub #1172 |
| `worktree-dirty-tree` | A read-only subagent restores the executor's branch and a clean tree before returning. | skill · `pipeline-run` worktree-restore reflex, Code Review `Step FINAL` | #36 |
| `unstaged-work-loss` | Pre-commit can stash unstaged work and fail to restore it; check `git status` after every pipeline commit. | skill · `pipeline-run` reflex | #292 |
| `state-file-bypass` | No PR without a state file; the outer loop re-reads state before every task. | skill · `pipeline-run` State-File Gate | #840 |
| `duplicate-pr` | Check `gh pr list --head` before creating a PR. | skill · `pipeline-run` Commit & PR | — |
| `prose-only-action` | A retro finding's `Action taken:` is a diff, a skill edit, a tracker row or a close — never the prose itself. | skill · `pipeline-retro` Stage 3.5 gate | — |
| `stale-base-review` | Reviewing a branch behind its base reviews a different program than the merge applies; three-dot diff, rebase first. | skill · `pipeline-shared` Code Review premises, `pipeline-ship` Stage 1 | — |
| `scope-creep-lint` | Leave pre-existing lint untouched in a security/lint pass; fix what the task cites. | skill · `pipeline-shared` Security Check | #5 |
| `ineffective-rule` | A rule that keeps being re-violated is a rejected proposal; harden it into a gate or demote it. | skill · `pipeline-retro` Stage 3.7 | ADR-0004 |
