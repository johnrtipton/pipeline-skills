# Canon and Enforcement Venues

> Where do project rules live, and why does it matter which venue
> you pick?

## What "canon" means here

A rule that has graduated from "lesson learned in a retro" to
"mechanically enforced by tooling." Pre-canon rules rely on operator
memory; post-canon rules rely on a forcing function. When a retro
recommends a new rule, the question isn't *whether* to canonicalize
it — it's *where*.

## Enforcement venues

Four common venues, ordered roughly from weakest to strongest guard:

| Venue | Where it lives | Fires when | Operator can bypass? |
|---|---|---|---|
| **CLAUDE.md canon** | Project `CLAUDE.md` | Agent reads + remembers | Easy (forget) |
| **Pre-push hook canon** | `.pre-commit-config.yaml`, `scripts/check-*.py` | At git push | Possible (`--no-verify`) |
| **CI workflow canon** | `.github/workflows/*.yml` | After push, on PR | Possible (admin merge bypass) |
| **Pipeline-template canon** | `.pipeline-templates/{feature,bugfix}-state.json` mandatory checklist items | Stage executor reads from disk and must tick mandatory box | Hard (gate-check refuses to advance the stage) |

These are the *common* venues, not an exhaustive list — projects may
add others (server-side git hooks, IDE plugins, etc.).

## Pipeline-template canon

A rule encoded as a `mandatory: true` checklist item or as text inside
a `subagent_prompt` in one of the project's pipeline state-file
templates (`.pipeline-templates/feature-state.json`,
`.pipeline-templates/bugfix-state.json`, etc.). The pipeline-run loop
reads templates fresh from disk between stages, so canon updates take
effect immediately for any new pipeline (no skill reinstall required).

Why it has the strongest guard:

- **Mandatory** items are programmatically required to be ticked
  before the stage advances.
- The state file persists on disk, so even after context compression
  or session restart the canon is re-read from the file rather than
  remembered.
- The gate-check stage refuses to spawn a stage subagent if any prior
  mandatory item is unticked or if the stage is backfilled without
  evidence.

## Where should new canon live?

When a retro recommends a new rule, ask:

1. **Does the rule fire on every PR, or only when specific files
   change?**
   - Every PR → pipeline-template canon (Stage 4 / Stage 7 mandatory
     checklist item).
   - Only when specific files change → pre-push hook (file-pattern
     guard) or CI workflow (path-filtered trigger).
2. **Is the rule about prose discipline or mechanical content?**
   - Prose / judgment ("write the retro per these guidelines") →
     pipeline-template `subagent_prompt` or CLAUDE.md.
   - Mechanical content ("no `f"..."` inside `logger.X(`") →
     pre-push hook (lint script).
3. **Is the rule a behaviour contract (something runtime-checkable)?**
   - Yes → CI workflow (run the actual check at PR time).
   - No → pipeline-template canon or CLAUDE.md.

If the answer is "any PR, prose discipline, not runtime-checkable" —
that's pipeline-template canon territory.

## Examples

| Rule | Venue chosen | Why |
|---|---|---|
| "Two-commit shape: impl+tests, then docs+CHANGELOG" | Pipeline-template canon (Stage 5 + Stage 9 mandatory items) | Fires on every PR. Mandatory tick stops the stage if the executor tries to mix docs into Stage 5. |
| "No `# noqa` without a justification comment" | Pre-push hook (`scripts/check-noqa-just.py`) | Mechanical text-pattern rule; runs only when `.py` changes. |
| "Daily audit: flag merged PRs missing retro markers" | CI workflow (`.github/workflows/retro-gate-audit.yml`) | Runs on a schedule, not on PR. Surfaces violations as workflow annotations. |
| "Bug-report triage: trust the symptom, not the cited path" | CLAUDE.md section | Judgment rule for the agent, not mechanically checkable. |

## See also

- [README.md](README.md) — pipeline-skill setup and skill reference
- [CLAUDE.md](CLAUDE.md) — architecture and design philosophy
- `templates/feature-state.json`, `templates/bugfix-state.json` —
  built-in default templates (project overrides at
  `.pipeline-templates/`).
