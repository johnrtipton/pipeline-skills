# Releasing

How this repo versions and tags. Established in v0.5.0 (the outward pivot,
ADR-0002) — for four milestones the repo shipped with 0 tags, so nothing was
consumable at a known version.

## Scheme

- **SemVer-ish `vX.Y.Z`**, one minor version per milestone (`v0.1.0`, `v0.2.0`, …).
  Pre-1.0, a milestone is a minor bump; patch (`Z`) is reserved for hotfixes to a
  released milestone.
- A milestone is **released when its retrospective merges** — that is the
  canonical "milestone closed" marker (after `/pipeline-retro` updates the Action
  Tracker and the ROADMAP reconciliation has moved it to `## Completed`).

## Cutting a release

At milestone close, after the retro PR merges to the default branch:

```bash
git checkout main && git pull
# tag the retro (milestone-closed) commit:
git tag -a vX.Y.Z -m "vX.Y.Z — <milestone title>"
git push origin vX.Y.Z
```

Optionally publish a GitHub release from the tag with the CHANGELOG section:

```bash
gh release create vX.Y.Z --title "vX.Y.Z — <title>" --notes-from-tag
```

The CHANGELOG `## [Unreleased]` section's entries for the milestone move under a
`## [vX.Y.Z]` heading at release time.

## Released versions

Tagged retroactively in v0.5.0 at each milestone's retrospective commit:

| Tag | Milestone | Retro commit |
|-----|-----------|--------------|
| `v0.1.0` | Branch-agnostic family + self-bootstrap | `cc66204` (#19) |
| `v0.2.0` | Pipeline hardening | `b528822` (#30) |
| `v0.3.0` | Executable gates + CI | `4e4f7d9` (#37) |
| `v0.4.0` | Drift guards | `768ea56` (#43) |

`v0.5.0` (Outward pivot) will be tagged when its retrospective merges.
