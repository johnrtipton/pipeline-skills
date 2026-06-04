# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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
