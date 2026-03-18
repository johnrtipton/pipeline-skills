# Pipeline Skills for Claude Code

Development pipeline skills that turn Claude Code into a self-orchestrating development agent. Each skill encodes a complete software development workflow — from environment setup through implementation, testing, review, and merge.

## Skills

| Skill | Command | Description |
|---|---|---|
| **pipeline-feature** | `/pipeline-feature <task>` | Full feature implementation: planning, TDD, test, self-review, security, docs, commit & PR, code review, merge |
| **pipeline-bugfix** | `/pipeline-bugfix <bug report>` | Bug fix: diagnosis, targeted fix, regression check, test, docs, commit & PR, code review, merge |
| **pipeline-refactor** | `/pipeline-refactor <description>` | Refactor: analysis, behavior-preserving execution, review, test, docs, commit & PR, code review, merge |
| **pipeline-shared** | *(reference only)* | Shared procedures used by all pipeline skills — not invoked directly |

## Installation

Copy the skill directories into your Claude Code skills folder:

```bash
cp -r skills/* ~/.claude/skills/
```

Or symlink them:

```bash
for skill in skills/pipeline-*; do
  ln -sf "$(pwd)/$skill" ~/.claude/skills/$(basename $skill)
done
```

## How It Works

Each pipeline skill guides Claude Code through a multi-stage development workflow in a single session:

1. **Environment Check** — validate project env, create fresh branch from upstream
2. **Type-specific stages** — planning/diagnosis/analysis → implementation/fix/refactor
3. **Quality gates** — test execution, self-review, security scan (self-enforcing with retry + rewind)
4. **Ship it** — documentation, commit & PR, code review, merge, retrospective

### Quality Gates

Every stage has a self-enforcing quality gate:
- **Retry**: On failure, the stage retries once (attempt 2 of 2)
- **Rewind**: If retry fails, stages with rewind capability go back to an earlier stage (e.g., Self-Review → Planning)
- **Stop**: If all retries and rewinds are exhausted, the pipeline stops with a clear failure report

### Context Continuity

Unlike subprocess-based orchestrators that lose context between stages, these skills run in a single Claude Code session. The Self-Review stage can directly reference the Planning output. The Regression Check can directly reference the Diagnosis. No information loss.

### Independent Evaluation

Security Check and Retrospective run as subagents (via Claude Code's Agent tool) for independent evaluation with clean context — preventing bias from the implementation session.

## Customization

The skills read project configuration from CLAUDE.md in the project root. Supported config:
- `test_command` — how to run tests
- `venv_path` — virtual environment location
- `default_branch` — main branch name
- `pr_target_branch` — branch PRs should target
- `build_command`, `lint_command`

If CLAUDE.md doesn't specify these, the skills auto-detect from Makefile, pyproject.toml, package.json, etc.

## Origin

These skills were derived from the [djust-orchestrator](https://github.com/tip/djust-orchestrator) pipeline engine, which runs the same methodology via Django-managed subprocess agents. The skill versions trade fleet management (multi-task concurrency, per-stage cost tracking, DB observability) for context continuity and simplicity.

## License

MIT
