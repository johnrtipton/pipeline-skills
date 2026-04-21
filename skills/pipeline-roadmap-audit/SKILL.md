---
name: pipeline-roadmap-audit
description: >
  Verify every "not started" / "Not started" / non-✅ / non-~~strikethrough~~
  ROADMAP.md entry against the actual codebase. Catches stale entries where
  a feature has shipped but the ROADMAP still lists it as pending. Run before
  cutting a release candidate, before starting a milestone, or after any
  large-scale consolidation.
user_invocable: true
argument: >
  Optional: --milestone vX.Y.Z (limit audit to entries targeting this milestone).
  Optional: --dry-run (default — show audit report, do not edit ROADMAP).
  Optional: --apply (edit ROADMAP.md with strikethrough + shipped-in annotations).
  Optional: --summary-only (compact table; skip per-item evidence paragraphs).
---

# Pipeline Roadmap Audit — Verify Pending Items Against the Codebase

Stops a recurring failure mode: the ROADMAP claims feature X is "not started"
when X already ships (e.g., djust v0.5.1 had the theming-fold, WizardMixin,
error boundaries, and dj-lazy all listed as pending when the code was live).
Release notes built from the stale ROADMAP overstate what's left and understate
what's done — and a downstream operator can waste a week reimplementing
something that's already there.

## Why this is a distinct skill (not part of pipeline-next)

- **pipeline-next** picks the highest-priority pending task and sets up a
  state file. It trusts the ROADMAP as source of truth.
- **pipeline-drain** closes stale open GitHub *issues* by checking merged PRs.
- **pipeline-roadmap-audit** closes stale ROADMAP *entries* by checking the
  codebase directly. Complementary to pipeline-drain — same defect class, but
  in the roadmap text rather than the issue tracker.

Run this skill upstream of the others; pipeline-next is then working from a
truthful roadmap.

## Steps

### 1. Locate ROADMAP.md

Check `ROADMAP.md`, `docs/ROADMAP.md`, `docs/roadmap.md` in that order.

### 2. Parse roadmap entries that claim "not started"

An entry is a candidate for audit if it has NONE of these markers:
- `~~...~~` (markdown strikethrough)
- ✅
- "Shipped" / "SHIPPED"
- "Moved to" / "Split into" (explicit reparenting)

Parse from three structural locations:

1. **Priority Matrix** at the top of the file — table rows like
   `| **P2** | <feature name> | <description> | vX.Y.Z |`
2. **Milestone detail sections** — headings `### Milestone: vX.Y.Z — Title`
   followed by `**Feature Name**` bullet entries
3. **Parity tracker** — tables that include a "Not started" column value

Apply `--milestone` filter if supplied.

### 3. For each candidate, map to an expected codebase path

Use the roadmap entry's description to extract verification hooks:

| In the roadmap text | Verification hook |
|---|---|
| `` `ClassName` `` or `**ClassName**` | `grep -rn "class ClassName\b"` in source |
| `` `@decorator_name` `` | `grep -rn "^def decorator_name\b\|@decorator_name("` |
| `` `dj-attr-name` `` | `grep -rn "dj-attr-name" <js-source>` |
| `` `function_name()` `` | `grep -rn "^def function_name\|def function_name("` |
| `` `some.module.path` `` or "`filename.py`" | `ls <path>` |
| `` `{% template_tag %}` `` | `grep -rn "register.tag.*template_tag\|@register.(tag|simple_tag)" <templatetags>` |
| Management command name | `ls <app>/management/commands/<name>.py` |
| GitHub issue `(#NNN)` | `gh issue view NNN --json state` + `gh pr list --search "fixes #NNN OR closes #NNN"` |

Also scan `git log --all --oneline --grep="<primary keyword>" --since="6 months ago"`
for PRs that mention the feature by name — strong prior-art signal.

### 4. Classify each entry

- **SHIPPED** — file/symbol exists AND matches the roadmap-described API.
  Strong evidence: a PR title that directly names the feature.
- **PARTIAL** — file/symbol exists but the API is narrower or different than
  the roadmap describes. Example: djust's `dj-lazy` shipped as "lazy LiveView
  hydration" but the roadmap described "lazy component loading" — related
  but not identical. Keep a narrower entry, strike through the broader one.
- **NOT SHIPPED** — no matching file/symbol; roadmap is accurate.

**Do not trust a subagent's "shipped" classification without verification.**
Subagents have been observed to report features as shipped when the matching
symbol is for a completely different feature (e.g., "error overlay" matched
a WebSocket-connection error overlay, not the dev-mode Python-traceback
overlay the roadmap described). Spot-check by grepping the specific roadmap
API, not just the feature name.

### 5. Print the audit report

Format:

```
## ROADMAP Audit — <ROADMAP path>, <N> entries audited

### SHIPPED — should be struck through (N items)

1. <entry name> — PR #<N>, <file:line>
   Roadmap location: <priority matrix line / milestone section line>
   Evidence: <2-3 sentences>

### PARTIAL — scope mismatch (N items)

1. <entry name> — PR #<N>, <file:line>
   Shipped scope: <what's in the code>
   Roadmap scope: <what the entry claims>
   Recommendation: <strike broader | keep narrower | both>

### NOT SHIPPED — ROADMAP accurate (N items)

- <entry name>
- <entry name>
- ...

### Audit stats
Total entries audited: N
Shipped (stale roadmap): N
Partial (scope drift): N
Accurate (not shipped): N
```

### 6. Apply fixes (only if `--apply`)

For each SHIPPED entry:
- Replace the priority-matrix row with a strikethrough version that names
  the shipping PR:
  ```markdown
  | ~~**P2**~~ | ~~<feature>~~ ✅ Shipped in PR #NNN (`<path>`) | ~~<description>~~ | ~~vX.Y.Z~~ |
  ```
- Replace the milestone-section entry with a strikethrough-and-annotation
  form that preserves the original text for historical context.
- Update the parity-tracker "Not started" column to `✅ Shipped (PR #NNN)`.

For each PARTIAL entry:
- Add an inline note after the existing text explaining what shipped and
  what remains. Do not delete the original — leave a targeted description
  of the narrower unshipped portion.

Commit with a message like:

```
docs(roadmap): mark N items as shipped, M as partial

Audit caught N entries listed as pending but already shipped, and M where
the roadmap scope drifted from what actually landed.

Shipped:
- <feature> — PR #NNN (path)
- ...

Partial:
- <feature> — <scope note>
...
```

Commit to a new branch (not main) for review if `--branch` supplied; commit
to main directly if on main and the user previously acknowledged the audit
output.

### 7. Recommend follow-ups

- If 3+ items were stale, print:
  "Consider running `/pipeline-roadmap-audit` before every release candidate —
  the accumulated drift here suggests it's not currently part of the release
  flow."
- If a PARTIAL item's narrower scope is interesting, suggest adding a
  dedicated GitHub issue so it stays tracked.

## Anti-patterns to avoid

1. **Classifying as SHIPPED based on name match alone.** The roadmap may
   describe feature X; the codebase may have something ALSO named X that
   does something different. Grep the specific API (method names, attribute
   names, flag names) from the roadmap, not just the feature title.

2. **Automated --apply without human review.** The edits change the public
   narrative of what the framework has. Even if the dry-run looks correct,
   a second set of eyes should land the strikethrough commit.

3. **Skipping milestone-section detail entries.** The priority matrix row
   may be struck through while the milestone section still describes the
   item as unshipped (or vice versa). Audit all three structural locations
   (matrix, milestone, parity tracker) — they drift independently.

4. **Mistaking "planned but not scoped" for shipped.** Some roadmap entries
   reference items in ADRs that have implementation sketches but no code.
   Grep the ADR number (e.g., "ADR-008") and verify the corresponding PR
   actually merged, not just that the ADR document exists.

## When to run

- Before cutting an RC (run as `--dry-run`, review, then `--apply` if
  anything stale)
- At the start of a milestone (so pipeline-next works from a clean list)
- After any large consolidation (e.g., package-fold PRs can silently ship
  multiple unrelated features)
- After a milestone retrospective mentions "we thought we hadn't shipped X
  but actually..."
- On a cron (monthly?) for long-lived projects with heavy roadmaps

## Observed cost in the field

djust v0.5.1rc1 was cut with 4 ROADMAP items still listed as pending that had
already shipped (theming-fold PR #772, WizardMixin PR #632, Error boundaries
PR #773, dj-lazy hydration PR #54). The first-pass audit missed one (dj-lazy)
and falsely reported one as shipped (dj-transition) — confirming that
automated audits need spot-check verification. This skill formalizes the
verification loop.
