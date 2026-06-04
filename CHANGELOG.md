# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- `docs/adoption.md` — clone-to-first-PR adoption guide for using the family in
  an external repo, linked from the README (v0.5.0 outward pivot).
- `docs/releasing.md` — release process; cut the first four tags (`v0.1.0`–`v0.4.0`)
  retroactively at each milestone's retrospective commit (v0.5.0 outward pivot).

### Fixed
- Worktree-restore reflex now also removes untracked files a subagent leaves
  (`git clean -fd`, preserving `.gitignore`'d files) and re-verifies the tree is
  clean — closes the tracked-files-only gap in the #36 fix (#40).
- `check-branch-literals.sh` no longer false-positives on backtick-wrapped prose
  mentions of `git diff origin/main` etc.: it strips inline-code spans before
  matching, so doc examples are ignored while real fenced-block commands are
  still caught (#29).
- Review subagents no longer leave the executor's working tree on the base
  branch: the Code Review `subagent_prompt` in all four templates now restores
  HEAD on exit, and pipeline-run gains a worktree-restore reflex before any
  build/scp/ship that follows a subagent (#36).

### Added
- `scripts/pipeline-gates.sh` — the pipeline quality gates as executable
  functions (Gate 1-4 + pipeline-ship pre-merge), per ADR-0001 (#28).
- `scripts/validate-templates.sh` + `make validate-templates` — validates every
  state-file template parses and has the required stage shape (numeric,
  strictly-ascending keys; name/status/verdict/checklist per stage). Wired into
  `make check`.
- `.github/workflows/ci.yml` — CI runs `make check` (branch-literal guard +
  template validator), shell-script syntax checks, and a pipeline.py parse on
  every PR and push, enforcing the gates automatically (ADR-0001). Completes
  v0.3.0 "Executable gates + CI".

## [v0.1.0]

### Added
- Vendored, hardened `pipeline-init` skill — one-time repo bootstrap (PR #10).
- Stage-5 "enumerated-unit inventories" documentation gate in `pipeline-shared`
  and all four state templates (PR #15).
- Pipeline-config block, ROADMAP, RETRO, and CHANGELOG scaffolding for this repo
  (self-init).

### Changed
- Made the entire `pipeline-*` skill family branch-agnostic — no hard-coded
  `origin/main` / `master` in any execution path (PR #10).
- Documented `/pipeline-init` across README, CLAUDE.md, and install.sh
  (PRs #12, #13, #14).
