#!/usr/bin/env bash
# check-branch-literals.sh (#18) — guard against reintroduced hard-coded
# default-branch literals in skill execution paths or pipeline.py.
#
# The whole pipeline-* family resolves the default branch dynamically
# (pipeline-config default_branch -> origin/HEAD -> git remote show -> fallback).
# This check fails if a literal `main`/`master` sneaks back into an actual git
# COMMAND or a pipeline.py branch-naming literal. It deliberately ignores
# backtick-wrapped prose (docs may discuss `origin/main` as an anti-pattern) and
# the documented `BASE=...main` fallback assignment.
#
# Usage: bash scripts/check-branch-literals.sh   (or: make check)
set -uo pipefail
cd "$(dirname "$0")/.."

fail=0

# --- skills: literal git commands that should use "$BASE" ---
# Match real commands (push/pull/checkout/diff/rev-parse) against a literal
# main|master; exclude any line referencing $BASE (the parameterized form and
# the BASE=...main fallback both legitimately contain "main").
skill_hits=$(grep -rnE \
  'git (push|pull) origin (main|master)\b|git checkout (main|master)\b|checkout -B [^ ]+ origin/(main|master)\b|git (diff|rev-parse)[^`]*origin/(main|master)\b' \
  skills/*/SKILL.md 2>/dev/null | grep -v 'BASE' || true)
if [ -n "$skill_hits" ]; then
  echo "✗ Hard-coded default branch in skill command (use \"\$BASE\"):"
  echo "$skill_hits" | sed 's/^/    /'
  fail=1
fi

# --- pipeline.py: branch-naming literals (ternary fallback / origin string) ---
# Allows the last-resort `return "main"` in detect_default_branch and the
# user-overridable argparse `default="main"`; flags `else "main"` naming and
# any `"origin/main"` string literal.
py_hits=$(grep -nE 'else[[:space:]]+"(main|master)"|"origin/(main|master)"' pipeline.py 2>/dev/null || true)
if [ -n "$py_hits" ]; then
  echo "✗ Hard-coded branch literal in pipeline.py (resolve via detect_default_branch):"
  echo "$py_hits" | sed 's/^/    /'
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "✓ no reintroduced default-branch literals"
fi
exit $fail
