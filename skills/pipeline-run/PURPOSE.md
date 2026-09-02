# PURPOSE — pipeline-run

Why each mandatory gate, reflex or stage rule in `SKILL.md` exists: the
pattern it serves (a row in [`docs/patterns/README.md`](../../docs/patterns/README.md))
and where it came from. A row whose pattern is `—` is a gate with no
living pattern behind it — a candidate for the Stage 3.7 gate once a
page exists. (ADR-0004.)

| gate / rule | pattern | origin | in SKILL.md |
|---|---|---|---|
| One implementer agent per checkout | `parallel-agent-contention` | GitHub #1172 | “One Implementer Agent Per Checkout” |
| Branch-verify reflex before any pipeline commit | `wrong-branch-commit` | — | “Branch-verify reflex” |
| Branch-checkout preamble for code-writing subagents | `wrong-branch-commit` | — | “Branch-checkout preamble” |
| Worktree-restore reflex after any subagent | `worktree-dirty-tree` | #36 | “Worktree-restore reflex” |
| Unstaged-work-preservation reflex | `unstaged-work-loss` | #292 | “Unstaged-work-preservation reflex” |
| Gate 1: Stage 5 commit excludes CHANGELOG | `changelog-cross-contamination` | GitHub #1173 | “Gate 1” |
| Gate 2: Stage 9 commit is docs + CHANGELOG only | `changelog-cross-contamination` | GitHub #1173 | “Gate 2” |
| Gate 3: 3-clean-runs for pollution-class fixes | `test-pollution` | GitHub #1174 | “Gate 3” |
| Gate 4: retrospective artifact gate | `retro-dropout` | #8 | “Gate 4” |
| Post-commit verification (`git log -1`) | `swallowed-commit` | Action #122 | “MANDATORY Post-Commit Verification” |
| `git commit --amend` hash-changed check | `swallowed-commit` | Action #122 | “The `git commit --amend` companion” |
| Duplicate PR prevention | `duplicate-pr` | — | “Duplicate PR Prevention” |
| State-file gate before `gh pr create` | `state-file-bypass` | #840 | “State-File Gate” |
| Outer-loop integrity in `--all` mode | `state-file-bypass` | #840 | “Outer-loop integrity” |
| Retro-artifact gate before `completed_at` | `retro-dropout` | #8 | “MANDATORY retro-artifact gate” |
| Wiki access rule for subagent prompts | `ineffective-rule` | ADR-0004 | “Wiki access rule” |
| Review Quality: `[class: …]` on every finding | `ineffective-rule` | ADR-0004 | “Review Quality Rules” |
