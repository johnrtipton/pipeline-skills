# Project profiles

A profile is the **project-specific half** of the pipeline: detection, environment
commands, the security patterns a reviewer should look for, the shapes that
auto-reject a change, and per-stage checklist items the generic templates cannot
know. `/pipeline-next` matches a profile by `detection` and merges its
`stage_additions` into the run's state file.

Two profiles ship: `django.json` (also used by the djust consumer) and
`generic.json` (the fallback). A project may add its own beside them.

## Schema

| key | meaning |
|---|---|
| `name`, `description` | identity |
| `detection` | list of `{file, contains?}`; the first matching rule wins |
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
