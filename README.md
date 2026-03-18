# Pipeline Skill

A development pipeline harness for Claude Code. Runs multi-stage pipelines (feature, bugfix, refactor) with enforced quality gates, PR reviews, and retrospectives.

## The Problem

Claude Code can't reliably execute a 13-stage pipeline from a single skill prompt. Context compression loses later stage instructions — the agent implements the fix but skips code review, forgets to post the PR review to GitHub, and never runs the retrospective.

## The Solution

**`pipeline.py`** — a lightweight external harness that controls the stage flow. Claude Code handles the work within each stage; the script ensures every stage runs.

```
pipeline.py (external loop)
  ├── reads state file from template (all stages + checklists)
  ├── for each pending stage:
  │     ├── builds focused prompt from checklist + subagent_prompt
  │     ├── calls `claude -p` with that prompt
  │     ├── extracts verdict from output
  │     ├── updates state file
  │     └── continues or stops
  └── prints summary when all stages complete
```

## Quick Start

```bash
# Clone
git clone <repo-url> ~/pipeline-skill
cd ~/pipeline-skill

# Install skills (optional — for /pipeline-feature etc. in Claude Code)
./install.sh --symlink

# Run a bugfix pipeline
python pipeline.py bugfix \
  --task "Fix event sequencing during ticks (#560)" \
  --project ~/my-project

# Run a feature pipeline targeting a dev branch
python pipeline.py feature \
  --task "Add dj-value-* static event params" \
  --project ~/my-project \
  --target-branch dev/v0.4.0

# Resume after interruption
python pipeline.py --resume --project ~/my-project

# Check status
python pipeline.py --list --project ~/my-project
```

## Pipeline Types

### Feature (15 stages)

```
Env Check → Change Detection → Conflict Check → Planning → Implementation (TDD)
→ Test → Self-Review → Security Check → Documentation → Commit & PR
→ Code Review → Review Verdict → Merge → Retrospective
```

### Bug Fix (12 stages)

```
Env Check → Conflict Check → Diagnosis → Fix → Test → Regression Check
→ Documentation → Commit & PR → Code Review → Review Verdict → Merge
→ Retrospective
```

### Refactor (12 stages)

```
Env Check → Conflict Check → Analysis → Refactor Execution → Test → Review
→ Documentation → Commit & PR → Code Review → Review Verdict → Merge
→ Retrospective
```

## How It Works

### State File

Every pipeline is driven by a state file at `.pipeline-state/<branch-name>.json`. It's created from a template at pipeline start and updated after every stage.

```json
{
  "pipeline_type": "bugfix",
  "task_description": "Fix event sequencing during ticks (#560)",
  "branch_name": "fix/fix-event-sequencing-during-ticks-560",
  "current_stage": 5,
  "stages": {
    "1": {"name": "Environment Check", "status": "passed", "verdict": "ENV_OK"},
    "4": {"name": "Fix", "status": "passed", "verdict": "..."},
    "5": {
      "name": "Test Execution",
      "status": "pending",
      "checklist": [
        {"action": "run full test suite", "done": false},
        {"action": "output TESTS_PASSED or TESTS_FAILED", "done": false, "mandatory": true}
      ]
    }
  }
}
```

### Stage Checklists

Each stage has a checklist of actions. Items with `"mandatory": true` must be completed — these flag the actions most likely to be skipped (posting reviews to GitHub, writing to the pipeline log).

### Subagent Stages

Stages marked `"run_as": "subagent"` include a `subagent_prompt` field with the complete prompt. These are the post-PR stages (Code Review, Merge, Retrospective) that need fresh context for independent evaluation.

### Quality Gates

- **Verdict extraction**: The harness scans Claude's output for verdict strings (`TESTS_PASSED`, `REVIEW_FAILED`, `PR_MERGED`, etc.)
- **FAILED overrides PASSED**: If both appear, the result is FAILED
- **Stop on failure**: Failed stages halt the pipeline. Fix the issue and `--resume`
- **Skip conditions**: Stages with `"skip_if": "DOCS_ONLY"` are skipped when Change Detection found only markdown changes

### Resume

If a pipeline is interrupted (context limit, crash, Ctrl+C), the state file persists on disk. Run `--resume` to pick up from the last incomplete stage.

## What Gets Posted to GitHub

| Stage | What | Where |
|---|---|---|
| Commit & PR | PR with conventional commit message | `gh pr create` |
| Code Review | Formatted review with checklist + findings | `gh pr review --comment` |
| Review Verdict | APPROVE or REQUEST_CHANGES | `gh pr comment` or `gh pr review --request-changes` |
| Retrospective | Quality rating, lessons, improvements | `gh pr comment` |

Note: The harness does NOT self-approve PRs (GitHub blocks approving your own PRs). It posts the review as a comment, then merges directly.

## What Gets Persisted Locally

| File | Content | Gitignored |
|---|---|---|
| `.pipeline-state/<branch>.json` | Stage-by-stage progress with checklists | Yes |
| `.pipeline-status.md` | Summary of all pipeline runs | No |
| `.pipeline-log.md` | Retrospective history (lessons, improvements) | Yes |
| `pr/feedback/pr-<N>-<slug>.md` | Review feedback (if project uses this convention) | No |

## Project Structure

```
pipeline-skill/
├── pipeline.py                         # External harness — runs the stage loop
├── install.sh                          # Install skills into ~/.claude/skills/
├── templates/
│   ├── feature-state.json              # Feature pipeline template (15 stages)
│   ├── bugfix-state.json               # Bug fix pipeline template (12 stages)
│   └── refactor-state.json             # Refactor pipeline template (12 stages)
└── skills/
    ├── pipeline-shared/SKILL.md        # Shared procedures (reference)
    ├── pipeline-feature/SKILL.md       # Feature pipeline skill
    ├── pipeline-bugfix/SKILL.md        # Bug fix pipeline skill
    ├── pipeline-refactor/SKILL.md      # Refactor pipeline skill
    └── pipeline-auto/SKILL.md          # ROADMAP parser + task runner skill
```

### Two ways to use

1. **`pipeline.py` (recommended)** — External harness enforces every stage. Each stage runs as a separate `claude -p` call. Stages can't be skipped.

2. **Skills (`/pipeline-feature` etc.)** — Single-session mode. Claude Code reads the skill and executes all stages in one session. Simpler but stages may be skipped due to context compression. Best for small tasks where context continuity matters more than stage enforcement.

## Customization

### Project Configuration

The pipeline reads project config from CLAUDE.md in the project root:
- `test_command` — how to run tests (e.g., `make test`, `pytest`)
- `venv_path` — virtual environment location
- `default_branch` — main branch name
- `pr_target_branch` — branch PRs should target
- `build_command`, `lint_command`

Auto-detects from Makefile, pyproject.toml, package.json if not specified.

### PR Review Checklist

If the project has `docs/PULL_REQUEST_CHECKLIST.md`, the Code Review stage uses it as the review framework. The checklist is loaded by the review subagent and used to structure findings.

### Auto-Reject Triggers

The Code Review stage flags these as critical issues:
- `print()` instead of project logging system
- f-string formatting in logger calls
- `console.log` without debug guards
- Silent exception handling (`except: pass`)
- No tests for new functionality
- `mark_safe()` with unescaped interpolation
- `|safe` on user-controlled variables
- Placeholder/stub code shipped as production
- Missing CHANGELOG update for feat/fix PRs

## Origin

Derived from the [djust-orchestrator](https://github.com/tip/djust-orchestrator) pipeline engine. The orchestrator runs the same methodology via Django-managed subprocess agents with full DB observability, brain-level task dispatch, and multi-pipeline concurrency. This repo is the lightweight standalone version — same quality gates, no infrastructure.

## License

MIT
