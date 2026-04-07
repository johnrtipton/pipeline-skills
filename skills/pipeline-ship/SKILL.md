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
2. Check for existing changes:
   - `git status -s` — must have modified/added/untracked files OR recent commits not on target
   - If no changes found, abort: "Nothing to ship."
3. Determine branch:
   - If already on a feature branch (not main/master): use it
   - If on main: create a new branch from `--branch` or auto-generate
4. Determine description:
   - If `--description` provided: use it
   - Otherwise: read the diff and generate a one-line summary
5. Create state file:
   - Read template from the pipeline plugin's `templates/ship-state.json` (locate via directory containing `pipeline.py`, or `PIPELINE_SKILL_DIR` env var)
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
| 9 | **Merge PR** | Verify CI, squash-merge, delete branch | `PR_MERGED` |
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
