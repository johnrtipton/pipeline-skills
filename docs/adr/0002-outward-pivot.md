# ADR-0002: Outward pivot — prove and package the family, not just harden it

**Status**: Accepted — in force since v0.5.0 (PRs #46–#49); continued in v0.6.0
**Date**: 2026-06-04
**Source**: Strategy session [2026-06-04-v0-4-end](../strategy-sessions/2026-06-04-v0-4-end.md) (Path 2)

## Context

Four consecutive milestones (v0.1.0–v0.4.0) were entirely inward: branch-agnostic
refactor, pipeline hardening, executable gates + CI, drift guards. They produced
strong internal machinery — but the strategy skill's own "cost in the field"
section names this exact pattern as the inward-drift trap, and the
"how is this useful?" question is now due.

Three concrete signals say the marginal value has shifted from hardening to
reach:

1. **Asymmetric bug signal.** The single externally-sourced bug (#36, from the
   djustlive project) was higher-impact than anything dogfooding surfaced —
   external use exercises paths self-use never does. More inward drift-guards
   have declining marginal value; outward validation has rising value.
2. **Nothing is consumable.** 0 git tags after 4 milestones; `install.sh` is a
   manual symlink; there is no adoption guide. The family works for its author
   and nobody else has a supported path in.
3. **A claimed-but-absent artifact.** CLAUDE.md says the project is "also
   published as a flexion plugin," but that copy is not in the repo — the
   outward story is asserted, not real.

## Decision

For v0.5.0 the project pivots from *hardening the machinery* to *proving and
packaging it for real external consumers*:

- **Validate on a foreign repo** — run the full `init → next → run → retro` loop
  on a repository that is not this one (ideally `master`-default and/or
  non-python) and file every assumption-gap as an issue. The deliverable is a
  report + issues, not a green checkmark.
- **Adoption quickstart** — a clone-to-first-PR guide an external user can follow
  without reading skill internals.
- **Release process + first tags** — version and tag the shipped milestones so
  the family is consumable at a known version.

Inward drift-guard work (SKILL self-test harness, flexion sync) is deferred until
a real external consumer's drift makes it matter. ADR-0001 (executable gates)
remains in force — this pivot is about reach, not relaxing quality.

## Consequences

- **Gains**: the strong internal machinery becomes adoptable; external validation
  will surface real assumption-gaps (the point); a versioned release exists.
- **Costs**: foreign-repo validation has unknowns and may spawn a backlog of
  gap-fix issues; writing/maintaining adoption docs is ongoing.
- **Risk**: discovering the family is more pipeline-skill-specific than believed.
  That is information worth having — better surfaced by a deliberate validation
  than by the next external user hitting it cold (as djustlive did with #36).
- **Reversible**: if foreign-repo validation shows the family isn't ready for
  outward use, a future ADR can re-prioritize inward fixes — but the gaps will
  be documented either way.
