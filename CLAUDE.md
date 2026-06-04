# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A development pipeline harness for Claude Code. `pipeline.py` is an external script that drives Claude Code through multi-stage quality pipelines (feature, bugfix, refactor, ship, strategy) by controlling stage flow via state files. Claude handles the work within each stage; the script ensures every stage runs — solving the problem of context compression losing later-stage instructions.

The same state-file-as-program pattern covers both **execution** (feature/bugfix/refactor/ship — make the change, ship it) and **planning** (strategy — decide what change to make next). The strategy pipeline is structurally identical: 8 stages with mandatory checklists, gated by a hard rule that ≥2 distinct paths must be presented before a recommendation is captured. See `skills/pipeline-strategy/SKILL.md`.

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
- `templates/*.json` — State file templates defining all stages, checklists, verdicts, and subagent prompts per pipeline type. Mandatory checklist items here are the strongest form of project canon (see [CANON.md](CANON.md) for how this venue compares to CLAUDE.md / pre-push / CI).
- `skills/pipeline-init/SKILL.md` — One-time repo bootstrap: detects default branch + test/lint/build commands, scaffolds `.pipeline-state/` and `.pipeline-templates/` (copied from `templates/*.json` with the detected branch/commands substituted), gitignore entries, CHANGELOG/RETRO stubs, and a `CLAUDE.md` pipeline-config block. Run once per repo before any other pipeline-* skill
- `skills/pipeline-shared/SKILL.md` — Shared stage procedures (environment check, testing, security, review, merge, retro)
- `skills/pipeline-next/SKILL.md` — Task picker: parses ROADMAP.md, filters by milestone/priority, groups related tasks
- `skills/pipeline-run/SKILL.md` — Stage executor: reads state file, spawns agents per stage, updates state
- `skills/pipeline-ship/SKILL.md` — Ships existing working tree changes through quality gates to merged PR
- `skills/pipeline-strategy/SKILL.md` — Plans the next milestone via state-file-driven 8-stage session: survey → brainstorm → triage → cluster → present-paths (≥2) → recommend → decide → capture (ROADMAP/ADR/next-step)

**State files** live in the target project at `.pipeline-state/<branch>.json` (gitignored). They track per-stage status, checklists with mandatory flags, verdicts, PR info, and enable resume after interruption.

**Verdict system:** The harness scans Claude's output for verdict strings (e.g., `TESTS_PASSED`, `REVIEW_FAILED`, `PR_MERGED`). FAILED always overrides PASSED. Failed stages halt the pipeline for `--resume`.

## Why the state file is the program (instruction rot is the real enemy)

The most important design decision isn't the stage count or the verdict system — it's that **the stages live in a JSON state file the LLM has to tick off**, not in the skill prompt itself. The rationale is worth making explicit because it shapes every other design choice.

### The problem: LLM instructions rot over a long conversation

A skill prompt is loaded once at session start. As the conversation grows (tool results, file reads, code diffs, intermediate analysis), the original instructions get pushed further from the model's active attention. By the time the model reaches Stage 11 of a 15-stage pipeline, the Stage 5 hard gates might as well be unread. Four well-documented LLM failure modes drive this:

- **Attention dilution** — earlier tokens compete with hundreds of recent tokens
- **Summarization loss** — context compression drops detail from the original prompt
- **Rationalization drift** — after many tool calls, the model invents permission to skip steps ("I already covered that," "this case doesn't need it")
- **Plausible-sounding shortcuts** — a tired model writes a PR description and calls the pipeline "done" without running the final review/retro stages

No amount of "MANDATORY" or "CRITICAL" or "YOU MUST" in the original skill prompt fixes this. The instruction is gone by the time it's needed.

### The solution: make the state file the program

Every pipeline run creates `.pipeline-state/<branch>.json` — a complete, persistent, versioned record of every stage and every mandatory checklist item. The model cannot advance a stage without:

1. **Reading the current state file from disk** — fresh tokens, not cached from 50 tool calls ago
2. **Locating the next pending stage and its checklist**
3. **Executing each checklist item with `"done": false` → `"done": true`**
4. **Writing the updated state file back to disk**
5. **Setting the stage's `verdict` and `status: "completed"` before moving on**

If the model is unsure what a specific checklist item actually requires, it **re-reads the skill file** — pulling the full definition back into active context rather than guessing from a half-remembered instruction.

The framing the `pipeline-run` skill itself uses:

> This skill is a tiny loop. **The state file is the program. You are the executor.**

That framing is intentional. The state file is data; the model is an interpreter. Every iteration of the loop is short-lived — read state, execute next checklist item, write state — so instruction rot cannot accumulate.

### Why this matters for auditability

Other AI-coding approaches rely on the model remembering its orders. This harness doesn't. Durability comes from forcing the model to **re-read fresh instructions at every stage boundary** and **record commitment in a format that can be audited after the fact**. A reviewer can open any `.pipeline-state/<branch>.json` and see exactly which checklist items the model checked off, when, and with what verdict.

This is also the reason post-PR stages (Code Review, Re-Review, Retrospective) run as **isolated subagents via `"run_as": "subagent"` + `subagent_prompt`**: a fresh agent with no conversation history forces a clean read of the PR, the checklist, and the diff — immune to the biases that would build up in the implementing agent's context.

### Design principle

Don't trust the model to remember. Build a structured artifact the model has to interact with. Let the artifact — not the skill prompt — be the authority.

## Capture everything, block nothing (the learning-channel design)

The most valuable information in a pipeline run is the stuff that surfaces *during* implementation and retro — accidental discoveries a traditional dev process would lose. When a model is mid-implementation on Feature A, it frequently notices things that are out-of-scope: a field missing a `db_index`, a form that silently discards data, a template typo, a test file that's outside the CI path, a security gap tangential to the current change. Without a capture channel, two bad things happen:

1. **Perfectionist mode** — the model stops Feature A to fix everything it sees. The PR sprawls, the batch-size limit breaks, a 30-minute feature becomes a 3-hour yak-shave.
2. **Ship-and-forget mode** — findings never get written down. Same bug rediscovered by three subsequent PRs; knowledge accumulated during implementation evaporates.

The harness solves this with **three explicit asynchronous escape hatches**, none of which stop the current PR:

| Channel | Where it lives | Processed by |
|---------|---------------|--------------|
| **PR retro** (`pr/feedback/retro-{N}-*.md`) | Written in Stage 15 of every pipeline. "What to improve" + "KB updates needed" sections capture ambient findings | `/pipeline-retro --reconcile` (at milestone end) |
| **GitHub issue** (label: `tech-debt`) | Stage 15 creates an issue for every deferred finding — a 15-second write that preserves the context | `/pipeline-drain --label tech-debt` (tech-debt sprint) |
| **RETRO.md Action Tracker** | Single source of truth. Each row: finding → source PR → GitHub issue → status | Human review / `/pipeline-retro --reconcile` |

A finding noticed during Feature A goes into Feature A's retro ("tangential finding: X needs Y"). At the next milestone retro, `/pipeline-retro --reconcile` scans every PR retro, deduplicates, and creates GitHub issues for anything still open. Weeks later, `/pipeline-drain --label tech-debt` batches those issues into a focused cleanup pass.

**The rule this replaces**: "fix it now" vs "ignore it." Neither is right. The right rule is: **ship what's in scope, capture what's out of scope, process captured items in dedicated sprints.** Stage 15 takes 30–60 seconds per finding to write a GitHub issue. The PR merges on schedule. The finding isn't lost. The next tech-debt sprint is able to batch similar findings together (e.g., "audit all templates for FK dot-notation" is 40 template edits in one PR, not 40 drive-by fixes across unrelated features).

### Retrospective structure

Every `pr/feedback/retro-{N}-*.md` should have five sections:

1. **What Worked** — patterns to repeat (so successful approaches don't get forgotten either)
2. **What Didn't Work** — bugs, wrong assumptions, dead-end approaches
3. **What to Improve** — candidate CLAUDE.md rules, new Stage 5 gates, or checklist items
4. **Knowledge Base Updates Needed** — domain facts discovered mid-implementation
5. **Review Stats** — findings found, fixed, deferred, re-review rounds

The "Knowledge Base Updates Needed" section is especially load-bearing when the project keeps a separate KB (see the three-phase process pattern below). Domain facts discovered mid-implementation flow through the retro → the milestone retro → a KB patch → the next feature benefits from the correction. No PR blocks, no knowledge lost.

## The three-phase process (recommended upstream workflow)

This harness assumes a three-phase project workflow. The harness itself only implements Phase 3, but works best when Phases 1 and 2 are in place:

```
PHASE 1: KNOWLEDGE BASE
  RFP / specs / domain research → a navigable, AI-readable KB
  (e.g., knowledgebase/ directory, Karpathy LLM Wiki pattern)
       ↓
PHASE 2: LIVING ROADMAP
  KB + priorities → ROADMAP.md with per-feature priority + status + milestone
  Rewritten after every retro (reorder, add, defer, split)
       ↓
PHASE 3: EXECUTE VIA THE PIPELINE
  /pipeline-next → /pipeline-run → /pipeline-retro
       ↕
  Feedback loops: retros → CLAUDE.md rules → Stage-5 gates →
                  tech-debt GitHub issues → /pipeline-drain → ROADMAP reorder
```

The three phases never freeze. The KB gets new files when gaps are discovered. The ROADMAP gets reordered after retros. The pipeline skills themselves evolve — new hard gates added every time an incident proves they're needed. A new project adopting this harness should scaffold all three phases; skipping Phase 1 or 2 leaves the pipeline with no grounding for the LLM's domain decisions.

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

<!-- pipeline-config: managed by /pipeline-init -->
## Pipeline configuration

- default_branch: main
- pr_target_branch: main
- test_command:            # none — standalone Python 3.12+ stdlib script, no test runner
- lint_command:            # none configured
- build_command:           # none — no build step
- venv_path:               # none
- changelog: keep-a-changelog
- state_templates: templates/   # this repo IS the canonical template source; pipeline-* skills resolve templates via the directory containing pipeline.py, so no .pipeline-templates/ copies are created here (they would be stale duplicates)
<!-- /pipeline-config -->
