# Pipeline Skill

A development pipeline harness for Claude Code. Runs multi-stage pipelines (feature, bugfix, refactor) with enforced quality gates, PR reviews, and retrospectives. Ships as both:

- **8 interactive skills** (`/pipeline-next`, `/pipeline-run`, `/pipeline-ship`, etc.) for use from a Claude Code chat — this is the primary interface
- **`pipeline.py` harness** for autonomous / headless runs against a project

## The Problem

Claude Code can't reliably execute a 15-stage pipeline from a single skill prompt. As the conversation grows, the original instructions get pushed out of active attention. The model implements the fix but skips code review, forgets to post the PR review to GitHub, and never runs the retrospective. See [CLAUDE.md § Why the state file is the program](CLAUDE.md) for the full failure-mode writeup.

## The Solution

**The state file is the program. The model is the executor.** Every pipeline creates `.pipeline-state/<branch>.json` on disk — a complete, persistent record of every stage and every mandatory checklist item. The model must tick off checklist items from this file (fresh from disk, not remembered from earlier in the conversation) before advancing a stage. This pattern defends against the four LLM failure modes (attention dilution, summarization loss, rationalization drift, plausible-sounding shortcuts) that break long-running agentic work.

## Skill Reference

Each skill is a single `SKILL.md` invoked by typing `/<skill-name>` in Claude Code.

| Skill | What it does | When to use |
|-------|--------------|-------------|
| [`/pipeline-next`](skills/pipeline-next/SKILL.md) | Parses `ROADMAP.md`, filters by milestone/priority, picks the next task, creates `.pipeline-state/<branch>.json` from the template. Can `--group` related small features into batches | Start of every feature from a roadmap |
| [`/pipeline-run`](skills/pipeline-run/SKILL.md) | Stage executor. Reads the state file, spawns agents for each pending stage, updates state after each. Can process a single task, all tasks in a milestone (`--all`), or all milestones | After `/pipeline-next`, or to resume an interrupted run |
| [`/pipeline-ship`](skills/pipeline-ship/SKILL.md) | Takes existing uncommitted/committed changes in your working tree and runs them through test → review → security → docs → commit → PR → code review → merge → retro | When you've been coding interactively and want to formalize and ship |
| [`/pipeline-dev`](skills/pipeline-dev/SKILL.md) | Fast-iteration loop for early development: branch → implement → push → verify → merge. No subagent review, no CHANGELOG, no roadmap coupling | Early exploration, where **you** are the reviewer (manual browser/CLI verification) |
| [`/pipeline-retro`](skills/pipeline-retro/SKILL.md) | Milestone retrospectives + Action Tracker reconciliation. Synthesizes per-PR retros into `RETRO.md`, creates GitHub issues for deferred findings. `--reconcile` scans all tracking locations for drift | End of every milestone |
| [`/pipeline-roadmap-audit`](skills/pipeline-roadmap-audit/SKILL.md) | Verifies every "not started" ROADMAP entry against the actual codebase. Catches stale entries where a feature shipped but the ROADMAP still claims it's pending | Before cutting a release candidate; after large consolidations |
| [`/pipeline-drain`](skills/pipeline-drain/SKILL.md) | Drains open GitHub issues (optionally by label) into the current milestone, then runs `/pipeline-run --milestone --all` to process them all | Tech-debt sprint day; processing a backlog of retro-created issues |
| [`/pipeline-shared`](skills/pipeline-shared/SKILL.md) | Shared stage procedures (env check, testing, security, docs, PR, review, merge, retro) referenced by the other pipeline skills. **Not invoked directly** | Internal — referenced by name from the other skills |

### How the skills chain

```
FEATURE FROM ROADMAP:
  /pipeline-next --milestone v0.4.0          # pick P0 task, create state file
  /pipeline-next --milestone v0.4.0 --group  # pick + batch related small tasks
  /pipeline-run                              # execute all stages
  /pipeline-run --milestone v0.4.0 --all     # process every remaining task

AD-HOC WORK IN WORKING TREE:
  [code freely]
  /pipeline-ship --description "fix rendering bug"   # formalize and ship

FAST ITERATION (no CI, no formal review):
  /pipeline-dev                              # branch → implement → verify → merge

END OF MILESTONE:
  /pipeline-retro --milestone v0.4.0         # synthesize per-PR retros
  /pipeline-retro --actions                  # show open action-tracker items
  /pipeline-retro --reconcile                # create GitHub issues for deferred findings

HYGIENE:
  /pipeline-roadmap-audit --milestone v0.5.0 # verify ROADMAP matches reality
  /pipeline-drain --label tech-debt          # batch-process open tech-debt issues
```

## Quick Start

```bash
# Clone
git clone git@github.com:johnrtipton/pipeline-skills.git ~/pipeline-skill
cd ~/pipeline-skill

# Install skills into Claude Code
./install.sh --symlink

# In Claude Code, from within your target project:
/pipeline-next --milestone v0.4.0
/pipeline-run
```

That's it. Your project should have a `ROADMAP.md` for `/pipeline-next` to parse, a `CLAUDE.md` for project-specific rules, and ideally a `.pipeline-templates/feature-state.json` if you want to customize stages (otherwise the built-in templates are used).

### Also supported: autonomous `pipeline.py` harness

For headless / CI / cron runs, there's a `pipeline.py` external harness. Most developers won't need this — the interactive skills are the primary interface. Skip to [`pipeline.py` details](#pipelinepy-autonomous-harness-advanced) below if you have a reason to run the pipeline without a human in the chat.

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

## `pipeline.py` (autonomous harness, advanced)

For headless / cron / unattended runs where no human is in the chat, `pipeline.py` wraps the same templates + stages but drives them by shelling out to `claude -p`. Use this when:

- You want a pipeline to run from a CI job or cron
- You need multiple pipelines to run sequentially without you approving each `/pipeline-run` invocation
- You're processing a milestone queue (`auto` mode) on a long overnight run

```bash
# Run a bugfix pipeline autonomously
python pipeline.py bugfix \
  --task "Fix event sequencing during ticks (#560)" \
  --project ~/my-project

# Feature pipeline targeting a dev branch
python pipeline.py feature \
  --task "Add dj-value-* static event params" \
  --project ~/my-project \
  --target-branch dev/v0.4.0

# Resume after interruption
python pipeline.py --resume --project ~/my-project

# Check status
python pipeline.py --list --project ~/my-project

# Auto mode — process tasks from ROADMAP.md
python pipeline.py auto --project ~/my-project --milestone v1.0 --priority P0
python pipeline.py auto --project ~/my-project --milestone v1.0 --all
```

Both modes read the same state files and templates. You can start interactively (`/pipeline-run`) and finish with the harness (`pipeline.py --resume`), or vice versa. Interactive is the default for most day-to-day work.

## Project Structure

```
pipeline-skill/
├── pipeline.py                         # Autonomous harness (advanced)
├── install.sh                          # Install skills into ~/.claude/skills/
├── profiles/
│   ├── generic.json                    # Framework-agnostic defaults
│   └── django.json                     # Django/Python-specific checks
├── templates/
│   ├── feature-state.json              # Feature pipeline template (15 stages)
│   ├── bugfix-state.json               # Bug fix pipeline template (12 stages)
│   ├── refactor-state.json             # Refactor pipeline template (12 stages)
│   └── ship-state.json                 # Ship pipeline template (10 stages)
└── skills/
    ├── pipeline-next/SKILL.md          # Task picker from ROADMAP.md
    ├── pipeline-run/SKILL.md           # Stage executor
    ├── pipeline-ship/SKILL.md          # Ship existing working tree changes
    ├── pipeline-dev/SKILL.md           # Fast-iteration loop (no subagent review)
    ├── pipeline-retro/SKILL.md         # Milestone retros + action tracker
    ├── pipeline-roadmap-audit/SKILL.md # Catch stale ROADMAP entries
    ├── pipeline-drain/SKILL.md         # Batch-process open GitHub issues
    └── pipeline-shared/SKILL.md        # Shared procedures (referenced, not invoked)
```

## Profile System

Profiles customize security checks, checklist items, and conventions for your framework. Three customization layers:

### Layer 1: Built-in Profiles

```bash
# Auto-detects profile from project files (manage.py → django)
python pipeline.py feature --task "Add endpoint" --project ~/my-project

# Or specify explicitly
python pipeline.py feature --task "Add endpoint" --project ~/my-project --profile django
```

**Available profiles:**
- `generic` — Framework-agnostic: secrets, shell injection, eval/exec, raw SQL, XSS
- `django` — Adds: mark_safe, csrf_exempt, |safe, pytest, f-string logger checks

### Layer 2: Project CLAUDE.md

Set `pipeline_profile: django` in your project's CLAUDE.md to auto-select a profile.

### Layer 3: Per-repo `.pipeline/` Overrides

Drop files in your project's `.pipeline/` directory:

- **`.pipeline/profile.json`** — Extra security patterns, auto-reject triggers, or stage checklist items merged on top of the selected profile:
  ```json
  {
    "security_patterns": ["custom pattern for this repo"],
    "stage_additions": {
      "feature.5": [
        {"action": "verify dual-path wiring", "done": false, "mandatory": true}
      ]
    }
  }
  ```

- **`.pipeline/feature-state.json`** — Complete template override for projects needing different stages.

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

The Code Review stage flags these as critical issues (generic profile):
- `print()` instead of project logging system
- Silent exception handling (`except: pass`)
- No tests for new functionality
- Tests reference modules/APIs that don't exist in the diff
- Placeholder/stub code shipped as production

The Django profile adds: f-string loggers, `console.log` guards, `mark_safe()` interpolation, `|safe` on user vars, missing CHANGELOG.

## Flexion Plugin

Also published as a plugin for the [flexion-ai-claude-plugin](https://github.com/flexion/flexion-ai-claude-plugin) marketplace at `flexion-ai-pipeline/`. The plugin includes activation phrases for skill auto-discovery.

## Origin

Derived from the [djust-orchestrator](https://github.com/tip/djust-orchestrator) pipeline engine. The orchestrator runs the same methodology via Django-managed subprocess agents with full DB observability, brain-level task dispatch, and multi-pipeline concurrency. This repo is the lightweight standalone version — same quality gates, no infrastructure.

## License

MIT
