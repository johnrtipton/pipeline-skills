# Pipeline Cycle — Self-Driving the Plan→Execute→Close Loop

The other pipeline skills each own one phase: `/pipeline-strategy` plans,
`/pipeline-next` picks, `/pipeline-run` executes, `/pipeline-retro` closes. For
six milestones a human chained them by hand — `strategy → run → retro →
strategy` — about twenty invocations. `/pipeline-cycle` is the missing **outer
loop**: it drives that cadence to a clean terminal state, pausing only where
human judgment changes the outcome.

**The state file is the program. The model is the executor.** Same pattern as
`/pipeline-run`, one level up: each loop iteration is a milestone arc, recorded
in `.pipeline-state/cycle-<YYYY-MM-DD>-<slug>.json`.

## The autonomy boundary (ADR-0003 — read this first)

The loop has two phases with very different judgment needs:

- **Execution** (`next → run --all → retro` for a *planned* milestone) is safely
  autonomous — `--all` already runs it with subagent review + programmatic gates.
- **The strategy decision** (`/pipeline-strategy` Stage 7, choosing among ≥2
  distinct paths) is where human judgment is load-bearing. The v0.4.0→v0.5.0
  outward pivot — which found a real bug — came from a human choosing a path the
  recommendation would have continued past.

So, **by default, `/pipeline-cycle` is semi-autonomous**: it runs execution
hands-off and **STOPS at every strategy Stage-7 decision** (and on any failure),
handing control back to you. Full hands-off autonomy is available **only behind
the explicit `--auto` flag** (see below). This is not a limitation to engineer
away — it is the design.

## Usage

```
/pipeline-cycle                       # semi-autonomous: drive the loop, pause at strategy decisions
/pipeline-cycle --auto                # full autonomy: auto-confirm the strategy recommendation, run to terminal
/pipeline-cycle --dry-run             # print the loop plan + current terminal-state check; execute nothing
/pipeline-cycle --resume              # resume an interrupted cycle from its state file
/pipeline-cycle --max-iterations N    # safety cap on milestone arcs (default 5)
```

## The loop

```
1. Terminal-state check — `make terminal-state` (or scripts/terminal-state.sh).
   If CLEAN (0 open issues, 0 active ROADMAP tasks, no Proposed ADR, CI green)
   → the work is done. STOP, print the cycle summary.

2. Are there active ROADMAP tasks for an open milestone?
   - YES → skip to step 4 (execute the already-planned milestone).
   - NO  → step 3 (plan one).

3. PLAN — run /pipeline-strategy (deep).
   - It surveys → brainstorms → triages → clusters → presents ≥2 paths →
     recommends → **Stage 7 DECISION**.
   - DEFAULT (semi-autonomous): STOP here. Surface the paths + recommendation to
     the user and hand off. The cycle resumes (`/pipeline-cycle --resume`) once
     the user has decided and strategy has captured the chosen path into ROADMAP.
   - `--auto`: do NOT stop. Let strategy run in light/auto-confirm mode — it
     adopts its own recommended path and captures it. Record
     `auto_confirmed: true` for that iteration in the state file.
   - If strategy's brainstorm yields no pass-tagged candidates → nothing worth
     doing → STOP (terminal by exhaustion).

4. EXECUTE — run /pipeline-run --milestone <v> --all.
   - Runs every task in the milestone through all stages to merged PRs, fully
     autonomously (this is already --all's contract). Each task's Code Review,
     Merge, and Retrospective gates apply unchanged.
   - On any stage FAILURE → STOP the cycle (do not advance). Report the failure;
     the user fixes and re-runs `/pipeline-cycle --resume`.

5. CLOSE — run /pipeline-retro --milestone <v>.
   - Synthesizes the milestone, updates the Action Tracker, files deferred issues.

6. Reconcile the ROADMAP (mark the milestone Completed), increment the iteration
   counter, and GO TO step 1.
```

Each iteration re-reads the sub-skills fresh (it does not remember them from a
prior iteration), exactly as `/pipeline-run` re-reads the state file each loop —
that is what keeps the cadence immune to instruction rot across a long session.

## How an orchestrator "calls" the other skills

In a single Claude Code session there is no subprocess: invoking
`/pipeline-strategy`, `/pipeline-next`, `/pipeline-run`, `/pipeline-retro` means
the executor **re-reads that skill and follows its instructions in sequence**,
then returns here. `/pipeline-cycle` is therefore a thin driver loop — it owns
the *ordering, the stop-contract, and the terminal check*, and delegates all
real work to the existing skills. It mirrors how `/pipeline-run --all-milestones`
already chains milestones, except it also **plans (strategy) and closes (retro)**
between them, which `--all-milestones` does not.

## Stop conditions (the whole contract)

The cycle halts and returns to the human on exactly these:

| Condition | Default | `--auto` |
|-----------|---------|----------|
| Terminal state clean | STOP (done) | STOP (done) |
| Strategy finds no candidates | STOP (done) | STOP (done) |
| **Strategy Stage-7 path decision** | **STOP (hand off)** | auto-confirm, continue |
| Any stage FAILED | STOP (report) | STOP (report) |
| `--max-iterations` reached | STOP (cap) | STOP (cap) |

Nothing else pauses it — within a planned milestone it runs straight through.

## State file

`.pipeline-state/cycle-<YYYY-MM-DD>-<slug>.json`:

```json
{
  "pipeline_type": "cycle",
  "mode": "semi | auto",
  "max_iterations": 5,
  "started_at": "...",
  "completed_at": null,
  "iterations": [
    {"n": 1, "milestone": "v0.7.0", "auto_confirmed": false,
     "strategy": "DECIDE_DONE", "run": "MILESTONE_COMPLETE", "retro": "RETRO_COMPLETE"}
  ],
  "terminal": "not-clean | clean",
  "stopped_reason": "strategy-decision | failure | clean | no-candidates | max-iterations | null"
}
```

## Completion

When the loop stops, print:

```
═══════════════════════════════════════════
  Cycle Complete — stopped: <reason>
  Iterations: <N>  (milestones: <list>)
  Mode: semi | auto
  Terminal state: clean | not-clean (<which condition failed>)
═══════════════════════════════════════════
```

If `stopped_reason == "strategy-decision"`, the cycle is *paused, not done* —
remind the user to decide and run `/pipeline-cycle --resume`.

## Anti-patterns

- **Auto-confirming strategy without `--auto`.** The default MUST pause at the
  path decision. Silently adopting the recommendation is the exact failure
  ADR-0003 exists to prevent.
- **Skipping retro between milestones** (the `--all-milestones` gap). The cycle
  closes every milestone before planning the next, so the Action Tracker and
  ROADMAP stay truthful for the next strategy survey.
- **Running mid-feature.** Like `/pipeline-strategy`, never start a cycle with an
  in-progress un-retroed feature — finish it first.
- **No silent cap bypass.** `--max-iterations` is a real backstop; log when it
  trips, don't quietly raise it.

## Composing

```
/pipeline-cycle              # drives strategy→run→retro→… ; pauses at each strategy decision
# ...you decide a path, strategy captures it...
/pipeline-cycle --resume     # continues: executes that milestone, closes it, plans the next
# ... until terminal-state clean → done
```

`/pipeline-cycle --auto` collapses that to a single hands-off invocation — use it
only when the backlog is unambiguous and no directional fork is live.
