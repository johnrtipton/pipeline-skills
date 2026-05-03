---
name: pipeline-strategy
description: >
  Run a strategy session — the planning equivalent of /pipeline-run. Surveys
  the project state, brainstorms candidate features from pluggable sources,
  triages them, clusters into possible milestones, presents >= 2 distinct
  paths forward, recommends one, captures the chosen path back into ROADMAP
  and (if directional) a new ADR. State-file-as-program pattern: each stage
  is gated by a mandatory checklist on disk, same as /pipeline-run.
user_invocable: true
argument: >
  Optional: --light (cheap post-retro check; runs only stages 1+2+5-or-shortcut).
  Optional: --deep (full 8-stage pipeline; default at milestone boundaries).
  Optional: --slug <name> (used in state filename and session markdown; e.g., "v3-p0-end").
  Optional: --resume (continue an existing strategy session from disk).
---

# Pipeline Strategy — State-File-Driven Planning Sessions

Pipeline-skill's other skills assume a plan exists. `/pipeline-next` reads
ROADMAP.md, picks an entry, executes it. That works while the plan is
truthful. But planning itself — *should the next ROADMAP item change?
are there competing paths to consider? does this need a new ADR?* — is
left to ad-hoc conversation, where the same drift modes that motivated
the execution-side state file (attention dilution, summarization loss,
rationalization drift, plausible-sounding shortcuts) silently take over.

This skill closes that loop. A strategy session is itself a multi-stage
pipeline. The state file is the program; the model is the executor;
each stage has a mandatory checklist that must be ticked off from disk
before advancing.

## When to run

- **Deep mode** (default) at milestone boundaries — end of a release,
  before starting the next. Or on demand when "what's next?" feels
  unsettled.
- **Light mode** automatically after every `/pipeline-retro`. Asks one
  question: *does anything in this commit's retro suggest the next
  ROADMAP item should change?* Default answer: no. If yes, escalate
  to deep mode.
- **Never** during execution of an in-progress feature — finish the
  feature, retro it, then strategize. Strategy sessions during
  execution produce thrash.

## Why this is a distinct skill (not part of pipeline-next)

- `/pipeline-next` picks the next pending task from a trusted ROADMAP.
  It does not decide *whether the ROADMAP itself is right.*
- `/pipeline-roadmap-audit` checks ROADMAP entries against shipped code.
  It does not generate new candidate work or compare paths.
- `/pipeline-retro` looks backward at a finished milestone. It does not
  forward-plan the next one.
- `/pipeline-strategy` sits between retro and next: takes the closing
  state of one milestone and produces a concrete chosen path for the
  next one, with the alternatives recorded in case a future retro
  needs to revisit the choice.

## Hard rule: >= 2 distinct paths

Stage 5 (Present-Paths) must produce at least two distinct paths before
advancing. "Distinct" means different *scope, ordering, or risk profile* —
not "fast version" vs. "slow version" of the same plan. This is the
strategic-comparison equivalent of `/pipeline-run`'s mandatory-checklist
gate: it forces the model to actually compare options instead of locking
onto the first plausible one.

If only one path is genuinely viable (e.g., a critical bug forces a
specific fix), record `short_circuit_reason` in the state file and
proceed. The short-circuit itself is a captured decision, not a glossed
shortcut.

## Steps

### 1. Locate or create the state file

State files live in `.pipeline-state/strategy-<YYYY-MM-DD>-<slug>.json`,
where `<slug>` is provided via `--slug` or derived from the trigger
context (e.g., `v3-p0-end`, `post-retro-check`).

If `--resume` and a strategy state file exists, load it and jump to
the first pending stage. Otherwise, copy `templates/strategy-state.json`
to `.pipeline-state/strategy-<date>-<slug>.json` and fill in
`task_description`, `branch_name` (use the slug; no actual branch is
created), `project_path`, `started_at`, `trigger`, and `mode`.

### 2. Execute stages 1 → 8 in order

Each stage is identical in structure to a `/pipeline-run` stage:

1. Read the stage's `checklist` from the state file (fresh from disk).
2. Perform each checklist action, in order.
3. Mark each `done: true` after completing it.
4. After all mandatory items are done, set `verdict` per the stage's
   exit criterion and `status: "passed"`.
5. Advance `current_stage`.

The `pipeline-shared` skill's stage-execution conventions apply:
mandatory items are non-skippable; verdict strings are required output
markers; failure halts the session for `--resume`.

### 3. Stage-specific guidance

#### Stage 1 — Survey

Read-only collection. The output is a one-paragraph "where we are"
summary stored in `output.summary`. Pull from:

- ROADMAP.md (current/next milestone status)
- last 3 retro entries (look for "deferred to vN+1", "blocked on", "regression caught")
- project insights file (if the project uses a tiered learning system)
- decisions.md / docs/adr/ — note which ADRs are still load-bearing
- failing tests / failing static checks / bench regressions (project-specific commands)
- open GitHub issues, especially stale-PR signals on dependencies
- user-feedback memory entries (scope/style constraints to honor)

If a category isn't applicable to this project, note "(no source)" and
move on. The survey establishes what's actually in front of you, not
what should hypothetically exist.

#### Stage 2 — Brainstorm

Generate >= 6 candidates from the pluggable sources below. Each
candidate gets `{title, source, description (one line), est_effort}`.
Fewer than 6 means a survey miss — go back to stage 1 and look harder.

Default sources (project may add or override):

| Source | What it produces |
|---|---|
| `roadmap-pending` | Open ROADMAP entries not yet started (the obvious next-things) |
| `retro-deferred` | "Deferred to vN+1" entries from recent retros (the explicitly-postponed things) |
| `insights-near-threshold` | Insights at reinforcement count >= 2 (one more re-discovery from promotion) |
| `bench-regressions` | Ops with `regressed` verdict in any bench-comparison output (perf-driven) |
| `doctor-failures` | Any failing project doctor / static check (correctness-driven) |
| `github-stale-prs` | Open PRs older than N days on dependent repos (unblock-driven) |
| `external-pivot-signal` | User-supplied: "X just released vN — what does that unblock?" |

Projects can register additional sources by dropping a Python entry-point
or a shell hook in `.pipeline/strategy-sources/<name>.sh` that prints
candidates as JSON lines.

#### Stage 3 — Triage

Score each candidate. If the project defines a **user-visible-value
test** (e.g., master_control's ADR-0001 three tests), use it. Otherwise
score on signal/effort and dependency order.

Tag each candidate one of: `pass` | `borderline` | `fails-uvv` |
`cleanup` | `pre-req`. Note any active ADR commitment that constrains a
tag (e.g., "ADR-0001 says we don't pursue tool-internal features").

#### Stage 4 — Cluster

Group related triaged candidates into 2-5 coherent themes. Each cluster
becomes a candidate-milestone with total effort and a signal/effort
score. Cleanup-tagged candidates often cluster separately so they can
ship as a parallel hygiene PR rather than blocking the headline work.

#### Stage 5 — Present-Paths

Construct >= 2 paths. Each path = an ordered selection of clusters. To
count as distinct, paths must differ in *ordered milestones, scope, or
risk profile* — not just "fast" vs "slow."

Common path archetypes:

- **Continue-as-planned**: pre-reqs + the cluster that matches the
  current ROADMAP plan.
- **Pivot**: a cluster that overrides an active ADR or roadmap
  commitment, producing a directional change.
- **Cleanup-first**: hygiene clusters before forward work; usually a
  weak path under outward-pivot ADRs but worth presenting for
  comparison.
- **Pre-req sequencing**: cluster-of-blockers before the headline
  cluster.

Each path records: `name`, `included_clusters`, `total_effort`,
`signal_per_effort`, `risks`, `dependencies`.

If only one path is genuinely viable, set `short_circuit_reason` and
proceed. The short-circuit is logged.

#### Stage 6 — Recommend

Pick one path as the default. Write the reasoning (>= 3 sentences) into
`output.reasoning`, naming which active ADRs / constraints support or
oppose the choice. The recommendation is the **default** — not an
order. Output `RECOMMEND_READY`.

#### Stage 7 — Decide

In **deep mode**: surface the recommendation + alternatives to the user.
User confirms or picks an alternative. If `chosen != recommended`,
capture the user's reasoning briefly.

In **light mode** with an unambiguous recommendation (e.g., "continue
v3.1.0 as planned, no escalation needed"), the model may default-confirm.
Any other case escalates to deep mode.

**Detect directional change**: if the chosen path's cluster includes a
candidate tagged as overriding an active ADR commitment, set
`output.directional_change = true` and flag the cluster slug for stage
8's ADR-draft step.

Output `DECIDE_DONE`.

#### Stage 8 — Capture

This is where the strategy session writes back to the project. The
state file is the source of truth; these artifacts are derived.

1. **Update ROADMAP.md** — add or modify the priority-matrix rows for
   the chosen path. Use a strikethrough + replacement form if a row is
   being deprioritized so history is preserved.
2. **If `directional_change`**: draft a new ADR under `docs/adr/`
   numbered N+1 of the highest existing ADR. Status: Proposed. Include
   Context (why was this needed?), Decision (the chosen path's
   override), and Consequences (what changes / what risks).
3. **Append to retros.md** (or `RETRO.md` or `.pipeline-log.md`,
   whichever the project uses): a forward-link from the most recent
   arc retro to this strategy session.
4. **Render `docs/strategy-sessions/<YYYY-MM-DD>-<slug>.md`** — the
   human-readable summary. Include all alternatives considered, the
   recommendation, and the decision. The state file is for the model;
   the markdown is for humans.
5. **Kick off `/pipeline-next`** for the first execution task in the
   chosen path. The strategy session ends; execution begins.

Output `CAPTURE_DONE`.

## State-file shape

The full template is at `templates/strategy-state.json`. Top-level
fields mirror the other pipeline templates (`pipeline_type`,
`task_description`, `branch_name`, `project_path`, etc.) plus three
strategy-specific fields:

- `trigger`: `milestone-boundary | on-demand | post-retro-escalation`
- `mode`: `light | deep`
- `context_summary`: a one-paragraph "what just shipped, what's queued,
  what triggered this session" written at session start.

Each stage has a `checklist` (with `mandatory` items) plus an `output`
object with stage-specific keys. The output object is *the artifact*
of that stage — it persists alongside the checklist so later stages
read structured input rather than parsing prose.

## Anti-patterns to avoid

1. **Path-presentation theater.** Producing 2 paths that aren't really
   distinct (e.g., "ship v3.1.0 in 1 week" vs "ship v3.1.0 in 2 weeks")
   satisfies the rule mechanically and defeats its purpose. Distinct
   means *different scope, ordering, or risk profile.*

2. **Survey laziness.** Stage 1 must read real artifacts. A survey
   that just paraphrases ROADMAP.md misses the retros, insights, bench
   data, and feedback memory that often contain the signal that
   reshapes the plan.

3. **Silent ADR drift.** If the chosen path overrides an existing ADR
   and stage 8 doesn't draft a new ADR, the override is invisible to
   future strategy sessions. The directional-change detector is
   load-bearing.

4. **Default-confirm in deep mode.** Light mode may default-confirm
   when the recommendation is unambiguous. Deep mode at a milestone
   boundary always surfaces the alternatives and waits for user input.
   The whole point of deep mode is the human-in-the-loop comparison.

5. **Strategy during execution.** Running this skill mid-feature
   produces thrash because the in-progress work hasn't been retroed
   yet. Finish the feature, retro it, then strategize.

## Cost in the field

The pattern this skill formalizes was practiced manually during
master_control's v2.7.0 → v2.19.0 arc. 13 ROADMAP versions shipped clean
because the user kept the planning loop tight: each turn was scoped,
each retro was written, each ADR captured at the moment of decision.
That took active effort.

The arc-ending question — *"how is this useful?"* — surfaced that the
project had drifted inward. The honest answer required a directional
ADR (master_control's ADR-0001, "outward pivot"). That ADR was easy to
write because the planning loop had been disciplined. Without that
discipline — i.e., for projects where the planning loop is ad-hoc — the
inward drift would have been invisible until much later.

This skill ports that discipline to any project using pipeline-skill.

## Composing with the other pipeline skills

```
END OF MILESTONE:
  /pipeline-retro --milestone v3.0.0          # close out the arc
  /pipeline-strategy --light                   # auto-fired after retro: anything to escalate?
  # (if escalated:)
  /pipeline-strategy --deep --slug v3-p0-end   # full 8-stage planning session
  /pipeline-next --milestone v3.1.0            # execution begins on chosen path
  /pipeline-run                                # the rest is execution as usual
```

A clean handoff: retro looks backward, strategy looks forward, next
picks the work, run executes. Each skill stays focused; the state files
are the contracts between them.
