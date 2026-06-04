# Foreign-repo validation — 2026-06-04

First outward validation (v0.5.0, ADR-0002): run the pipeline family's detection
and parser logic against a repository deliberately unlike pipeline-skill itself,
and record every assumption-gap. **The deliverable is this report + filed issues,
not a green checkmark.**

## Method

Built a throwaway foreign repo under `scratch/foreign-repo/` chosen to violate
this repo's defaults:

| Dimension | pipeline-skill | foreign repo |
|-----------|----------------|--------------|
| default branch | `main` | **`master`** |
| language/stack | Python (stdlib) | **Node/JS** (`package.json`: jest/eslint/webpack) |
| build | none | Makefile + npm scripts |
| version scheme | none (0 tags) | `package.json` version `2.3.1` |
| ROADMAP | conforming priority-matrix | **checkbox format** (`### N. Title \`[x]\``) |

Ran the real functions (`pipeline.py`) and the documented detection chains
against it.

## Findings

| # | Check | Result | Verdict |
|---|-------|--------|---------|
| 1 | `detect_default_branch` | returned **`main`** for a `master` repo with no `origin/HEAD` | 🔴 **BUG → issue #45** |
| 2 | `detect_default_branch` (with `origin/HEAD=master` set) | returned `master` | ✅ correct |
| 3 | `detect_profile` | `generic` (not django) | ✅ correct |
| 4 | `parse_roadmap` on checkbox ROADMAP | 0 tasks (non-conforming) | ✅ expected — this is the FOREIGN case `pipeline-init` migrates |

**Finding #1 (🔴)** — `pipeline.py detect_default_branch` lacks the local-branch
probe and current-branch fallback that the **pipeline-init SKILL's own** chain
documents (probes 4–5). On a `master`-default repo with no `origin` remote / unset
`origin/HEAD` (common on fresh clones), it silently returns `main`. The whole
branch-agnostic effort (v0.1.0–v0.2.0) is undermined at the harness entry point
for exactly the non-`main` repos it was meant to support. Filed as **issue #45**.

This is the outward-pivot thesis confirmed on the first try: external use surfaced
a branch-agnosticism gap four inward milestones never hit, because dogfooding only
ever ran on this `main`-default repo with an origin.

## Not tested (validation scope)

The PR-dependent stages (Commit & PR, Code Review, Merge, Retrospective) need a
real GitHub remote and were **not** exercised here — a local scratch repo has no
`origin` on GitHub, so those stages would `PR_SKIPPED`. This validation covers the
**detection + parser layer**, which is where the foreign-repo assumptions
concentrate. A fuller validation (a real throwaway GitHub repo run end-to-end) is
a future v0.6.0 candidate.

## Outcome

1 real bug filed (#45); 3 behaviors confirmed correct. The adoption quickstart
(next v0.5.0 task) should call out the `default_branch` pipeline-config line as
the reliable override until #45 lands. Tracks the validate-on-foreign-repo task
(PR #46).
