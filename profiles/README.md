# Project profiles

A profile is the **project-specific half** of the pipeline: detection, environment
commands, the security patterns a reviewer should look for, the shapes that
auto-reject a change, and per-stage checklist items the generic templates cannot
know. `pipeline.py` picks a profile by its `detection` rules and merges its
`stage_additions` and `stage_replacements` into the run's state file;
`/pipeline-ship` gets the same through `pipeline.py ship --init-only`.

Two profiles ship: `django.json` (also used by the djust consumer) and
`generic.json` (the fallback). A project may add its own beside them.

**Private profiles.** This repo is public. A profile that encodes a company's
internal repos, people or process goes in `~/.config/pipeline-skills/profiles/`
(or the directory in `PIPELINE_PROFILES_DIR`), never here. That directory is
searched first, and a profile there with a built-in's name shadows it. Check one
with `make validate-profiles DIRS="profiles ~/.config/pipeline-skills/profiles"`.

**Selection.** `--profile <name>` → `pipeline_profile: <name>` in the project's
`CLAUDE.md` → the first profile whose `detection` matches, the highest
`detection_priority` first (ties by name) → `generic`. Give a project profile a
priority above `django` (10), so a repo that names itself in its manifest gets
its own profile even when it also uses a framework.

## Schema

| key | meaning |
|---|---|
| `name`, `description` | identity |
| `detection` | list of `{file, contains?}`; the profile matches when any rule matches (`contains` is case-insensitive) |
| `detection_priority` | **NEW** — int; profiles are tried highest first. `generic` 0, `django` 10, a project profile 100 |
| `environment.smoke_test` | one-liner proving the toolchain imports |
| `environment.venv_check` | whether to assert a venv is active |
| `environment.dependency_command` | install command (`null` = none) |
| `environment.isolation` | **NEW** — how to run tests in a git worktree without silently testing the main checkout. `why`, `run_prefix`, `verify`, `worktree_setup[]`, `do_not_symlink[]` |
| `environment.regenerate` | **NEW** — `command`, `artifacts[]`, `why`. What to run when generated artifacts conflict on a sibling merge: regenerate them, never hand-merge |
| `merge` | **NEW** — `method` (`squash`\|`merge`\|`rebase`), `admin_authorized` (is bypass sanctioned?), `why` |
| `completion.artifacts[]` | **NEW** — what "this bucket is done" means; read by `gate_retro_coverage` |
| `test.gate_off_required` | **NEW** — must every regression case be shown RED without the fix? |
| `security_patterns[]` | reviewer prompts |
| `auto_reject_triggers[]` | shapes that fail a change outright |
| `stage_additions` | `{"<type>.<stage-number>": [{action, done, mandatory?}]}`, merged into the state file |
| `stage_replacements` | **NEW** — `{"<type>.<stage-number>": [{match, action, mandatory?, in?}]}`. Replaces the first template checklist item whose action contains `match`; with `"in": "subagent_prompt"` it swaps the `match` text inside the stage's subagent prompt instead. For a template step that must not run in the project (post the review, a plain `git push`): `stage_additions` can only add. A replacement that matches nothing prints a warning |
| `scaffolding` | **NEW** — `commit_to_repo` (may pipeline-init commit its files?), `ignore_file` (`.gitignore` or `.git/info/exclude`: where `.pipeline-state/` and `.pipeline-log.md` are ignored), `why`. Use `false` and `.git/info/exclude` for a repo the team owns |
| `docs[]` | project docs a stage should read |

## Rules for contributors

- **Add a new key to EVERY profile**, even when only one project uses it — with a
  neutral value (`null`, `[]`, `false`) elsewhere. A key that exists in one file
  and not another is a schema that can only be learned by reading that file, and
  the consumer side then cannot rely on it.
- **State the `why` in the profile, not just the value.** These fields encode
  incidents; a command with no reason attached gets deleted by the next person who
  finds it inconvenient.
- **Prefer a field over prose in a skill.** Project knowledge that lives in
  `skills/*/SKILL.md` is re-derived by every consumer; the same knowledge as a
  profile field is read.
