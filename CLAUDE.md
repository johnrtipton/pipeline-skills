# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A development pipeline harness for Claude Code. `pipeline.py` is an external script that drives Claude Code through multi-stage quality pipelines (feature, bugfix, refactor, ship) by controlling stage flow via state files. Claude handles the work within each stage; the script ensures every stage runs — solving the problem of context compression losing later-stage instructions.

## Architecture

**Two execution modes:**

1. **`pipeline.py` (recommended)** — External harness runs each stage as a separate `claude -p` call. Stages can't be skipped. State file on disk is the program counter.

2. **Skills (`/pipeline-next`, `/pipeline-run`, `/pipeline-ship`)** — Single-session mode via Claude Code skills installed to `~/.claude/skills/`. Simpler but stages may be skipped due to context compression. Best for small tasks.

**Core flow:**
```
pipeline.py reads state file → builds prompt from stage checklist → calls claude -p → 
extracts verdict from output → updates state file → repeats for next stage
```

**Key components:**
- `pipeline.py` — The harness: state management, verdict extraction, stage loop, ROADMAP parser, auto mode, profile system
- `profiles/*.json` — Framework-specific customization (security patterns, checklist items, auto-reject triggers)
- `templates/*.json` — State file templates defining all stages, checklists, verdicts, and subagent prompts per pipeline type
- `skills/pipeline-shared/SKILL.md` — Shared stage procedures (environment check, testing, security, review, merge, retro)
- `skills/pipeline-next/SKILL.md` — Task picker: parses ROADMAP.md, filters by milestone/priority, groups related tasks
- `skills/pipeline-run/SKILL.md` — Stage executor: reads state file, spawns agents per stage, updates state
- `skills/pipeline-ship/SKILL.md` — Ships existing working tree changes through quality gates to merged PR

**State files** live in the target project at `.pipeline-state/<branch>.json` (gitignored). They track per-stage status, checklists with mandatory flags, verdicts, PR info, and enable resume after interruption.

**Verdict system:** The harness scans Claude's output for verdict strings (e.g., `TESTS_PASSED`, `REVIEW_FAILED`, `PR_MERGED`). FAILED always overrides PASSED. Failed stages halt the pipeline for `--resume`.

## Profile System (3-layer customization)

Profiles customize security checks, checklist items, and conventions per framework. Three layers, each extending the previous:

1. **Built-in profiles** (`profiles/generic.json`, `profiles/django.json`) — Framework-level defaults
2. **Project CLAUDE.md** — Repo-level settings (`test_command`, `pipeline_profile`, etc.)
3. **Per-repo `.pipeline/` overrides** — Repo-specific template patches and extra checklist items

**Profile selection** (in priority order):
- `--profile django` CLI flag
- `pipeline_profile: django` in target project's CLAUDE.md
- Auto-detection: `manage.py` → django, fallback → generic

**Per-repo overrides:**
- `.pipeline/profile.json` — Extra security patterns, auto-reject triggers, stage checklist items
- `.pipeline/feature-state.json` — Complete template override for custom stage structures

**Merge order:** built-in template → project template override → built-in profile → project profile override → final state file

## Commands

```bash
# Install skills (symlink to ~/.claude/skills/)
./install.sh --symlink

# Start a pipeline (auto-detects profile)
python pipeline.py feature --task "Add health check endpoint" --project ~/my-project

# Start with explicit profile
python pipeline.py bugfix --task "Fix auth bug" --project ~/my-project --profile django

# Resume interrupted pipeline
python pipeline.py --resume --project ~/my-project

# Check pipeline status
python pipeline.py --list --project ~/my-project

# Auto mode — process tasks from ROADMAP.md
python pipeline.py auto --project ~/my-project --milestone v1.0 --priority P0
python pipeline.py auto --project ~/my-project --milestone v1.0 --all
python pipeline.py auto --project ~/my-project --list --milestone v1.0
```

No tests, no build step, no linter configured. This is a standalone Python 3.12+ script with no dependencies beyond the standard library. It shells out to `claude` CLI and `gh` CLI.

## Pipeline Types and Stage Counts

- **Feature**: 14 stages (env → change detection → conflict → planning → implementation → test → self-review → security → docs → commit/PR → code review → review verdict → merge → retro)
- **Bugfix**: 12 stages (env → conflict → diagnosis → fix → test → regression → docs → commit/PR → review → verdict → merge → retro)
- **Refactor**: 12 stages (env → conflict → analysis → refactor → test → review → docs → commit/PR → review → verdict → merge → retro)
- **Ship**: 10 stages (inventory → test → self-review → security → docs → commit/PR → review → verdict → merge → retro)

## Key Design Decisions

- Stages marked `"run_as": "subagent"` include a `subagent_prompt` field — these are post-PR stages (code review, merge, retro) that need fresh context
- Stages with `"skip_if": "DOCS_ONLY"` are conditionally skipped when change detection found only markdown changes
- Checklist items with `"mandatory": true` flag actions most likely to be skipped (GitHub postings, verdict outputs)
- The harness does NOT self-approve PRs (GitHub blocks it). Reviews are posted as comments, then merged directly
- `parse_roadmap()` and `parse_priority_matrix()` parse structured ROADMAP.md files with milestone headings and priority tables — these are tightly coupled to a specific markdown format
- Templates are framework-agnostic; framework-specific checks are injected at runtime via profiles
- Also published as a flexion plugin at `flexion-ai-claude-plugin/flexion-ai-pipeline/`
