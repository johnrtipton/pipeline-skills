# Adopting the pipeline family in your repo

A clone-to-first-shipped-PR guide for using the `pipeline-*` skills in a
repository other than this one. You should not need to read any skill internals
to follow it.

## 0. Prerequisites

- [Claude Code](https://claude.com/claude-code) with skills support.
- `git` and the [`gh`](https://cli.github.com/) CLI, authenticated (`gh auth status`).
- A repo with a GitHub remote (PR/review/merge stages use `gh`; a repo with no
  remote still works for the local stages — those stages just report `PR_SKIPPED`).

## 1. Install the skills

```bash
git clone git@github.com:johnrtipton/pipeline-skills.git ~/pipeline-skill
cd ~/pipeline-skill
./install.sh --symlink     # symlinks every skills/pipeline-* into ~/.claude/skills/
```

`install.sh` prints the installed skills, including `/pipeline-init`.

## 2. Bootstrap your repo (once)

From within your target project, in Claude Code:

```
/pipeline-init
```

This detects your default branch, test/lint/build commands, ROADMAP format, and
version scheme, then scaffolds `.pipeline-state/`, a `CLAUDE.md` pipeline-config
block, `ROADMAP.md` (migrating a non-conforming one), `RETRO.md`, `CHANGELOG.md`,
and the support dirs. It is idempotent — safe to re-run; it only fills gaps.

> **Set `default_branch` explicitly.** `pipeline-init` writes a
> `<!-- pipeline-config -->` block into your repo-root `CLAUDE.md`. **Verify the
> `default_branch:` line is correct** — on a `master`-default repo whose
> `origin/HEAD` isn't populated, auto-detection can currently mis-guess `main`
> (known issue [#45]); the explicit `default_branch:` line is the reliable
> override that the whole family reads first. Edit it if needed before running
> anything else.

## 3. The daily loop

```
/pipeline-next --milestone v0.1.0     # pick the next task from ROADMAP.md, create a state file
/pipeline-run                          # execute every stage → commit → PR → review → merge
```

`/pipeline-next` chooses the highest-priority unstarted task in the milestone and
writes `.pipeline-state/<branch>.json` — the state file *is* the program;
`/pipeline-run` walks its stages. Add `--all` to process every task in the
milestone autonomously.

## 4. Close a milestone

```
/pipeline-retro --milestone v0.1.0     # synthesize per-PR retros, update the Action Tracker
/pipeline-strategy                     # plan the next milestone (>=2 paths, recommend, capture)
```

## 5. What "done" looks like for one task

`/pipeline-run` takes a task through: environment check → implementation →
test/self-review/security → docs → commit & PR → **Code Review** (a fresh-context
subagent posts to the PR) → merge → **Retrospective** (posted to the PR). The
quality gates (`scripts/pipeline-gates.sh`, run in CI here) enforce the
two-commit shape and the retro artifact so steps can't be silently skipped.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `/pipeline-next` finds 0 tasks | ROADMAP isn't in the priority-matrix format the parser reads → re-run `/pipeline-init` (it migrates a foreign ROADMAP). |
| Branch operations target the wrong branch | Check the `default_branch:` line in your `CLAUDE.md` pipeline-config block (see step 2 / #45). |
| PR stages report `PR_SKIPPED` | No GitHub remote, or `gh` not authenticated (`gh auth status`). |
| Pre-commit hook bounces the commit | The skills scope formatters to staged files; see pipeline-run's Pre-Commit Checklist. |

## Where things live

- Skills: `~/.claude/skills/pipeline-*` (symlinked from the clone).
- Per-repo state: `.pipeline-state/` (gitignored) — the program counter.
- Per-repo config: the `<!-- pipeline-config -->` block in your `CLAUDE.md`.
- Templates: this repo's `templates/*.json` (or a project-local `.pipeline-templates/`).
