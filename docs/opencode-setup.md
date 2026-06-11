# Using Pipeline Skills with OpenCode

This guide gets you from zero to running `/pipeline-run` in OpenCode's TUI.

## Prerequisites

- macOS or Linux
- `git` and [`gh` CLI](https://cli.github.com/) installed and authenticated (`gh auth status`)
- A GitHub repo you want to run pipelines against

## Quick Start (5 minutes)

```bash
# 1. Install OpenCode
curl -fsSL https://opencode.ai/install | bash

# 2. Clone pipeline-skills
git clone https://github.com/johnrtipton/pipeline-skills.git ~/pipeline-skills

# 3. Install for OpenCode (+ USAi provider if you have a key)
cd ~/pipeline-skills
./install-opencode.sh              # basic install
./install-opencode.sh --with-usai  # also configure USAi API provider

# 4. Set your API key (if using USAi)
echo "export USAI_API_KEY='<client-id>:<client-secret>'" >> ~/.zshrc
source ~/.zshrc

# 5. Go!
cd ~/my-project
opencode -m usai/claude_4_6_sonnet
```

Then in the OpenCode TUI:
```
/pipeline-init                        # one-time repo setup
/pipeline-run --milestone v1.0        # run tasks from your roadmap
/pipeline-ship                        # ship uncommitted work
```

## What the installer does

`install-opencode.sh` does three things:

1. **Symlinks skill files** to `~/.claude/skills/pipeline-*/` (same as the Claude Code install — both tools read from the same location)

2. **Creates OpenCode commands** in `~/.config/opencode/commands/pipeline-*.md` — thin wrappers that tell OpenCode "read this SKILL.md and follow it"

3. **Optionally configures USAi** as an OpenAI-compatible provider in `~/.config/opencode/opencode.jsonc`

## Available commands

| Command | What it does |
|---------|-------------|
| `/pipeline-init` | One-time repo setup (detect branch, scaffold state/templates/config) |
| `/pipeline-next` | Pick next task from ROADMAP.md, create state file |
| `/pipeline-run` | Execute pipeline stages from the state file |
| `/pipeline-ship` | Ship working-tree changes through quality gates to merged PR |
| `/pipeline-dev` | Fast iteration loop (no formal review) |
| `/pipeline-strategy` | Plan the next milestone |
| `/pipeline-retro` | Run milestone retrospectives |
| `/pipeline-drain` | Drain GitHub issues into milestone and process |
| `/pipeline-cycle` | Outer loop: strategy → run → retro to terminal state |

## Headless mode (via `pipeline.py`)

The harness can drive OpenCode non-interactively for CI or batch processing:

```bash
python3 ~/pipeline-skills/pipeline.py feature \
  --task "Add health check endpoint" \
  --project ~/my-project \
  --agent opencode \
  --agent-model usai/claude_4_6_sonnet
```

Or process an entire milestone:
```bash
python3 ~/pipeline-skills/pipeline.py auto \
  --project ~/my-project \
  --milestone v1.0 --all \
  --agent opencode --agent-model usai/claude_4_6_sonnet
```

The `--agent` choice persists in the state file, so `--resume` keeps using the same backend.

## Model options

With the USAi provider configured, these models are available:

| Model ID | Use case |
|----------|----------|
| `usai/claude_4_6_sonnet` | Best balance of speed and quality (recommended) |
| `usai/claude_4_8_opus` | Highest quality, slower |
| `usai/claude_4_5_haiku` | Fastest, good for simple stages |
| `usai/gemini-2.5-flash` | Fast alternative |

Pass via `-m` in the TUI or `--agent-model` with the harness.

## Setting a default model

Pin a default model so you don't have to pass `-m` every time:

```bash
# In your project's .opencode/config.jsonc (per-project)
{
  "model": "usai/claude_4_6_sonnet"
}
```

Or launch with: `opencode -m usai/claude_4_6_sonnet`

## Pinning the backend per-project

Add to your project's `CLAUDE.md` (in the pipeline-config block):

```markdown
- pipeline_agent: opencode
```

Then the harness uses OpenCode by default for that project without needing `--agent`.

## Differences from Claude Code

| | Claude Code | OpenCode |
|--|--|--|
| Skill discovery | Native (`~/.claude/skills/`) | Via custom commands reading the same files |
| Slash commands | Built-in | `~/.config/opencode/commands/*.md` |
| Headless flag | `claude -p PROMPT` | `opencode run PROMPT` (positional) |
| Working dir | Honors process cwd | Requires `--dir` flag (handled by harness) |
| Unattended edits | Default with `-p` | Needs `--dangerously-skip-permissions` |
| Max turns | `--max-turns N` | Not available |
| Model format | `--model name` | `-m provider/model` |

## Troubleshooting

**"Permission denied" when reading skill files**
OpenCode will prompt the first time it tries to read `~/.claude/skills/`. Approve it — it's remembered for future sessions.

**Commands not appearing**
Restart OpenCode after running the installer. Commands are loaded at startup from `~/.config/opencode/commands/`.

**"No incomplete pipeline found"**
Run `/pipeline-init` first (one-time repo setup), then `/pipeline-next --milestone v1.0` to pick a task.

**Model not found**
Run `opencode models` to list configured models. If using USAi, verify `USAI_API_KEY` is exported.
