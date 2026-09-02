# ADR-0004: Separate the pattern wiki from the rule sheet, and gate rules on measured impact

**Status**: Accepted — skill-side changes (3, 4, 5 + CANON.md guidance) implemented in PR #81; consumer-side split (1, 2) is per-repo
**Date**: 2026-09-01
**Source**: WikiSkill — *Persistent Knowledge for Agent Skill Evolution* (arXiv 2608.27454), applied to the djust consumer repo at ~440 harness runs. Closes ROADMAP Future item #77 (canon-compaction guidance) and gives #68 (retro-bypass audit) a per-rule companion.

## Context

WikiSkill's claim is narrow and matches what the family's largest consumer
shows: knowledge from agent runs stays scattered across optimization
artifacts unless a persistent, *organized* wiki sits between the raw traces
and the skills. It separates three layers — immutable **raw** traces, a
**wiki** (pattern directory + evolution log + skill-impact tracker) that is
never rolled back, and **skills** that are gated on validation and can be
rolled back — and four roles: an inference agent that reads skills but not
the wiki, a wiki maintainer, a skill proposer that reads the wiki (including
rejected proposals), and a gate.

The pipeline family already runs three of the four roles. Measured on djust
on 2026-09-01:

| WikiSkill component | pipeline family / djust today | gap |
|---|---|---|
| raw traces | `pr/feedback/retro-N.md` (395 files), review threads, gate-off logs, `.pipeline-state/*.json` | scattered; the retro samples what its author remembers |
| wiki: pattern directory | consumer `CLAUDE.md` "Process canonicalizations from *X* retro arc" — 31 sections, 132 KB | organized by **date**, not failure class; parallel-path drift (#1646) is cited 15 times across ten sections with no instance table |
| wiki: evolution log | `RETRO.md` milestone sections, never rolled back | matches the paper |
| wiki: skill-impact tracker | Action Tracker (333 rows) | records *issues filed*, not whether a rule fired or was violated again |
| skills | `pipeline-*/SKILL.md` (4,851 lines), PR checklist, state templates, gates in `pipeline-run` | no `PURPOSE.md`; provenance is inline prose ("canonicalized from Action Tracker #180") |
| inference agent | `pipeline-run` implementer / reviewer subagents | receive the **whole** wiki via the session hook, not just the skill |
| wiki maintainer | `pipeline-retro` Stage 14 + milestone retro + `--reconcile` | exists, gated |
| skill proposer | retro "canonicalize" step | accept-only; no record of ineffective proposals |
| gating / rollback | none | rules only accumulate; **0 rules have ever been demoted** |

Two consequences. Every implementer subagent pays ~33k tokens for rules that
rarely apply to its task. And when a rule fails to stick — drift recurred
four times in one djust release cycle *after* its rule was written — nothing
flags it as a proposal that should be re-shaped into a mechanical gate. This
is the failure `CANON.md` names (the weakest venue accumulates the most)
without yet saying how to compact or graduate a section.

## Decision

Adopt WikiSkill's layer split and its gate, in five changes. Changes 1–2 are
consumer-side conventions the family documents in `CANON.md`; changes 3–5 are
edits to the skills themselves.

### 1. Split the consumer `CLAUDE.md` into a rule sheet and a pattern directory

`CLAUDE.md` keeps one line per rule plus a pointer. Case studies, instance
tables and rationale move to `docs/patterns/<class>.md`, one page per
failure class, with a fixed template so the planner and the retro can grep
it:

```
# <Class name>

**Rule** (the line CLAUDE.md carries): ...
**Status**: skill | wiki-only · gate: none | <script/test/checklist row> · candidate for mechanical gate?

## Instances
| PR | what drifted / what was missed | cure | rule in force? |

## Detection
What a reviewer or test can look for. Structural pins that exist.

## Rejected shapes
Fixes tried for this class that did not hold, with the PR.
```

`docs/patterns/README.md` is the index: class, one-line rule, status, gate.
Target for the consumer rule sheet: under 30 KB.

### 2. Extend the Action Tracker into a skill-impact tracker

Rows that introduced a canon rule or a gate gain three columns:

- **pattern** — the `docs/patterns/` page the rule serves.
- **fired** — PRs where the retro says the rule caught something.
- **re-violated** — PRs where the class recurred with the rule in force.

A rule with several re-violated entries and few fired entries is the paper's
*rejected proposal*. `pipeline-retro` Stage 4 (which already touches every
row) maintains the two count columns.

### 3. Add a gating stage to `pipeline-retro`

New **Stage 3.7 — Gate the rule sheet**, between Synthesis and the Action
Tracker update, run for every rule in force for at least two milestones:

```
1. From docs/patterns/<class>.md count instances marked
   "rule in force = yes, missed" in this milestone and the prior one.
2. Count "fired" entries over the same window.
3. Decide, and record the decision in the tracker row:
   KEEP     fired > 0 and missed trending down
   HARDEN   missed >= 2 with the rule in force: prose did not work; file
            a proposal for a mechanical gate (test, grep, script,
            checklist row), citing the pattern page
   DEMOTE   fired = 0 and missed = 0 for two milestones: move the rule
            out of CLAUDE.md to the pattern page only. The page stays;
            the wiki is never rolled back.
4. A rule may be demoted once; a second demotion deletes it from the
   rule sheet with the pattern page kept as history.
```

Prerequisite: the `pipeline-run` Stage 11 reviewer prompt requires every
🔴/🟡 finding to name its pattern class, or `new`. The per-PR retro lists
findings with their class; the milestone Review Stats section becomes the
validation data.

### 4. Asymmetric access in subagent briefs

- Stage 4 plan gains a required row, **patterns in play**, listing the
  pages the task touches (the planner's existing "how do other features do
  X" grep *is* the proposer consulting the wiki).
- Implementer briefs include those pages inline and nothing else from
  `docs/patterns/`.
- Reviewer briefs include the same pages plus the Detection section of
  every page marked *candidate for mechanical gate*.
- The session hook keeps loading `CLAUDE.md`, which after change 1 is the
  rule sheet alone.

The paper measured a 2.8-point drop when its inference agent could read the
wiki. Its setting is a benchmark with repeated rollouts, so that figure is
directional; the reason to adopt the restriction here is context cost and
brief focus.

### 5. `PURPOSE.md` per pipeline skill

One table per skill mapping each mandatory gate, checklist row or stage rule
to the pattern page and origin PR that motivated it:

```
| gate / rule                       | pattern                        | origin        |
|-----------------------------------|--------------------------------|---------------|
| Gate 4 retro-artifact             | retro-dropout                  | #8            |
| post-commit hash verification     | swallowed-commit               | #122, #1524   |
| branch-name state-file check      | wrong-branch-commit            | #169 / #1144  |
| two-commit shape (impl / docs)    | changelog-cross-contamination  | #181 / #1173  |
| stale-base check before Stage 11  | stale-base-review              | #250 / #1450  |
```

Most of this provenance exists as inline comments. Extracting it makes the
impact tracker computable across the skill boundary and exposes gates with
no living pattern behind them.

## Rollout

| phase | what | where |
|---|---|---|
| 1 · split | extract the consumer's 31 canonicalization sections into class pages with instance tables; reduce `CLAUDE.md` to rules + pointers; no skill behaviour change | one docs PR in the consumer; `CANON.md` gains the compaction guidance (#77) |
| 2 · tag and track | Stage 11 findings carry a class; tracker rows gain pattern / fired / re-violated; Stage 4 plan gains "patterns in play"; briefs narrow to named pages | `pipeline-run`, `pipeline-retro`, `pipeline-shared` |
| 3 · gate | Stage 3.7 lands once two milestones of tagged findings exist; first run is **dry** (prints KEEP / HARDEN / DEMOTE without applying) | `pipeline-retro`; `PURPOSE.md` files land alongside |

## What we deliberately do not take from the paper

- **Strict improve-or-reject gating.** The paper rejects any proposal that
  does not improve validation accuracy. Our signal is milestone-granular
  and noisy, so the gate is a demotion rule with a two-milestone window.
- **An automated maintainer sampling raw traces.** Per-PR retros are
  written by the agent that did the work, with the retro-artifact gate
  enforcing existence. The missing piece is structured output, which the
  page template supplies.
- **Skill retrieval.** The paper injects full skills and says so. So does
  the session hook; change 1 is what keeps that affordable.

## Consequences

- The consumer's per-subagent context drops from ~33k to under ~8k tokens
  of canon, and the planner is the one role that reads the full wiki.
- Rules acquire a lifecycle (skill → hardened gate, or skill → wiki-only)
  instead of accumulating forever; #77 gets a concrete mechanism rather
  than advice.
- The family gains its second *measurement* of its own promise, after the
  retro-bypass audit (#68): not "did the stage run" but "did the rule the
  stage produced change anything."
- Cost: one mechanical docs PR per consumer, three skill edits, and a
  classification burden on the Stage 11 reviewer (one word per finding).

## Open questions

1. Does `docs/patterns/` live in the consumer repo or in the tiered
   learning directory under `~/.local/share/claude-projects/`? The repo is
   greppable by worktree subagents and versioned with the code; the
   learning directory already has `/promote`. Recommendation: repo, with
   `/promote` pointed at it.
2. Do downstream consumers of a framework (djust.org, djustlive) get their
   own pattern pages or cite the framework's? Several classes are already
   cross-project in the workspace-tier `learnings.md`.
3. Who classifies a finding the reviewer marks `new`? Proposed: the retro
   author at Stage 14, creating the page stub if none fits.
