---
name: pipeline-ship
description: >
  Ship existing changes through quality gates to a merged PR.
  Starts from uncommitted/committed changes in your working tree and runs
  test → review → security → docs → commit → PR → code review → merge → retrospective.
  Use when you've been coding interactively and want to formalize and ship.
---

# pipeline-ship

Ship existing changes through quality gates to a merged PR. Unlike `pipeline-next` + `pipeline-run` which starts from a ROADMAP task, `pipeline-ship` starts from **changes already in your working tree** (staged, unstaged, or recently committed) and runs them through test → review → security → docs → commit → PR → code review → merge → retrospective.

Use this when you've been coding interactively and want to formalize, review, and ship what you have.

## Usage

```
/pipeline-ship                          # Ship all uncommitted changes
/pipeline-ship --description "..."      # Provide a description for the PR
/pipeline-ship --branch feat/my-thing   # Use a specific branch name
/pipeline-ship --no-merge               # Stop after PR creation (skip merge)
/pipeline-ship --resume                 # Resume an interrupted ship pipeline
```

## Arguments

- `--description "text"` — Task description for the PR and state file. If omitted, auto-generate from the diff.
- `--branch name` — Branch name. If omitted, derive from the current branch or auto-generate from the description.
- `--target branch` — PR target branch (default: `main`).
- `--no-merge` — Create the PR but do not merge. Stops after Code Review.
- `--resume` — Resume an interrupted pipeline from the last incomplete stage.

## How It Works

### Step 0: Initialize

1. Detect the project: `git rev-parse --show-toplevel`
2. **Worktree-staleness check** — if `git status` shows many deleted files against HEAD (`^ D ` lines) AND HEAD is a recent rebase/fast-forward, the worktree is stale from a pre-rebase populate. Sync before proceeding:
   ```bash
   STALE_D=$(git status -s | grep -c '^ D ')
   if [ "$STALE_D" -gt 5 ]; then
       echo "WARNING: $STALE_D deleted-against-HEAD entries — worktree appears stale."
       echo "If there is no genuine WIP, run: git reset --hard HEAD"
       echo "Otherwise stash WIP first."
   fi
   ```
   Observed cost: djust PR #836 pipeline-ship found 30+ stale `D` entries because the worktree was populated before the branch was rebased onto current main; had to `git reset --hard HEAD` before Stage 1 inventory was meaningful. A dozen `D` entries on a branch that claims to add code is a strong staleness signal.
2.5. **Stacked-PR check** — if the branch has merge commits pulling in another open PR's branch, surface the dependency before Stage 9 (Merge) discovers it as a 20+ conflict rebase:
   ```bash
   # Resolve the repo's default branch (pipeline-config → origin/HEAD → remote → fallback). Never assume main/master.
   BASE=$(sed -n 's/^- *default_branch: *//p' CLAUDE.md 2>/dev/null | awk 'NR==1{print $1}')
   [ -z "$BASE" ] && BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
   [ -z "$BASE" ] && BASE=$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p')
   [ -z "$BASE" ] && BASE=main
   MERGES=$(git log --merges --pretty=format:'%h %s' "origin/$BASE..HEAD" 2>/dev/null)
   if [ -n "$MERGES" ]; then
       echo "WARNING: branch contains merge commits from origin/$BASE..HEAD:"
       echo "$MERGES" | sed 's/^/  /'
       echo "If any source branch matches an open PR (gh pr list --state open),"
       echo "this PR is STACKED. After the base PR squash-merges to the default branch, this"
       echo "branch's history will diverge and Stage 9's merge will hit"
       echo "tree-equivalent-but-commit-different conflicts on every overlapping file."
       echo "Plan: merge base PR first, then rebase or merge the default branch here BEFORE Stage 6."
   fi
   ```
   Observed cost: max-companion PR #10 was stacked on PR #9 via merge commit `f445b66`. After PR #9 squash-merged, the resume of PR #10's pipeline-ship hit 21 conflicts across 7 files — all "same content, different commit identity." Resolvable but cost ~30 min of focused conflict-resolution work that a Step 2.5 warning would have surfaced upfront.
2.6. **MANDATORY — review with the THREE-DOT diff (the behind-base phantom-deletion trap).** Every stage that reads the diff — **Stage 1 (Inventory), Stage 3 (Self-Review), and the Stage 7 Code Review subagent** — MUST use the three-dot form:
   ```bash
   git diff "origin/$BASE...HEAD"     # ✅ changes since the merge-base — what the PR actually does
   git diff "origin/$BASE..HEAD"      # ❌ two-dot — LIES when the branch is behind its base
   ```
   **Why it matters:** two-dot `A..B` shows B relative to A's *tip*. When your branch is behind its base (base moved ahead after you forked), every commit the base gained shows up as a **phantom deletion** — as if your PR is *removing* that content. Three-dot `A...B` diffs from the merge-base, showing only what your branch changed. GitHub's PR view is three-dot; your local review must match it.
   ```bash
   # If the inventory shows large deletions of files/sections your PR never touched, do NOT conclude it reverts them. Confirm:
   git diff "origin/$BASE...HEAD" --stat      # the real change set
   git merge-tree "$(git merge-base HEAD "origin/$BASE")" HEAD "origin/$BASE" | grep -c '^<<<<<<<'   # 0 = clean merge
   ```
   Observed cost: max-companion PR #10's Stage 1 ran a two-dot diff on a branch 3 commits behind `origin/main` and showed ~90 phantom deletions — including the pipeline-ship Pre-Merge Gate and pipeline-drain Step 8.5 — looking as if the PR *reverted those safety gates*. It did not (three-dot: 984/13, `merge-tree`: 0 conflicts). The danger runs both ways: a false "this PR reverts gates" abort, or — if the phantom deletions are waved off — merging something that *genuinely* reverts base content while the reviewer assumes they're phantom. Always three-dot; when in doubt, `merge-tree`.
3. Check for existing changes:
   - `git status -s` — must have modified/added/untracked files OR recent commits not on target
   - If no changes found, abort: "Nothing to ship."
4. Determine branch:
   - If already on a feature branch (not main/master): use it
   - If on main: create a new branch from `--branch` or auto-generate
5. Determine description:
   - If `--description` provided: use it
   - Otherwise: read the diff and generate a one-line summary
6. Create state file:
   - Read template from the pipeline plugin's `templates/ship-state.json` (locate via directory containing `pipeline.py`, or `PIPELINE_SKILL_DIR` env var). Project-local `.pipeline-templates/ship-state.json` overrides the default — see pipeline-next for the override convention.
   - Fill in: `task_description`, `branch_name`, `pr_target_branch`, `project_path`, `started_at`
   - Write to `.pipeline-state/<branch-name>.json`
   - Ensure `.pipeline-state/` is in `.gitignore`

### Step 1: Run the Stage Loop

Use the same stage loop as `pipeline-run`:

1. READ `.pipeline-state/<branch-name>.json`
2. FIND next stage where `status != "passed"`
3. EXECUTE checklist items for that stage
4. WRITE verdict and update state file
5. REPEAT until all stages pass or a stage fails

### Stage Definitions

The ship template has **10 stages** (compared to 14 for a full feature pipeline):

| # | Stage | What it does | Gate |
|---|-------|-------------|------|
| 1 | **Inventory Changes** | Catalog all changes (diff, status, classify) | `INVENTORY_COMPLETE` |
| 2 | **Test Execution** | Run full test suite | `TESTS_PASSED` / `TESTS_FAILED` |
| 3 | **Self-Review** | Re-read diff as reviewer, check auto-reject triggers, fix issues | `REVIEW_PASSED` / `REVIEW_FAILED` |
| 4 | **Security Check** | Scan for security patterns per profile (secrets, XSS, injection) | `SECURITY_PASSED` / `SECURITY_FAILED` |
| 5 | **Documentation** | Update docs, CHANGELOG, docstrings | `DOCS_UPDATED` / `DOCS_SKIPPED` |
| 6 | **Commit & PR** | Stage, commit, push, create PR | `PR_CREATED` / `PR_EXISTS` |
| 7 | **Code Review** | Subagent reviews the PR, posts to GitHub | `APPROVE` / `REQUEST_CHANGES` |
| 8 | **Review Verdict** | If changes requested → fix and re-review | `APPROVE` |
| 9 | **Merge PR** | **Pre-merge gate** (Code Review artifact + state), verify CI, squash-merge, delete branch | `PR_MERGED` |
| 10 | **Retrospective** | Quality rating, lessons learned, post to GitHub | `RETRO_COMPLETE` |

Stages 2-4 (Test, Self-Review, Security) can run in **parallel** since they're all read-only.

Stages 2-4 are **skipped** if Inventory classified changes as `DOCS_ONLY`.

If `--no-merge` is passed, stages 9 and 10 are skipped.

### Stage Details

Refer to `pipeline-shared/SKILL.md` for detailed procedures on each stage. The ship pipeline uses the same stage implementations with these differences:

- **No Environment Check** — you're already in a working environment (you just made the changes)
- **No Planning/Implementation** — the code is already written
- **No Change Detection** — folded into Inventory (stage 1)
- **No Conflict Check** — folded into Commit & PR (stage 6)
- **Inventory stage** replaces the planning artifact with a changes summary

### MANDATORY Pre-Merge Programmatic Gate (Stage 9)

Code Review (Stage 7) and Retrospective (Stage 10) are load-bearing quality
gates, but the text imperatives are a **soft gate** — under context pressure or
a "ship it quick" frame the executor can skip the read entirely. This happened
on GSA-TTS/usai-admin-portal PR #13 (merged with neither stage run; post-hoc
review then caught a 🔴 critical auth-exemption on a credential endpoint,
needing 3 recovery PRs). Mirror `pipeline-run`'s post-commit gates with a
**programmatic** check that physically blocks the merge.

**Run this at the START of Stage 9, before `gh pr merge`. If it fails, STOP —
do not merge. Run the missing stage, then retry.**

```bash
# Gate 1 — state file: Code Review stage must have passed.
STATUS=$(python3 -c "import json; print(json.load(open('.pipeline-state/<branch>.json'))['stages']['7']['status'])")
[ "$STATUS" = "passed" ] || { echo "GATE FAIL: Stage 7 (Code Review) status=$STATUS, not passed. Run it before merge."; exit 1; }

# Gate 2 — artifact: a Code Review must exist on the PR. The Stage 7 subagent
# posts via `gh pr review --comment`, which lands in `.reviews[]` — NOT
# `.comments[]`. Check BOTH arrays or the gate false-fails on every ship.
# Defends against a state file ticked without the review actually happening.
REVIEW=$(gh pr view "$PR" --json comments,reviews -q '[.comments[].body, .reviews[].body] | join("\n")' | grep -ic "code review\|REQUEST_CHANGES\|APPROVE")
[ "$REVIEW" -ge 1 ] || { echo "GATE FAIL: PR #$PR has no Code Review artifact. Run Stage 7 before merge."; exit 1; }
```

**Retrospective (Stage 10)** runs post-merge, so its gate is checked at the END
of the pipeline: a per-PR retro comment must exist on the PR within the run. If
absent, the pipeline is not complete — run Stage 10.

```bash
RETRO=$(gh pr view "$PR" --json comments,reviews -q '[.comments[].body, .reviews[].body] | join("\n")' | grep -ic "retrospective\|RETRO_COMPLETE\|quality:")
[ "$RETRO" -ge 1 ] || { echo "GATE FAIL: PR #$PR has no Retrospective artifact. Run Stage 10."; exit 1; }
```

`--no-merge` runs skip Gate 1/2 (no merge happens) but should still reach
Stage 7 — the whole point of `--no-merge` is to stop *after* Code Review.

### Resume

If interrupted (context compression, error, user abort):

1. Check `.pipeline-state/` for state files with `completed_at == null`
2. Read the state file
3. Find first stage where `status != "passed"`
4. Continue from there

The state file is the program counter — all progress is on disk.

### Cleanup

When pipeline completes (`completed_at` is set):
- State file remains for audit (manually delete with `rm .pipeline-state/<branch>.json`)
- `.pipeline-state/` stays in `.gitignore`

### Configuration

Auto-detected from the project (same as pipeline-shared):
- `test_command` — from Makefile, pyproject.toml, package.json
- `venv_path` — `.venv/` or `venv/`
- `default_branch` — `main` or `master`
- `pr_target_branch` — same as default_branch unless overridden

## Examples

```bash
# You've been coding for an hour, changes look good — ship them
/pipeline-ship --description "add user authentication with OAuth2"

# Ship changes on an existing feature branch
/pipeline-ship --branch feat/oauth2-auth

# Just get it reviewed, don't merge yet
/pipeline-ship --no-merge

# Pick up where you left off after context compression
/pipeline-ship --resume
```

## What This Is NOT

- Not a replacement for `pipeline-next` + `pipeline-run` — those start from ROADMAP tasks
- Not for greenfield work — this assumes code is already written
- Not for reviewing someone else's PR — use `pr-workflow` for that
